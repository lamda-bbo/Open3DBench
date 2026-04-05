export DESIGN_NAME = ariane136
export DESIGN_NICKNAME = ariane136
export PLATFORM    = nangate45_3D

export SYNTH_HIERARCHICAL = 1
export FLOW_VARIANT = lol
export PLACE_LOL_ROOT ?= ../../Place-LoL
export INPUT_DEF = $(PLACE_LOL_ROOT)/binaries/converted_output/${DEF_VARIANT}/${METHOD}/ariane136.def
export IDEAL_CLOCK = 1

export VERILOG_FILES = ./designs/src/$(DESIGN_NICKNAME)/ariane.sv2v.v \
                       ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/macros.v

export SDC_FILE      = ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/ariane.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef_upper/fakeram45_256x16.upper.lef \
                         $(PLATFORM_DIR)/lef_upper/NangateOpenCellLibrary.macro.mod.upper.lef \
                         $(PLATFORM_DIR)/lef_bottom/fakeram45_256x16.bottom.lef 
                
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib_upper/fakeram45_256x16.upper.lib \
                         $(PLATFORM_DIR)/lib_upper/NangateOpenCellLibrary_typical.upper.lib \
                         $(PLATFORM_DIR)/lib_bottom/fakeram45_256x16.bottom.lib \
                         $(PLATFORM_DIR)/lib_bottom/NangateOpenCellLibrary_typical.bottom.lib 


export DIE_AREA    = 0 0 1000 1000
export CORE_AREA   = 0 0 1000 1000

export MACRO_PLACE_HALO = 10 10
export MACRO_PLACE_CHANNEL = 20 20
export TNS_END_PERCENT = 100

export DETAILED_ROUTE_ARGS = -droute_end_iter 5
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 5
