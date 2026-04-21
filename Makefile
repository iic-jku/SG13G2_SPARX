# Makefile for SPARX: An Automated, Programmatically Generated Frequency-Scalable Six-Port Receiver in 130-nm CMOS
#
# SPDX-FileCopyrightText: 2026 Simon Dorrer
# Johannes Kepler University, Department for Integrated Circuits
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# SPDX-License-Identifier: Apache-2.0
# ========================================================================

MAKEFILE_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

TOP = sparx_top
POWDET = sparx_powdet_sbd

.DEFAULT_GOAL := help

# Cell name for verification targets (default: top-level cell)
# Override with: make <target> CELL=<cellname>
CELL ?= $(TOP)

# PEX mode (1 = C-decoupled, 2 = C-coupled, 3 = full-RC)
# Override with: make <target> EXT_MODE=<1|2|3>
EXT_MODE ?= 3

# Floating-point precision (significant digits) for xschem's ev function
# Override with: make <target> EV_PRECISION=<digits>
EV_PRECISION ?= 5

# Design frequency in GHz (default: 160)
# Override with: make build-layout FREQ=<frequency_in_GHz>
FREQ ?= 160

# Metal fill options for build-layout (0 = fill enabled, 1 = fill disabled)
# Override with: make build-layout NO_FILL=1 NO_FILL_M5=1
NO_FILL ?= 0
NO_FILL_M5 ?= 0

# Frequency sweep in GHz
# Override with: make build-layout-sweep START_FREQ=<GHz> STOP_FREQ=<GHz> STEP_FREQ=<GHz>
START_FREQ ?= 60
STOP_FREQ ?= 300
STEP_FREQ ?= 20

# Folder structure
LAY_DIR     := layout
SCH_DIR     := schematic
RENDER_DIR  := render
NET_SCH_DIR := netlist/schematic
NET_LAY_DIR := netlist/layout
NET_PEX_DIR := netlist/pex
LVS_RPT_DIR := verification/lvs
DRC_RPT_DIR := verification/drc


# Help Target
help: ## Show this help message
	@echo 'Usage: make <target> [CELL=<cellname>] [EXT_MODE=<1|2|3>] [EV_PRECISION=<digits>] [FREQ=<GHz>] [START_FREQ=<GHz>] [STOP_FREQ=<GHz>] [STEP_FREQ=<GHz>] [NO_FILL=0|1] [NO_FILL_M5=0|1]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ''
	@echo 'CELL defaults to $(TOP). Override to verify subcells.'
	@echo 'EXT_MODE defaults to 3 (full-RC). 1=C-decoupled, 2=C-coupled.'
	@echo 'FREQ defaults to 160 (GHz). Override for build-layout.'
	@echo 'NO_FILL defaults to 0 (fill enabled). Set to 1 to disable metal fill.'
	@echo 'NO_FILL_M5 defaults to 0 (M5 fill enabled). Set to 1 to disable M5 ground fill.'
	@echo 'START_FREQ, STOP_FREQ, STEP_FREQ default to 60, 300, and 20 (GHz) for build-layout-sweep.'
	@echo 'EV_PRECISION defaults to 5 significant digits for xschem ev function.'
.PHONY: help
# ================================================================================================


# LVS Targets
klayout-lvs-netlist: ## Export CDL schematic netlist from Xschem for KLayout LVS (usage: make klayout-lvs-netlist [CELL=<cellname>] [EV_PRECISION=<digits>])
	mkdir -p $(NET_SCH_DIR)
	xschem -s -r -x -q --rcfile $(SCH_DIR)/xschemrc --command ' \
		set spiceprefix 1; \
		set lvs_netlist 1; \
		set top_is_subckt 1; \
		set lvs_ignore 0; \
		set ev_precision $(EV_PRECISION); \
		set netlist_dir $(NET_SCH_DIR); \
		xschem set netlist_name [file tail [file rootname [xschem get current_name]]]_klayout.cdl; \
		xschem netlist \
	' $(SCH_DIR)/$(CELL).sch
.PHONY: klayout-lvs-netlist

