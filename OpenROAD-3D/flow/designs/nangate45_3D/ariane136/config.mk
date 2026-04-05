export DESIGN_NAME = ariane136
export DESIGN_NICKNAME = ariane136
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
export RTLMP_SIGNATURE_NET_THRESHOLD = 30

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
export CORE_AREA   = 10 12 1000 1000

# export PLACE_PINS_ARGS = -exclude left:0-500 -exclude left:1000-1500: -exclude right:* -exclude top:* -exclude bottom:*

export MACRO_PLACE_HALO = 10 10
export MACRO_PLACE_CHANNEL = 20 20
export TNS_END_PERCENT = 100

export DETAILED_ROUTE_ARGS = -droute_end_iter 0
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 2
