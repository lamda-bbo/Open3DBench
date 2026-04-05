#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)


SKIPPED_3D_NETS = {
    "clk_i",
    "rst_n_i",
    "clk",
    "p_bsg_tag_clk_i",
    "p_clk_A_i",
    "p_clk_B_i",
    "p_clk_C_i",
    "p_ci_clk_i",
    "p_ci2_tkn_i",
    "p_co_clk_i",
    "p_co2_tkn_i",
}


def load_placedb(params_path):
    _ensure_dreamplace_configure()
    import Params
    import PlaceDB

    params = Params.Params()
    params.load(params_path)
    placedb = PlaceDB.PlaceDB()
    placedb(params)
    return params, placedb


def _ensure_dreamplace_configure():
    try:
        import dreamplace.configure  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    import importlib.util

    candidates = [
        Path(root_dir) / "build" / "dreamplace" / "configure.py",
        Path(root_dir) / "install" / "dreamplace" / "configure.py",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        spec = importlib.util.spec_from_file_location("dreamplace.configure", candidate)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        sys.modules["dreamplace.configure"] = module
        return

    raise ModuleNotFoundError(
        "Cannot find dreamplace.configure. Build/install Place-LoL first so build/dreamplace/configure.py exists."
    )


def default_input_path(design_name, input_variant):
    return Path(f"../binaries/converted_input/{input_variant}/{design_name}.input")


def _mean_movable_node_area(placedb):
    mean_node_area, num = 0, 0
    for node_name in placedb.node_names:
        node = placedb.node_name2id_map[node_name.decode("utf-8")]
        if node < (placedb.num_physical_nodes - placedb.num_terminal_NIs):
            node_area = placedb.node_size_x[node] * placedb.node_size_y[node]
            mean_node_area += node_area
            num += 1

    return mean_node_area / num


def _is_macro_node(placedb, node_id, mean_node_area):
    return (
        (placedb.node_size_x[node_id] * placedb.node_size_y[node_id] > (mean_node_area * 10))
        and (placedb.node_size_y[node_id] > (placedb.row_height * 5))
    )


def has_macro(placedb):
    mean_node_area = _mean_movable_node_area(placedb)
    for node_name in placedb.node_names:
        node_id = placedb.node_name2id_map[node_name.decode("utf-8")]
        if node_id >= (placedb.num_physical_nodes - placedb.num_terminal_NIs):
            continue
        if _is_macro_node(placedb, node_id, mean_node_area):
            return True

    return False


def default_output_txt_path(design_name, method, input_variant, has_macro_flag):
    iccad_dir = "iccad2023" if has_macro_flag else "iccad2022"
    return Path(f"../binaries/{iccad_dir}/{method}/output/{input_variant}/{design_name}.txt")


def default_output_dir(method, input_variant):
    return Path(f"../binaries/converted_output/{input_variant}/{method}")


def group_similar_lib(name2lib):
    groups = defaultdict(list)
    for key, value in name2lib.items():
        groups[value].append(key)
    new_name2lib = {}
    libs = []
    for idx, (lib, keys) in enumerate(groups.items(), 1):
        for key in keys:
            new_name2lib[key] = idx
        libs.append(lib)
    return libs, new_name2lib


def write_input(placedb, terminal_size, outfile):
    outfile = Path(outfile)
    outfile.parent.mkdir(parents=True, exist_ok=True)

    with outfile.open("w", encoding="utf-8") as f:
        placedb.node_size_x = np.round(placedb.node_size_x / placedb.scale_factor / 20).astype(int)
        placedb.node_size_y = np.round(placedb.node_size_y / placedb.scale_factor / 20).astype(int)
        placedb.row_height = np.round(placedb.row_height / placedb.scale_factor / 20).astype(int)
        placedb.pin_offset_x = np.round(placedb.pin_offset_x / placedb.scale_factor / 20).astype(int)
        placedb.pin_offset_y = np.round(placedb.pin_offset_y / placedb.scale_factor / 20).astype(int)
        placedb.xl = np.round(placedb.xl / placedb.scale_factor / 20).astype(int)
        placedb.yl = np.round(placedb.yl / placedb.scale_factor / 20).astype(int)
        placedb.xh = np.round(placedb.xh / placedb.scale_factor / 20).astype(int)
        placedb.yh = np.round(placedb.yh / placedb.scale_factor / 20).astype(int)

        mean_node_area = _mean_movable_node_area(placedb)
        names = []
        id2name = {}
        name2lib = {}
        has_macro_flag = has_macro(placedb)
        for node_name in placedb.node_names:
            node_name = node_name.decode("utf-8")
            node_id = placedb.node_name2id_map[node_name]

            if node_id >= (placedb.num_physical_nodes - placedb.num_terminal_NIs):
                continue

            names.append(node_name)
            id2name[node_id] = node_name

            is_macro = "Y" if _is_macro_node(placedb, node_id, mean_node_area) else "N"

            pins = placedb.node2pin_map[node_id]
            lib = [is_macro, placedb.node_size_x[node_id], placedb.node_size_y[node_id], len(pins)]
            for i, pin_id in enumerate(pins):
                lib.extend([(i, placedb.pin_offset_x[pin_id], placedb.pin_offset_y[pin_id])])
            name2lib[node_name] = tuple(lib)

        libs, name2lib = group_similar_lib(name2lib)
        f.write("NumTechnologies 1 \nTech TA {:d} \n".format(len(libs)))
        for i, lib in enumerate(libs, 1):
            if has_macro_flag:
                f.write("LibCell {} MC{:d} {:d} {:d} {:d} \n".format(lib[0], i, lib[1], lib[2], lib[3]))
            else:
                f.write("LibCell MC{:d} {:d} {:d} {:d} \n".format(i, lib[1], lib[2], lib[3]))
            for pin in lib[4:]:
                f.write("Pin P{:d} {:d} {:d} \n".format(pin[0] + 1, pin[1], pin[2]))

        f.write("\nDieSize {:d} {:d} {:d} {:d} \n\n".format(placedb.xl, placedb.yl, placedb.xh, placedb.yh))
        f.write("TopDieMaxUtil 80 \nBottomDieMaxUtil 80 \n\n")

        repeat_count = int(placedb.yh / placedb.row_height)
        f.write("TopDieRows 0 0 {:d} {:d} {:d} \n".format(placedb.xh, placedb.row_height, repeat_count))
        f.write("BottomDieRows 0 0 {:d} {:d} {:d} \n\n".format(placedb.xh, placedb.row_height, repeat_count))

        f.write("TopDieTech TA \nBottomDieTech TA \n\n")

        if has_macro_flag:
            f.write(f"TerminalSize {terminal_size} {terminal_size} \nTerminalSpacing {terminal_size} \nTerminalCost 1000 \n\n")
        else:
            f.write(f"TerminalSize {terminal_size} {terminal_size} \nTerminalSpacing {terminal_size} \n\n")

        f.write("NumInstances {:d} \n".format(len(names)))
        for name in names:
            node_id = placedb.node_name2id_map[name]
            f.write("Inst C{} MC{} \n".format(node_id + 1, name2lib[name]))

        is_io = False
        net_block = ""
        num_net = 0
        for net_name in placedb.net_names:
            net_name = net_name.decode("utf-8")
            net_id = placedb.net_name2id_map[net_name]
            net_pins = placedb.net2pin_map[net_id]
            num_pins = len(net_pins)
            pin_line = ""
            for pin in net_pins:
                node_id = placedb.pin2node_map[pin]
                if node_id not in id2name:
                    is_io = True
                    continue
                pins = placedb.node2pin_map[node_id]
                pin_line += "Pin C{}/P{} \n".format(node_id + 1, np.where(pins == pin)[0][0] + 1)

            if is_io:
                is_io = False
                continue
            if num_pins == 1:
                continue
            net_block += "Net N{} {} \n".format(net_id + 1, num_pins)
            net_block += pin_line
            num_net += 1

        f.write("\nNumNets {:d} \n".format(num_net))
        f.write(net_block)


NET_START = re.compile(r"^\s*-\s+(\S+)")


def process_net_buf(placedb, buf, splited_nets, three_d_map, hbt_types):
    first = buf[0]
    match = NET_START.match(first)
    if not match:
        return buf

    net_name = match.group(1)
    net_id = int(placedb.net_name2id_map[net_name])
    if net_id not in three_d_map:
        return buf

    idx = three_d_map[net_id]
    bot_pins, top_pins = splited_nets[idx]

    def build(subnet_name, pin_list, hbt_inst, io_name):
        lines = [f"- {subnet_name}"]
        for inst, pin in pin_list:
            if inst == pin:
                lines.append(f"( PIN {pin} )")
            else:
                lines.append(f"( {inst} {pin} )")
        lines.append(f"( {hbt_inst} {io_name} )")
        lines.append("+ USE SIGNAL ;")
        return lines

    if hbt_types[idx] == 0:
        hbt_inst = f"HBT_BOTIN_{net_id}"
    else:
        hbt_inst = f"HBT_TOPIN_{net_id}"

    new_lines = build(f"N{net_id}_BOT", bot_pins, hbt_inst, "BOT")
    new_lines += build(f"N{net_id}_TOP", top_pins, hbt_inst, "TOP")
    return new_lines


def convert_output(placedb, params, design_name, method, input_variant, txt_file=None, target_dir=None):
    txt_file = Path(txt_file) if txt_file else default_output_txt_path(
        design_name, method, input_variant, has_macro(placedb)
    )
    target_dir = Path(target_dir) if target_dir else default_output_dir(method, input_variant)
    target_dir.mkdir(parents=True, exist_ok=True)

    name2die = {}
    name2orient = {}
    orient_map = {"R0": "N", "R90": "E", "R180": "S", "R270": "W", "R360": "N"}
    id2name = {i: n.decode("utf-8") for i, n in enumerate(placedb.node_names)}

    three_d_nets = []
    hbt_coords = []
    hbt_types = []
    splited_nets = []

    with txt_file.open() as f:
        die_name = None
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("TopDie"):
                die_name = "_upper"
            elif line.startswith("BottomDie"):
                die_name = "_bottom"
            elif line.startswith("Inst"):
                if len(line.split()) == 4:
                    _, inst_id, x, y = line.split()
                    ori = "R0"
                else:
                    _, inst_id, x, y, ori = line.split()

                if inst_id[0] != "C":
                    continue
                node_id = int(inst_id[1:]) - 1
                node_name = id2name[node_id]
                name2die[node_name] = die_name
                placedb.node_x[node_id] = int(x) * 20 * placedb.scale_factor
                placedb.node_y[node_id] = int(y) * 20 * placedb.scale_factor
                placedb.node_orient[node_id] = orient_map[ori]
                name2orient[node_name] = orient_map[ori]
            elif line.startswith("Terminal"):
                _, net, x_co, y_co = line.split()
                net_id = int(net[1:]) - 1
                net_name = placedb.net_names[net_id].decode("utf-8")
                if net_name in SKIPPED_3D_NETS:
                    print(f"[WARNING] Skip net {placedb.net_names[net_id]}")
                    continue
                x_real = int(x_co) * 20 + params.shift_factor[0]
                y_real = int(y_co) * 20 + params.shift_factor[1]

                three_d_nets.append(net_id)
                hbt_coords.append((x_real, y_real))

                connected_pins = placedb.net2pin_map[net_id]
                bottom_pins, top_pins = [], []
                for pin_id in connected_pins:
                    node_id = placedb.pin2node_map[pin_id]
                    node_name = id2name[node_id]
                    if node_name not in name2die:
                        die = "_bottom"
                    else:
                        die = name2die[node_name]
                    pin_name = placedb.pin_names[pin_id].decode("utf-8")
                    direction = placedb.pin_direct[pin_id].decode("utf-8")
                    if die == "_bottom":
                        bottom_pins.append((node_name, pin_name))
                        if direction == "OUTPUT":
                            hbt_types.append(0)
                    elif die == "_upper":
                        top_pins.append((node_name, pin_name))
                        if direction == "OUTPUT":
                            hbt_types.append(1)
                    else:
                        raise RuntimeError("die_name not set")
                splited_nets.append((bottom_pins, top_pins))

    def_file = target_dir / f"{design_name}.def"
    def_file.parent.mkdir(parents=True, exist_ok=True)
    placedb.write(params, str(def_file))

    new_def_lines = []
    skip_next_flag = False
    with def_file.open() as f:
        inside_comp = False
        inside_nets = False
        process_fakeram_flag = False
        comp_buf = []
        net_buf = []
        three_d_map = {net_id: i for i, net_id in enumerate(three_d_nets)}

        for raw in f:
            line = raw.rstrip("\n")

            if line.strip().startswith("COMPONENTS"):
                inside_comp = True
            elif inside_comp and line.strip().startswith("END COMPONENTS"):
                inside_comp = False
                new_def_lines.extend(comp_buf)
                comp_buf.clear()
                for idx, net_id in enumerate(three_d_nets):
                    x, y = hbt_coords[idx]
                    if hbt_types[idx] == 0:
                        inst_name = f"HBT_BOTIN_{net_id}"
                        new_def_lines.append(f"  - {inst_name} HBT_BOTIN")
                    else:
                        inst_name = f"HBT_TOPIN_{net_id}"
                        new_def_lines.append(f"  - {inst_name} HBT_TOPIN")
                    new_def_lines.append(f"    + PLACED ( {int(x)} {int(y)} ) N ;")
                new_def_lines.append(line)
                continue

            if inside_comp:
                if "fakeram" in line:
                    process_fakeram_flag = True
                    node_name, lef_name = line.split()[1:3]
                    line = line.replace(lef_name, lef_name + name2die[node_name])
                    comp_buf.append(line)
                    continue
                if process_fakeram_flag:
                    line = line.replace("PLACED", "FIXED")
                    new_orient = name2orient[node_name]
                    orig_orient = line.split()[6]
                    line = line.replace(orig_orient, new_orient)
                    comp_buf.append(line)
                    process_fakeram_flag = False
                    continue
                if "COMPONENTS" in line:
                    comp_buf.append(line)
                    continue
                if skip_next_flag:
                    skip_next_flag = False
                    continue
                if "TAPCELL" in line:
                    skip_next_flag = True
                    continue
                if "-" in line:
                    line_ls = line.split()
                    node_name, lef_name = line_ls[1], line_ls[2]
                    line = line.replace(lef_name, lef_name + name2die[node_name])
                    comp_buf.append(line)
                    continue
                comp_buf.append(line)
                continue

            if line.strip().startswith("NETS"):
                inside_nets = True
                new_def_lines.append(line)
                continue
            elif inside_nets and line.strip().startswith("END NETS"):
                if net_buf:
                    new_def_lines.extend(process_net_buf(placedb, net_buf, splited_nets, three_d_map, hbt_types))
                    net_buf = []
                inside_nets = False
                new_def_lines.append(line)
                continue

            if inside_nets:
                net_buf.append(line)
                if ";" in line:
                    new_def_lines.extend(process_net_buf(placedb, net_buf, splited_nets, three_d_map, hbt_types))
                    net_buf = []
                continue

            new_def_lines.append(line)

    with def_file.open("w") as fw:
        fw.write("\n".join(new_def_lines))
    print(f"[INFO] DEF regenerated at {def_file}")
    return def_file
