#!/usr/bin/env python3
"""Validate and bind exact post-preparation metadata from the native exporter."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

LABELS = frozenset(('2d_bottom', '2d_upper', '3d', 'unknown'))


@dataclass(frozen=True)
class PreparedMetadata:
    sha256: str
    nets: list[tuple[str, str, int]]
    split_net_pins: dict[str, list[tuple[str, int, int]]]

    def classification(self) -> dict[str, str]:
        return {name: label for name, label, count in self.nets}


def _unique_object(entries):
    result = {}
    for key, value in entries:
        if key in result:
            raise ValueError(f'Duplicate prepared metadata key: {key!r}')
        result[key] = value
    return result


def _read(path: Path, expected_sha256: str | None):
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None:
        if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256) or actual != expected_sha256:
            raise ValueError('Prepared routing metadata fingerprint mismatch')
    record = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(record, dict) or type(record.get('schema_version')) is not int or record['schema_version'] != 1:
        raise ValueError('Unsupported prepared routing metadata schema')
    if type(record.get('compatible')) is not bool:
        raise ValueError('Prepared routing metadata compatibility must be boolean')
    return actual, record


def _validate(actual: str, record: dict) -> PreparedMetadata:
    if not record['compatible']:
        raise ValueError('Prepared routing metadata requires the original DEF path')
    for key in ('def_units', 'dbu_per_micron'):
        if type(record.get(key)) is not int or record[key] <= 0:
            raise ValueError(f'Invalid prepared routing metadata {key}')
    rows, points = record.get('nets'), record.get('split_net_pins')
    if not isinstance(rows, list) or not isinstance(points, dict):
        raise ValueError('Prepared routing metadata is missing complete net/pin records')
    counts = {}
    nets = []
    previous = None
    for row in rows:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError('Malformed prepared net record')
        name, label, count = row
        if not isinstance(name, str) or not name or not isinstance(label, str) or label not in LABELS:
            raise ValueError('Malformed prepared net name/classification')
        if type(count) is not int or count < 0:
            raise ValueError('Malformed prepared net pin count')
        if previous is not None and name <= previous:
            raise ValueError('Prepared net records are duplicated or not in DEF writer order')
        if name.endswith('_BOT') and label != '2d_bottom' or name.endswith('_TOP') and label != '2d_upper':
            raise ValueError('Prepared net classification violates forced die suffix')
        counts[name] = count
        nets.append((name, label, count))
        previous = name
    pins = {}
    for name, tuples in points.items():
        if name not in counts or not name.endswith(('_BOT', '_TOP')) or not isinstance(tuples, list):
            raise ValueError('Prepared diagnostic pins reference an invalid split net')
        if len(tuples) > counts[name]:
            raise ValueError('Prepared diagnostic pins exceed the net pin count')
        values = []
        for point in tuples:
            if (not isinstance(point, list) or len(point) != 3 or not isinstance(point[0], str)
                    or not point[0] or type(point[1]) is not int or type(point[2]) is not int
                    or point[1] < 0 or point[2] < 0):
                raise ValueError('Malformed prepared diagnostic component location')
            values.append(tuple(point))
        if values:
            pins[name] = values
    return PreparedMetadata(actual, nets, pins)


def read_prepared_metadata(path: Path, expected_sha256: str) -> PreparedMetadata:
    if not expected_sha256:
        raise ValueError('Prepared routing metadata requires its preparation fingerprint')
    actual, record = _read(path, expected_sha256)
    return _validate(actual, record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', required=True, type=Path)
    args = parser.parse_args()
    actual, record = _read(args.probe, None)
    if not record['compatible']:
        reason = record.get('reason')
        if not isinstance(reason, str) or not re.fullmatch(r'[a-z0-9_]+', reason):
            raise ValueError('Malformed metadata fallback reason')
        print('fallback', reason)
        return
    _validate(actual, record)
    print('native', actual)


if __name__ == '__main__':
    main()
