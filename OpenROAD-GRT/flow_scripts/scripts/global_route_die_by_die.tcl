# Wrapper for die-by-die GRT implementation in scripts_3D.
source [file join $::env(SCRIPTS_DIR) ../scripts_3D/global_route_die_by_die.tcl]

# This is a complete replacement for the stock global-route step.  Exit the
# OpenROAD process cleanly so the stock single-pass commands do not run.
exit 0
