# settings.mk is not under source control. Put variables into this
# file to avoid having to adding the to the make command line.
-include settings.mk

# ==============================================================================
# Uncomment or add the design to run
# ==============================================================================

# DESIGN_CONFIG=./designs/nangate45/aes/config.mk
# DESIGN_CONFIG=./designs/nangate45/ariane133/config.mk
# DESIGN_CONFIG=./designs/nangate45/ariane136/config.mk
# DESIGN_CONFIG=./designs/nangate45/black_parrot/config.mk
# DESIGN_CONFIG=./designs/nangate45/bp_be_top/config.mk
# DESIGN_CONFIG=./designs/nangate45/bp_fe_top/config.mk
DESIGN_CONFIG=./designs/nangate45/bp_multi_top/config.mk
# DESIGN_CONFIG=./designs/nangate45/bp_quad/config.mk
# DESIGN_CONFIG=./designs/nangate45/dynamic_node/config.mk
# DESIGN_CONFIG=./designs/nangate45/gcd/config.mk
# DESIGN_CONFIG=./designs/nangate45/ibex/config.mk
# DESIGN_CONFIG=./designs/nangate45/jpeg/config.mk
# DESIGN_CONFIG=./designs/nangate45/mempool_group/config.mk
# DESIGN_CONFIG=./designs/nangate45/swerv/config.mk
# DESIGN_CONFIG=./designs/nangate45/swerv_wrapper/config.mk
# DESIGN_CONFIG=./designs/nangate45/tinyRocket/config.mk

# DESIGN_CONFIG=./designs/tsmc65lp/aes/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/ariane/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/black_parrot/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/bp_be_top/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/bp_fe_top/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/bp_multi_top/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/coyote/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/dynamic_node/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/gcd/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/ibex/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/jpeg/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/swerv/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/swerv_wrapper/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/tinyRocket/config.mk
# DESIGN_CONFIG=./designs/tsmc65lp/vanilla5/config.mk

# DESIGN_CONFIG=./designs/gf12/aes/config.mk
# DESIGN_CONFIG=./designs/gf12/ariane/config.mk
# DESIGN_CONFIG=./designs/gf12/ca53/config.mk
# DESIGN_CONFIG=./designs/gf12/coyote/config.mk
# DESIGN_CONFIG=./designs/gf12/gcd/config.mk
# DESIGN_CONFIG=./designs/gf12/ibex/config.mk
# DESIGN_CONFIG=./designs/gf12/jpeg/config.mk
# DESIGN_CONFIG=./designs/gf12/swerv_wrapper/config.mk
# DESIGN_CONFIG=./designs/gf12/tinyRocket/config.mk

# DESIGN_CONFIG=./designs/gf12/ariane133/config.mk
# DESIGN_CONFIG=./designs/gf12/bp_dual/config.mk
# DESIGN_CONFIG=./designs/gf12/bp_quad/config.mk
# DESIGN_CONFIG=./designs/gf12/bp_single/config.mk

# DESIGN_CONFIG=./designs/sky130hd/aes/config.mk
# DESIGN_CONFIG=./designs/sky130hd/chameleon/config.mk
# DESIGN_CONFIG=./designs/sky130hd/chameleon_hier/config.mk
# DESIGN_CONFIG=./designs/sky130hd/coyote_tc/config.mk
# DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk
# DESIGN_CONFIG=./designs/sky130hd/ibex/config.mk
# DESIGN_CONFIG=./designs/sky130hd/jpeg/config.mk
# DESIGN_CONFIG=./designs/sky130hd/microwatt/config.mk
# DESIGN_CONFIG=./designs/sky130hd/riscv32i/config.mk

# DESIGN_CONFIG=./designs/sky130hs/aes/config.mk
# DESIGN_CONFIG=./designs/sky130hs/gcd/config.mk
# DESIGN_CONFIG=./designs/sky130hs/ibex/config.mk
# DESIGN_CONFIG=./designs/sky130hs/jpeg/config.mk
# DESIGN_CONFIG=./designs/sky130hs/riscv32i/config.mk

# DESIGN_CONFIG=./designs/asap7/aes/config.mk
# DESIGN_CONFIG=./designs/asap7/ethmac/config.mk
# DESIGN_CONFIG=./designs/asap7/gcd/config.mk
# DESIGN_CONFIG=./designs/asap7/ibex/config.mk
# DESIGN_CONFIG=./designs/asap7/jpeg/config.mk
# DESIGN_CONFIG=./designs/asap7/megaboom/config.mk
# DESIGN_CONFIG=./designs/asap7/mock-array/config.mk
# DESIGN_CONFIG=./designs/asap7/riscv32i/config.mk
# DESIGN_CONFIG=./designs/asap7/swerv_wrapper/config.mk
# DESIGN_CONFIG=./designs/asap7/uart/config.mk

# DESIGN_CONFIG=./designs/intel16/aes/config.mk
# DESIGN_CONFIG=./designs/intel16/gcd/config.mk

# DESIGN_CONFIG=./designs/intel22/aes/config.mk
# DESIGN_CONFIG=./designs/intel22/gcd/config.mk
# DESIGN_CONFIG=./designs/intel22/ibex/config.mk
# DESIGN_CONFIG=./designs/intel22/jpeg/config.mk

# DESIGN_CONFIG=./designs/gf180/aes/config.mk
# DESIGN_CONFIG=./designs/gf180/ibex/config.mk
# DESIGN_CONFIG=./designs/gf180/jpeg/config.mk
# DESIGN_CONFIG=./designs/gf180/riscv32i/config.mk
# DESIGN_CONFIG=./designs/gf180/uart-blocks/config.mk
#
# Default design
# DESIGN_CONFIG ?= ./designs/nangate45/gcd/config.mk

# Default TNS_END_PERCENT value
export TNS_END_PERCENT ?=5

# If we are running headless use offscreen rendering for save_image
ifndef DISPLAY
export QT_QPA_PLATFORM ?= offscreen
endif

# ==============================================================================
#  ____  _____ _____ _   _ ____
# / ___|| ____|_   _| | | |  _ \
# \___ \|  _|   | | | | | | |_) |
#  ___) | |___  | | | |_| |  __/
# |____/|_____| |_|  \___/|_|
#
# ==============================================================================

#-------------------------------------------------------------------------------
# Default target when invoking without specific target.
.DEFAULT_GOAL := finish

#-------------------------------------------------------------------------------
# Proper way to initiate SHELL for make
SHELL          := /usr/bin/env bash
.SHELLFLAGS    := -o pipefail -c

#-------------------------------------------------------------------------------
# Setup variables to point to root / head of the OpenROAD directory
# - the following settings allowed user to point OpenROAD binaries to different
#   location
# - default is current install / clone directory
export FLOW_HOME ?= $(shell pwd)

#-------------------------------------------------------------------------------
# Setup variables to point to other location for the following sub directory
# - designs - default is under current directory
# - platforms - default is under current directory
# - work home - default is current directory
# - utils, scripts, test - default is under current directory
export DESIGN_HOME   ?= $(FLOW_HOME)/designs
export PLATFORM_HOME ?= $(FLOW_HOME)/platforms
export WORK_HOME     ?= .

export UTILS_DIR     ?= $(FLOW_HOME)/util
export SCRIPTS_DIR   ?= $(FLOW_HOME)/scripts
export TEST_DIR      ?= $(FLOW_HOME)/test
# 
export HOTSPOT_SCRIPTS_DIR ?= $(FLOW_HOME)/HotSpot

export MAX_T_PY      := $(HOTSPOT_SCRIPTS_DIR)/scripts/max_t.py
export DIVIDE_GRID_PY      := $(HOTSPOT_SCRIPTS_DIR)/scripts/divide_grid.py
export DIVIDE_DEF_PY      := $(HOTSPOT_SCRIPTS_DIR)/scripts/divide_def.py
export REPORT_POWER_TCL   := $(HOTSPOT_SCRIPTS_DIR)/scripts/run_report_power.tcl
export MERGE_PTRACE_PY      := $(HOTSPOT_SCRIPTS_DIR)/scripts/merge_ptrace.py
export HOTSPOT_OUTPUT   := $(HOTSPOT_SCRIPTS_DIR)/scripts/output
export STA_EXE            ?= $(shell which sta)
export FINAL_DEF ?= $(RESULTS_DIR)/6_final.def
export FINAL_V ?= $(RESULTS_DIR)/6_final.v
export FINAL_SDC ?= $(RESULTS_DIR)/6_1_fill.sdc
export FINAL_SPEF ?= $(RESULTS_DIR)/6_final.spef
export NAME1= $(basename $(SDC_FILE))
export NAME= $(notdir $(NAME1))

export PLATFORMS_TYPICAL_UPPER ?= $(PLATFORM_DIR)/lib_upper/NangateOpenCellLibrary_typical.upper.lib
export PLATFORMS_1024_32_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_1024x32.upper.lib
export PLATFORMS_128_116_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_128x116.upper.lib
export PLATFORMS_128_256_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_128x256.upper.lib
export PLATFORMS_128_32_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_128x32.upper.lib
export PLATFORMS_2048_39_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_2048x39.upper.lib
export PLATFORMS_256_16_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_256x16.upper.lib
export PLATFORMS_256_32_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_256x32.upper.lib
export PLATFORMS_256_34_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_256x34.upper.lib
export PLATFORMS_256_48_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_256x48.upper.lib
export PLATFORMS_256_95_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_256x95.upper.lib
export PLATFORMS_256_96_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_256x96.upper.lib
export PLATFORMS_32_32_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_32x32.upper.lib
export PLATFORMS_32_64_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_32x64.upper.lib
export PLATFORMS_512_64_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_512x64.upper.lib
export PLATFORMS_64_124_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_64x124.upper.lib
export PLATFORMS_64_15_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_64x15.upper.lib
export PLATFORMS_64_21_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_64x21.upper.lib
export PLATFORMS_64_32_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_64x32.upper.lib
export PLATFORMS_64_62_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_64x62.upper.lib
export PLATFORMS_64_64_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_64x64.upper.lib
export PLATFORMS_64_7_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_64x7.upper.lib
export PLATFORMS_64_96_UPPER ?= $(PLATFORM_DIR)/lib_upper/fakeram45_64x96.upper.lib

