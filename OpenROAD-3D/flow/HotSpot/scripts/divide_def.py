import argparse

def split_def_file(input_file, output_dir):
    output_bottom = f"{output_dir}/6_final_bottom.def"
    output_upper = f"{output_dir}/6_final_upper.def"

    with open(input_file, "r") as infile, \
         open(output_bottom, "w") as bottom_file, \
         open(output_upper, "w") as upper_file:

        write_bottom = write_upper = False

        for line in infile:
            if "DIEAREA" in line:
                bottom_file.write(line)
                upper_file.write(line)
                continue

            if line.startswith("COMPONENTS"):
                bottom_file.write(line)
                upper_file.write(line)
                write_bottom = write_upper = True
                continue

            if write_bottom and write_upper:
                if line.startswith("END COMPONENTS"):
                    bottom_file.write(line)
                    upper_file.write(line)
                    break

                parts = line.strip().split()
                if len(parts) >= 3:
                    comp_type_parts = parts[2].rsplit("_", 1)
                    if len(comp_type_parts) > 1:
                        last_part = comp_type_parts[-1].lower()
                        if last_part == "bottom":
                            bottom_file.write(line)
                        elif last_part == "upper":
                            upper_file.write(line)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DEF File Splitter")
    parser.add_argument("-i", "--input", required=True, help="Input DEF file path")
    parser.add_argument("-o", "--output", default="output", help="Output directory")

    args = parser.parse_args()

    split_def_file(args.input, args.output)

    print(f"DEF : {args.output}6_final_bottom.def and {args.output}6_final_upper.def")
