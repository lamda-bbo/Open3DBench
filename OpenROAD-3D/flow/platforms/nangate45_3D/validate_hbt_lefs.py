#!/usr/bin/env python3
"""Validate the platform's HBT geometry, resistance, and Liberty capacitance."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

HBT_PITCH_UM = 6.4
HBT_CUT_WIDTH_UM = 0.5
HBT_CUT_SPACING_UM = HBT_PITCH_UM - HBT_CUT_WIDTH_UM
HBT_RESISTANCE_OHM = 3.0
HBT_CAPACITANCE_FF = 0.6


def block(text: str, start: str, end: str, source: Path) -> str:
    match = re.search(
        rf"^{re.escape(start)}\s*$\n(.*?)^{re.escape(end)}\s*$",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise ValueError(f"missing {start} block in {source}")
    return match.group(1)


def require_value(pattern: str, text: str, expected: float, label: str) -> None:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if match is None:
        raise ValueError(f"missing {label}")
    actual = float(match.group(1))
    if abs(actual - expected) > 1e-9:
        raise ValueError(f"{label}: expected {expected:g}, found {actual:g}")


def files_with(lefs: list[Path], pattern: str) -> list[Path]:
    regex = re.compile(pattern, flags=re.MULTILINE)
    return [path for path in lefs if regex.search(path.read_text(encoding="utf-8"))]


def require_unique(lefs: list[Path], pattern: str, label: str) -> Path:
    matches = files_with(lefs, pattern)
    if len(matches) != 1:
        paths = ", ".join(str(path) for path in matches) or "none"
        raise ValueError(f"{label} must have one definition, found {len(matches)}: {paths}")
    return matches[0]


def braced_block(text: str, pattern: str, label: str, source: Path) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if match is None:
        raise ValueError(f"missing {label} block in {source}")
    start = text.find("{", match.start(), match.end())
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index]
    raise ValueError(f"unterminated {label} block in {source}")


def validate(platform_dir: Path) -> None:
    lefs = sorted(platform_dir.rglob("*.lef"))
    if not lefs:
        raise ValueError(f"no LEF files below {platform_dir}")

    layer_file = require_unique(lefs, r"^LAYER hb_layer\s*$", "hb_layer")
    via_file = require_unique(lefs, r"^VIA hb_layer_0 DEFAULT\s*$", "hb_layer_0")
    rule_file = require_unique(
        lefs,
        r"^VIARULE hb_layerArray-0 GENERATE\s*$",
        "hb_layerArray-0",
    )
    if len({layer_file, via_file, rule_file}) != 1:
        raise ValueError("HBT layer, via, and generated-via rule must share one TECH_LEF")

    tech_text = layer_file.read_text(encoding="utf-8")
    layer = block(tech_text, "LAYER hb_layer", "END hb_layer", layer_file)
    require_value(r"^\s*WIDTH\s+([0-9.]+)\s*;", layer, HBT_CUT_WIDTH_UM, "HBT cut width")
    require_value(
        r"^\s*SPACING\s+([0-9.]+)\s*;",
        layer,
        HBT_CUT_SPACING_UM,
        "HBT cut edge spacing",
    )
    require_value(
        r"^\s*RESISTANCE\s+([0-9.]+)\s*;",
        layer,
        HBT_RESISTANCE_OHM,
        "HBT cut resistance",
    )

    default_via = block(tech_text, "VIA hb_layer_0 DEFAULT", "END hb_layer_0", via_file)
    cut_rect = re.search(
        r"LAYER\s+hb_layer\s*;\s*\n\s*RECT\s+"
        r"(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s*;",
        default_via,
    )
    if cut_rect is None:
        raise ValueError("missing hb_layer cut rectangle in hb_layer_0")
    xl, yl, xh, yh = map(float, cut_rect.groups())
    if (
        abs((xh - xl) - HBT_CUT_WIDTH_UM) > 1e-9
        or abs((yh - yl) - HBT_CUT_WIDTH_UM) > 1e-9
    ):
        raise ValueError(
            "hb_layer_0 cut must be "
            f"{HBT_CUT_WIDTH_UM:g} BY {HBT_CUT_WIDTH_UM:g} um"
        )

    via_rule = block(
        tech_text,
        "VIARULE hb_layerArray-0 GENERATE",
        "END hb_layerArray-0",
        layer_file,
    )
    spacing = re.search(
        r"^\s*SPACING\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;",
        via_rule,
        flags=re.MULTILINE,
    )
    if spacing is None:
        raise ValueError("missing hb_layerArray-0 center spacing")
    pitch_x, pitch_y = float(spacing.group(1)), float(spacing.group(2))
    if abs(pitch_x - HBT_PITCH_UM) > 1e-9 or abs(pitch_y - HBT_PITCH_UM) > 1e-9:
        raise ValueError(
            f"HBT generated-via pitch: expected {HBT_PITCH_UM:g} BY "
            f"{HBT_PITCH_UM:g}, found {pitch_x:g} BY {pitch_y:g}"
        )

    same_net = re.findall(
        r"^\s*SAMENET\s+hb_layer\s+hb_layer\s+([0-9.]+)\s*;",
        tech_text,
        flags=re.MULTILINE,
    )
    if len(same_net) != 1 or abs(float(same_net[0]) - HBT_CUT_SPACING_UM) > 1e-9:
        raise ValueError(
            f"HBT same-net edge spacing must be exactly {HBT_CUT_SPACING_UM:g} um"
        )

    macro_files = {
        name: require_unique(lefs, rf"^MACRO {name}\s*$", name)
        for name in ("HBT_BOTIN", "HBT_TOPIN")
    }
    if len(set(macro_files.values())) != 1:
        raise ValueError("HBT_BOTIN and HBT_TOPIN must share one macro LEF")

    macro_text = next(iter(macro_files.values())).read_text(encoding="utf-8")
    for name in macro_files:
        macro = block(macro_text, f"MACRO {name}", f"END {name}", macro_files[name])
        require_value(r"^\s*SIZE\s+([0-9.]+)\s+BY", macro, 1.0, f"{name} width")
        if "LAYER metal10 ;" not in macro or "LAYER metal11 ;" not in macro:
            raise ValueError(f"{name} must expose pins on metal10 and metal11")

    libs = sorted(platform_dir.rglob("*.lib"))
    liberty_files = {
        name: require_unique(libs, rf"^\s*cell \({name}\)\s*\{{", name)
        for name in ("HBT_BOTIN", "HBT_TOPIN")
    }
    if len(set(liberty_files.values())) != 1:
        raise ValueError("HBT_BOTIN and HBT_TOPIN must share one Liberty file")
    liberty_file = next(iter(liberty_files.values()))
    liberty_text = liberty_file.read_text(encoding="utf-8")
    for cell_name, input_pin in (("HBT_BOTIN", "BOT"), ("HBT_TOPIN", "TOP")):
        cell = braced_block(
            liberty_text,
            rf"^\s*cell \({cell_name}\)\s*\{{",
            cell_name,
            liberty_file,
        )
        pin = braced_block(
            cell,
            rf"^\s*pin \({input_pin}\)\s*\{{",
            f"{cell_name}/{input_pin}",
            liberty_file,
        )
        for attribute in ("capacitance", "fall_capacitance", "rise_capacitance"):
            require_value(
                rf"^\s*{attribute}\s*:\s*([0-9.]+)\s*;",
                pin,
                HBT_CAPACITANCE_FF,
                f"{cell_name}/{input_pin} {attribute}",
            )

    print(
        f"PASS: {len(lefs)} LEFs; HBT pitch={HBT_PITCH_UM:g} um, "
        f"cut={HBT_CUT_WIDTH_UM:g} um, edge spacing={HBT_CUT_SPACING_UM:g} um, "
        f"resistance={HBT_RESISTANCE_OHM:g} ohm"
    )
    print(f"  TECH_LEF: {layer_file.relative_to(platform_dir)}")
    print(f"  HBT macros: {next(iter(macro_files.values())).relative_to(platform_dir)}")
    print(
        f"  HBT Liberty: {liberty_file.relative_to(platform_dir)}; "
        f"input capacitance={HBT_CAPACITANCE_FF:g} fF"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "platform_dir",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    args = parser.parse_args()
    try:
        validate(args.platform_dir.resolve())
    except ValueError as error:
        print(f"FAIL: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