export PLATFORMS_TYPICAL_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/NangateOpenCellLibrary_typical.bottom.lib
export PLATFORMS_1024_32_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_1024x32.bottom.lib
export PLATFORMS_128_116_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_128x116.bottom.lib
export PLATFORMS_128_256_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_128x256.bottom.lib
export PLATFORMS_128_32_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_128x32.bottom.lib
export PLATFORMS_2048_39_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_2048x39.bottom.lib
export PLATFORMS_256_16_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_256x16.bottom.lib
export PLATFORMS_256_32_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_256x32.bottom.lib
export PLATFORMS_256_34_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_256x34.bottom.lib
export PLATFORMS_256_48_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_256x48.bottom.lib
export PLATFORMS_256_95_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_256x95.bottom.lib
export PLATFORMS_256_96_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_256x96.bottom.lib
export PLATFORMS_32_32_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_32x32.bottom.lib
export PLATFORMS_32_64_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_32x64.bottom.lib
export PLATFORMS_512_64_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_512x64.bottom.lib
export PLATFORMS_64_124_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_64x124.bottom.lib
export PLATFORMS_64_15_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_64x15.bottom.lib
export PLATFORMS_64_21_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_64x21.bottom.lib
export PLATFORMS_64_32_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_64x32.bottom.lib
export PLATFORMS_64_62_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_64x62.bottom.lib
export PLATFORMS_64_64_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_64x64.bottom.lib
export PLATFORMS_64_7_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_64x7.bottom.lib
export PLATFORMS_64_96_BOTTOM ?= $(PLATFORM_DIR)/lib_bottom/fakeram45_64x96.bottom.lib

export PLATFORMS_TYPICAL ?= $(PLATFORM_DIR)/lib/NangateOpenCellLibrary_typical.lib
export PLATFORMS_1024_32 ?= $(PLATFORM_DIR)/lib/fakeram45_1024x32.lib
export PLATFORMS_128_116 ?= $(PLATFORM_DIR)/lib/fakeram45_128x116.lib
export PLATFORMS_128_256 ?= $(PLATFORM_DIR)/lib/fakeram45_128x256.lib
export PLATFORMS_128_32 ?= $(PLATFORM_DIR)/lib/fakeram45_128x32.lib
export PLATFORMS_2048_39 ?= $(PLATFORM_DIR)/lib/fakeram45_2048x39.lib
export PLATFORMS_256_16 ?= $(PLATFORM_DIR)/lib/fakeram45_256x16.lib
export PLATFORMS_256_32 ?= $(PLATFORM_DIR)/lib/fakeram45_256x32.lib
export PLATFORMS_256_34 ?= $(PLATFORM_DIR)/lib/fakeram45_256x34.lib
export PLATFORMS_256_48 ?= $(PLATFORM_DIR)/lib/fakeram45_256x48.lib
export PLATFORMS_256_95 ?= $(PLATFORM_DIR)/lib/fakeram45_256x95.lib
export PLATFORMS_256_96 ?= $(PLATFORM_DIR)/lib/fakeram45_256x96.lib
export PLATFORMS_32_32 ?= $(PLATFORM_DIR)/lib/fakeram45_32x32.lib
export PLATFORMS_32_64 ?= $(PLATFORM_DIR)/lib/fakeram45_32x64.lib
export PLATFORMS_512_64 ?= $(PLATFORM_DIR)/lib/fakeram45_512x64.lib
export PLATFORMS_64_124 ?= $(PLATFORM_DIR)/lib/fakeram45_64x124.lib
export PLATFORMS_64_15 ?= $(PLATFORM_DIR)/lib/fakeram45_64x15.lib
export PLATFORMS_64_21 ?= $(PLATFORM_DIR)/lib/fakeram45_64x21.lib
export PLATFORMS_64_32 ?= $(PLATFORM_DIR)/lib/fakeram45_64x32.lib
export PLATFORMS_64_62 ?= $(PLATFORM_DIR)/lib/fakeram45_64x62.lib
export PLATFORMS_64_64 ?= $(PLATFORM_DIR)/lib/fakeram45_64x64.lib
export PLATFORMS_64_7 ?= $(PLATFORM_DIR)/lib/fakeram45_64x7.lib
export PLATFORMS_64_96 ?= $(PLATFORM_DIR)/lib/fakeram45_64x96.lib
#-------------------------------------------------------------------------------
# Include design and platform configu	ration
include $(DESIGN_CONFIG)

PUBLIC=nangate45 sky130hd sky130hs asap7

ifneq ($(wildcard $(PLATFORM_HOME)/$(PLATFORM)),)
  export PLATFORM_DIR = $(PLATFORM_HOME)/$(PLATFORM)
else ifneq ($(findstring $(PLATFORM),$(PUBLIC)),)
  export PLATFORM_DIR = ./platforms/$(PLATFORM)
else ifneq ($(wildcard ../../$(PLATFORM)),)
  export PLATFORM_DIR = ../../$(PLATFORM)
else
  $(error [ERROR][FLOW] Platform '$(PLATFORM)' not found.)
endif

ifeq ($(MAKELEVEL),0)
$(info [INFO][FLOW] Using platform directory $(PLATFORM_DIR))
endif
include $(PLATFORM_DIR)/config.mk

export GALLERY_REPORT ?= 0
# Enables hierarchical yosys
export SYNTH_HIERARCHICAL ?= 0
export SYNTH_STOP_MODULE_SCRIPT = $(OBJECTS_DIR)/mark_hier_stop_modules.tcl
ifeq ($(SYNTH_HIERARCHICAL), 1)
export HIER_REPORT_SCRIPT = $(SCRIPTS_DIR)/synth_hier_report.tcl
export MAX_UNGROUP_SIZE ?= 0
endif
# Enables Re-synthesis for area reclaim
export RESYNTH_AREA_RECOVER ?= 0
export RESYNTH_TIMING_RECOVER ?= 0
export ABC_AREA ?= 0

# Global setting for Synthesis
export SYNTH_ARGS ?= -flatten

# Global setting for Floorplan
export PLACE_PINS_ARGS

export FLOW_VARIANT ?= base

export GPL_TIMING_DRIVEN ?= 1
export GPL_ROUTABILITY_DRIVEN ?= 1

export ENABLE_DPO ?= 1
export DPO_MAX_DISPLACEMENT ?= 5 1

# Setup working directories
export DESIGN_NICKNAME ?= $(DESIGN_NAME)

export DESIGN_DIR  = $(dir $(DESIGN_CONFIG))
export LOG_DIR     = $(WORK_HOME)/logs/$(PLATFORM)/$(DESIGN_NICKNAME)/$(FLOW_VARIANT)
export OBJECTS_DIR = $(WORK_HOME)/objects/$(PLATFORM)/$(DESIGN_NICKNAME)/$(FLOW_VARIANT)
export REPORTS_DIR = $(WORK_HOME)/reports/$(PLATFORM)/$(DESIGN_NICKNAME)/$(FLOW_VARIANT)
export RESULTS_DIR = $(WORK_HOME)/results/$(PLATFORM)/$(DESIGN_NICKNAME)/$(FLOW_VARIANT)
export HOTSPOT_EXAMPLE_DIR ?= $(FLOW_VARIANT)_$(DEF_VERSION)

ifdef BLOCKS
ifeq ($(MAKELEVEL),0)
  $(info [INFO][FLOW] Invoked hierarchical flow.)
  $(foreach block,$(BLOCKS),$(info Block ${block} needs to be hardened.))
endif
  $(foreach block,$(BLOCKS),$(eval BLOCK_LEFS += ./results/$(PLATFORM)/$(DESIGN_NICKNAME)_$(block)/$(FLOW_VARIANT)/${block}.lef))
  $(foreach block,$(BLOCKS),$(eval BLOCK_LIBS += ./results/$(PLATFORM)/$(DESIGN_NICKNAME)_$(block)/$(FLOW_VARIANT)/${block}.lib))
  $(foreach block,$(BLOCKS),$(eval BLOCK_GDS += ./results/$(PLATFORM)/$(DESIGN_NICKNAME)_$(block)/$(FLOW_VARIANT)/6_final.gds))
  $(foreach block,$(BLOCKS),$(eval BLOCK_CDL += ./results/$(PLATFORM)/$(DESIGN_NICKNAME)_$(block)/$(FLOW_VARIANT)/6_final.cdl))
  $(foreach block,$(BLOCKS),$(eval BLOCK_LOG_FOLDERS += ./logs/$(PLATFORM)/$(DESIGN_NICKNAME)_$(block)/$(FLOW_VARIANT)/))
  export ADDITIONAL_LEFS += $(BLOCK_LEFS)
  export ADDITIONAL_LIBS += $(BLOCK_LIBS)
  export ADDITIONAL_GDS += $(BLOCK_GDS)
  export GDS_FILES += $(BLOCK_GDS)
  ifdef CDL_FILES
    export CDL_FILES += $(BLOCK_CDL)
  endif
endif

export RTLMP_RPT_DIR ?= $(OBJECTS_DIR)/rtlmp
export RTLMP_RPT_FILE ?= partition.txt
export RTLMP_BLOCKAGE_FILE ?= $(OBJECTS_DIR)/rtlmp/partition.txt.blockage