klayout-lvs: ## Run KLayout LVS of the CELL cell (usage: make klayout-lvs [CELL=<cellname>])
	$(MAKE) klayout-lvs-netlist CELL=$(CELL)
	mkdir -p $(LVS_RPT_DIR)
	mkdir -p $(NET_LAY_DIR)
	python3 $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/lvs/run_lvs.py \
		--layout=$(LAY_DIR)/$(CELL)_flat.gds \
		--netlist=$(NET_SCH_DIR)/$(CELL)_klayout.cdl \
		--topcell=$(CELL) \
		--run_dir=$(LVS_RPT_DIR) \
		--run_mode=deep
	mv $(LVS_RPT_DIR)/$(CELL)_flat_extracted.cir $(NET_LAY_DIR)/$(CELL)_klayout.cir
	mv $(LVS_RPT_DIR)/$(CELL)_flat.lvsdb $(LVS_RPT_DIR)/$(CELL).lvsdb
	sleep 4
.PHONY: klayout-lvs

magic-lvs-netlist: ## Export SPICE schematic netlist from Xschem for Magic + Netgen LVS (usage: make magic-lvs-netlist [CELL=<cellname>] [EV_PRECISION=<digits>])
	mkdir -p $(NET_SCH_DIR)
	xschem -s -r -x -q --rcfile $(SCH_DIR)/xschemrc --command ' \
		set spiceprefix 1; \
		set lvs_netlist 0; \
		set top_is_subckt 1; \
		set lvs_ignore 1; \
		set ev_precision $(EV_PRECISION); \
		set netlist_dir $(NET_SCH_DIR); \
		xschem set netlist_name [file tail [file rootname [xschem get current_name]]]_magic.spice; \
		xschem netlist \
	' $(SCH_DIR)/$(CELL).sch
.PHONY: magic-lvs-netlist

