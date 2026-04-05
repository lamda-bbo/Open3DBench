export DESIGN_NAME = bp_quad
export DESIGN_NICKNAME = bp_quad
export PLATFORM    = nangate45_3D

export SYNTH_HIERARCHICAL = 1
export RTLMP_FLOW = 0
export FLOW_VARIANT ?= 3D
# export MACRO_PLACEMENT = mp_out

# RTL_MP Settings
export RTLMP_MAX_INST = 30000
export RTLMP_MIN_INST = 5000
export RTLMP_MAX_MACRO = 16
export RTLMP_MIN_MACRO = 4

export VERILOG_FILES = ./designs/src/$(DESIGN_NICKNAME)/bsg_chip_block.sv2v.v \
                       ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/macros.v

export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/bsg_chip.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef_upper_shrink/fakeram45_256x48.upper.lef \
                         $(PLATFORM_DIR)/lef_upper_shrink/fakeram45_32x32.upper.lef \
                         $(PLATFORM_DIR)/lef_upper_shrink/fakeram45_64x124.upper.lef \
                         $(PLATFORM_DIR)/lef_upper_shrink/fakeram45_512x64.upper.lef \
                         $(PLATFORM_DIR)/lef_upper_shrink/fakeram45_64x62.upper.lef \
                         $(PLATFORM_DIR)/lef_upper_shrink/fakeram45_128x116.upper.lef \
                         $(PLATFORM_DIR)/lef_upper_shrink/NangateOpenCellLibrary.macro.mod.upper.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_256x48.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_32x32.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_64x124.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_512x64.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_64x62.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_128x116.bottom.lef
                
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib_upper/fakeram45_256x48.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_32x32.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_64x124.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_512x64.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_64x62.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_128x116.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/NangateOpenCellLibrary_typical.upper.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_256x48.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_32x32.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_64x124.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_512x64.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_64x62.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_128x116.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/NangateOpenCellLibrary_typical.bottom.lib 

# export DIE_AREA    = 0 0 3600 3600
# export CORE_AREA   = 10 12 3590 3590 

export DIE_AREA    = 0 0 2500 2500
export CORE_AREA   = 10 12 2500 2500 

# export PLACE_PINS_ARGS = -exclude left:* -exclude right:* -exclude top:* -exclude bottom:0-1000 -exclude bottom:2400-3600

export MACRO_PLACE_HALO = 10 10
export MACRO_PLACE_CHANNEL = 20 20

export DETAILED_ROUTE_ARGS = -droute_end_iter 0
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 2
