import os
import re
from pathlib import Path


COMPONENT_START_RE = re.compile(r"^\s*-\s+\S+\s+(\S+)")


def component_die(line):
    match = COMPONENT_START_RE.match(line)
    if match is None:
        return None

    master = match.group(1).lower()
    if "bottom" in master or master == "hbt_botin":
        return "bottom"
    if "upper" in master or master == "hbt_topin":
        return "upper"
    raise ValueError(f"Cannot classify component master '{match.group(1)}'")


def count_components(def_path):
    counts = {"bottom": 0, "upper": 0}
    in_components = False

    with def_path.open(encoding="utf-8") as def_file:
        for line in def_file:
            stripped = line.lstrip()
            if stripped.startswith("COMPONENTS "):
                in_components = True
                continue
            if in_components and stripped.startswith("END COMPONENTS"):
                break
            if not in_components:
                continue

            die = component_die(line)
            if die is not None:
                counts[die] += 1

    return counts


def split_def(def_path, bottom_path, upper_path, counts):
    outputs = {
        "bottom": bottom_path.open("w", encoding="utf-8"),
        "upper": upper_path.open("w", encoding="utf-8"),
    }
    in_components = False
    skipped_section = None
    component_output = None

    try:
        with def_path.open(encoding="utf-8") as def_file:
            for line in def_file:
                stripped = line.lstrip()

                if skipped_section is not None:
                    if stripped.startswith(f"END {skipped_section}"):
                        skipped_section = None
                    continue

                if not in_components and stripped.startswith("SPECIALNETS "):
                    skipped_section = "SPECIALNETS"
                    continue
                if not in_components and stripped.startswith("NETS "):
                    skipped_section = "NETS"
                    continue

                if stripped.startswith("COMPONENTS "):
                    in_components = True
                    for die, output in outputs.items():
                        output.write(f"COMPONENTS {counts[die]} ;\n")
                    continue

                if in_components and stripped.startswith("END COMPONENTS"):
                    in_components = False
                    component_output = None
                    for output in outputs.values():
                        output.write(line)
                    continue

                if in_components:
                    die = component_die(line)
                    if die is not None:
                        component_output = outputs[die]
                    if component_output is not None:
                        component_output.write(line)
                    if ";" in line:
                        component_output = None
                    continue

                for output in outputs.values():
                    output.write(line)
    finally:
        for output in outputs.values():
            output.close()


def main():
    results_dir = os.environ.get("RESULTS_DIR")
    if not results_dir:
        raise RuntimeError("RESULTS_DIR environment variable is not set")

    results_path = Path(results_dir)
    input_def = results_path / "4_1_cts.def"
    bottom_def = results_path / "bottom.def"
    upper_def = results_path / "upper.def"

    counts = count_components(input_def)
    print(
        "Splitting CTS DEF: "
        f"bottom={counts['bottom']} upper={counts['upper']}"
    )
    split_def(input_def, bottom_def, upper_def, counts)


if __name__ == "__main__":
    main()
