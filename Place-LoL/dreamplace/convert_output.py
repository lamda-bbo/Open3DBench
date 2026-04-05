#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from dreamplace.convert_common import convert_output, load_placedb


def build_parser():
    parser = argparse.ArgumentParser(description="Convert external placer output back into DEF.")
    parser.add_argument("params_json", help="Path to the DreamPlace params json")
    parser.add_argument("design_name", help="Design name")
    parser.add_argument("method", help="Placement method name, used to locate txt input/output dir")
    parser.add_argument("input_variant", help="Input variant, e.g. default or inflated")
    parser.add_argument(
        "--txt-file",
        default=None,
        help="Optional explicit raw txt path. Default: ../data/binary_output/<variant>/<method>/<design>.txt",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional explicit DEF output directory. Default: ../data/converted_output/<variant>/<method>",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    params, placedb = load_placedb(args.params_json)
    convert_output(
        placedb,
        params,
        args.design_name,
        args.method,
        args.input_variant,
        txt_file=args.txt_file,
        target_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
