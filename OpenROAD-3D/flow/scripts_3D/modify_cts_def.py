import pickle
import os

def modify_file(filename, name2partition_map):
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    inside_components = False
    modified_lines = []
    count = 0
    count1 = 0
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
                if cell_name in name2partition_map:
                    count1 += 1
                    part_to_replace = parts[2]
                    if "_upper" in part_to_replace and name2partition_map[cell_name] == 0:
                        new_part = part_to_replace.replace("_upper", "_bottom")
                        parts[2] = new_part
                        count += 1
                    elif "_bottom" in part_to_replace and name2partition_map[cell_name] == 1:
                        new_part = part_to_replace.replace("_bottom", "_upper")
                        parts[2] = new_part
                        count += 1
                    modified_line = " ".join(parts) + "\n"
                    modified_lines.append(modified_line)
                    continue
        modified_lines.append(line)
    print(f"modified lines: {count}")
    print(f"all lines : {count1}")
    with open(filename, 'w') as file:
        file.writelines(modified_lines)



try:
    results_dir = os.environ['RESULTS_DIR']
    print(f"Results directory is located at: {results_dir}")
except KeyError:
    print("ERROR: RESULTS_DIR environment variable is not set.")

filename = f"{results_dir}/4_1_cts.def"
with open(f"{results_dir}/name_die_map.pkl", 'rb') as f:
	name2partition_map = pickle.load(f)

modify_file(filename, name2partition_map)