#-------------------------------------------------------------------------------
ifeq (, $(strip $(NPROC)))
  # Linux (utility program)
  NPROC := $(shell nproc 2>/dev/null)

  ifeq (, $(strip $(NPROC)))
    # Linux (generic)
    NPROC := $(shell grep -c ^processor /proc/cpuinfo 2>/dev/null)
  endif
  ifeq (, $(strip $(NPROC)))
    # BSD (at least FreeBSD and Mac OSX)
    NPROC := $(shell sysctl -n hw.ncpu 2>/dev/null)
  endif
  ifeq (, $(strip $(NPROC)))
    # Fallback
    NPROC := 1
  endif
endif
export NUM_CORES := $(NPROC)

export LSORACLE_CMD ?= $(shell command -v lsoracle)
ifeq ($(LSORACLE_CMD),)
  LSORACLE_CMD = $(abspath $(FLOW_HOME)/../tools/install/LSOracle/bin/lsoracle)
endif

LSORACLE_PLUGIN ?= $(abspath $(FLOW_HOME)/../tools/install/yosys/share/yosys/plugin/oracle.so)
export LSORACLE_KAHYPAR_CONFIG ?= $(abspath $(FLOW_HOME)/../tools/install/LSOracle/share/lsoracle/test.ini)
ifneq ($(USE_LSORACLE),)
  YOSYS_FLAGS ?= -m $(LSORACLE_PLUGIN)
endif

YOSYS_FLAGS += -v 3

#-------------------------------------------------------------------------------
# setup all commands used within this flow
TIME_CMD = /usr/bin/time -f 'Elapsed time: %E[h:]min:sec. CPU time: user %U sys %S (%P). Peak memory: %MKB.'
TIME_TEST = $(shell $(TIME_CMD) echo foo 2>/dev/null)
ifeq (, $(strip $(TIME_TEST)))
  TIME_CMD = /usr/bin/time
endif

# The following determine the executable location for each tool used by this flow.
# Priority is given to
#       1 user explicit set with variable in Makefile or command line, for instance setting OPENROAD_EXE
#       2 ORFS compiled tools: openroad, yosys
export OPENROAD_EXE ?= $(shell which openroad)

OPENROAD_ARGS            = -no_init $(OR_ARGS)
OPENROAD_CMD             = $(OPENROAD_EXE) -exit $(OPENROAD_ARGS)
OPENROAD_NO_EXIT_CMD     = $(OPENROAD_EXE) $(OPENROAD_ARGS)
OPENROAD_GUI_CMD         = $(OPENROAD_EXE) -gui $(OR_ARGS)

YOSYS_EXE               ?= $(shell which yosys)

# Use locally installed and built klayout if it exists, otherwise use klayout in path
KLAYOUT_DIR = $(abspath $(FLOW_HOME)/../tools/install/klayout/)
KLAYOUT_BIN_FROM_DIR = $(KLAYOUT_DIR)/klayout

ifeq ($(wildcard $(KLAYOUT_BIN_FROM_DIR)), $(KLAYOUT_BIN_FROM_DIR))
KLAYOUT_CMD ?= sh -c 'LD_LIBRARY_PATH=$(dir $(KLAYOUT_BIN_FROM_DIR)) $$0 "$$@"' $(KLAYOUT_BIN_FROM_DIR)
else
KLAYOUT_CMD ?= $(shell command -v klayout)
endif
KLAYOUT_FOUND            = $(if $(KLAYOUT_CMD),,$(error KLayout not found in PATH))

ifneq ($(shell command -v stdbuf),)
  STDBUF_CMD = stdbuf -o L
endif

#-------------------------------------------------------------------------------
WRAPPED_LEFS = $(foreach lef,$(notdir $(WRAP_LEFS)),$(OBJECTS_DIR)/lef/$(lef:.lef=_mod.lef))
WRAPPED_LIBS = $(foreach lib,$(notdir $(WRAP_LIBS)),$(OBJECTS_DIR)/$(lib:.lib=_mod.lib))
export ADDITIONAL_LEFS += $(WRAPPED_LEFS) $(WRAP_LEFS)
export LIB_FILES += $(WRAP_LIBS) $(WRAPPED_LIBS)

export DONT_USE_LIBS   = $(patsubst %.lib.gz, %.lib, $(addprefix $(OBJECTS_DIR)/lib/, $(notdir $(LIB_FILES))))
export DONT_USE_SC_LIB ?= $(firstword $(DONT_USE_LIBS))

# Stream system used for final result (GDS is default): GDS, GSDII, GDS2, OASIS, or OAS
STREAM_SYSTEM ?= GDS
ifneq ($(findstring GDS,$(shell echo $(STREAM_SYSTEM) | tr '[:lower:]' '[:upper:]')),)
	export STREAM_SYSTEM_EXT := gds
	GDSOAS_FILES = $(GDS_FILES)
	ADDITIONAL_GDSOAS = $(ADDITIONAL_GDS)
	SEAL_GDSOAS = $(SEAL_GDS)
else
	export STREAM_SYSTEM_EXT := oas
	GDSOAS_FILES = $(OAS_FILES)
	ADDITIONAL_GDSOAS = $(ADDITIONAL_OAS)
	SEAL_GDSOAS = $(SEAL_OAS)
endif
export WRAPPED_GDSOAS = $(foreach lef,$(notdir $(WRAP_LEFS)),$(OBJECTS_DIR)/$(lef:.lef=_mod.$(STREAM_SYSTEM_EXT)))

define GENERATE_ABSTRACT_RULE
ifeq ($(wildcard $(3)),)
# There is no unqiue config.mk for this module, use the shared
# block.mk that, by convention, is in the same folder as config.mk
# of the parent macro.
#
# At an early stage, before refining each of the macros, a shared
# block.mk file can be useful to run through the flow to explore
# more global concerns instead of getting mired in the details of
# each macro.
block := $(patsubst ./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/%,%,$(dir $(3)))
$(1) $(2) &:
	$$(UNSET_AND_MAKE) DESIGN_NAME=${block} DESIGN_NICKNAME=$$(DESIGN_NICKNAME)_${block} DESIGN_CONFIG=./designs/$$(PLATFORM)/$$(DESIGN_NICKNAME)/block.mk generate_abstract
else
# There is a unqiue config.mk for this Verilog module
$(1) $(2) &:
	$$(UNSET_AND_MAKE) DESIGN_CONFIG=$(3) generate_abstract
endif
endef

# Targets to harden Blocks in case of hierarchical flow is triggered
.PHONY: build_macros
build_macros: $(BLOCK_LEFS) $(BLOCK_LIBS)

$(foreach block,$(BLOCKS),$(eval $(call GENERATE_ABSTRACT_RULE,./results/$(PLATFORM)/$(DESIGN_NICKNAME)_$(block)/$(FLOW_VARIANT)/${block}.lef,./results/$(PLATFORM)/$(DESIGN_NICKNAME)_$(block)/$(FLOW_VARIANT)/${block}.lib,./designs/$(PLATFORM)/$(DESIGN_NICKNAME)/${block}/config.mk)))
$(foreach block,$(BLOCKS),$(eval ./results/$(PLATFORM)/$(DESIGN_NICKNAME)_$(block)/$(FLOW_VARIANT)/6_final.gds: ./results/$(PLATFORM)/$(DESIGN_NICKNAME)_$(block)/$(FLOW_VARIANT)/${block}.lef))

# Utility to print tool version information
#-------------------------------------------------------------------------------
.PHONY: versions.txt
versions.txt:
	@$(YOSYS_EXE) -V > $@
	@echo openroad `$(OPENROAD_EXE) -version` >> $@
	@$(KLAYOUT_CMD) -zz -v >> $@

# Pre-process libraries
# ==============================================================================

# Create temporary Liberty files which have the proper dont_use properties set
# For use with Yosys and ABC
.SECONDEXPANSION:
$(DONT_USE_LIBS): $$(filter %$$(@F) %$$(@F).gz,$(LIB_FILES))
	@mkdir -p $(OBJECTS_DIR)/lib
	$(UTILS_DIR)/preprocessLib.py -i $^ -o $@

$(OBJECTS_DIR)/lib/merged.lib:
	$(UTILS_DIR)/mergeLib.pl $(PLATFORM)_merged $(DONT_USE_LIBS) > $@

# Pre-process KLayout tech
# ==============================================================================
$(OBJECTS_DIR)/klayout_tech.lef: $(TECH_LEF)
	@mkdir -p $(OBJECTS_DIR)
	cp $< $@

KLAYOUT_ENV_VAR_IN_PATH_VERSION = 0.28.11
ifneq ($(KLAYOUT_CMD),)
    KLAYOUT_VERSION = $(shell $(KLAYOUT_CMD) -v 2>/dev/null | grep 'KLayout' | cut -d ' ' -f2)
else
    KLAYOUT_VERSION = 0.0.0
endif

KLAYOUT_ENV_VAR_IN_PATH = $(shell \
	if [ -z "$(KLAYOUT_VERSION)" ]; then \
		echo "not_found"; \
	elif [ "$$(echo -e "$(KLAYOUT_VERSION)\n$(KLAYOUT_ENV_VAR_IN_PATH_VERSION)" | sort -V | head -n1)" = "$(KLAYOUT_VERSION)" ] && [ "$(KLAYOUT_VERSION)" != "$(KLAYOUT_ENV_VAR_IN_PATH_VERSION)" ]; then \
		echo "invalid"; \
	else \
		echo "valid"; \
	fi)

