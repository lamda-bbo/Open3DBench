# Define the grid size
set grid_size 10

# Define the output directory
set output_dir $env(HOTSPOT_OUTPUT)/

# Load the necessary libraries
foreach varName [array names env PLATFORMS_*] {
    read_liberty $env($varName)
}

# Read the Verilog and SDC files
read_verilog $env(FINAL_V)

link_design $env(NAME)
read_sdc $env(FINAL_SDC)

# Read the SPEF file
read_spef $env(FINAL_SPEF) >> log.tmp

# Set the power activity
set_power_activity -input -activity 0.1
set_power_activity -input_port reset -activity 0

# Helper function to read file content as a large string
proc read_file_as_string {filename} {
    # Open file for reading
    set file_id [open $filename r]
    set content [read $file_id]
    close $file_id
    return $content
}

proc sum_total_power {filename} {
    set total_sum 0.0
    set number_count 0
    # Open the file and process each line
    set file_id [open $filename r]
    
    # Skip the first two lines (headers or separator lines)
    set line1 [gets $file_id]
    set line2 [gets $file_id]

    # Process the rest of the lines
    while {[gets $file_id line] != -1} {
        # Skip empty lines
        if {[string length $line] > 0} {
            # Split the line by spaces
            set columns [split $line]

            # Ensure the line has at least two columns
            if {[llength $columns] > 1} {
                # Get the second-to-last column value
                set value_str [lindex $columns [expr {[llength $columns] - 2}]]

                # Check if value_str is a valid number, if not, set it to 0.0
                if {[regexp {^-?[0-9]+(\.[0-9]*)?(e[+-]?[0-9]+)?$} $value_str]} {
                    set value [expr {$value_str}]
                } else {
                    set value 0.0
                }

                # Add to the total sum
                set total_sum [expr {$total_sum + $value}]
                incr number_count
            }
        }
    }
    close $file_id

    # Return the total sum and the number count
    return $total_sum 
}


# Open the .ptrace file for writing
set ptrace_filename "${output_dir}gcc.ptrace"
set ptrace_file [open $ptrace_filename "w"]

# Create an empty list to store grid names and their corresponding total powers
set grid_names ""
set total_powers ""

# Loop over the grid and execute report_power for each grid
for {set i 0} {$i < $grid_size} {incr i} {
    for {set j 0} {$j < $grid_size} {incr j} {
        # Construct the filename for the grid (Grid_i_j.txt)
        set grid_filename "${output_dir}Grid_($i, $j).txt"
        
        # Check if the grid file exists
        if {[file exists $grid_filename]} {
            # Read the content of the grid file as a large string
            set instance_string [read_file_as_string $grid_filename]
            
            # grid_filename
            file delete $grid_filename

            # Define the output filename for the report
            set report_filename "${output_dir}report_power_grid_($i, $j).txt"

            # Run the report_power command for the grid with the full instance string
            report_power -instances $instance_string >> $report_filename

            if {$i < 10} {
                # 1. 读取文件所有内容
                set fp [open $report_filename r]
                set file_data [read $fp]
                close $fp

                set lines [split $file_data "\n"]
                set new_lines {}

                # 2. 遍历并过滤
                foreach line $lines {
                    # 跳过空行
                    if {[string trim $line] eq ""} { continue }

                    # 按空白字符分割行内容
                    set cols [regexp -all -inline {\S+} $line]

                    # 检查是否为有效的数据行：
                    # 至少有5列，且第4列(索引3，Total Power)必须是数字，避免误删表头
                    set keep_line 1
                    if {[llength $cols] >= 5 && [string is double [lindex $cols 3]]} {
                        set total_pwr [lindex $cols 3]
                        set inst_name [lindex $cols 4]

                        # 核心判断：Instance以max_cap开头 且 Total Power > 1e-4
                        if {[string match "max_cap*" $inst_name] && $total_pwr > 1e-2} {
                            set keep_line 0
                            puts "Info: Removing high-power max_cap cell: $inst_name with Total Power: $total_pwr"
                        }

                        if {$env(NAME) == "bp_fe_top" && $total_pwr > 2e-3} {
                            set keep_line 0
                            puts "Finding cell: $inst_name with Total Power: $total_pwr"
                        }
                    }

                    # 3. 如果不需要删除，则保留该行
                    if {$keep_line} {
                        lappend new_lines $line
                    }
                }

                # 4. 将过滤后的内容写回文件（原地修改）
                set fp [open $report_filename w]
                puts $fp [join $new_lines "\n"]
                close $fp
                
                puts "Info: Filtered high-power max_cap cells in $report_filename"
            }

            # Output to the console
            # puts "Report for Grid_($i, $j) written to $report_filename"

            # Sum the "Total Power" column in the report and scale it by 100
            set total_power [expr {[sum_total_power $report_filename] * 10}]

            # report_filename
            file delete $report_filename

            # Add the grid name and total power to the respective lists
            lappend grid_names "Grid_${i}_${j}"
            lappend total_powers $total_power
        } else {
            puts "Warning: $grid_filename does not exist."
        }
    }
}


# Write the grid names and total powers in the desired format
set grid_line [join $grid_names " "]
set power_line [join $total_powers " "]
puts $ptrace_file "$grid_line"
puts $ptrace_file "$power_line"

# Close the .ptrace file
close $ptrace_file

# Exit STA
exit
