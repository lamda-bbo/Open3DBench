export DESIGN_NAME = swerv
export PLATFORM    = nangate45_3D

export VERILOG_FILES = $(DESIGN_HOME)/src/$(DESIGN_NAME)/swerv_wrapper.sv2v.v
export SDC_FILE      = $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NAME)/swerv.sdc

export SYNTH_HIERARCHICAL = 1
export FLOW_VARIANT = lol
export PLACE_LOL_ROOT ?= ../../Place-LoL
export INPUT_DEF = $(PLACE_LOL_ROOT)/binaries/converted_output/${DEF_VARIANT}/${METHOD}/swerv.def
export IDEAL_CLOCK = 1

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef_upper/NangateOpenCellLibrary.macro.mod.upper.lef \
                         
                
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib_upper/NangateOpenCellLibrary_typical.upper.lib \
                         $(PLATFORM_DIR)/lib_bottom/NangateOpenCellLibrary_typical.bottom.lib 

export DIE_AREA    = 0 0 350 350
export CORE_AREA   = 0 0 350 350

export PLACE_DENSITY_LB_ADDON = 0.25
export TNS_END_PERCENT        = 100

export DETAILED_ROUTE_ARGS = -droute_end_iter 5
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 5