$(OBJECTS_DIR)/klayout.lyt: $(KLAYOUT_TECH_FILE) $(OBJECTS_DIR)/klayout_tech.lef
ifeq ($(KLAYOUT_ENV_VAR_IN_PATH),valid)
	SC_LEF_RELATIVE_PATH="$$\(env('FLOW_HOME')\)/$(shell realpath --relative-to=$(FLOW_HOME) $(SC_LEF))"; \
	OTHER_LEFS_RELATIVE_PATHS=$$(echo "$(foreach file, $(OBJECTS_DIR)/klayout_tech.lef $(ADDITIONAL_LEFS),<lef-files>$$(realpath --relative-to=$(RESULTS_DIR) $(file))</lef-files>)"); \
	sed 's,<lef-files>.*</lef-files>,<lef-files>'"$$SC_LEF_RELATIVE_PATH"'</lef-files>'"$$OTHER_LEFS_RELATIVE_PATHS"',g' $< > $@
else
	sed 's,<lef-files>.*</lef-files>,$(foreach file, $(OBJECTS_DIR)/klayout_tech.lef $(SC_LEF) $(ADDITIONAL_LEFS),<lef-files>$(shell realpath --relative-to=$(RESULTS_DIR) $(file))</lef-files>),g' $< > $@
endif

$(OBJECTS_DIR)/klayout_wrap.lyt: $(KLAYOUT_TECH_FILE) $(OBJECTS_DIR)/klayout_tech.lef
	sed 's,<lef-files>.*</lef-files>,$(foreach file, $(OBJECTS_DIR)/klayout_tech.lef $(WRAP_LEFS),<lef-files>$(shell realpath --relative-to=$(OBJECTS_DIR)/def $(file))</lef-files>),g' $< > $@
# Create Macro wrappers (if necessary)
# ==============================================================================
WRAP_CFG = $(PLATFORM_DIR)/wrapper.cfg


export TCLLIBPATH := util/cell-veneer $(TCLLIBPATH)
$(WRAPPED_LEFS):
	mkdir -p $(OBJECTS_DIR)/lef $(OBJECTS_DIR)/def
	util/cell-veneer/wrap.tcl -cfg $(WRAP_CFG) -macro $(filter %$(notdir $(@:_mod.lef=.lef)),$(WRAP_LEFS))
	mv $(notdir $@) $@
	mv $(notdir $(@:lef=def)) $(dir $@)../def/$(notdir $(@:lef=def))

$(WRAPPED_LIBS):
	mkdir -p $(OBJECTS_DIR)/lib
	sed 's/library(\(.*\))/library(\1_mod)/g' $(filter %$(notdir $(@:_mod.lib=.lib)),$(WRAP_LIBS)) | sed 's/cell(\(.*\))/cell(\1_mod)/g' > $@

# ==============================================================================
#  ______   ___   _ _____ _   _ _____ ____ ___ ____
# / ___\ \ / / \ | |_   _| | | | ____/ ___|_ _/ ___|
# \___ \\ V /|  \| | | | | |_| |  _| \___ \| |\___ \
#  ___) || | | |\  | | | |  _  | |___ ___) | | ___) |
# |____/ |_| |_| \_| |_| |_| |_|_____|____/___|____/
#
.PHONY: synth
synth: versions.txt \
       $(RESULTS_DIR)/1_synth.v \
       $(RESULTS_DIR)/1_synth.sdc

.PHONY: synth-report
synth-report: synth
	$(UNSET_AND_MAKE) do-synth-report

.PHONY: do-synth-report
do-synth-report:
	($(TIME_CMD) $(OPENROAD_CMD) $(SCRIPTS_DIR)/synth_metrics.tcl) 2>&1 | tee -a $(LOG_DIR)/1_1_yosys.log

# ==============================================================================


# Run Synthesis using yosys
#-------------------------------------------------------------------------------
SYNTH_SCRIPT ?= $(SCRIPTS_DIR)/synth.tcl

$(SYNTH_STOP_MODULE_SCRIPT):
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	($(TIME_CMD) $(YOSYS_EXE) $(YOSYS_FLAGS) -c $(HIER_REPORT_SCRIPT)) 2>&1 | tee $(LOG_DIR)/1_1_yosys_hier_report.log

ifeq ($(SYNTH_HIERARCHICAL), 1)
$(RESULTS_DIR)/1_1_yosys.v: $(SYNTH_STOP_MODULE_SCRIPT)
endif

$(RESULTS_DIR)/1_1_yosys.v $(RESULTS_DIR)/1_synth.sdc &: $(DONT_USE_LIBS) $(WRAPPED_LIBS) $(DONT_USE_SC_LIB) $(DFF_LIB_FILE) $(VERILOG_FILES) $(CACHED_NETLIST) $(LATCH_MAP_FILE) $(ADDER_MAP_FILE) $(SDC_FILE)
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	($(TIME_CMD) $(YOSYS_EXE) $(YOSYS_FLAGS) -c $(SYNTH_SCRIPT)) 2>&1 | tee $(LOG_DIR)/1_1_yosys.log
	cp $(SDC_FILE) $(RESULTS_DIR)/1_synth.sdc

$(RESULTS_DIR)/1_synth.v: $(RESULTS_DIR)/1_1_yosys.v
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	cp $< $@

.PHONY: clean_synth
clean_synth:
	rm -f  $(RESULTS_DIR)/1_*.v $(RESULTS_DIR)/1_synth.sdc
	rm -f  $(REPORTS_DIR)/synth_*
	rm -f  $(LOG_DIR)/1_*
	rm -f  $(SYNTH_STOP_MODULE_SCRIPT)
	rm -rf _tmp_yosys-abc-*


# ==============================================================================
#  _____ _     ___   ___  ____  ____  _        _    _   _
# |  ___| |   / _ \ / _ \|  _ \|  _ \| |      / \  | \ | |
# | |_  | |  | | | | | | | |_) | |_) | |     / _ \ |  \| |
# |  _| | |__| |_| | |_| |  _ <|  __/| |___ / ___ \| |\  |
# |_|   |_____\___/ \___/|_| \_\_|   |_____/_/   \_\_| \_|
#
.PHONY: floorplan
floorplan: $(RESULTS_DIR)/2_floorplan.odb \
           $(RESULTS_DIR)/2_floorplan.sdc

# ==============================================================================

ifneq ($(FOOTPRINT),)
IS_CHIP = 1
else ifneq ($(FOOTPRINT_TCL),)
IS_CHIP = 1
endif

PRESERVED_MAKE_ARGS = DETAILED_ROUTE_ARGS="$(DETAILED_ROUTE_ARGS)"
UNSET_AND_MAKE = @bash -c 'for var in $(UNSET_VARIABLES_NAMES); do unset $$var; done; $(MAKE) --no-print-directory DESIGN_CONFIG=$(DESIGN_CONFIG) $(PRESERVED_MAKE_ARGS) $$@' --

# Separate dependency checking and doing a step. This can
# be useful to retest a stage without having to delete the
# target, or when building a wafer thin layer on top of
# ORFS using CMake, Ninja, Bazel, etc. where makefile
# dependecy checking only gets in the way.
#
# Note that there is no "do-synth" step as it is a special
# first step that for usecases such as Bazel where it should
# always be built when invoked. Latter stages in the build process
# are conditionally built by the Bazel implementation.
#
# A "do-synth" step would be welcomed, but it isn't strictly necessary
# for the Bazel use-case.
#
# do-floorplan, do-place, do-cts, do-route, do-finish are the
# supported interface to execute those stages without checking
# for dependencies.
#
# The do- substeps of each of these stages are subject to change.
#
# $(1) stem, e.g. 2_1_floorplan
# $(2) dependencies
# $(3) tcl script step
# $(4) extension of result, default .odb
# $(5) folder of target, default $(RESULTS_DIR)
define do-step
$(if $(5),$(5),$(RESULTS_DIR))/$(1)$(if $(4),$(4),.odb): $(2)
	$$(UNSET_AND_MAKE) do-$(1)

.PHONY: do-$(1)
do-$(1):
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	($(TIME_CMD) $(OPENROAD_CMD) $(SCRIPTS_DIR)/$(3).tcl -metrics $(LOG_DIR)/$(1).json) 2>&1 | tee $(LOG_DIR)/$(1).tmp.log
	mv $(LOG_DIR)/$(1).tmp.log $(LOG_DIR)/$(1).log
endef

# generate make rules to copy a file, if a dependency change and
# a do- sibling rule that copies the file unconditionally.
#
# The file is copied within the $(RESULTS_DIR)
#
# $(1) stem of target, e.g. 2_2_floorplan_io
# $(2) basename of file to be copied
# $(3) further dependencies
# $(4) target extension, default .odb
define do-copy
$(RESULTS_DIR)/$(1)$(if $(4),$(4),.odb): $(RESULTS_DIR)/$(2) $(3)
	$$(UNSET_AND_MAKE) do-$(1)$(if $(4),$(4),)

.PHONY: do-$(1)$(if $(4),$(4),)
do-$(1)$(if $(4),$(4),):
	cp $(RESULTS_DIR)/$(2) $(RESULTS_DIR)/$(1)$(if $(4),$(4),.odb)
endef


# STEP 1: Translate verilog to odb
#-------------------------------------------------------------------------------
$(eval $(call do-step,2_1_floorplan,$(RESULTS_DIR)/1_synth.v $(RESULTS_DIR)/1_synth.sdc $(TECH_LEF) $(SC_LEF) $(ADDITIONAL_LEFS) $(FOOTPRINT) $(SIG_MAP_FILE) $(FOOTPRINT_TCL),floorplan))

# STEP 2: IO Placement (random)
#-------------------------------------------------------------------------------
ifndef IS_CHIP
$(eval $(call do-step,2_2_floorplan_io,$(RESULTS_DIR)/2_1_floorplan.odb $(IO_CONSTRAINTS),io_placement_random))
else
$(eval $(call do-copy,2_2_floorplan_io,2_1_floorplan.odb,$(IO_CONSTRAINTS)))
endif

