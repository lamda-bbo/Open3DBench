import sys
import argparse

def merge_ptrace(upper_file, bottom_file, output_file):
    with open(upper_file, 'r') as f:
        upper_lines = f.readlines()
    upper_header = upper_lines[0].strip().split()
    if len(upper_lines) < 2:
        print("Upper file has no data line.")
        sys.exit(1)
    upper_data = upper_lines[1].strip().split()

    with open(bottom_file, 'r') as f:
        bottom_lines = f.readlines()
    bottom_header = bottom_lines[0].strip().split()
    if len(bottom_lines) < 2:
        print("Bottom file has no data line.")
        sys.exit(1)
    bottom_data = bottom_lines[1].strip().split()

    if len(upper_header) != len(upper_data):
        print(f"Upper file header length ({len(upper_header)}) does not match data length ({len(upper_data)})")
        sys.exit(1)
    if len(bottom_header) != len(bottom_data):
        print(f"Bottom file header length ({len(bottom_header)}) does not match data length ({len(bottom_data)})")
        sys.exit(1)
    if len(upper_header) != len(bottom_header):
        print(f"Grid count mismatch: upper={len(upper_header)}, bottom={len(bottom_header)}")
        sys.exit(1)

    upper_processed = ['upper' + s[4:] for s in upper_header]
    bottom_processed = ['bottom' + s[4:] for s in bottom_header]

    for u, b in zip(upper_processed, bottom_processed):
        u_coords = u.split('_')[1:]
        b_coords = b.split('_')[1:]
        if u_coords != b_coords:
            print(f"Coordinate mismatch: {u} vs {b}")
            sys.exit(1)

    merged_header = upper_processed + bottom_processed  
    merged_data = upper_data + bottom_data 

    with open(output_file, 'w') as f:
        f.write(' '.join(merged_header) + '\n')
        f.write(' '.join(merged_data) + '\n')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge two ptrace files")
    parser.add_argument("-u", "--upper", required=True, help="Path to the upper ptrace file")
    parser.add_argument("-b", "--bottom", required=True, help="Path to the bottom ptrace file")
    parser.add_argument("-o", "--output", required=True, help="Path to the output merged ptrace file")
    args = parser.parse_args()

    merge_ptrace(args.upper, args.bottom, args.output)