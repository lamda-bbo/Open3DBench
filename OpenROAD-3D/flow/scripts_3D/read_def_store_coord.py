import os
import re
import stat
import tempfile
from pathlib import Path


COMPONENT_RE = re.compile(r"^\s*-\s+(\S+)\s+\S+", re.MULTILINE)
PLACEMENT_RE = re.compile(
    r"(\+\s+(?:PLACED|FIXED|COVER)\s*\(\s*)"
    r"(-?\d+)(\s+)(-?\d+)(\s*\))"
)


def component_records(def_path):
    in_components = False
    record = []

    with def_path.open(encoding="utf-8") as def_file:
        for line in def_file:
            stripped = line.lstrip()
            if stripped.startswith("COMPONENTS "):
                in_components = True
                continue
            if in_components and stripped.startswith("END COMPONENTS"):
                if record:
                    yield "".join(record)
                return
            if not in_components:
                continue

            if stripped.startswith("- "):
                if record:
                    yield "".join(record)
                record = [line]
            elif record:
                record.append(line)

            if record and ";" in line:
                yield "".join(record)
                record = []


def read_coordinates(def_path, coordinates):
    count = 0
    for record in component_records(def_path):
        component = COMPONENT_RE.search(record)
        placement = PLACEMENT_RE.search(record)
        if component is None or placement is None:
            continue
        coordinates[component.group(1)] = (
            placement.group(2),
            placement.group(4),
        )
        count += 1
    print(f"Read coordinates: {count} from {def_path}")


def update_component(record, coordinates):
    component = COMPONENT_RE.search(record)
    if component is None:
        return record, False

    coordinate = coordinates.get(component.group(1))
    if coordinate is None:
        return record, False

    def replace_placement(match):
        return (
            f"{match.group(1)}{coordinate[0]}"
            f"{match.group(3)}{coordinate[1]}{match.group(5)}"
        )

    updated, replacements = PLACEMENT_RE.subn(
        replace_placement, record, count=1
    )
    return updated, replacements == 1


def rewrite_def(def_path, coordinates):
    in_components = False
    record = []
    modified = 0
    original_mode = stat.S_IMODE(def_path.stat().st_mode)
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=def_path.parent,
            prefix=f".{def_path.name}.",
            delete=False,
        ) as output:
            temporary_path = Path(output.name)
            with def_path.open(encoding="utf-8") as def_file:
                for line in def_file:
                    stripped = line.lstrip()

                    if stripped.startswith("COMPONENTS "):
                        in_components = True
                        output.write(line)
                        continue

                    if in_components and stripped.startswith("END COMPONENTS"):
                        if record:
                            updated, changed = update_component(
                                "".join(record), coordinates
                            )
                            output.write(updated)
                            modified += int(changed)
                            record = []
                        in_components = False
                        output.write(line)
                        continue

                    if not in_components:
                        output.write(line)
                        continue

                    if stripped.startswith("- "):
                        if record:
                            updated, changed = update_component(
                                "".join(record), coordinates
                            )
                            output.write(updated)
                            modified += int(changed)
                        record = [line]
                    elif record:
                        record.append(line)
                    else:
                        output.write(line)

                    if record and ";" in line:
                        updated, changed = update_component(
                            "".join(record), coordinates
                        )
                        output.write(updated)
                        modified += int(changed)
                        record = []

        os.chmod(temporary_path, original_mode)
        os.replace(temporary_path, def_path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise

    print(f"Updated coordinates: {modified} in {def_path}")


def main():
    results_dir = os.environ.get("RESULTS_DIR")
    if not results_dir:
        raise RuntimeError("RESULTS_DIR environment variable is not set")

    results_path = Path(results_dir)
    coordinates = {}
    read_coordinates(results_path / "upper_legalized.def", coordinates)
    read_coordinates(results_path / "bottom_legalized.def", coordinates)
    rewrite_def(results_path / "4_1_cts.def", coordinates)


if __name__ == "__main__":
    main()
