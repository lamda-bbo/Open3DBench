#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from dreamplace.convert_common import default_input_path, load_placedb, write_input


def build_parser():
    parser = argparse.ArgumentParser(description="Convert DreamPlace params.json into Place-LoL input format.")
    parser.add_argument("params_json", help="Path to the DreamPlace params json")
    parser.add_argument("design_name", help="Design name")
    parser.add_argument("input_variant", help="Input variant, e.g. default or inflated")
    parser.add_argument("terminal_size", type=int, help="Terminal size/spacing in the generated input")
    parser.add_argument(
        "--outfile",
        default=None,
        help="Optional explicit output path. Default: ../data/converted_input/<variant>/<design>.input",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    _, placedb = load_placedb(args.params_json)
    outfile = args.outfile or default_input_path(args.design_name, args.input_variant)
    write_input(placedb, args.terminal_size, outfile)
    print(f"[INFO] Input written to {outfile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
