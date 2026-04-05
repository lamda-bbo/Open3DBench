export DESIGN_NAME = swerv_wrapper
export PLATFORM    = nangate45_3D

export SYNTH_HIERARCHICAL = 1
export FLOW_VARIANT = lol
export PLACE_LOL_ROOT ?= ../../Place-LoL
export INPUT_DEF = $(PLACE_LOL_ROOT)/binaries/converted_output/${DEF_VARIANT}/${METHOD}/swerv_wrapper.def
export IDEAL_CLOCK = 1

export VERILOG_FILES = ./designs/src/swerv/swerv_wrapper.sv2v.v \
                       ./designs/$(PLATFORM)/swerv/macros.v
export SDC_FILE      = ./designs/$(PLATFORM)/swerv_wrapper/swerv_wrapper.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef_upper/fakeram45_2048x39.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/fakeram45_256x34.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/fakeram45_64x21.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/NangateOpenCellLibrary.macro.mod.upper.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_2048x39.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_256x34.bottom.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_64x21.bottom.lef 
                
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib_upper/fakeram45_2048x39.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_256x34.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/fakeram45_64x21.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/NangateOpenCellLibrary_typical.upper.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_2048x39.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_256x34.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_64x21.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/NangateOpenCellLibrary_typical.bottom.lib 

export DIE_AREA    = 0 0 800 700
export CORE_AREA   = 0 0 800 700

export MACRO_PLACE_HALO = 10 10
export MACRO_PLACE_CHANNEL = 20 20

export PLACE_DENSITY = 0.43
export TNS_END_PERCENT        = 100

export DETAILED_ROUTE_ARGS = -droute_end_iter 5
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 5