# STEP 3: Timing Driven Mixed Sized Placement
#-------------------------------------------------------------------------------
ifeq ($(MACRO_PLACEMENT)$(MACRO_PLACEMENT_TCL)$(RTLMP_FLOW),)
$(eval $(call do-step,2_3_floorplan_tdms,$(RESULTS_DIR)/2_2_floorplan_io.odb $(RESULTS_DIR)/1_synth.v $(RESULTS_DIR)/1_synth.sdc $(LIB_FILES),tdms_place))
else
$(eval $(call do-copy,2_3_floorplan_tdms,2_2_floorplan_io.odb,$(RESULTS_DIR)/1_synth.v $(RESULTS_DIR)/1_synth.sdc $(LIB_FILES)))
endif

# STEP 4: Macro Placement
#-------------------------------------------------------------------------------
$(eval $(call do-step,2_4_floorplan_macro,$(RESULTS_DIR)/2_3_floorplan_tdms.odb $(RESULTS_DIR)/1_synth.v $(RESULTS_DIR)/1_synth.sdc $(MACRO_PLACEMENT) $(MACRO_PLACEMENT_TCL),macro_place))

$(eval $(call do-step,2_floorplan_debug_macros,$(RESULTS_DIR)/2_1_floorplan.odb $(RESULTS_DIR)/1_synth.v $(MACRO_PLACEMENT) $(MACRO_PLACEMENT_TCL),floorplan_debug_macros))

# Mixed-size Placement:
$(eval $(call do-step,2_3_place_mixgp,$(RESULTS_DIR)/2_2_floorplan_io.odb $(RESULTS_DIR)/1_synth.sdc $(LIB_FILES),mix_sized_gp))


.PHONY: do-def_eval
do-def_eval:
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	$(OPENROAD_EXE) -exit scripts_3D/init_odb.tcl
	cp $(RESULTS_DIR)/3D_out.odb $(RESULTS_DIR)/2_5_floorplan_tapcell.odb
	$(UNSET_AND_MAKE) do-2_6_floorplan_pdn do-2_floorplan 
	cp $(RESULTS_DIR)/1_synth.sdc $(RESULTS_DIR)/2_floorplan.sdc
	cp $(RESULTS_DIR)/2_floorplan.odb $(RESULTS_DIR)/3_3_place_gp.odb
	$(UNSET_AND_MAKE) do-3_4_place_resized do-3_5_place_dp do-3_place do-3_place.sdc do-cts do-route do-finish

.PHONY: do-pre_cts
do-pre_cts:
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	cp $(DESIGN_DIR)/*.sdc $(RESULTS_DIR)/1_synth.sdc
	cp $(RESULTS_DIR)/3D_out.odb $(RESULTS_DIR)/2_6_floorplan_pdn.odb
	$(UNSET_AND_MAKE) do-2_floorplan 
	cp $(RESULTS_DIR)/1_synth.sdc $(RESULTS_DIR)/2_floorplan.sdc
	cp $(RESULTS_DIR)/2_floorplan.odb $(RESULTS_DIR)/3_3_place_gp.odb
	$(UNSET_AND_MAKE) do-3_4_place_resized do-3_5_place_dp do-3_place do-3_place.sdc do-cts 

.PHONY: do-2D_flow
do-2D_flow:
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	$(UNSET_AND_MAKE) do-2_1_floorplan do-2_2_floorplan_io do-2_3_floorplan_tdms do-2_4_floorplan_macro 
	cp $(RESULTS_DIR)/2_4_floorplan_macro.odb $(RESULTS_DIR)/2_5_floorplan_tapcell.odb
	$(UNSET_AND_MAKE) do-2_6_floorplan_pdn do-2_floorplan 
	cp $(RESULTS_DIR)/2_floorplan.odb $(RESULTS_DIR)/3_2_place_iop.odb
	$(UNSET_AND_MAKE) do-3_3_place_gp do-3_4_place_resized do-3_5_place_dp do-3_place do-3_place.sdc do-cts do-route do-finish

.PHONY: do-autoflow
do-autoflow:
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	$(OPENROAD_EXE) -exit scripts_3D/init_odb.tcl
	$(UNSET_AND_MAKE) do-pre_cts


.PHONY: do-place_macros
do-place_macros:
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	$(OPENROAD_EXE) -exit scripts_3D/place_macros.tcl
	
.PHONY: do-cts_eval
do-cts_eval:
	python3 scripts_3D/save_map.py
	python3 scripts_3D/modify_cts_def.py
	python3 scripts_3D/split_cts_def.py
	$(OPENROAD_EXE) -exit scripts_3D/lg_bottom.tcl
	$(OPENROAD_EXE) -exit scripts_3D/lg_upper.tcl
	python3 scripts_3D/read_def_store_coord.py
	$(OPENROAD_EXE) -exit scripts_3D/load_cts.tcl
	
	cp $(RESULTS_DIR)/my_cts.odb $(RESULTS_DIR)/4_cts.odb
	cp $(RESULTS_DIR)/1_synth.sdc $(RESULTS_DIR)/4_cts.sdc
	$(UNSET_AND_MAKE) do-route do-finish

.PHONY: do-lolflow
do-lolflow:
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	cp $(SDC_FILE) $(RESULTS_DIR)/1_synth.sdc
	$(OPENROAD_EXE) -exit scripts_3D/read_def.tcl
	python3 scripts_3D/save_map_lol.py
	python3 scripts_3D/split_cts_def_lol.py
	$(OPENROAD_EXE) -exit scripts_3D/lg_bottom.tcl
	$(OPENROAD_EXE) -exit scripts_3D/lg_upper.tcl
	python3 scripts_3D/read_def_store_coord.py
	$(OPENROAD_EXE) -exit scripts_3D/load_cts.tcl
	cp $(RESULTS_DIR)/my_cts.odb $(RESULTS_DIR)/4_cts.odb
	cp $(RESULTS_DIR)/1_synth.sdc $(RESULTS_DIR)/4_cts.sdc
	$(UNSET_AND_MAKE) do-route do-finish

.PHONY: do-get_3d_hpwl
do-get_3d_hpwl:
	$(OPENROAD_EXE) -exit scripts_3D/get_hpwl_3d.tcl

# RWQ
.PHONY: do-hotspot
do-hotspot: 
	@echo "Starting HotSpot Thermal Analysis for design: $(DESIGN_NAME)"
	python3 $(DIVIDE_DEF_PY) -i $(FINAL_DEF) -o $(RESULTS_DIR)

	@echo "[1/8] Dividing upper DEF into grids..."
	python3 $(DIVIDE_GRID_PY) \
		-i "$(RESULTS_DIR)/6_final_upper.def" \
		-o "$(HOTSPOT_OUTPUT)" \
		-g 10 \
		--flp "floorplan1.flp" \
		--prefix "upper"
	
	@echo "[2/8] Running power analysis with STA for upper die..."
	$(STA_EXE) $(REPORT_POWER_TCL)

	@mv "$(HOTSPOT_OUTPUT)/gcc.ptrace" "$(HOTSPOT_OUTPUT)/upper.ptrace"

	@echo "[3/8] Dividing bottom DEF into grids..."
	python3 $(DIVIDE_GRID_PY) \
		-i "$(RESULTS_DIR)/6_final_bottom.def" \
		-o "$(HOTSPOT_OUTPUT)" \
		-g 10 \
		--flp "floorplan2.flp" \
		--prefix "bottom"

	@echo "[4/8] Running power analysis with STA for bottom die..."
	$(STA_EXE) $(REPORT_POWER_TCL)

	@mv "$(HOTSPOT_OUTPUT)/gcc.ptrace" "$(HOTSPOT_OUTPUT)/bottom.ptrace"

	python3 $(MERGE_PTRACE_PY) \
		-u "$(HOTSPOT_OUTPUT)/upper.ptrace" \
		-b "$(HOTSPOT_OUTPUT)/bottom.ptrace" \
		-o "$(HOTSPOT_OUTPUT)/test.ptrace"

	rm -f "$(HOTSPOT_OUTPUT)/upper.ptrace" "$(HOTSPOT_OUTPUT)/bottom.ptrace"
	
	@echo "[6/8] Creating version directory..."
	@mkdir -p "$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)"
	@mkdir -p "$(HOTSPOT_SCRIPTS_DIR)/examples/thermal/"
	@chown -R $(USER):$(USER) "$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)"
	
	@rsync -a --exclude='*/' \
		"$(HOTSPOT_SCRIPTS_DIR)/examples/thermal/" \
		"$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)/"
	
	@cp -f "$(HOTSPOT_SCRIPTS_DIR)/scripts/output/"* \
		"$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)/" 2>/dev/null || true
	
	@echo "Running HotSpot analysis..."
	@cd "$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)/" && \
		chown -R $(USER):$(USER) ./ && \
		chmod +x run.sh && \
		./run.sh
	
	@mkdir -p "$(RESULTS_DIR)/hotspot_outputs"
	@rsync -a --delete \
		"$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)/outputs/" \
		"$(RESULTS_DIR)/hotspot_outputs/" 2>/dev/null || true
	@chown -R $(USER):$(USER) "$(RESULTS_DIR)/hotspot_outputs"


	@rm -r "$(HOTSPOT_SCRIPTS_DIR)/examples/thermal/outputs" || true
	@mkdir -p "$(HOTSPOT_SCRIPTS_DIR)/examples/thermal/outputs"
	@chown -R $(USER):$(USER) "$(HOTSPOT_SCRIPTS_DIR)/examples/thermal/outputs"

	@echo "[8/8] Analysis completed. Results: $(RESULTS_DIR)/hotspot_outputs"

