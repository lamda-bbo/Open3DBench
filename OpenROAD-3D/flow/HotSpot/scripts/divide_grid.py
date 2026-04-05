import re
import os
import argparse
from typing import Dict, List, Tuple

class Cell:
    """Represents a cell in the DEF file with position and fixed status."""
    def __init__(self, code: str):
        self.name = ""
        self.type = ""
        self.pos = (0, 0)
        self.fixed = False
        self._parse_code(code)

    def _parse_code(self, code: str) -> None:
        """Parse cell information from DEF component line."""
        parts = code.split()
        self.name = parts[1]
        self.type = parts[2]

        if 'PLACED' in parts:
            idx = parts.index('PLACED')
            self.pos = (int(float(parts[idx+2])), int(float(parts[idx+3])))
        elif 'FIXED' in parts:
            idx = parts.index('FIXED')
            self.pos = (int(float(parts[idx+2])), int(float(parts[idx+3])))
            self.fixed = True

    def __repr__(self):
        return f"Cell({self.name}, {self.type}, {self.pos}, {'Fixed' if self.fixed else 'Placed'})"

class DefParser:
    """Parses DEF file and divides cells into grids."""
    def __init__(self, def_path: str, grid_size: int, output_dir: str):
        self.def_path = def_path
        self.grid_size = grid_size
        self.output_dir = output_dir
        self.die_width = 0
        self.die_height = 0
        self.cells: List[Cell] = []
        self.grids: Dict[Tuple[int, int], List[Cell]] = {}

        os.makedirs(output_dir, exist_ok=True)

    def _read_die_area(self, line: str) -> None:
        """Extract die area dimensions from DIEAREA line."""
        match = re.match(r"DIEAREA \(\s*(\d+)\s*(\d+)\s*\)\s*\(\s*(\d+)\s*(\d+)\s*\) ;", line)
        if not match:
            raise ValueError(f"Invalid DIEAREA format: {line}")
        x1, y1, x2, y2 = map(int, match.groups())
        self.die_width = x2 - x1
        self.die_height = y2 - y1
        
    def _parse_components(self, lines: List[str]) -> None:
        """Parse COMPONENTS section from DEF file."""
        for line in lines:
            if any(kw in line for kw in ["PLACED", "FIXED"]):
                self.cells.append(Cell(line))

    def _assign_to_grids(self) -> None:
        """Assign cells to grid buckets based on positions."""
        grid_x_size = self.die_width // self.grid_size
        grid_y_size = self.die_height // self.grid_size

        for cell in self.cells:
            x, y = cell.pos
            grid = (x // grid_x_size, y // grid_y_size)
            self.grids.setdefault(grid, []).append(cell)

    def parse(self) -> None:
        """Main parsing workflow."""
        with open(self.def_path, 'r') as f:
            components = []
            in_components = False
            
            for line in f:
                line = line.strip()
                if line.startswith("DIEAREA"):
                    self._read_die_area(line)
                elif line.startswith("COMPONENTS"):
                    in_components = True
                elif line.startswith("END COMPONENTS"):
                    in_components = False
                    break
                elif in_components:
                    components.append(line)

        self._parse_components(components)
        self._assign_to_grids()

    def generate_flp(self, flp_name: str = "ev6.flp", prefix: str = "Grid") -> str:
        """Generate .flp file with customizable grid name."""
        flp_path = os.path.join(self.output_dir, flp_name)
        grid_x_size = self.die_width / self.grid_size / 1e9
        grid_y_size = self.die_height / self.grid_size / 1e9

        def format_number(num: float) -> str:
            return ("%.6f" % num).rstrip('0').rstrip('.') if num != int(num) else str(int(num))

        with open(flp_path, 'w') as f:
            for x in range(self.grid_size):
                for y in range(self.grid_size):
                    f.write(
                        f"{prefix}_{x}_{y}\t"
                        f"{format_number(grid_x_size)}\t"
                        f"{format_number(grid_y_size)}\t"
                        f"{format_number(x * grid_x_size)}\t"
                        f"{format_number(y * grid_y_size)}\n"
                    )
        return flp_path

    def export_grids(self) -> Dict[Tuple[int, int], str]:
        grid_files = {}

        os.makedirs(self.output_dir, exist_ok=True)

        for x in range(self.grid_size):
            for y in range(self.grid_size):
                cells = self.grids.get((x, y), [])
                
                filename = os.path.join(self.output_dir, f"Grid_({x}, {y}).txt")
                
                with open(filename, 'w') as f:
                    if cells:
                        content = " ".join(cell.name for cell in cells)
                        f.write(content)
                
                grid_files[(x, y)] = filename
        
        return grid_files

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="DEF File Grid Partitioner")
    parser.add_argument("-i", "--input", required=True, help="Input DEF file path")
    parser.add_argument("-o", "--output", default="output", help="Output directory")
    parser.add_argument("-g", "--grid", type=int, default=10, help="Grid size (N x N)")
    parser.add_argument("--flp", default="ev6.flp", help="Output FLP filename")
    parser.add_argument("--prefix", default="Grid", help="Prefix for grid names")
    args = parser.parse_args()

    # print(f"[1/3] Parsing DEF file: {args.input}")
    def_parser = DefParser(args.input, args.grid, args.output)
    def_parser.parse()

    # print(f"[2/3] Generating FLP file: {args.flp}")
    flp_path = def_parser.generate_flp(args.flp, args.prefix)

    # print(f"[3/3] Exporting {def_parser.grid_size}x{def_parser.grid_size} grids to {args.output}")
    grid_files = def_parser.export_grids()

    print(f"Done! Created {len(grid_files)} grid files and FLP file: {flp_path}")