magic-lvs: ## Run Magic + Netgen LVS of the CELL cell (usage: make magic-lvs [CELL=<cellname>])
	mkdir -p $(LVS_RPT_DIR)
	mkdir -p $(NET_LAY_DIR)
	$(MAKE) magic-lvs-netlist CELL=$(CELL)
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) sak-lvs.sh -d -w $(LVS_RPT_DIR) -s $(NET_SCH_DIR)/$(CELL)_magic.spice -l $(LAY_DIR)/$(CELL)_flat.gds -c $(CELL)
# 	Alternative using sak-lvs.sh for netlist export and LVS in one step (replaces magic-lvs-netlist target):
#   PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) STD_CELL_LIBRARY=$(STD_CELL_LIBRARY) sak-lvs.sh -d -w $(LVS_RPT_DIR) -s $(SCH_DIR)/$(CELL).sch -l $(LAY_DIR)/$(CELL)_flat.gds -c $(CELL)
	mv $(LVS_RPT_DIR)/$(CELL).ext.spc $(NET_LAY_DIR)/$(CELL)_magic.ext.spc
	rm -f $(LVS_RPT_DIR)/$(CELL).sch.spc
	rm -f $(LVS_RPT_DIR)/ext_$(CELL).tcl
	rm -f $(LVS_RPT_DIR)/*.ext
	sleep 4
.PHONY: magic-lvs
# ================================================================================================


# DRC Targets
klayout-drc: ## Run KLayout DRC of the CELL cell (usage: make klayout-drc [CELL=<cellname>])
	mkdir -p $(DRC_RPT_DIR)
	python3 $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/drc/run_drc.py \
		--path=$(LAY_DIR)/$(CELL).gds \
		--topcell=$(CELL) \
		--run_dir=$(DRC_RPT_DIR) \
		--no_feol \
		--no_density \
		--disable_extra_rules \
		--mp=32 \
		--density_thr=32
	sleep 4
.PHONY: klayout-drc

klayout-drc-regular: ## Run regular DRC of the TOP cell (usage: make klayout-drc-regular)
	mkdir -p $(DRC_RPT_DIR)
	python3 $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/drc/run_drc.py \
		--path=$(LAY_DIR)/$(TOP).gds \
		--topcell=$(TOP) \
		--run_dir=$(DRC_RPT_DIR) \
		--mp=32 \
		--density_thr=32
	sleep 4
.PHONY: klayout-drc-regular

magic-drc: ## Run Magic DRC of the CELL cell (usage: make magic-drc [CELL=<cellname>])
	mkdir -p $(DRC_RPT_DIR)
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) sak-drc.sh -d -m -f "*" -w $(DRC_RPT_DIR) $(LAY_DIR)/$(CELL).gds
	rm -f $(DRC_RPT_DIR)/drc_$(CELL).tcl
	sleep 4
.PHONY: magic-drc
# ================================================================================================


# Parasitic Extraction Targets
klayout-pex: ## Run Parasitic Extraction with KPEX of the CELL cell (usage: make klayout-pex [CELL=<cellname>] [EXT_MODE=<1|2|3>])
	mkdir -p $(NET_PEX_DIR)
	PDK_UNDERSCORED=$$(echo $$PDK | sed -e 's/-/_/g'); \
	case $(EXT_MODE) in \
		1) echo "WARNING: KPEX does not support C-decoupled (C) mode yet, using C-coupled (CC) mode instead."; KPEX_MODE=CC ;; \
		2) KPEX_MODE=CC ;; \
		3) KPEX_MODE=RC ;; \
		*) echo "Invalid EXT_MODE: $(EXT_MODE). Use 1, 2, or 3."; exit 1;; \
	esac; \
	kpex \
	--pdk $$PDK_UNDERSCORED \
	--cell $(CELL) \
	--schematic $(SCH_DIR)/$(CELL).sch \
	--gds $(LAY_DIR)/$(CELL)_flat.gds \
	--magic \
	--magic_mode $$KPEX_MODE \
	--out_dir $(NET_PEX_DIR) \
	--out_spice $(NET_PEX_DIR)/$(CELL)_klayout_pex.spice
#	--2.5D
#	--mode $$KPEX_MODE
	sed -i 's/$(CELL)_flat/$(CELL)_pex/g' $(NET_PEX_DIR)/$(CELL)_klayout_pex.spice
	rm -rf $(NET_PEX_DIR)/$(CELL)_flat__$(CELL)
	rm -f $(CELL)_flat.nodes $(CELL)_flat.sim
	@if [ -f $(SCH_DIR)/$(CELL)_pex.sym ]; then \
		echo "Reordering pins in $(CELL)_klayout_pex.spice to match $(CELL)_pex.sym..."; \
		python3 $(NET_PEX_DIR)/reorder_spice_pins.py $(SCH_DIR)/$(CELL)_pex.sym $(NET_PEX_DIR)/$(CELL)_klayout_pex.spice; \
	else \
		echo "No symbol $(SCH_DIR)/$(CELL)_pex.sym found, skipping pin reorder."; \
	fi
	sleep 4
.PHONY: klayout-pex

magic-pex: ## Run Parasitic Extraction with Magic of the CELL cell (usage: make magic-pex [CELL=<cellname>] [EXT_MODE=<1|2|3>])
	mkdir -p $(NET_PEX_DIR)
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) sak-pex.sh -d -m $(EXT_MODE) -w $(NET_PEX_DIR) $(LAY_DIR)/$(CELL)_flat.gds
	mv $(NET_PEX_DIR)/$(CELL)_flat.pex.spice $(NET_PEX_DIR)/$(CELL)_magic_pex.spice
	sed -i 's/$(CELL)/$(CELL)_pex/g' $(NET_PEX_DIR)/$(CELL)_magic_pex.spice
	rm -f $(NET_PEX_DIR)/pex_$(CELL)_flat.tcl $(NET_PEX_DIR)/$(CELL).ext $(NET_PEX_DIR)/$(CELL)_flat.ext $(NET_PEX_DIR)/$(CELL)_flat.res.ext
	@if [ -f $(SCH_DIR)/$(CELL)_pex.sym ]; then \
		echo "Reordering pins in $(CELL)_magic_pex.spice to match $(CELL)_pex.sym..."; \
		python3 $(NET_PEX_DIR)/reorder_spice_pins.py $(SCH_DIR)/$(CELL)_pex.sym $(NET_PEX_DIR)/$(CELL)_magic_pex.spice; \
	else \
		echo "No symbol $(SCH_DIR)/$(CELL)_pex.sym found, skipping pin reorder."; \
	fi
	sleep 4
.PHONY: magic-pex
# ================================================================================================


# Verify Targets
klayout-verify-cell: ## Verify a specific cell with KLayout (usage: make klayout-verify-cell CELL=<cellname>)
	$(MAKE) klayout-lvs klayout-drc klayout-pex CELL=$(CELL)
.PHONY: klayout-verify-cell

klayout-verify-top: ## Verify top cell with KLayout (usage: make klayout-verify-top)
	$(MAKE) klayout-lvs klayout-drc-regular klayout-pex
.PHONY: klayout-verify-top

magic-verify-cell: ## Verify a specific cell with Magic (usage: make magic-verify-cell CELL=<cellname>)
	$(MAKE) magic-lvs magic-drc magic-pex CELL=$(CELL)
.PHONY: magic-verify-cell

magic-verify-top: ## Verify top cell with Magic (usage: make magic-verify-top)
	$(MAKE) magic-lvs magic-drc magic-pex
.PHONY: magic-verify-top
# ================================================================================================


# Rendering Target
render-gds: ## Render an image from the GDS of the TOP macro (usage: make render-gds)
	mkdir -p $(RENDER_DIR)/
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) python3 $(MAKEFILE_DIR)/scripts/lay2img.py $(LAY_DIR)/$(TOP).gds $(RENDER_DIR)/$(TOP).png --width 2048 --oversampling 4
.PHONY: render-gds
# ================================================================================================


# Build Targets
build-pdk: ## Clone & install the IHP-Open-PDK repository with GDSFactory cells (usage: make build-pdk)
	rm -rf IHP/
	git clone -b IHP-TO https://github.com/iic-jku/IHP.git
	/usr/bin/python3 -m venv --system-site-packages .venv
	. .venv/bin/activate && cd IHP && pip install .
.PHONY: build-pdk

build-layout: ## Build the six-port layout for a specific frequency (usage: make build-layout [FREQ=<GHz>] [NO_FILL=0|1] [NO_FILL_M5=0|1])
	. .venv/bin/activate && PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) python3 $(MAKEFILE_DIR)/scripts/six_port_gen.py \
		$(LAY_DIR)/sparx$(FREQ)_top.gds $(LAY_DIR)/sparx_powdet_sbd.gds \
		--frequency $(FREQ)e9 \
		$(if $(filter 1,$(NO_FILL)),--no-fill) \
		$(if $(filter 1,$(NO_FILL_M5)),--no-fill-m5)
	rm -rf build/
.PHONY: build-layout

build-layout-sweep: ## Build frequency-scalable six-port layouts over a sweep (usage: make build-layout-sweep [START_FREQ=<GHz>] [STOP_FREQ=<GHz>] [STEP_FREQ=<GHz>] [NO_FILL=0|1] [NO_FILL_M5=0|1])
	bash -lc ' \
		for ghz in $$(seq $(START_FREQ) $(STEP_FREQ) $(STOP_FREQ)); do \
			echo "=== Running make build-layout for $${ghz} GHz ==="; \
			$(MAKE) build-layout FREQ=$${ghz} NO_FILL=$(NO_FILL) NO_FILL_M5=$(NO_FILL_M5); \
		done'
	rm -rf build/
.PHONY: build-layout-sweep

build-top: ## Build TOP cell (usage: make build-top [FREQ=<GHz>])
	$(MAKE) build-pdk
	$(MAKE) build-layout FREQ=$(FREQ)
	$(MAKE) render-gds
.PHONY: build-top

all: ## Build and verify the TOP cell (usage: make all)
	$(MAKE) build-top
#	$(MAKE) klayout-verify-top
#	$(MAKE) magic-verify-top
	$(MAKE) magic-verify-cell CELL=$(POWDET)
.PHONY: all
# ================================================================================================