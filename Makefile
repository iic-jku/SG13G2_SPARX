# Makefile for SPARX: An Automated, Programmatically Generated Frequency-Scalable Six-Port Receiver in 130-nm CMOS
#
# SPDX-FileCopyrightText: 2025-2026 The SPARX Team
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

# Variables
TOP = sparx160_top
POWDET = sparx_powdet_sbd

.DEFAULT_GOAL := help

# Version for release target
# Override with: make <target> VERSION=<version>
VERSION ?= 2.0.0

# Cell name for verification targets (default: top-level cell)
# Override with: make <target> CELL=<cellname>
CELL ?= $(TOP)

# PEX mode (1 = C-decoupled, 2 = C-coupled, 3 = full-RC)
# Override with: make <target> EXT_MODE=<1|2|3>
EXT_MODE ?= 3

# Floating-point precision (significant digits) for Xschem's ev function
# Override with: make <target> EV_PRECISION=<digits>
EV_PRECISION ?= 5

# Design frequency in GHz (default: 160)
# Override with: make build-layout FREQ=<frequency_in_GHz>
FREQ ?= 160

# Metal fill options for build-layout (0 = fill enabled, 1 = fill disabled)
# Override with: make build-layout NO_FILL=1 NO_FILL_M5=1
NO_FILL ?= 0
NO_FILL_M5 ?= 0

# Characteristic impedance and substrate parameters for EM simulation
# Override with: make sim-blc-em FREQ=<GHz> SIGNAL_CROSS_SECTION=<metal> GROUND_CROSS_SECTION=<metal> Z0=<Ohms> E_R=<relative_permittivity>
SIGNAL_CROSS_SECTION ?= TM2
GROUND_CROSS_SECTION ?= M5
Z0 ?= 50
E_R ?= 4.1

# HBPF-specific filter parameters for EM simulation
# Override with: make sim-hbpf-em BANDWIDTH=<GHz> FILTER_TYPE=<butter|cheby|ellip> FILTER_ORDER=<N> RIPPLE_DB=<dB>
BANDWIDTH ?= 1
FILTER_TYPE ?= butter
FILTER_ORDER ?= 3
RIPPLE_DB ?= 3

# Additional config parameter for wpd simulation
# Override with: make sim-wpd-em FREQ=<GHz> SIGNAL_CROSS_SECTION=<metal> GROUND_CROSS_SECTION=<metal> Z0=<Ohms> E_R=<relative_permittivity> CONFIG=<config_name>
CONFIG ?= U 	# C or U 

# Palace number of processors for EM simulation# Override with: make sim-blc-em NP=<num_processors>
NP ?= 4

# Frequency sweep in GHz
# Override with: make build-layout-sweep START_FREQ=<GHz> STOP_FREQ=<GHz> STEP_FREQ=<GHz>
START_FREQ ?= 60
STOP_FREQ ?= 300
STEP_FREQ ?= 20

# Folder structure
SCH_DIR     	:= schematic
LAY_DIR     	:= layout
SCRIPTS_DIR     := scripts
RELEASE_DIR		:= release
RENDER_IMG_DIR  := render/img
NET_SCH_DIR 	:= netlist/schematic
NET_LAY_DIR 	:= netlist/layout
NET_PEX_DIR 	:= netlist/pex
LVS_RPT_DIR 	:= verification/lvs
DRC_RPT_DIR 	:= verification/drc
EM_RPT_DIR 		:= verification/em
PALACE_SCRIPTS_DIR := $(PDK_ROOT)/$(PDK)/libs.tech/palace/scripts


# Help target
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
	@echo 'EV_PRECISION defaults to 5 significant digits for Xschem ev function.'
.PHONY: help
# ================================================================================================


# Build Targets
build-pdk: ## Clone & install the IHP-Open-PDK repository with GDSFactory cells (usage: make build-pdk)
	rm -rf IHP/
	git clone -b IHP-TO https://github.com/iic-jku/IHP.git
	/usr/bin/python3 -m venv --system-site-packages .venv
	. .venv/bin/activate && cd IHP && pip install .
.PHONY: build-pdk

build-layout: ## Build the six-port layout for a specific frequency (usage: make build-layout [FREQ=<GHz>] [NO_FILL=0|1] [NO_FILL_M5=0|1])
	. .venv/bin/activate && python3 $(SCRIPTS_DIR)/six_port_gen.py \
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
	$(MAKE) render-gds FREQ=$(FREQ)
.PHONY: build-top
# ================================================================================================


# Rendering Target
render-gds: ## Render an image from the GDS of the TOP cell (usage: make render-gds [FREQ=<GHz>])
	mkdir -p $(RENDER_IMG_DIR)/
	python3 $(SCRIPTS_DIR)/lay2img.py $(LAY_DIR)/sparx$(FREQ)_top.gds $(RENDER_IMG_DIR)/sparx$(FREQ)_top.png --width 2048 --oversampling 4
