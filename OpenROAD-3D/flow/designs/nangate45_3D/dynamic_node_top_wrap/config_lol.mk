export DESIGN_NICKNAME = dynamic_node
export DESIGN_NAME = dynamic_node_top_wrap
export PLATFORM    = nangate45_3D

export SYNTH_HIERARCHICAL = 1
export FLOW_VARIANT = lol
export PLACE_LOL_ROOT ?= ../../Place-LoL
export INPUT_DEF = $(PLACE_LOL_ROOT)/binaries/converted_output/${DEF_VARIANT}/${METHOD}/dynamic_node.def
export IDEAL_CLOCK = 1

export VERILOG_FILES = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/dynamic_node.pickle.v
export SDC_FILE      = $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NICKNAME)/dynamic_node_top_wrap.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef_upper/NangateOpenCellLibrary.macro.mod.upper.lef \
                         
                
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib_upper/NangateOpenCellLibrary_typical.upper.lib \
                         $(PLATFORM_DIR)/lib_bottom/NangateOpenCellLibrary_typical.bottom.lib 

export DIE_AREA    = 0 0 150 150
export CORE_AREA   = 0 0 150 150 

export PLACE_DENSITY_LB_ADDON = 0.20
export TNS_END_PERCENT = 100

export DETAILED_ROUTE_ARGS = -droute_end_iter 5
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 5