.PHONY: do-hotspot_2D
do-hotspot_2D: 
	@echo "Starting HotSpot Thermal Analysis for design: $(DESIGN_NAME)"

	@echo "[1/6] Dividing DEF into grids..."
	python3 $(DIVIDE_GRID_PY) \
		-i "$(RESULTS_DIR)/6_final.def" \
		-o "$(HOTSPOT_OUTPUT)" \
		-g 10 \
		--flp "ev6.flp" \
		--prefix "Grid"

	@echo "[2/6] Running power analysis with STA..."
	$(STA_EXE) $(REPORT_POWER_TCL)

	@echo "[3/6] Creating version directory..."
	@mkdir -p "$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)"
	@chown -R $(USER):$(USER) "$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)"
	
	@echo "[4/6] Copying 2D baseline configuration..."
	@rsync -a --exclude='*/' \
		"$(HOTSPOT_SCRIPTS_DIR)/examples/example2/" \
		"$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)/"
	
	@echo "[5/6] Overwriting with scripts/output..."
	@cp -f "$(HOTSPOT_SCRIPTS_DIR)/scripts/output/"* \
		"$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)/" 2>/dev/null || true
	
	@echo "[6/6] Running HotSpot analysis..."
	@cd "$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)/" && \
		chown -R $(USER):$(USER) ./ && \
		chmod +x run.sh && \
		./run.sh
	
	@mkdir -p "$(RESULTS_DIR)/hotspot_outputs"
	@rsync -a --delete \
		"$(HOTSPOT_SCRIPTS_DIR)/examples/$(HOTSPOT_EXAMPLE_DIR)/outputs/" \
		"$(RESULTS_DIR)/hotspot_outputs/" 2>/dev/null || true
	@chown -R $(USER):$(USER) "$(RESULTS_DIR)/hotspot_outputs"


	@rm -r "$(HOTSPOT_SCRIPTS_DIR)/examples/example2/outputs" || true
	@mkdir -p "$(HOTSPOT_SCRIPTS_DIR)/examples/example2/outputs"
	@chown -R $(USER):$(USER) "$(HOTSPOT_SCRIPTS_DIR)/examples/example2/outputs"

	@echo "[8/8] Analysis completed. Results: $(RESULTS_DIR)/hotspot_outputs"

# STEP 5: Tapcell and Welltie insertion
#-------------------------------------------------------------------------------
$(eval $(call do-step,2_5_floorplan_tapcell,$(RESULTS_DIR)/2_4_floorplan_macro.odb $(TAPCELL_TCL),tapcell))

# STEP 6: PDN generation
#-------------------------------------------------------------------------------
$(eval $(call do-step,2_6_floorplan_pdn,$(RESULTS_DIR)/2_5_floorplan_tapcell.odb $(PDN_TCL),pdn))

$(eval $(call do-copy,2_floorplan,2_6_floorplan_pdn.odb,))

$(RESULTS_DIR)/2_floorplan.sdc: $(RESULTS_DIR)/2_1_floorplan.odb

.PHONY: do-floorplan
do-floorplan:
	$(UNSET_AND_MAKE) do-2_1_floorplan do-2_2_floorplan_io do-2_3_floorplan_tdms do-2_4_floorplan_macro do-2_5_floorplan_tapcell do-2_6_floorplan_pdn do-2_floorplan

.PHONY: do-floorplan-macro
do-floorplan-macro:
	$(UNSET_AND_MAKE) do-2_5_floorplan_tapcell do-2_6_floorplan_pdn do-2_floorplan

.PHONY: do-macroflow
do-macroflow: do-floorplan-macro do-place do-cts do-route do-finish

.PHONY: baseline
baseline: do-floorplan do-place do-cts do-route do-finish

.PHONY: clean_floorplan
clean_floorplan:
	rm -f $(RESULTS_DIR)/2_*floorplan*.odb $(RESULTS_DIR)/2_floorplan.sdc $(RESULTS_DIR)/2_*.v $(RESULTS_DIR)/2_*.def
	rm -f $(REPORTS_DIR)/2_*
	rm -f $(LOG_DIR)/2_*

# ==============================================================================
#  ____  _        _    ____ _____
# |  _ \| |      / \  / ___| ____|
# | |_) | |     / _ \| |   |  _|
# |  __/| |___ / ___ \ |___| |___
# |_|   |_____/_/   \_\____|_____|
#
.PHONY: place
place: $(RESULTS_DIR)/3_place.odb \
       $(RESULTS_DIR)/3_place.sdc
# ==============================================================================
# STEP 1: Global placement without placed IOs, timing-driven, and routability-driven.
#-------------------------------------------------------------------------------
#$(eval $(call do-step,3_1_place_gp_skip_io,$(RESULTS_DIR)/2_floorplan.odb $(RESULTS_DIR)/2_floorplan.sdc $(LIB_FILES),global_place_skip_io))

$(eval $(call do-copy,3_1_place_gp_skip_io,2_floorplan.odb,))

# STEP 2: IO placement (non-random)
#-------------------------------------------------------------------------------
# ifndef IS_CHIP
# $(eval $(call do-step,3_2_place_iop,$(RESULTS_DIR)/3_1_place_gp_skip_io.odb $(IO_CONSTRAINTS),io_placement))
# else
$(eval $(call do-copy,3_2_place_iop,3_1_place_gp_skip_io.odb,$(IO_CONSTRAINTS)))
# endif

# STEP 3: Global placement with placed IOs, timing-driven, and routability-driven.
#-------------------------------------------------------------------------------
$(eval $(call do-step,3_3_place_gp,$(RESULTS_DIR)/3_2_place_iop.odb $(RESULTS_DIR)/2_floorplan.sdc $(LIB_FILES),global_place))

# STEP 4: Resizing & Buffering
#-------------------------------------------------------------------------------
$(eval $(call do-step,3_4_place_resized,$(RESULTS_DIR)/3_3_place_gp.odb $(RESULTS_DIR)/2_floorplan.sdc,resize))

.PHONY: clean_resize
clean_resize:
	rm -f $(RESULTS_DIR)/3_4_place_resized.odb

# STEP 5: Detail placement
#-------------------------------------------------------------------------------
$(eval $(call do-step,3_5_place_dp,$(RESULTS_DIR)/3_4_place_resized.odb,detail_place))

$(eval $(call do-copy,3_place,3_5_place_dp.odb,))

$(eval $(call do-copy,3_place,2_floorplan.sdc,,.sdc))

.PHONY: do-place
do-place:
	$(UNSET_AND_MAKE) do-3_1_place_gp_skip_io do-3_2_place_iop do-3_3_place_gp do-3_4_place_resized do-3_5_place_dp do-3_place do-3_place.sdc

.PHONY: do-place-global
do-place-global:
	$(UNSET_AND_MAKE) do-3_4_place_resized do-3_5_place_dp do-3_place do-3_place.sdc

.PHONY: do-globalflow
do-globalflow: do-place-global do-cts do-route do-finish


# Clean Targets
#-------------------------------------------------------------------------------
.PHONY: clean_place
clean_place:
	rm -f $(RESULTS_DIR)/3_*place*.odb
	rm -f $(RESULTS_DIR)/3_place.sdc
	rm -f $(RESULTS_DIR)/3_*.def $(RESULTS_DIR)/3_*.v
	rm -f $(REPORTS_DIR)/3_*
	rm -f $(LOG_DIR)/3_*


# ==============================================================================
#   ____ _____ ____
#  / ___|_   _/ ___|
# | |     | | \___ \
# | |___  | |  ___) |
#  \____| |_| |____/
#
.PHONY: cts
cts: $(RESULTS_DIR)/4_cts.odb \
     $(RESULTS_DIR)/4_cts.sdc
# ==============================================================================

# Run TritonCTS
# ------------------------------------------------------------------------------
$(eval $(call do-step,4_1_cts,$(RESULTS_DIR)/3_place.odb $(RESULTS_DIR)/3_place.sdc,cts))

# Filler cell insertion
# ------------------------------------------------------------------------------
$(eval $(call do-step,4_2_cts_fillcell,$(RESULTS_DIR)/4_1_cts.odb,fillcell))

$(RESULTS_DIR)/4_cts.sdc: $(RESULTS_DIR)/4_cts.odb

$(eval $(call do-copy,4_cts,4_2_cts_fillcell.odb))

.PHONY: do-cts
do-cts:
	$(UNSET_AND_MAKE) do-4_1_cts do-4_2_cts_fillcell do-4_cts

.PHONY: clean_cts
clean_cts:
	rm -rf $(RESULTS_DIR)/4_*cts*.odb $(RESULTS_DIR)/4_cts.sdc $(RESULTS_DIR)/4_*.v $(RESULTS_DIR)/4_*.def
	rm -f  $(REPORTS_DIR)/4_*
	rm -f  $(LOG_DIR)/4_*


# ==============================================================================
#  ____   ___  _   _ _____ ___ _   _  ____
# |  _ \ / _ \| | | |_   _|_ _| \ | |/ ___|
# | |_) | | | | | | | | |  | ||  \| | |  _
# |  _ <| |_| | |_| | | |  | || |\  | |_| |
# |_| \_\\___/ \___/  |_| |___|_| \_|\____|
#
.PHONY: route
route: $(RESULTS_DIR)/5_route.odb \
       $(RESULTS_DIR)/5_route.sdc
# ==============================================================================


# STEP 1: Run global route
#-------------------------------------------------------------------------------
$(eval $(call do-step,5_1_grt,$(RESULTS_DIR)/4_cts.odb $(FASTROUTE_TCL) $(PRE_GLOBAL_ROUTE) $(GRT_PREPARE_TCL),global_route))