.PHONY: render-gds
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
	sak-lvs.sh -d -w $(LVS_RPT_DIR) -s $(NET_SCH_DIR)/$(CELL)_magic.spice -l $(LAY_DIR)/$(CELL).gds -c $(CELL)
# 	Alternative using sak-lvs.sh for netlist export and LVS in one step (replaces magic-lvs-netlist target):
# 	sak-lvs.sh -d -w $(LVS_RPT_DIR) -s $(SCH_DIR)/$(CELL).sch -l $(LAY_DIR)/$(CELL)_flat.gds -c $(CELL)
	mv $(LVS_RPT_DIR)/$(CELL).ext.spc $(NET_LAY_DIR)/$(CELL)_magic.ext.spc
	rm -f $(LVS_RPT_DIR)/$(CELL).sch.spc
	rm -f $(LVS_RPT_DIR)/ext_$(CELL).tcl
	rm -f $(LVS_RPT_DIR)/*.ext
	sleep 4
.PHONY: magic-lvs
# ================================================================================================


# DRC Targets
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

magic-drc: ## Run Magic DRC of the CELL cell (usage: make magic-drc [CELL=<cellname>])
	mkdir -p $(DRC_RPT_DIR)
	sak-drc.sh -d -m -f "*" -w $(DRC_RPT_DIR) $(LAY_DIR)/$(CELL).gds $(CELL)
	rm -f $(DRC_RPT_DIR)/drc_$(CELL).tcl
	sleep 4
.PHONY: magic-drc
# ================================================================================================


# PEX Targets
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
	sak-pex.sh -d -m $(EXT_MODE) -w $(NET_PEX_DIR) $(LAY_DIR)/$(CELL)_flat.gds
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
klayout-verify: ## Verify the CELL cell with KLayout (usage: make klayout-verify [CELL=<cellname>])
	$(MAKE) klayout-lvs CELL=$(CELL)
	$(MAKE) klayout-drc CELL=$(CELL)
	$(MAKE) klayout-pex CELL=$(CELL)
.PHONY: klayout-verify

magic-verify: ## Verify the CELL cell with Magic (usage: make magic-verify [CELL=<cellname>])
	$(MAKE) magic-lvs CELL=$(CELL)
	$(MAKE) magic-drc CELL=$(CELL)
	$(MAKE) magic-pex CELL=$(CELL)
.PHONY: magic-verify
# ================================================================================================


# EM Simulation Targets
sim-blc-em: ## Run EM simulation with BLC of the CELL cell (usage: make sim-blc-em [FREQ=<GHz>] [SIGNAL_CROSS_SECTION=<metal>] [GROUND_CROSS_SECTION=<metal>] [Z0=<Ohms>] [E_R=<e_r>])
	BLC_GDS_FILENAME=blc_$(FREQ)GHz_$(Z0)Ohm_$(SIGNAL_CROSS_SECTION)_$(GROUND_CROSS_SECTION)_e_r_$(subst .,_,$(E_R)); \
	. .venv/bin/activate && \
		python3 $(EM_RPT_DIR)/scripts/blc_em_sim.py \
			--frequency $(FREQ)e9 \
			--signal_cross_section $(SIGNAL_CROSS_SECTION) \
			--ground_cross_section $(GROUND_CROSS_SECTION) \
			--Z0 $(Z0) \
			--e_r $(E_R) && \
		python3 $(EM_RPT_DIR)/scripts/palace_sim.py ../layout/$$BLC_GDS_FILENAME.gds && \
		cd $(EM_RPT_DIR)/palace_model/$${BLC_GDS_FILENAME}_data && \
		palace -np $(NP) config.json && \
		python3 $(PALACE_SCRIPTS_DIR)/combine_extend_snp.py
.PHONY: sim-blc-em

sim-wpd-em: ## Run EM simulation with WPD of the CELL cell (usage: make sim-wpd-em [FREQ=<GHz>] [SIGNAL_CROSS_SECTION=<metal>] [GROUND_CROSS_SECTION=<metal>] [Z0=<Ohms>] [E_R=<e_r>])
	WPD_GDS_FILENAME=wpd_$(FREQ)GHz_$(Z0)Ohm_$(SIGNAL_CROSS_SECTION)_$(GROUND_CROSS_SECTION)_e_r_$(subst .,_,$(E_R))_config_$(CONFIG); \
	. .venv/bin/activate && \
		python3 $(EM_RPT_DIR)/scripts/wpd_em_sim.py \
			--frequency $(FREQ)e9 \
			--signal_cross_section $(SIGNAL_CROSS_SECTION) \
			--ground_cross_section $(GROUND_CROSS_SECTION) \
			--Z0 $(Z0) \
			--e_r $(E_R) \
			--config $(CONFIG) && \
		python3 $(EM_RPT_DIR)/scripts/palace_sim.py ../layout/$$WPD_GDS_FILENAME.gds && \
		cd $(EM_RPT_DIR)/palace_model/$${WPD_GDS_FILENAME}_data && \
		palace -np $(NP) config.json && \
		python3 $(PALACE_SCRIPTS_DIR)/combine_extend_snp.py
.PHONY: sim-wpd-em

sim-bpf-em: ## Run EM simulation with BPF of the CELL cell (usage: make sim-bpf-em [FREQ=<GHz>] [BANDWIDTH=<GHz>] [SIGNAL_CROSS_SECTION=<metal>] [GROUND_CROSS_SECTION=<metal>] [Z0=<Ohms>] [E_R=<e_r>] [FILTER_TYPE=<butter|cheby>] [FILTER_ORDER=<N>] [RIPPLE_DB=<dB>])
	BPF_FILTER_TYPE_LOWER=$$(echo "$(FILTER_TYPE)" | tr '[:upper:]' '[:lower:]'); \
	if [ "$$BPF_FILTER_TYPE_LOWER" = "butter" ]; then \
		RIPPLE_TAG=""; \
	else \
		RIPPLE_DB_TAG=$$(printf '%s' "$(RIPPLE_DB)" | sed 's/\.0$$//'); \
		RIPPLE_TAG="_rip_$$(printf '%s' "$$RIPPLE_DB_TAG" | tr '.' '_')dB"; \
	fi; \
	BPF_GDS_FILENAME=bpf_f_$(FREQ)GHz_bw_$(BANDWIDTH)GHz_sig_$(SIGNAL_CROSS_SECTION)_gnd_$(GROUND_CROSS_SECTION)_z0_$(Z0)Ohm_er_$(subst .,_,$(E_R))_$(FILTER_TYPE)_ord_$(FILTER_ORDER)$$RIPPLE_TAG; \
	. .venv/bin/activate && \
		python3 $(EM_RPT_DIR)/scripts/bpf_em_sim.py \
			--frequency $(FREQ)e9 \
			--bandwidth $(BANDWIDTH)e9 \
			--signal_cross_section $(SIGNAL_CROSS_SECTION) \
			--ground_cross_section $(GROUND_CROSS_SECTION) \
			--Z0 $(Z0) \
			--e_r $(E_R) \
			--filter_type $(FILTER_TYPE) \
			--filter_order $(FILTER_ORDER) \
			--ripple_dB $(RIPPLE_DB) && \
		python3 $(EM_RPT_DIR)/scripts/palace_sim.py ../layout/$$BPF_GDS_FILENAME.gds && \
		cd $(EM_RPT_DIR)/palace_model/$${BPF_GDS_FILENAME}_data && \
		palace -np $(NP) config.json && \
		python3 $(PALACE_SCRIPTS_DIR)/combine_extend_snp.py
.PHONY: sim-bpf-em
# ================================================================================================


# view the sim results of EM simulation
FILE_NAME ?= blc_$(FREQ)GHz_$(Z0)Ohm_$(SIGNAL_CROSS_SECTION)_$(GROUND_CROSS_SECTION)_e_r_$(subst .,_,$(E_R)).s4p
view-em-sim: ## View EM simulation results with s-parameter plots (usage: make view-em-sim FILE_NAME=<name_with_extension>)
	cd $(EM_RPT_DIR)/palace_model && python3 ../scripts/plot_snp.py $$(find . -type f -name "$(FILE_NAME)")
.PHONY: view-em-sim
# ================================================================================================


all: ## Build and verify the TOP cell (usage: make all)
	$(MAKE) build-top
#	$(MAKE) klayout-verify
#	$(MAKE) magic-verify
	$(MAKE) magic-lvs CELL=$(POWDET)
	$(MAKE) magic-drc CELL=$(POWDET)
	$(MAKE) magic-drc
	$(MAKE) klayout-drc
.PHONY: all
# ================================================================================================


# Release Target
release: ## Copy the gds and netlist files to the release folder (usage: make release VERSION=<version>)
	mkdir -p $(RELEASE_DIR)/v.$(VERSION)/gds
	mkdir -p $(RELEASE_DIR)/v.$(VERSION)/netlist
	cp -f $(LAY_DIR)/$(TOP).gds $(RELEASE_DIR)/v.$(VERSION)/gds/$(TOP).gds
	cp -r $(NET_SCH_DIR) $(RELEASE_DIR)/v.$(VERSION)/netlist/schematic
	cp -r $(NET_LAY_DIR) $(RELEASE_DIR)/v.$(VERSION)/netlist/layout
.PHONY: release
# ================================================================================================
