#! /usr/bin/python3
import re
import argparse

def process_files(file_list):
    pattern = re.compile(r'^(\S+)(\s+)(\d+\.?\d*)$')
    
    for file_path in file_list:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        processed_lines = []
        for line in lines:
            line = line.strip('\n')
            match = pattern.match(line)
            
            if match:
                col1 = match.group(1)
                separator = match.group(2)
                temp_k = float(match.group(3))
                temp_c = temp_k - 273.15
                new_line = f"{col1}{separator}{temp_c:.2f}"
            else:
                new_line = line
            
            processed_lines.append(new_line + '\n')
        
        with open(file_path, 'w') as f:
            f.writelines(processed_lines)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Temperature Unit Converter")
    parser.add_argument("-f", "--files", 
                        nargs='+',
                        required=True,
                        help="List of files to process")
    
    args = parser.parse_args()
    process_files(args.files)
    # print(f"Conversion completed for {len(args.files)} files!")