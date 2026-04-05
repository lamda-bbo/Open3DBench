export DESIGN_NICKNAME = bp_multi
export DESIGN_NAME = bp_multi_top
export PLATFORM    = nangate45_3D

export SYNTH_HIERARCHICAL = 1
export RTLMP_FLOW = 1
export FLOW_VARIANT ?= 3D
# export MACRO_PLACEMENT = mp_out
#
# RTL_MP Settings
export RTLMP_MAX_INST = 30000
export RTLMP_MIN_INST = 5000
export RTLMP_MAX_MACRO = 12
export RTLMP_MIN_MACRO = 4 

export VERILOG_FILES = ./designs/src/$(DESIGN_NAME)/pickled.v \
                       ./designs/$(PLATFORM)/$(DESIGN_NAME)/macros.v
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NAME)/bp_multi_top.sdc
export ABC_AREA      = 1

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef_upper/fakeram45_512x64.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/fakeram45_256x96.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/fakeram45_32x64.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/fakeram45_64x7.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/fakeram45_64x15.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/fakeram45_64x96.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/NangateOpenCellLibrary.macro.mod.upper.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_512x64.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_256x96.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_32x64.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_64x7.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_64x15.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_64x96.bottom.lef \
                
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib_upper/fakeram45_512x64.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_256x96.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_32x64.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_64x7.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_64x15.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_64x96.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/NangateOpenCellLibrary_typical.upper.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_512x64.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_256x96.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_32x64.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_64x7.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_64x15.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_64x96.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/NangateOpenCellLibrary_typical.bottom.lib 

# export DIE_AREA    = 0 0 1100 1100 
# export CORE_AREA   = 10.07 9.8 1090 1090

export DIE_AREA    = 0 0 800 800 
export CORE_AREA   = 10.07 9.8 800 800

# export PLACE_PINS_ARGS = -exclude left:100-1100 -exclude right:100-1100 -exclude top:*

export MACRO_PLACE_HALO = 10 10
export MACRO_PLACE_CHANNEL = 20 20

export PLACE_DENSITY_LB_ADDON = 0.05
export SKIP_GATE_CLONING      = 1

export DETAILED_ROUTE_ARGS = -droute_end_iter 0
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 2