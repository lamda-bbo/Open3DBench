export DESIGN_NAME = ariane
export DESIGN_NICKNAME = ariane133
export PLATFORM    = nangate45

export SYNTH_HIERARCHICAL = 1
export RTLMP_FLOW = 1
export FLOW_VARIANT = 2D
# export MACRO_PLACEMENT = mp_out

# RTL_MP Settings
export RTLMP_MAX_INST = 30000
export RTLMP_MIN_INST = 5000
export RTLMP_MAX_MACRO = 16
export RTLMP_MIN_MACRO = 4

export VERILOG_FILES = ./designs/src/$(DESIGN_NICKNAME)/ariane.sv2v.v \
                       ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/macros.v

export SDC_FILE      = ./designs/$(PLATFORM)/ariane133/ariane.sdc

export ADDITIONAL_LEFS = $(PLATFORM_DIR)/lef/fakeram45_256x16.lef
export ADDITIONAL_LIBS = $(PLATFORM_DIR)/lib/fakeram45_256x16.lib

export DIE_AREA    = 0 0 1500 1500
export CORE_AREA   = 10 12 1448 1448

# export DIE_AREA    = 0 0 1000 1000
# export CORE_AREA   = 10 12 1000 1000

export PLACE_PINS_ARGS = -exclude left:0-500 -exclude left:1000-1500: -exclude right:* -exclude top:* -exclude bottom:*

export MACRO_PLACE_HALO    = 10 10
export MACRO_PLACE_CHANNEL = 20 20
export TNS_END_PERCENT     = 100
export SKIP_GATE_CLONING   = 1

export DETAILED_ROUTE_ARGS = -droute_end_iter 0
export GLOBAL_ROUTE_ARGS = -allow_congestion -verbose -congestion_iterations 2