# STEP 2: Run detailed route
#-------------------------------------------------------------------------------
ifeq ($(USE_WXL),)
$(eval $(call do-step,5_2_route,$(RESULTS_DIR)/5_1_grt.odb,detail_route))
else
$(eval $(call do-step,5_2_route,$(RESULTS_DIR)/4_cts.odb,detail_route))
endif

$(eval $(call do-copy,5_route,5_2_route.odb))

$(eval $(call do-copy,5_route,4_cts.sdc,,.sdc))

.PHONY: do-route
do-route:
	$(UNSET_AND_MAKE) do-5_1_grt do-5_2_route do-5_route do-5_route.sdc





$(RESULTS_DIR)/5_route.v:
	@export OR_DB=5_route ;\
	$(OPENROAD_CMD) ./scripts/write_verilog.tcl

.PHONY: clean_route
clean_route:
	rm -rf output*/ results*.out.dmp layer_*.mps
	rm -rf *.gdid *.log *.met *.sav *.res.dmp
	rm -rf $(RESULTS_DIR)/route.guide $(RESULTS_DIR)/output_guide.mod $(RESULTS_DIR)/updated_clks.sdc
	rm -rf $(RESULTS_DIR)/5_*.odb $(RESULTS_DIR)/5_route.sdc $(RESULTS_DIR)/5_*.def $(RESULTS_DIR)/5_*.v
	rm -f  $(REPORTS_DIR)/5_*
	rm -f  $(LOG_DIR)/5_*

.PHONY: klayout_tr_rpt
klayout_tr_rpt: $(RESULTS_DIR)/5_route.def $(OBJECTS_DIR)/klayout.lyt
	$(call KLAYOUT_FOUND)
	$(KLAYOUT_CMD) -rd in_drc="$(REPORTS_DIR)/5_route_drc.rpt" \
	        -rd in_def="$<" \
	        -rd tech_file=$(OBJECTS_DIR)/klayout.lyt \
	        -rm $(UTILS_DIR)/viewDrc.py

.PHONY: klayout_guides
klayout_guides: $(RESULTS_DIR)/5_route.def $(OBJECTS_DIR)/klayout.lyt
	$(call KLAYOUT_FOUND)
	$(KLAYOUT_CMD) -rd in_guide="$(RESULTS_DIR)/route.guide" \
	        -rd in_def="$<" \
	        -rd net_name=$(GUIDE_NET) \
	        -rd tech_file=$(OBJECTS_DIR)/klayout.lyt \
	        -rm $(UTILS_DIR)/viewGuide.py

# ==============================================================================
#  _____ ___ _   _ ___ ____  _   _ ___ _   _  ____
# |  ___|_ _| \ | |_ _/ ___|| | | |_ _| \ | |/ ___|
# | |_   | ||  \| || |\___ \| |_| || ||  \| | |  _
# |  _|  | || |\  || | ___) |  _  || || |\  | |_| |
# |_|   |___|_| \_|___|____/|_| |_|___|_| \_|\____|
#
GDS_FINAL_FILE = $(RESULTS_DIR)/6_final.$(STREAM_SYSTEM_EXT)
.PHONY: finish
finish: $(LOG_DIR)/6_report.log \
        $(RESULTS_DIR)/6_final.v \
        $(RESULTS_DIR)/6_final.sdc \
        $(GDS_FINAL_FILE)
	$(UNSET_AND_MAKE) elapsed

.PHONY: elapsed
elapsed:
	-@$(UTILS_DIR)/genElapsedTime.py -d $(BLOCK_LOG_FOLDERS) $(LOG_DIR)

# ==============================================================================

ifneq ($(USE_FILL),)
$(eval $(call do-step,6_1_fill,$(RESULTS_DIR)/5_route.odb $(RESULTS_DIR)/5_route.sdc $(FILL_CONFIG),density_fill))
else
$(eval $(call do-copy,6_1_fill,5_route.odb))
endif

$(eval $(call do-copy,6_1_fill,5_route.sdc,,.sdc))

$(eval $(call do-copy,6_final,5_route.sdc,,.sdc))

$(eval $(call do-step,6_report,$(RESULTS_DIR)/6_1_fill.odb $(RESULTS_DIR)/6_1_fill.sdc,final_report,.log,$(LOG_DIR)))

$(RESULTS_DIR)/6_final.def: $(LOG_DIR)/6_report.log
$(eval $(call do-step,6_figure,$(RESULTS_DIR)/6_1_fill.odb $(RESULTS_DIR)/6_1_fill.sdc,generate_fig,.log,$(LOG_DIR)))

.PHONY: do-img
do-img:
	$(UNSET_AND_MAKE) do-6_figure


# NOTE! No GDS file for now
.PHONY: do-finish
do-finish:
	$(UNSET_AND_MAKE) do-6_1_fill do-6_1_fill.sdc do-6_final.sdc do-6_report elapsed

# Skipping resize can be useful for mock abstracts
.PHONY: skip_resize
skip_resize: $(RESULTS_DIR)/3_3_place_gp.odb
	cp $(RESULTS_DIR)/3_3_place_gp.odb $(RESULTS_DIR)/3_4_place_resized.odb

# Skipping CTS can be useful to smoketest later stages.
.PHONY: skip_cts
skip_cts: $(RESULTS_DIR)/3_place.odb $(RESULTS_DIR)/3_place.sdc
	# mock all intermediate results
	cp $(RESULTS_DIR)/3_place.odb $(RESULTS_DIR)/4_1_cts.odb
	cp $(RESULTS_DIR)/3_place.odb $(RESULTS_DIR)/4_2_cts_fillcell.odb
	cp $(RESULTS_DIR)/3_place.sdc $(RESULTS_DIR)/4_cts.sdc
	cp $(RESULTS_DIR)/3_place.odb $(RESULTS_DIR)/4_cts.odb

# Skipping route can be useful to create a mock abstract
.PHONY: skip_route
skip_route: $(RESULTS_DIR)/4_cts.odb $(RESULTS_DIR)/4_cts.sdc
	cp $(RESULTS_DIR)/3_place.odb $(RESULTS_DIR)/5_1_grt.odb
	cp $(RESULTS_DIR)/3_place.odb $(RESULTS_DIR)/5_2_route.odb
	cp $(RESULTS_DIR)/3_place.odb $(RESULTS_DIR)/6_1_fill.odb
	touch $(RESULTS_DIR)/6_final.spef

# To create a mock abstract quickly, good enough to iterate quickly on
# floorplanning and detailed route at higher levels, run:
#
# make skip_resize skip_cts skip_route generate_abstract
.PHONY: generate_abstract
generate_abstract: $(RESULTS_DIR)/6_final.gds $(RESULTS_DIR)/6_final.def  $(RESULTS_DIR)/6_final.v $(RESULTS_DIR)/6_final.sdc
	$(UNSET_AND_MAKE) do-generate_abstract

.PHONY: do-generate_abstract
do-generate_abstract:
	($(TIME_CMD) $(OPENROAD_CMD) $(SCRIPTS_DIR)/generate_abstract.tcl -metrics $(LOG_DIR)/generate_abstract.json) 2>&1 | tee $(LOG_DIR)/generate_abstract.log

.PHONY: clean_abstract
clean_abstract:
	rm -f $(RESULTS_DIR)/$(DESIGN_NAME).lib $(RESULTS_DIR)/$(DESIGN_NAME).lef

# Merge wrapped macros using Klayout
#-------------------------------------------------------------------------------
$(WRAPPED_GDSOAS): $(OBJECTS_DIR)/klayout_wrap.lyt $(WRAPPED_LEFS)
	$(call KLAYOUT_FOUND)
	($(TIME_CMD) $(KLAYOUT_CMD) -zz -rd design_name=$(basename $(notdir $@)) \
	        -rd in_def=$(OBJECTS_DIR)/def/$(notdir $(@:$(STREAM_SYSTEM_EXT)=def)) \
	        -rd in_files="$(ADDITIONAL_GDSOAS)" \
	        -rd config_file=$(FILL_CONFIG) \
	        -rd seal_file="" \
	        -rd out_file=$@ \
	        -rd tech_file=$(OBJECTS_DIR)/klayout_wrap.lyt \
	        -rd layer_map=$(GDS_LAYER_MAP) \
	        -r $(UTILS_DIR)/def2stream.py) 2>&1 | tee $(LOG_DIR)/6_merge_$(basename $(notdir $@)).log

# Merge GDS using Klayout
#-------------------------------------------------------------------------------
GDS_MERGED_FILE = $(RESULTS_DIR)/6_1_merged.$(STREAM_SYSTEM_EXT)
$(GDS_MERGED_FILE): $(RESULTS_DIR)/6_final.def $(OBJECTS_DIR)/klayout.lyt $(GDSOAS_FILES) $(WRAPPED_GDSOAS) $(SEAL_GDSOAS)
	$(call KLAYOUT_FOUND)
	($(TIME_CMD) $(STDBUF_CMD) $(KLAYOUT_CMD) -zz -rd design_name=$(DESIGN_NAME) \
	        -rd in_def=$< \
	        -rd in_files="$(GDSOAS_FILES) $(WRAPPED_GDSOAS)" \
	        -rd config_file=$(FILL_CONFIG) \
	        -rd seal_file="$(SEAL_GDSOAS)" \
	        -rd out_file=$@ \
	        -rd tech_file=$(OBJECTS_DIR)/klayout.lyt \
	        -rd layer_map=$(GDS_LAYER_MAP) \
	        -r $(UTILS_DIR)/def2stream.py) 2>&1 | tee $(LOG_DIR)/6_1_merge.log

