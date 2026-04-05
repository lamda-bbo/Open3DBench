export DESIGN_NICKNAME = bp_fe
export DESIGN_NAME = bp_fe_top
export PLATFORM    = nangate45_3D

export SYNTH_HIERARCHICAL = 1
export RTLMP_FLOW = 0
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
export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NAME)/bp_fe_top.sdc

# export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef_upper/fakeram45_512x64.upper.lef \
#                          $(PLATFORM_DIR)/lef_upper/fakeram45_64x7.upper.lef \
#                          $(PLATFORM_DIR)/lef_upper/fakeram45_64x96.upper.lef \
#                          $(PLATFORM_DIR)/lef_upper/NangateOpenCellLibrary.macro.mod.upper.lef \
#                          $(PLATFORM_DIR)/lef_bottom/fakeram45_512x64.bottom.lef \
#                          $(PLATFORM_DIR)/lef_bottom/fakeram45_64x7.bottom.lef \
#                          $(PLATFORM_DIR)/lef_bottom/fakeram45_64x96.bottom.lef

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef_upper/fakeram45_512x64.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/fakeram45_64x7.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/fakeram45_64x96.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/NangateOpenCellLibrary.macro.mod.upper.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_512x64.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_64x7.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_64x96.bottom.lef             
                
# export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib_upper/fakeram45_512x64.upper.lib \
#                          $(PLATFORM_DIR)/lib_upper/fakeram45_64x7.upper.lib \
#                          $(PLATFORM_DIR)/lib_upper/fakeram45_64x96.upper.lib \
#                          $(PLATFORM_DIR)/lib_bottom/fakeram45_512x64.bottom.lib \
#                          $(PLATFORM_DIR)/lib_bottom/fakeram45_64x7.bottom.lib \
#                          $(PLATFORM_DIR)/lib_bottom/fakeram45_64x96.bottom.lib \
#                          $(PLATFORM_DIR)/lib_bottom/NangateOpenCellLibrary_typical.bottom.lib 

export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib_upper/fakeram45_512x64.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_64x7.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_64x96.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/NangateOpenCellLibrary_typical.upper.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_512x64.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_64x7.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_64x96.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/NangateOpenCellLibrary_typical.bottom.lib 


export DIE_AREA    = 0 0 600 500 
export CORE_AREA   = 10 10 590 490 

# export PLACE_PINS_ARGS = -exclude left:400-700 -exclude right:400-700 -exclude top:*


export MACRO_PLACE_HALO = 10 10
export MACRO_PLACE_CHANNEL = 20 20

export PLACE_DENSITY_LB_ADDON = 0.10
export PLACE_DENSITY_MAX_POST_HOLD = 0.12
export TNS_END_PERCENT        = 100

export DETAILED_ROUTE_ARGS = -droute_end_iter 0
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 2