MAKEFILE_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

TOP = sparx160_top

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
LVS_SCH_DIR := netlist/schematic
LVS_LAY_DIR := netlist/layout
RCX_DIR     := netlist/rcx
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
	mkdir -p $(LVS_SCH_DIR)
	xschem -s -x -q --rcfile $(SCH_DIR)/xschemrc --command ' \
		set spiceprefix 0; \
		set lvs_netlist 1; \
		set ev_precision $(EV_PRECISION); \
		set netlist_dir $(LVS_SCH_DIR); \
		xschem set netlist_name [file tail [file rootname [xschem get current_name]]].cdl; \
		xschem netlist \
	' $(SCH_DIR)/$(CELL).sch
.PHONY: klayout-lvs-netlist

klayout-lvs: ## KLayout LVS of the CELL cell (usage: make klayout-lvs [CELL=<cellname>])
	$(MAKE) klayout-lvs-netlist CELL=$(CELL)
	mkdir -p $(LVS_RPT_DIR)
	python3 $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/lvs/run_lvs.py \
		--layout=$(LAY_DIR)/$(CELL).gds \
		--netlist=$(LVS_SCH_DIR)/$(CELL).cdl \
		--topcell=$(CELL) \
		--run_dir=$(LVS_RPT_DIR) \
		--run_mode=deep
	mkdir -p $(LVS_LAY_DIR)
	mv $(LVS_RPT_DIR)/$(CELL)_extracted.cir $(LVS_LAY_DIR)/$(CELL)_extracted.cir
	sleep 4
.PHONY: klayout-lvs

# magic-lvs-netlist: ## Export LVS netlist from Xschem for Magic LVS (usage: make magic-lvs-netlist [CELL=<cellname>] [EV_PRECISION=<digits>])
# 	mkdir -p $(LVS_SCH_DIR)
# 	xschem -s -x -q --rcfile $(SCH_DIR)/xschemrc --command ' \
# 		set spiceprefix 0; \
# 		set lvs_netlist 1; \
# 		# ToDo set lvs_ignore 1; \
# 		set ev_precision $(EV_PRECISION); \
# 		set netlist_dir $(LVS_SCH_DIR); \
# 		xschem set netlist_name [file tail [file rootname [xschem get current_name]]].cdl; \
# 		xschem netlist \
# 	' $(SCH_DIR)/$(CELL).sch
# .PHONY: magic-lvs-netlist

# magic-lvs: ## Magic LVS of the CELL cell (usage: make magic-lvs [CELL=<cellname>])
# 	$(MAKE) magic-lvs-netlist CELL=$(CELL)
# 	mkdir -p $(LVS_RPT_DIR)
# 	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) sak-lvs.sh -d -w $(LVS_RPT_DIR) -s $(LVS_SCH_DIR)/$(CELL).cdl $(LAY_DIR)/$(CELL).gds
# 	sleep 4
# .PHONY: magic-lvs
# ================================================================================================


# DRC Targets
klayout-drc: ## KLayout DRC of the CELL cell (usage: make klayout-drc [CELL=<cellname>])
	mkdir -p $(DRC_RPT_DIR)
	python3 $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/drc/run_drc.py \
		--path=$(LAY_DIR)/$(CELL).gds \
		--topcell=$(CELL) \
		--run_dir=$(DRC_RPT_DIR) \
		--antenna \
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
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) sak-drc.sh -d -w $(DRC_RPT_DIR) $(LAY_DIR)/$(CELL).gds
	sleep 4
.PHONY: magic-drc
# ================================================================================================


# Parasitic Extraction Targets
# klayout-rcx: ## RC-Extraction with KLayout of the CELL cell (usage: make klayout-rcx [CELL=<cellname>] [PEX_MODE=<1|2|3>])
# 	mkdir -p $(RCX_DIR)
# 	# ToDo: KLayout PEX not yet available for IHP SG13G2
# 	sleep 4
# .PHONY: klayout-rcx

magic-rcx: ## RC-Extraction with Magic of the CELL cell (usage: make magic-rcx [CELL=<cellname>] [PEX_MODE=<1|2|3>])
	mkdir -p $(RCX_DIR)
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) sak-pex.sh -d -m $(PEX_MODE) -w $(RCX_DIR) $(LAY_DIR)/$(CELL).gds
	mv $(RCX_DIR)/$(CELL).pex.spice $(RCX_DIR)/$(CELL)_pex.spice
	sed -i 's/$(CELL)/$(CELL)_pex/g' $(RCX_DIR)/$(CELL)_pex.spice
	rm -f $(RCX_DIR)/pex_$(CELL).tcl $(RCX_DIR)/$(CELL).ext
	@if [ -f $(SCH_DIR)/$(CELL)_pex.sym ]; then \
		echo "Reordering pins in $(CELL)_pex.spice to match $(CELL)_pex.sym..."; \
		python3 $(RCX_DIR)/reorder_spice_pins.py $(SCH_DIR)/$(CELL)_pex.sym $(RCX_DIR)/$(CELL)_pex.spice; \
	else \
		echo "No symbol $(SCH_DIR)/$(CELL)_pex.sym found, skipping pin reorder."; \
	fi
	sleep 4
.PHONY: magic-rcx
# ================================================================================================


# Verify Targets
klayout-verify-cell: ## Verify a specific cell with KLayout (usage: make klayout-verify-cell CELL=<cellname>)
	$(MAKE) klayout-lvs klayout-drc klayout-rcx CELL=$(CELL) 
.PHONY: klayout-verify-cell

klayout-verify-top: ## Verify top cell with KLayout (usage: make klayout-verify-top)
	$(MAKE) klayout-lvs klayout-drc-regular klayout-rcx
.PHONY: klayout-verify-top

magic-verify-cell: ## Verify a specific cell with Magic (usage: make magic-verify-cell CELL=<cellname>)
	$(MAKE) magic-lvs magic-drc magic-rcx CELL=$(CELL)
.PHONY: magic-verify-cell

magic-verify-top: ## Verify top cell with Magic (usage: make magic-verify-top)
	$(MAKE) magic-lvs magic-drc magic-rcx
.PHONY: magic-verify-top

verify-all: ## Verify all (usage: make verify-all)
	$(MAKE) klayout-lvs klayout-drc magic-rcx CELL=$(CELL)
	$(MAKE) klayout-lvs klayout-drc-regular magic-rcx
.PHONY: verify-all
# ================================================================================================


# Rendering Target
render-image: ## Render an image from the layout of the TOP macro (usage: make render-image)
	mkdir -p $(IMG_DIR)/
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) python3 $(MAKEFILE_DIR)/scripts/lay2img.py $(LAY_DIR)/$(TOP).gds $(IMG_DIR)/$(TOP).png --width 2048 --oversampling 4
.PHONY: render-image
# ================================================================================================


# Build Targets
build-pdk: ## Clone & install the IHP-Open-PDK repository with GDSFactory cells (usage: make pdk)
	git clone https://github.com/iic-jku/IHP.git
	cd IHP && pip install .
.PHONY: build-pdk

layout-six-port: ## Build layout of six-port (usage: make layout-six-port)
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) python3 $(MAKEFILE_DIR)/scripts/six_port_area_optimized.py $(LAY_DIR)/$(TOP).gds
.PHONY: layout-six-port

build-top: ## Build TOP cell (usage: make build-top)
	$(MAKE) build-pdk
	$(MAKE) layout-six-port
	$(MAKE) render-image
.PHONY: build-top

all: ## Build and verify the TOP cell
	$(MAKE) verify-all
	$(MAKE) build-top
.PHONY: all
# ================================================================================================