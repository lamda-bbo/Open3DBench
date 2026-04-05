import os

def read_def_and_store_coord(filename, name2coord_map):
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    inside_components = False
    modified_lines = []
    count = 0
    for line in lines:

        if line.strip().startswith("COMPONENTS"):
            inside_components = True
            modified_lines.append(line)
            continue
        elif line.strip() == "END COMPONENTS":
            inside_components = False
            modified_lines.append(line)
            continue
        
        if inside_components:
            parts = line.split()
            if len(parts) > 2:
                count += 1
                coord_x = parts[-5]
                coord_y = parts[-4]
                cell_name = parts[1]
                name2coord_map[cell_name] = (coord_x, coord_y)

    print(f"read lines: {count}")

def modify_def(filename, name2coord_map):
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    inside_components = False
    modified_lines = []
    count = 0
    for line in lines:

        if line.strip().startswith("COMPONENTS"):
            inside_components = True
            modified_lines.append(line)
            continue
        elif line.strip() == "END COMPONENTS":
            inside_components = False
            modified_lines.append(line)
            continue
        
        if inside_components:
            parts = line.split()
            if len(parts) > 2:
                cell_name = parts[1]
                if cell_name in name2coord_map:
                    count += 1
                    parts[-5] = name2coord_map[cell_name][0]
                    parts[-4] = name2coord_map[cell_name][1]
                    modified_line = " ".join(parts) + "\n"
                    modified_lines.append(modified_line)
                    continue
        modified_lines.append(line)
    print(f"modified lines: {count}")
    with open(filename, 'w') as file:
        file.writelines(modified_lines)

if __name__ == "__main__":
    name2coord_map = {}
    try:
        results_dir = os.environ['RESULTS_DIR']
        print(f"Results directory is located at: {results_dir}")
    except KeyError:
        print("ERROR: RESULTS_DIR environment variable is not set.")

    file_name_1 = f"{results_dir}/upper_legalized.def"
    file_name_2 = f"{results_dir}/bottom_legalized.def"
    read_def_and_store_coord(file_name_1, name2coord_map)
    read_def_and_store_coord(file_name_2, name2coord_map)

    target_def = f"{results_dir}/4_1_cts.def"
    modify_def(target_def, name2coord_map)