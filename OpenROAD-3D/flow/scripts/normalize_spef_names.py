#!/usr/bin/env python3
"""Normalize only OpenRCX SPEF NAME_MAP labels against an OpenDB inventory.

The caller temporarily applies these aliases in memory, reads the SPEF, then
restores canonical names. Never change RC, Liberty, constraints or connectivity.
Python 3 standard library only (compatible with the v1.1 evaluation image).
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def load_inventory(path):
    inventory = {"net": {}, "instance": {}}
    aliases = set()
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            kind, name, alias = row["kind"], row["name"], row["alias"]
            if kind not in inventory or name in inventory[kind] or alias in aliases:
                raise ValueError("Duplicate or invalid inventory entry")
            if not re.fullmatch(r"OPEN3D_STA_[NI]_[0-9]+", alias):
                raise ValueError("Unsafe STA alias: " + alias)
            inventory[kind][name] = alias
            aliases.add(alias)
    return inventory


def resolve_name(name, kinds, inventory):
    # OpenRCX escapes punctuation; OpenDB may retain literal bus escapes.
    # A collision is an error, never permission to choose a different net.
    candidates = {name, name.replace(r"\.", "."), re.sub(r"\\(.)", r"\1", name)}
    matches = {inventory[kind][candidate]
               for kind in kinds for candidate in candidates
               if candidate in inventory[kind]}
    if len(matches) != 1:
        raise ValueError("SPEF name is missing or ambiguous: " + repr(name))
    return next(iter(matches))


def normalize(source, inventory_path, output, audit_path):
    paths = [Path(p).resolve() for p in (source, inventory_path, output, audit_path)]
    if len(set(paths)) != len(paths):
        raise ValueError("Input, inventory, output and audit paths must differ")
    source, inventory_path, output, audit_path = paths
    inventory = load_inventory(inventory_path)
    names, kinds = {}, {}
    in_map = False
    dnet_count = 0
    with source.open(encoding="utf-8", newline="") as stream:
        for line in stream:
            fields = line.split()
            if not fields:
                continue
            if fields[0] == "*NAME_MAP":
                in_map = True
                continue
            if fields[0] in ("*PORTS", "*D_NET"):
                in_map = False
            if in_map:
                match = re.fullmatch(r"(\*\d+)\s+(.+?)\s*", line)
                if not match or match[1] in names:
                    raise ValueError("Invalid or duplicate NAME_MAP entry")
                names[match[1]] = match[2]
            elif fields[0] == "*D_NET":
                dnet_count += 1
                kinds.setdefault(fields[1], set()).add("net")
            elif fields[0] == "*I":
                kinds.setdefault(fields[1].rsplit(":", 1)[0], set()).add("instance")
            elif fields[0] == "*P" and fields[1].startswith("*"):
                raise ValueError("Mapped port references are not supported by this OpenRCX adapter")
    if not names or not dnet_count:
        raise ValueError("Expected a nonempty OpenRCX NAME_MAP and D_NET sections")
    for key, value in kinds.items():
        if key not in names or len(value) != 1:
            raise ValueError("Missing or conflicting NAME_MAP reference: " + key)
    mapped = {key: resolve_name(name, kinds.get(key, inventory), inventory)
              for key, name in names.items()}
    raw_hash, output_hash, body_hash = (hashlib.sha256() for _ in range(3))
    in_map = False
    with source.open("rb") as stream, output.open("wb") as destination:
        for line in stream:
            raw_hash.update(line)
            replacement = line
            if line.startswith(b"*NAME_MAP"):
                in_map = True
            elif line.startswith((b"*PORTS", b"*D_NET")):
                in_map = False
            if in_map:
                fields = line.split()
                if fields and fields[0].decode("ascii") in mapped:
                    key = fields[0].decode("ascii")
                    replacement = (key + " " + mapped[key] + "\n").encode("utf-8")
            else:
                body_hash.update(line)
            destination.write(replacement)
            output_hash.update(replacement)
    # Independently verify all content outside NAME_MAP stayed byte-identical.
    verify_hash = hashlib.sha256()
    in_map = False
    with output.open("rb") as stream:
        for line in stream:
            if line.startswith(b"*NAME_MAP"):
                in_map = True
            elif line.startswith((b"*PORTS", b"*D_NET")):
                in_map = False
            if not in_map:
                verify_hash.update(line)
    if verify_hash.digest() != body_hash.digest():
        raise ValueError("Non-name SPEF content changed")
    audit = {"schema_version": 1, "name_map_entries": len(names),
             "dnet_count": dnet_count, "source_sha256": raw_hash.hexdigest(),
             "normalized_sha256": output_hash.hexdigest(),
             "non_name_map_sha256": body_hash.hexdigest(),
             "rc_content_unchanged": True}
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "inventory", "output", "audit"):
        parser.add_argument(name)
    args = parser.parse_args()
    normalize(args.source, args.inventory, args.output, args.audit)
