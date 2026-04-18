"""
Utility class for processing DEF files: fix macro status and add die suffixes.

This module provides a class that:
1. Identifies macros from a ProblemInstance
2. Processes DEF files to change macro component status from PLACED to FIXED
3. Adds suffixes to component names: _upper for upper die macros, _bottom for others
"""

import os
from typing import Set, Optional, List, Tuple


class DefProcessor:
    """
    Class for processing DEF files: fixing macro status and adding die suffixes.
    """
    
    @staticmethod
    def _fix_macro_in_lines(macro_names: Set[str], lines: List[str]) -> Tuple[List[str], int]:
        """
        Fix macro status in a list of DEF lines: change PLACED to FIXED for all macros.
        Internal helper method that operates on line lists.
        
        Args:
            macro_names: Set of macro component names
            lines: List of DEF file lines
        
        Returns:
            Tuple of (processed_lines, fixed_count)
        """
        output_lines = []
        fixed_count = 0
        prev_line = None
        in_components_section = False
        
        for line in lines:
            stripped = line.strip()
            
            # Check if we're entering the COMPONENTS section
            if stripped.startswith('COMPONENTS'):
                in_components_section = True
                output_lines.append(line)
                prev_line = None
                continue
            
            # Check if we're leaving the COMPONENTS section
            if stripped.startswith('END COMPONENTS'):
                in_components_section = False
                output_lines.append(line)
                prev_line = None
                continue
            
            # Only process if we're in the COMPONENTS section
            if in_components_section:
                # Check if current line contains PLACED
                if 'PLACED' in line and prev_line is not None:
                    # Extract second-to-last field from previous line (split by spaces)
                    prev_fields = prev_line.split()
                    if len(prev_fields) >= 2:
                        # Get second-to-last field (component name in DEF format)
                        component_name = prev_fields[-2]
                        
                        # Check if this component is a macro
                        if component_name in macro_names:
                            # Replace PLACED with FIXED
                            new_line = line.replace('PLACED', 'FIXED')
                            output_lines.append(new_line)
                            fixed_count += 1
                            prev_line = line  # Update prev_line for next iteration
                            continue
                
                # Write the line as-is
                output_lines.append(line)
                prev_line = line  # Remember previous line
            else:
                # Outside COMPONENTS section, write as-is
                output_lines.append(line)
                prev_line = None  # Reset prev_line outside components section
        
        return output_lines, fixed_count
    
    @staticmethod
    def _change_direction_in_lines(macro_names: Set[str], lines: List[str]) -> Tuple[List[str], int]:
        """
        Change all macro directions to N in a list of DEF lines.
        Internal helper method that operates on line lists.
        
        DEF component format spans two lines:
          - component_name macro_type
            + PLACED ( x y ) orientation ;
        
        Args:
            macro_names: Set of macro component names
            lines: List of DEF file lines
        
        Returns:
            Tuple of (processed_lines, changed_count)
        """
        output_lines = []
        changed_count = 0
        in_components_section = False
        next_line_is_macro_placement = False
        
        for line in lines:
            stripped = line.strip()
            
            # Track if we're in COMPONENTS section
            if stripped.startswith('COMPONENTS'):
                in_components_section = True
                output_lines.append(line)
                continue
            elif stripped.startswith('END COMPONENTS'):
                in_components_section = False
                output_lines.append(line)
                continue
            
            # Process lines in COMPONENTS section
            if in_components_section:
                fields = stripped.split()
                
                # Check if this is a component definition line (starts with '-')
                if len(fields) >= 2 and fields[0] == '-':
                    component_name = fields[1]  # Second field is component name
                    
                    # Check if this component is a macro
                    if component_name in macro_names:
                        # Mark that the next line contains the placement info for this macro
                        next_line_is_macro_placement = True
                    else:
                        next_line_is_macro_placement = False
                    
                    # Keep the component definition line as-is
                    output_lines.append(line)
                    continue
                
                # Check if this is a placement line (starts with '+') for a macro
                elif next_line_is_macro_placement and len(fields) >= 2 and fields[0] == '+':
                    # The orientation is the second-to-last field
                    # Format: + PLACED ( x y ) orientation ;
                    if len(fields) >= 2:
                        second_to_last_idx = len(fields) - 2
                        current_orientation = fields[second_to_last_idx]
                        
                        # Only change if it's not already N
                        if current_orientation != 'N':
                            fields[second_to_last_idx] = 'N'
                            
                            # Reconstruct the line preserving original indentation
                            leading_whitespace = ''
                            for char in line:
                                if char in ' \t':
                                    leading_whitespace += char
                                else:
                                    break
                            
                            # Join fields with single space, add leading whitespace
                            new_line = leading_whitespace + ' '.join(fields)
                            # Preserve the original line ending
                            if line.endswith('\n'):
                                new_line += '\n'
                            
                            output_lines.append(new_line)
                            changed_count += 1
                            next_line_is_macro_placement = False
                            continue
                    
                    # Reset the flag after processing
                    next_line_is_macro_placement = False
            
            # Keep the line as-is
            output_lines.append(line)
        
        return output_lines, changed_count
    
    @staticmethod
    def _change_upper_die_macro_status_in_lines(
        upper_die_macro_names: Set[str], 
        lines: List[str], 
        from_status: str, 
        to_status: str
    ) -> Tuple[List[str], int]:
        """
        Change upper die macro status in a list of DEF lines: change from_status to to_status.
        Internal helper method that operates on line lists.
        
        DEF component format spans two lines:
          - component_name macro_type
            + STATUS ( x y ) orientation ;
        
        Args:
            upper_die_macro_names: Set of upper die macro component names
            lines: List of DEF file lines
            from_status: Status to change from (e.g., 'FIXED' or 'PLACED')
            to_status: Status to change to (e.g., 'PLACED' or 'FIXED')
        
        Returns:
            Tuple of (processed_lines, changed_count)
        """
        output_lines = []
        changed_count = 0
        prev_line = None
        in_components_section = False
        
        for line in lines:
            stripped = line.strip()
            
            # Track if we're in COMPONENTS section
            if stripped.startswith('COMPONENTS'):
                in_components_section = True
                output_lines.append(line)
                prev_line = None
                continue
            elif stripped.startswith('END COMPONENTS'):
                in_components_section = False
                output_lines.append(line)
                prev_line = None
                continue
            
            # Process lines in COMPONENTS section
            if in_components_section:
                # Check if current line contains from_status and previous line is component definition
                if from_status in line and prev_line is not None:
                    # Extract component name from previous line (second field)
                    prev_fields = prev_line.split()
                    if len(prev_fields) >= 2 and prev_fields[0] == '-':
                        component_name = prev_fields[1]  # Second field is component name
                        
                        # Check if this component is an upper die macro
                        if component_name in upper_die_macro_names:
                            # Replace from_status with to_status
                            new_line = line.replace(from_status, to_status)
                            output_lines.append(new_line)
                            changed_count += 1
                            prev_line = line  # Update prev_line for next iteration
                            continue
                
                # Write the line as-is
                output_lines.append(line)
                prev_line = line  # Remember previous line
            else:
                # Outside COMPONENTS section, write as-is
                output_lines.append(line)
                prev_line = None  # Reset prev_line outside components section
        
        return output_lines, changed_count
    
    @staticmethod
    def change_upper_die_macro_status_to_placed(
        upper_die_macro_names: Set[str], 
        input_def_path: str, 
        output_def_path: str
    ) -> int:
        """
        Change upper die macro status from FIXED to PLACED in DEF file.
        
        Args:
            upper_die_macro_names: Set of upper die macro component names
            input_def_path: Input DEF file path
            output_def_path: Output DEF file path
        
        Returns:
            int: Number of macro statuses changed
        """
        print(f"Changing upper die macro status from FIXED to PLACED: {input_def_path}")
        print(f"Output will be saved to: {output_def_path}")
        
        # Read input file
        with open(input_def_path, 'r') as infile:
            lines = infile.readlines()
        
        # Process lines
        output_lines, changed_count = DefProcessor._change_upper_die_macro_status_in_lines(
            upper_die_macro_names, lines, 'FIXED', 'PLACED'
        )
        
        # Write to output file
        if os.path.dirname(output_def_path):
            os.makedirs(os.path.dirname(output_def_path), exist_ok=True)
        
        with open(output_def_path, 'w') as outfile:
            outfile.writelines(output_lines)
        
        print(f"Changed {changed_count} upper die macro statuses from FIXED to PLACED")
        print(f"Output saved to: {output_def_path}")
        
        return changed_count
    
    @staticmethod
    def change_upper_die_macro_status_to_fixed(
        upper_die_macro_names: Set[str], 
        input_def_path: str, 
        output_def_path: str
    ) -> int:
        """
        Change upper die macro status from PLACED to FIXED in DEF file.
        
        Args:
            upper_die_macro_names: Set of upper die macro component names
            input_def_path: Input DEF file path
            output_def_path: Output DEF file path
        
        Returns:
            int: Number of macro statuses changed
        """
        print(f"Changing upper die macro status from PLACED to FIXED: {input_def_path}")
        print(f"Output will be saved to: {output_def_path}")
        
        # Read input file
        with open(input_def_path, 'r') as infile:
            lines = infile.readlines()
        
        # Process lines
        output_lines, changed_count = DefProcessor._change_upper_die_macro_status_in_lines(
            upper_die_macro_names, lines, 'PLACED', 'FIXED'
        )
        
        # Write to output file
        if os.path.dirname(output_def_path):
            os.makedirs(os.path.dirname(output_def_path), exist_ok=True)
        
        with open(output_def_path, 'w') as outfile:
            outfile.writelines(output_lines)
        
        print(f"Changed {changed_count} upper die macro statuses from PLACED to FIXED")
        print(f"Output saved to: {output_def_path}")
        
        return changed_count
    
    @staticmethod
    def identify_macros_from_instance(problem_instance) -> Set[str]:
        """
        Identify macro names from a ProblemInstance.
        
        Args:
            problem_instance: ProblemInstance object
        
        Returns:
            Set of macro names (component names)
        """
        # Determine macros if not already done
        if not hasattr(problem_instance, 'macro_names') or problem_instance.macro_names is None:
            problem_instance.determine_macro()
        
        # Get macro names as a set
        macro_names_set = set()
        for name in problem_instance.macro_names:
            name_str = str(name).strip()
            macro_names_set.add(name_str)
        
        return macro_names_set
    
    @staticmethod
    def change_macro_direction(macro_names: Set[str], input_def_path: str, output_def_path: str) -> int:
        """
        Change all macro directions to N in DEF file.
        
        Args:
            macro_names: Set of macro component names
            input_def_path: Input DEF file path
            output_def_path: Output DEF file path
        
        Returns:
            int: Number of macro orientations changed
        """
        print(f"Changing macro directions in DEF file: {input_def_path}")
        print(f"Output will be saved to: {output_def_path}")
        
        # Read input file
        with open(input_def_path, 'r') as infile:
            lines = infile.readlines()
        
        # Process lines
        output_lines, changed_count = DefProcessor._change_direction_in_lines(macro_names, lines)
        
        # Write to output file
        if os.path.dirname(output_def_path):
            os.makedirs(os.path.dirname(output_def_path), exist_ok=True)
        
        with open(output_def_path, 'w') as outfile:
            outfile.writelines(output_lines)
        
        print(f"Changed direction to N for {changed_count} macro components")
        print(f"Output saved to: {output_def_path}")
        
        return changed_count
    
    @staticmethod
    def _round_x_to_routing_track(value) -> int:
        """Round x to nearest 380n+260."""
        val = float(value)
        n = round((val - 260) / 380)
        return int(380 * n + 260)
    
    @staticmethod
    def _round_y_to_routing_track(value) -> int:
        """Round y to nearest 280n+210."""
        val = float(value)
        n = round((val - 210) / 280)
        return int(280 * n + 210)
    
    @staticmethod
    def def_post_process(
        all_macro_names: Set[str],
        upper_die_macro_names: Set[str],
        input_def_path: str,
        output_def_path: str,
    ) -> dict:
        """
        Single-pass DEF post-process: fix status, change direction, round coords, add suffixes.
        
        In one traversal of the DEF file:
        1. Change macro status from PLACED to FIXED (all_macro_names)
        2. Change macro orientation to N (all_macro_names)
        3. Round FIXED macro (x,y) to routing tracks: x=380n+260, y=280n+210
        4. Add die suffixes: _upper for upper_die_macro_names, _bottom for others
        
        DEF format (two lines per component):
          - component_name macro_type [optional...]
            + PLACED|FIXED ( x y ) orientation ;
        
        Args:
            all_macro_names: All macro component names (upper + bottom)
            upper_die_macro_names: Upper die macro names (for _upper suffix)
            input_def_path: Input DEF path
            output_def_path: Output DEF path
        
        Returns:
            dict with fixed_count, direction_count, rounded_count, upper_count, bottom_count
        """
        if os.path.dirname(output_def_path):
            os.makedirs(os.path.dirname(output_def_path), exist_ok=True)
        
        # Placement line format: "    + PLACED|FIXED ( x y ) orientation ;"
        # split() -> ['+', 'PLACED'|'FIXED', '(', x, y, ')', orientation, ';']
        fixed_count = 0
        direction_count = 0
        rounded_count = 0
        upper_count = 0
        bottom_count = 0
        in_components = False
        pending_def_line: Optional[str] = None
        pending_name: Optional[str] = None
        pending_type: Optional[str] = None
        pending_indent: str = ''
        pending_rest: List[str] = []
        
        with open(input_def_path, 'r') as infile, open(output_def_path, 'w') as outfile:
            for line in infile:
                stripped = line.strip()
                
                if stripped.startswith('COMPONENTS'):
                    in_components = True
                    pending_def_line = None
                    outfile.write(line)
                    continue
                if stripped.startswith('END COMPONENTS'):
                    in_components = False
                    pending_def_line = None
                    outfile.write(line)
                    continue
                
                if not in_components:
                    outfile.write(line)
                    continue
                
                fields = stripped.split()
                
                if len(fields) >= 2 and fields[0] == '-':
                    if pending_def_line is not None:
                        outfile.write(pending_def_line)
                    component_name = fields[1]
                    macro_type = fields[2] if len(fields) >= 3 else ''
                    rest = fields[3:] if len(fields) > 3 else []
                    indent = line[: len(line) - len(line.lstrip())]
                    line_end = '\n' if line.endswith('\n') else ''
                    pending_def_line = line
                    pending_name = component_name
                    pending_type = macro_type
                    pending_indent = indent
                    pending_rest = rest
                    continue
                
                if pending_def_line is not None and len(fields) >= 8 and fields[0] == '+' and fields[2] == '(' and fields[5] == ')':
                    status = fields[1]
                    x, y = fields[3], fields[4]
                    ori = fields[6]
                    indent = line[: len(line) - len(line.lstrip())]
                    name = pending_name
                    mtype = pending_type
                    is_macro = name in all_macro_names
                    is_upper = name in upper_die_macro_names

                    if is_macro:
                        status = 'FIXED'
                        fixed_count += 1
                        ori = 'N'
                        direction_count += 1
                        x = str(DefProcessor._round_x_to_routing_track(x))
                        y = str(DefProcessor._round_y_to_routing_track(y))
                        rounded_count += 1

                    new_place = f'{indent}+ {status} ( {x} {y} ) {ori} ;'
                    if line.endswith('\n'):
                        new_place += '\n'

                    new_type = mtype + '_upper' if is_upper else mtype + '_bottom'
                    if is_upper:
                        upper_count += 1
                    else:
                        bottom_count += 1
                    new_def_fields = ['-', name, new_type] + pending_rest
                    def_line = pending_indent + ' '.join(new_def_fields) + ('\n' if pending_def_line.endswith('\n') else '')
                    outfile.write(def_line)
                    outfile.write(new_place)
                    pending_def_line = None
                    pending_name = None
                    pending_type = None
                    pending_rest = []
                    continue
                
                if pending_def_line is not None:
                    outfile.write(pending_def_line)
                    pending_def_line = None
                    pending_name = None
                    pending_type = None
                    pending_rest = []
                outfile.write(line)
        
        if pending_def_line is not None:
            outfile.write(pending_def_line)
        
        return {
            'fixed_count': fixed_count,
            'direction_count': direction_count,
            'rounded_count': rounded_count,
            'upper_count': upper_count,
            'bottom_count': bottom_count,
        }
    
    @staticmethod
    def fix_macro_in_def_file(macro_names: Set[str], input_def_path: str, output_def_path: str) -> int:
        """
        Fix macro status in DEF file: change PLACED to FIXED for all macros.
        
        Args:
            macro_names: Set of macro component names
            input_def_path: Input DEF file path
            output_def_path: Output DEF file path
        
        Returns:
            int: Number of macros fixed
        """
        print(f"Processing DEF file: {input_def_path}")
        print(f"Output will be saved to: {output_def_path}")
        
        # Read input file
        with open(input_def_path, 'r') as infile:
            lines = infile.readlines()
        
        # Process lines
        output_lines, fixed_count = DefProcessor._fix_macro_in_lines(macro_names, lines)
        
        # Write to output file
        os.makedirs(os.path.dirname(output_def_path), exist_ok=True)
        with open(output_def_path, 'w') as outfile:
            outfile.writelines(output_lines)
        
        print(f"Fixed {fixed_count} macro components")
        print(f"Output saved to: {output_def_path}")
        
        return fixed_count
    
    @staticmethod
    def add_die_suffixes_to_def_file(
        upper_die_macro_names: Set[str],
        input_def_path: str,
        output_def_path: str
    ) -> Tuple[int, int]:
        """
        Add suffixes to component class (macro_name) in DEF file:
        - _upper suffix for upper die macros' class
        - _bottom suffix for all other components' class
        Only processes content between COMPONENTS and END COMPONENTS sections.
        
        DEF file format:
          - component_name macro_name
            + PLACED ( x y ) orient ;
        
        Args:
            upper_die_macro_names: Set of upper die macro component names
            input_def_path: Input DEF file path
            output_def_path: Output DEF file path
        
        Returns:
            tuple: (num_upper_renamed, num_bottom_renamed) - number of components renamed
        """
        print(f"Adding die suffixes to DEF file: {input_def_path}")
        print(f"Output will be saved to: {output_def_path}")
        print(f"Upper die macros: {len(upper_die_macro_names)}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_def_path), exist_ok=True)
        
        upper_count = 0
        bottom_count = 0
        in_components_section = False
        
        with open(input_def_path, 'r') as infile, open(output_def_path, 'w') as outfile:
            for line in infile:
                stripped = line.strip()
                
                # Check if we're entering the COMPONENTS section
                if stripped.startswith('COMPONENTS'):
                    in_components_section = True
                    outfile.write(line)
                    continue
                
                # Check if we're leaving the COMPONENTS section
                if stripped.startswith('END COMPONENTS'):
                    in_components_section = False
                    outfile.write(line)
                    continue
                
                # Only process if we're in the COMPONENTS section
                if in_components_section:
                    # Check if this is a component definition line (starts with "  -")
                    if stripped.startswith('-'):
                        # Split the line to get fields
                        fields = stripped.split()
                        if len(fields) >= 3:
                            # fields[0] is "-", fields[1] is component_name (name), fields[2] is class (macro_name)
                            component_name = fields[1]  # name
                            macro_class = fields[2]     # class
                            
                            # Determine if this is an upper die macro
                            is_upper_die = component_name in upper_die_macro_names
                            
                            # Add appropriate suffix to class
                            if is_upper_die:
                                new_macro_class = macro_class + '_upper'
                                upper_count += 1
                            else:
                                new_macro_class = macro_class + '_bottom'
                                bottom_count += 1
                            
                            # Reconstruct the line with new class name
                            # Preserve original indentation and line ending
                            indent = line[:len(line) - len(line.lstrip())]
                            line_ending = '\n' if line.endswith('\n') else ''
                            
                            # Reconstruct: "- name new_class [any remaining fields]"
                            new_fields = ['-', component_name, new_macro_class] + fields[3:]
                            new_line = indent + ' '.join(new_fields) + line_ending
                            outfile.write(new_line)
                        else:
                            # Line doesn't have enough fields, write as-is
                            outfile.write(line)
                    else:
                        # Not a component definition line, write as-is
                        outfile.write(line)
                else:
                    # Outside COMPONENTS section, write as-is
                    outfile.write(line)
        
        print(f"Renamed {upper_count} component classes with _upper suffix")
        print(f"Renamed {bottom_count} component classes with _bottom suffix")
        print(f"Output saved to: {output_def_path}")
        
        return upper_count, bottom_count
    
    @staticmethod
    def process_def_file(
        macro_names: Set[str],
        upper_die_macro_names: Set[str],
        input_def_path: str,
        output_def_path: str,
        add_suffixes: bool = True,
        fix_macro_status: bool = True
    ) -> dict:
        """
        Process DEF file: fix macro status and/or add die suffixes.
        
        Args:
            macro_names: Set of all macro component names (for fixing status)
            upper_die_macro_names: Set of upper die macro component names (for adding _upper suffix)
            input_def_path: Input DEF file path
            output_def_path: Output DEF file path
            add_suffixes: Whether to add die suffixes to component names
            fix_macro_status: Whether to fix macro status from PLACED to FIXED
        
        Returns:
            dict: Processing results with counts
        """
        results = {
            'fixed_count': 0,
            'upper_renamed': 0,
            'bottom_renamed': 0
        }
        
        # If both operations are needed, we need an intermediate file
        if add_suffixes and fix_macro_status:
            intermediate_path = output_def_path + '.tmp'
            
            # First, add suffixes
            upper_count, bottom_count = DefProcessor.add_die_suffixes_to_def_file(
                upper_die_macro_names,
                input_def_path,
                intermediate_path
            )
            results['upper_renamed'] = upper_count
            results['bottom_renamed'] = bottom_count
            
            # Update macro_names to include suffixes for the fix_macro_status step
            updated_macro_names = {name + '_upper' if name in upper_die_macro_names else name + '_bottom' 
                                 for name in macro_names}
            
            # Fix macro status on the intermediate file
            fixed_count = DefProcessor.fix_macro_in_def_file(
                updated_macro_names,
                intermediate_path,
                output_def_path
            )
            results['fixed_count'] = fixed_count
            # Remove intermediate file
            os.remove(intermediate_path)
        else:
            # Only one operation needed
            if add_suffixes:
                upper_count, bottom_count = DefProcessor.add_die_suffixes_to_def_file(
                    upper_die_macro_names,
                    input_def_path,
                    output_def_path
                )
                results['upper_renamed'] = upper_count
                results['bottom_renamed'] = bottom_count
            elif fix_macro_status:
                results['fixed_count'] = DefProcessor.fix_macro_in_def_file(
                    macro_names,
                    input_def_path,
                    output_def_path
                )
        
        return results
    
    @classmethod
    def fix_def_file_from_instance(cls, problem_instance, input_def_path: str, output_def_path: str, 
                                   change_direction: bool = True) -> dict:
        """
        Convenience method: identify macros from problem_instance and fix DEF file.
        Also optionally changes macro directions to N.
        
        Args:
            problem_instance: ProblemInstance object
            input_def_path: Input DEF file path
            output_def_path: Output DEF file path
            change_direction: Whether to also change macro directions to N (default: True)
        
        Returns:
            dict: {'fixed_count': int, 'changed_direction_count': int}
        """
        # Identify macros
        macro_names = cls.identify_macros_from_instance(problem_instance)
        print(f"Found {len(macro_names)} macros")
        
        print(f"Processing DEF file: {input_def_path}")
        print(f"Output will be saved to: {output_def_path}")
        
        # Read input file
        with open(input_def_path, 'r') as infile:
            lines = infile.readlines()
        
        results = {'fixed_count': 0, 'changed_direction_count': 0}
        
        if change_direction:
            # Do both operations in memory without intermediate file
            # First, fix macro status (PLACED -> FIXED)
            lines, fixed_count = cls._fix_macro_in_lines(macro_names, lines)
            results['fixed_count'] = fixed_count
            print(f"Fixed {fixed_count} macro components")
            
            # Then, change macro directions to N (operate on the result from previous step)
            lines, changed_count = cls._change_direction_in_lines(macro_names, lines)
            results['changed_direction_count'] = changed_count
            print(f"Changed direction to N for {changed_count} macro components")
        else:
            # Only fix macro status
            lines, fixed_count = cls._fix_macro_in_lines(macro_names, lines)
            results['fixed_count'] = fixed_count
            print(f"Fixed {fixed_count} macro components")
        
        # Write to output file
        os.makedirs(os.path.dirname(output_def_path), exist_ok=True)
        with open(output_def_path, 'w') as outfile:
            outfile.writelines(lines)
        
        print(f"Output saved to: {output_def_path}")
        
        return results
    
    @classmethod
    def process_def_file_from_instance(
        cls,
        problem_instance,
        upper_die_macro_names: List[str],
        input_def_path: str,
        output_def_path: str,
        add_suffixes: bool = True,
        fix_macro_status: bool = True
    ) -> dict:
        """
        Convenience method: process DEF file with both suffix addition and status fixing.
        
        Args:
            problem_instance: ProblemInstance object
            upper_die_macro_names: List of upper die macro component names
            input_def_path: Input DEF file path
            output_def_path: Output DEF file path
            add_suffixes: Whether to add die suffixes
            fix_macro_status: Whether to fix macro status
        
        Returns:
            dict: Processing results with counts
        """
        # Identify all macros
        all_macro_names = cls.identify_macros_from_instance(problem_instance)
        print(f"Found {len(all_macro_names)} total macros")
        
        # Convert upper_die_macro_names to set
        upper_die_macro_set = set(str(name).strip() for name in upper_die_macro_names)
        print(f"Upper die macros: {len(upper_die_macro_set)}")
        
        # Process DEF file
        results = cls.process_def_file(
            all_macro_names,
            upper_die_macro_set,
            input_def_path,
            output_def_path,
            add_suffixes=add_suffixes,
            fix_macro_status=fix_macro_status
        )
        
        return results

