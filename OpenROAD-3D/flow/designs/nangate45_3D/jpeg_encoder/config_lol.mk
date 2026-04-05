export DESIGN_NICKNAME = jpeg
export DESIGN_NAME = jpeg_encoder
export PLATFORM    = nangate45_3D

export SYNTH_HIERARCHICAL = 1
export FLOW_VARIANT = lol
export PLACE_LOL_ROOT ?= ../../Place-LoL
export INPUT_DEF = $(PLACE_LOL_ROOT)/binaries/converted_output/${DEF_VARIANT}/${METHOD}/jpeg.def
export IDEAL_CLOCK = 1

export VERILOG_FILES = $(sort $(wildcard $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/*.v))
export VERILOG_INCLUDE_DIRS = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/include
export SDC_FILE = $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NICKNAME)/jpeg_encoder.sdc
export ABC_AREA = 1

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef_upper/NangateOpenCellLibrary.macro.mod.upper.lef \
                         
                
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib_upper/NangateOpenCellLibrary_typical.upper.lib \
                         $(PLATFORM_DIR)/lib_bottom/NangateOpenCellLibrary_typical.bottom.lib 

export DIE_AREA    = 0 0 300 300
export CORE_AREA   = 0 0 300 300

export PLACE_DENSITY_LB_ADDON = 0.20
export TNS_END_PERCENT        = 100

export DETAILED_ROUTE_ARGS = -droute_end_iter 5
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 5
