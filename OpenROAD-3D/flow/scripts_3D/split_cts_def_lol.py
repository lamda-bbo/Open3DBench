import os
import pdb

try:
    results_dir = os.environ['RESULTS_DIR']
    print(f"Results directory is located at: {results_dir}")
except KeyError:
    print("ERROR: RESULTS_DIR environment variable is not set.")


gp_out_file = f"{results_dir}/4_1_cts.def"

upper_def = ''
bottom_def = ''
with open(gp_out_file, 'r', encoding='utf-8') as def_file:
        part = False
        indicator = False
        net_part = False
        for line in def_file:
            if 'COMPONENTS' in line:
                part = True
            if 'END' in line:
                part = False
            if 'NETS' in line:
                net_part = True


            if part:
                if ('PLACED' not in line) or ('FIXED' not in line):
                    class_name = line.split()[2]
                    # print(class_name)
                    if 'bottom' in class_name:
                        indicator = 'bottom'
                    elif 'upper' in class_name:
                        indicator = 'upper'
                    
            else:
                if net_part:
                    indicator = None
                else:
                    indicator = 'all'
            if indicator == 'bottom':
                if 'TAPCELL' not in line:
                    bottom_def += line
            if indicator == 'upper':
                if 'TAPCELL' not in line:
                    upper_def += line
            if indicator == 'all':
                if 'HBT_TOPIN' not in line and 'HBT_BOTIN' not in line:
                    bottom_def += line
                    upper_def += line
            if 'END NETS' in line:
                net_part = False

# pdb.set_trace()
with open(f"{results_dir}/upper.def", 'w', encoding='utf-8') as def_file:
    def_file.write(upper_def)

with open(f"{results_dir}/bottom.def", 'w', encoding='utf-8') as def_file:
    def_file.write(bottom_def)