$(RESULTS_DIR)/6_final.v: $(LOG_DIR)/6_report.log

$(GDS_FINAL_FILE): $(GDS_MERGED_FILE)
	cp $< $@

.PHONY: drc
drc: $(REPORTS_DIR)/6_drc.lyrdb

$(REPORTS_DIR)/6_drc.lyrdb: $(GDS_FINAL_FILE) $(KLAYOUT_DRC_FILE)
ifneq ($(KLAYOUT_DRC_FILE),)
	$(call KLAYOUT_FOUND)
	($(TIME_CMD) $(KLAYOUT_CMD) -zz -rd in_gds="$<" \
	        -rd report_file=$(abspath $@) \
	        -r $(KLAYOUT_DRC_FILE)) 2>&1 | tee $(LOG_DIR)/6_drc.log
	# Hacky way of getting DRV count (don't error on no matches)
	grep -c "<value>" $@ > $(REPORTS_DIR)/6_drc_count.rpt || [[ $$? == 1 ]]
else
	echo "DRC not supported on this platform" > $@
endif

$(RESULTS_DIR)/6_final.cdl: $(RESULTS_DIR)/6_final.v
	($(TIME_CMD) $(OPENROAD_CMD) $(SCRIPTS_DIR)/cdl.tcl) 2>&1 | tee $(LOG_DIR)/6_cdl.log

$(OBJECTS_DIR)/6_final_concat.cdl: $(RESULTS_DIR)/6_final.cdl $(CDL_FILE)
	cat $^ > $@

.PHONY: lvs
lvs: $(RESULTS_DIR)/6_lvs.lvsdb

$(RESULTS_DIR)/6_lvs.lvsdb: $(GDS_FINAL_FILE) $(KLAYOUT_LVS_FILE) $(OBJECTS_DIR)/6_final_concat.cdl
ifneq ($(KLAYOUT_LVS_FILE),)
	$(call KLAYOUT_FOUND)
	($(TIME_CMD) $(KLAYOUT_CMD) -b -rd in_gds="$<" \
	        -rd cdl_file=$(abspath $(OBJECTS_DIR)/6_final_concat.cdl) \
	        -rd report_file=$(abspath $@) \
	        -r $(KLAYOUT_LVS_FILE)) 2>&1 | tee $(LOG_DIR)/6_lvs.log
else
	echo "LVS not supported on this platform" > $@
endif

.PHONY: clean_finish
clean_finish:
	rm -rf $(RESULTS_DIR)/6_*.gds $(RESULTS_DIR)/6_*.oas $(RESULTS_DIR)/6_*.odb $(RESULTS_DIR)/6_*.v $(RESULTS_DIR)/6_*.def $(RESULTS_DIR)/6_*.sdc $(RESULTS_DIR)/6_*.spef
	rm -rf $(REPORTS_DIR)/6_*.rpt
	rm -f  $(LOG_DIR)/6_*


# ==============================================================================
#  __  __ ___ ____   ____
# |  \/  |_ _/ ___| / ___|
# | |\/| || |\___ \| |
# | |  | || | ___) | |___
# |_|  |_|___|____/ \____|
#
# ==============================================================================

.PHONY: all
all: $(SDC_FILE) $(WRAPPED_LIBS) $(DONT_USE_LIBS) $(OBJECTS_DIR)/klayout.lyt $(WRAPPED_GDSOAS) $(DONT_USE_SC_LIB)
	mkdir -p $(RESULTS_DIR) $(LOG_DIR) $(REPORTS_DIR)
	($(TIME_CMD) $(OPENROAD_CMD) $(SCRIPTS_DIR)/run_all.tcl -metrics $(LOG_DIR)/run_all.json) 2>&1 | tee $(LOG_DIR)/run_all.log

.PHONY: clean
clean:
	@echo
	@echo "Make clean disabled."
	@echo "Use make clean_all or clean individual steps:"
	@echo "  clean_synth clean_floorplan clean_place clean_cts clean_route clean_finish"
	@echo

.PHONY: clean_all
clean_all: clean_synth clean_floorplan clean_place clean_cts clean_route clean_finish clean_metadata clean_abstract
	rm -rf $(OBJECTS_DIR)

.PHONY: nuke
nuke: clean_test clean_issues
	rm -rf ./results ./logs ./reports ./objects
	rm -rf layer_*.mps macrocell.list *best.plt *_pdn.def dummy.guide
	rm -rf *.rpt *.rpt.old *.def.v pin_dumper.log
	rm -rf versions.txt

.PHONY: vars
vars:
	$(UTILS_DIR)/generate-vars.sh vars

# DEF/GDS/OAS viewer shortcuts
#-------------------------------------------------------------------------------
RESULTS_ODB = $(notdir $(sort $(wildcard $(RESULTS_DIR)/*.odb)))
RESULTS_DEF = $(notdir $(sort $(wildcard $(RESULTS_DIR)/*.def)))
RESULTS_GDS = $(notdir $(sort $(wildcard $(RESULTS_DIR)/*.gds)))
RESULTS_OAS = $(notdir $(sort $(wildcard $(RESULTS_DIR)/*.oas)))
.PHONY: $(foreach file,$(RESULTS_DEF) $(RESULTS_GDS) $(RESULTS_OAS),klayout_$(file))
$(foreach file,$(RESULTS_DEF) $(RESULTS_GDS) $(RESULTS_OAS),klayout_$(file)): klayout_%: $(OBJECTS_DIR)/klayout.lyt
	$(KLAYOUT_CMD) -nn $(OBJECTS_DIR)/klayout.lyt $(RESULTS_DIR)/$*

.PHONY: preview_macro_placement

ifneq ($(or $(MACRO_PLACEMENT),$(MACRO_PLACEMENT_TCL)),)
MACRO_PREVIEW_ODB = 2_floorplan_debug_macros.odb
else
MACRO_PREVIEW_ODB = 2_4_floorplan_macro.odb
endif

preview_macro_placement:
	@$(UNSET_AND_MAKE) $(RESULTS_DIR)/$(MACRO_PREVIEW_ODB)
	@$(UNSET_AND_MAKE) gui_$(MACRO_PREVIEW_ODB)

.PHONY: gui_synth
gui_synth:
	$(OPENROAD_GUI_CMD) $(SCRIPTS_DIR)/sta-synth.tcl
.PHONY: open_synth
open_synth:
	$(OPENROAD_NO_EXIT_CMD) $(SCRIPTS_DIR)/sta-synth.tcl

define OPEN_GUI_SHORTCUT
.PHONY: gui_$(1) open_$(1)
gui_$(1): gui_$(2)
open_$(1): open_$(2)
endef

$(eval $(call OPEN_GUI_SHORTCUT,floorplan,2_floorplan.odb))
$(eval $(call OPEN_GUI_SHORTCUT,place,3_place.odb))
$(eval $(call OPEN_GUI_SHORTCUT,cts,4_cts.odb))
$(eval $(call OPEN_GUI_SHORTCUT,route,5_route.odb))
$(eval $(call OPEN_GUI_SHORTCUT,final,6_final.odb))

define OPEN_GUI
.PHONY: $(1)_$(2)
$(1)_$(2):
	$(3)=$(RESULTS_DIR)/$(2) $(4) $(SCRIPTS_DIR)/gui.tcl
endef

$(foreach file,$(RESULTS_DEF),$(eval $(call OPEN_GUI,gui,$(file),DEF_FILE,$(OPENROAD_GUI_CMD))))
$(foreach file,$(RESULTS_ODB),$(eval $(call OPEN_GUI,gui,$(file),ODB_FILE,$(OPENROAD_GUI_CMD))))
$(foreach file,$(RESULTS_DEF),$(eval $(call OPEN_GUI,open,$(file),DEF_FILE,$(OPENROAD_NO_EXIT_CMD))))
$(foreach file,$(RESULTS_ODB),$(eval $(call OPEN_GUI,open,$(file),ODB_FILE,$(OPENROAD_NO_EXIT_CMD))))

# Write a def for the corresponding odb
$(foreach file,$(RESULTS_ODB),$(file).def): %.def:
	ODB_FILE=$(RESULTS_DIR)/$* DEF_FILE=$(RESULTS_DIR)/$@ $(OPENROAD_CMD) $(SCRIPTS_DIR)/write_def.tcl
#
# Write a verilog for the corresponding odb
$(foreach file,$(RESULTS_ODB),$(file).v): %.v:
	ODB_FILE=$(RESULTS_DIR)/$* VERILOG_FILE=$(RESULTS_DIR)/$@ $(OPENROAD_CMD) $(SCRIPTS_DIR)/write_verilog.tcl

# Drop into yosys with all environment variables, useful to for instance
# debug synthesis, or run other commands aftewards, such as "show" to
# generate a .dot file of the design to visualize designs.
.PHONY: yosys
yosys:
	$(YOSYS_EXE)

# Drop into a bash shell with all environment variables, useful for debugging
.PHONY: bash
bash:
	bash

.PHONY: all_defs
all_defs : $(foreach file,$(RESULTS_ODB),$(file).def)
.PHONY: all_verilog
all_verilog : $(foreach file,$(RESULTS_ODB),$(file).v)

.PHONY: handoff
handoff : all_defs all_verilog

.PHONY: print-%
# Print any variable, for instance: make print-DIE_AREA
print-%  : ; @echo $* = $($*)

.PHONY: test-unset-and-make-%
test-unset-and-make-%: ; $(UNSET_AND_MAKE) $*

.phony: klayout
klayout:
	$(KLAYOUT_CMD)

# Utilities
#-------------------------------------------------------------------------------
include $(UTILS_DIR)/utils.mk
export PRIVATE_DIR ?= ../../private_tool_scripts
-include $(PRIVATE_DIR)/private.mk
