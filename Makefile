# Makefile for SPARX160: A Programmatically Generated 160-GHz Six-Port Receiver in 130-nm CMOS
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

TOP = sparx160_top
POWDET = sparx160_powdet_sbd

.DEFAULT_GOAL := help

# Cell name for verification targets (default: top-level cell)
# Override with: make <target> CELL=<cellname>
CELL ?= $(TOP)

# PEX mode (1 = C-decoupled, 2 = C-coupled, 3 = full-RC)
# Override with: make pex PEX_MODE=<1|2|3>
PEX_MODE ?= 3

# Floating-point precision (significant digits) for xschem's ev function
# Override with: make lvs-netlist EV_PRECISION=<digits>
EV_PRECISION ?= 5

# Folder structure
LAY_DIR 	:= layout
SCH_DIR  	:= schematic
IMG_DIR     := img
NET_SCH_DIR := netlist/schematic
NET_LAY_DIR := netlist/layout
NET_PEX_DIR := netlist/pex
LVS_RPT_DIR := verification/lvs
DRC_RPT_DIR := verification/drc


# Help Target
help: ## Show this help message
	@echo 'Usage: make <target> [CELL=<cellname>] [PEX_MODE=<1|2|3>] [EV_PRECISION=<digits>]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ''
	@echo 'CELL defaults to $(TOP). Override to verify subcells.'
	@echo 'PEX_MODE defaults to 3 (full-RC). 1=C-decoupled, 2=C-coupled.'
	@echo 'EV_PRECISION defaults to 5 significant digits for xschem ev function.'
.PHONY: help
# ================================================================================================


# LVS Targets
klayout-lvs-netlist: ## Export LVS netlist from Xschem for KLayout LVS (usage: make klayout-lvs-netlist [CELL=<cellname>] [EV_PRECISION=<digits>])
	mkdir -p $(NET_SCH_DIR)
	xschem -s -x -q --rcfile $(SCH_DIR)/xschemrc --command ' \
		set spiceprefix 0; \
		set lvs_netlist 1; \
		set top_is_subckt 1; \
		set lvs_ignore 0; \
		set ev_precision $(EV_PRECISION); \
		set netlist_dir $(NET_SCH_DIR); \
		xschem set netlist_name [file tail [file rootname [xschem get current_name]]]_klayout.cdl; \
		xschem netlist \
	' $(SCH_DIR)/$(CELL).sch
.PHONY: klayout-lvs-netlist

klayout-lvs: ## KLayout LVS of the CELL cell (usage: make klayout-lvs [CELL=<cellname>])
	$(MAKE) klayout-lvs-netlist CELL=$(CELL)
	mkdir -p $(LVS_RPT_DIR)
	mkdir -p $(NET_LAY_DIR)
	python3 $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/lvs/run_lvs.py \
		--layout=$(LAY_DIR)/$(CELL).gds \
		--netlist=$(NET_SCH_DIR)/$(CELL)_klayout.cdl \
		--topcell=$(CELL) \
		--run_dir=$(LVS_RPT_DIR) \
		--run_mode=deep
	mkdir -p $(NET_LAY_DIR)
	mv $(LVS_RPT_DIR)/$(CELL)_extracted.cir $(NET_LAY_DIR)/$(CELL)_klayout.cir
	sleep 4
.PHONY: klayout-lvs

magic-lvs-netlist: ## Export LVS netlist from Xschem for Magic LVS (usage: make magic-lvs-netlist [CELL=<cellname>] [EV_PRECISION=<digits>])
	mkdir -p $(NET_SCH_DIR)
	-xschem -s -x -q --rcfile $(SCH_DIR)/xschemrc --command ' \
		set spiceprefix 0; \
		set lvs_netlist 0; \
		set top_is_subckt 1; \
		set lvs_ignore 1; \
		set ev_precision $(EV_PRECISION); \
		set netlist_dir $(NET_SCH_DIR); \
		xschem set netlist_name [file tail [file rootname [xschem get current_name]]]_magic.spice; \
		xschem netlist \
	' $(SCH_DIR)/$(CELL).sch
.PHONY: magic-lvs-netlist

magic-lvs: ## Magic + Netgen LVS of the CELL cell (usage: make magic-lvs [CELL=<cellname>])
	mkdir -p $(LVS_RPT_DIR)
	mkdir -p $(NET_LAY_DIR)
	$(MAKE) magic-lvs-netlist CELL=$(CELL)
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) sak-lvs.sh -d -w $(LVS_RPT_DIR) -s $(NET_SCH_DIR)/$(CELL)_magic.spice -l $(LAY_DIR)/$(CELL).gds -c $(CELL)
	mv $(LVS_RPT_DIR)/$(CELL).ext.spc $(NET_LAY_DIR)/$(CELL)_magic.ext.spc
	rm -f $(LVS_RPT_DIR)/$(CELL).sch.spc
	rm -f $(LVS_RPT_DIR)/ext_$(CELL).tcl
	rm -f $(LVS_RPT_DIR)/*.ext
	sleep 4
.PHONY: magic-lvs
# ================================================================================================


# DRC Targets
klayout-drc: ## KLayout DRC of the CELL cell (usage: make klayout-drc [CELL=<cellname>])
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

klayout-drc-regular: ## Regular DRC of the TOP cell (usage: make klayout-drc-regular)
	mkdir -p $(DRC_RPT_DIR)
	python3 $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/drc/run_drc.py \
		--path=$(LAY_DIR)/$(TOP).gds \
		--topcell=$(TOP) \
		--run_dir=$(DRC_RPT_DIR) \
		--mp=32 \
		--density_thr=32
	sleep 4
.PHONY: klayout-drc-regular

magic-drc: ## Magic DRC of the CELL cell (usage: make magic-drc [CELL=<cellname>])
	mkdir -p $(DRC_RPT_DIR)
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) sak-drc.sh -d -m -w $(DRC_RPT_DIR) $(LAY_DIR)/$(CELL).gds
	rm -f $(DRC_RPT_DIR)/drc_$(CELL).tcl
	sleep 4
.PHONY: magic-drc
# ================================================================================================


# Parasitic Extraction Targets
klayout-pex: ## Parasitic Extraction with KLayout of the CELL cell (usage: make klayout-pex [CELL=<cellname>] [PEX_MODE=<1|2|3>])
	mkdir -p $(NET_PEX_DIR)
	echo "KLayout PEX is not yet available for the IHP Open-PDK."
	sleep 4
.PHONY: klayout-pex

magic-pex: ## Parasitic Extraction with Magic of the CELL cell (usage: make magic-pex [CELL=<cellname>] [PEX_MODE=<1|2|3>])
	mkdir -p $(NET_PEX_DIR)
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) sak-pex.sh -d -m $(PEX_MODE) -w $(NET_PEX_DIR) $(LAY_DIR)/$(CELL).gds
	mv $(NET_PEX_DIR)/$(CELL).pex.spice $(NET_PEX_DIR)/$(CELL)_pex.spice
	sed -i 's/$(CELL)/$(CELL)_pex/g' $(NET_PEX_DIR)/$(CELL)_pex.spice
	rm -f $(NET_PEX_DIR)/pex_$(CELL).tcl $(NET_PEX_DIR)/$(CELL).ext $(NET_PEX_DIR)/$(CELL)_flat.ext $(NET_PEX_DIR)/$(CELL)_flat.res.ext
	@if [ -f $(SCH_DIR)/$(CELL)_pex.sym ]; then \
		echo "Reordering pins in $(CELL)_pex.spice to match $(CELL)_pex.sym..."; \
		python3 $(NET_PEX_DIR)/reorder_spice_pins.py $(SCH_DIR)/$(CELL)_pex.sym $(NET_PEX_DIR)/$(CELL)_pex.spice; \
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

verify-all: ## Verify all (usage: make verify-all)
	$(MAKE) klayout-lvs klayout-drc magic-pex CELL=$(CELL)
	$(MAKE) klayout-lvs klayout-drc-regular magic-pex
.PHONY: verify-all
# ================================================================================================


# Rendering Target
render-image: ## Render an image from the layout of the TOP macro (usage: make render-image)
	mkdir -p $(IMG_DIR)/
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) python3 $(MAKEFILE_DIR)/scripts/lay2img.py $(LAY_DIR)/$(TOP).gds $(IMG_DIR)/$(TOP).png --width 2048 --oversampling 4
.PHONY: render-image
# ================================================================================================


# Build Targets
build-pdk: ## Clone & install the IHP-Open-PDK repository with GDSFactory cells (usage: make build-pdk)
	rm -rf IHP/
	git clone -b IHP-TO https://github.com/iic-jku/IHP.git
	cd IHP && pip install .
.PHONY: build-pdk

build-layout: ## Build layout of six-port (usage: make build-layout)
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) python3 $(MAKEFILE_DIR)/scripts/six_port_area_optimized.py $(LAY_DIR)/$(TOP).gds $(LAY_DIR)/$(POWDET).gds
.PHONY: build-layout

build-top: ## Build TOP cell (usage: make build-top)
	$(MAKE) build-pdk
	$(MAKE) build-layout
	$(MAKE) render-image
.PHONY: build-top

all: ## Build and verify the TOP cell (usage: make all)
	$(MAKE) verify-all
	$(MAKE) build-top
.PHONY: all
# ================================================================================================