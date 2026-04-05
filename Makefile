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

help: ## Show this help message
	@echo 'Usage: make <target> [CELL=<cellname>] [PEX_MODE=<1|2|3>] [EV_PRECISION=<digits>]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
	@echo ''
	@echo 'CELL defaults to $(TOP). Override to verify subcells.'
	@echo 'PEX_MODE defaults to 2 (C-coupled). 1=C-decoupled, 3=full-RC.'
	@echo 'EV_PRECISION defaults to 5 significant digits for xschem ev function.'
.PHONY: help

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

klayout-lvs: ## KLayout LVS of the analog macro (usage: make klayout-lvs [CELL=<cellname>] [IGNORE_TOP_PORTS=1])
	$(MAKE) klayout-lvs-netlist CELL=$(CELL)
	mkdir -p $(LVS_RPT_DIR)
	python3 $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/lvs/run_lvs.py \
		--layout=$(LAY_DIR)/$(CELL).gds \
		--netlist=$(LVS_SCH_DIR)/$(CELL).cdl \
		--topcell=$(CELL) \
		--run_dir=$(LVS_RPT_DIR) \
		--run_mode=deep
	sleep 4
	mkdir -p $(LVS_LAY_DIR)
	mv $(LVS_RPT_DIR)/$(CELL)_extracted.cir $(LVS_LAY_DIR)/$(CELL)_extracted.cir
.PHONY: klayout-lvs

klayout-drc: ## KLayout DRC of the analog macro (usage: make klayout-drc [CELL=<cellname>])
	mkdir -p $(DRC_RPT_DIR)
	python3 $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/drc/run_drc.py \
		--path=$(LAY_DIR)/$(CELL).gds \
		--topcell=$(CELL) \
		--run_dir=$(DRC_RPT_DIR) \
		--mp=32 \
		--density_thr=32
	sleep 4
.PHONY: klayout-drc

magic-rcx: ## RC-Extraction of the analog macro (usage: make magic-rcx [CELL=<cellname>] [PEX_MODE=<1|2|3>])
	mkdir -p $(PEX_DIR)
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) sak-pex.sh -d -m $(PEX_MODE) -w $(PEX_DIR) $(call find_gds,$(CELL))
	mv $(PEX_DIR)/$(CELL).pex.spice $(PEX_DIR)/$(CELL)_pex.spice
	sed -i 's/$(CELL)/$(CELL)_pex/g' $(PEX_DIR)/$(CELL)_pex.spice
	rm -f $(PEX_DIR)/pex_$(CELL).tcl $(PEX_DIR)/$(CELL).ext
	@if [ -f $(XSCHEM_DIR)/$(CELL)_pex.sym ]; then \
		echo "Reordering pins in $(CELL)_pex.spice to match $(CELL)_pex.sym..."; \
		python3 $(PEX_DIR)/reorder_spice_pins.py $(XSCHEM_DIR)/$(CELL)_pex.sym $(PEX_DIR)/$(CELL)_pex.spice; \
	else \
		echo "No symbol $(XSCHEM_DIR)/$(CELL)_pex.sym found, skipping pin reorder."; \
	fi
	sleep 4
.PHONY: magic-rcx

verify-cell: ## Verify a specific cell (usage: make verify-cell CELL=<cellname> [IGNORE_TOP_PORTS=1])
	$(MAKE) lvs drc pex CELL=$(CELL) IGNORE_TOP_PORTS=$(IGNORE_TOP_PORTS)
.PHONY: verify-cell

verify-spdt: ## Verify spdt subcell GDS files in klayout/ (LVS, DRC, PEX each)
	$(MAKE) verify-cell CELL=iqmod_spdt_switch_inv
	$(MAKE) verify-cell CELL=iqmod_spdt_switch_tg
	$(MAKE) verify-cell CELL=iqmod_spdt_switch
.PHONY: verify-spdt

verify-filter: ## Verify filter subcell GDS files in klayout/ (LVS, DRC, PEX each)
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_ota_core_spdt_switch_inv
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_ota_core_spdt_switch_tg
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_ota_core_spdt_switch
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_ota_core_tg
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_ota_core_inv_NF6
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_ota_core_inv_NF10
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_ota_core_inv_NF20
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_ota_core_hybrid_bm
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_R1
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_R2
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_R3
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf_R4
	$(MAKE) verify-cell CELL=iqmod_mfb_lpf
.PHONY: verify-filter

verify-mixer: ## Verify mixer subcell GDS files in klayout/ (LVS, DRC, PEX each)
	$(MAKE) verify-cell CELL=iqmod_mixer_se2diff_tg_NF6
	$(MAKE) verify-cell CELL=iqmod_mixer_se2diff_inv_NF2
	$(MAKE) verify-cell CELL=iqmod_mixer_se2diff_inv_NF6
	$(MAKE) verify-cell CELL=iqmod_mixer_se2diff_inv_NF18
	$(MAKE) verify-cell CELL=iqmod_mixer_se2diff_inv_NF54
	$(MAKE) verify-cell CELL=iqmod_mixer_se2diff
	$(MAKE) verify-cell CELL=iqmod_mixer_tg
	$(MAKE) verify-cell CELL=iqmod_mixer
.PHONY: verify-mixer

verify-top: ## Verify top cell (usage: make verify-top)
	$(MAKE) lvs drc pex CELL=$(TOP)
.PHONY: verify-top

verify-all: ## Verify all subcell GDS files in klayout/ (LVS, DRC, PEX each)
	$(MAKE) verify-spdt
	$(MAKE) verify-filter
	$(MAKE) verify-mixer
	$(MAKE) verify-top
.PHONY: verify-all

verilog: ## Write a Verilog stub of the TOP cell from PEX netlist pins
	rm -rf $(VH_DIR)
	mkdir -p $(VH_DIR)
	@echo 'module $(TOP) (' > $(VH_DIR)/$(TOP).v
	@echo '`ifdef USE_POWER_PINS' >> $(VH_DIR)/$(TOP).v
	@echo '    inout VDD,' >> $(VH_DIR)/$(TOP).v
	@echo '    inout VSS,' >> $(VH_DIR)/$(TOP).v
	@echo '`endif' >> $(VH_DIR)/$(TOP).v
	@echo '    input di_analog_en,' >> $(VH_DIR)/$(TOP).v
	@echo '    input di_spdt_ctrl_I,' >> $(VH_DIR)/$(TOP).v
	@echo '    inout vinp_I,' >> $(VH_DIR)/$(TOP).v
	@echo '    input di_ds_I_p,' >> $(VH_DIR)/$(TOP).v
	@echo '    inout vinn_I,' >> $(VH_DIR)/$(TOP).v
	@echo '    input di_ds_I_n,' >> $(VH_DIR)/$(TOP).v
	@echo '    input di_lo_I,' >> $(VH_DIR)/$(TOP).v
	@echo '    input di_lo_Ix,' >> $(VH_DIR)/$(TOP).v
	@echo '    input di_lo_Qx,' >> $(VH_DIR)/$(TOP).v
	@echo '    input di_lo_Q,' >> $(VH_DIR)/$(TOP).v
	@echo '    input di_ds_Q_n,' >> $(VH_DIR)/$(TOP).v
	@echo '    inout vinn_Q,' >> $(VH_DIR)/$(TOP).v
	@echo '    input di_ds_Q_p,' >> $(VH_DIR)/$(TOP).v
	@echo '    inout vinp_Q,' >> $(VH_DIR)/$(TOP).v
	@echo '    input di_spdt_ctrl_Q,' >> $(VH_DIR)/$(TOP).v
	@echo '    inout voutp_I_RF,' >> $(VH_DIR)/$(TOP).v
	@echo '    inout voutn_I_RF,' >> $(VH_DIR)/$(TOP).v
	@echo '    inout voutn_Q_RF,' >> $(VH_DIR)/$(TOP).v
	@echo '    inout voutp_Q_RF' >> $(VH_DIR)/$(TOP).v
	@echo ');' >> $(VH_DIR)/$(TOP).v
	@echo 'endmodule' >> $(VH_DIR)/$(TOP).v
	@echo "Checking PEX pins against Verilog stub..."
	@pex_pins=$$(awk '/^\.subckt $(TOP)_pex/{sub(/^\.subckt [^ ]+ /,"");p=$$0;next} p&&/^[+]/{sub(/^[+] */,"");p=p" "$$0;next} p{exit} END{print p}' $(PEX_DIR)/$(TOP)_pex.spice); \
	vh_pins=$$(grep -oP '(?<=inout |input )\w+' $(VH_DIR)/$(TOP).v | tr '\n' ' '); \
	fail=0; \
	for pin in $$pex_pins; do \
		if ! echo " $$vh_pins " | grep -qw "$$pin"; then \
			echo "ERROR: PEX pin '$$pin' missing from Verilog stub!"; \
			fail=1; \
		fi; \
	done; \
	for pin in $$vh_pins; do \
		if ! echo " $$pex_pins " | grep -qw "$$pin"; then \
			echo "ERROR: Verilog pin '$$pin' not found in PEX netlist!"; \
			fail=1; \
		fi; \
	done; \
	if [ "$$fail" -ne 0 ]; then exit 1; fi; \
	echo "All pins match between PEX netlist and Verilog stub."
.PHONY: verilog

lef: ## Export LEF from the TOP cell layout using Magic
	rm -rf $(LEF_DIR)
	mkdir -p $(LEF_DIR)
	printf '%s\n' \
		'gds read $(KLAYOUT_DIR)/$(TOP).gds' \
		'load $(TOP)' \
		'lef write $(LEF_DIR)/$(TOP).lef -hide -pinonly 2um' | \
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) magic -dnull -noconsole \
		-rcfile $(PDK_ROOT)/$(PDK)/libs.tech/magic/ihp-sg13g2.magicrc
.PHONY: lef

lib:
	rm -rf $(LIB_DIR)
	mkdir -p $(LIB_DIR)
	@printf 'library ($(TOP)) {\n  input_threshold_pct_fall: 50.0;\n  input_threshold_pct_rise: 50.0;\n  output_threshold_pct_fall: 50.0;\n  output_threshold_pct_rise: 50.0;\n  slew_lower_threshold_pct_fall: 20.0;\n  slew_lower_threshold_pct_rise: 20.0;\n  slew_upper_threshold_pct_fall: 80.0;\n  slew_upper_threshold_pct_rise: 80.0;\n  \n  cell ($(TOP)) {\n  }\n}\n' > $(LIB_DIR)/$(TOP).lib
.PHONY: lib

copy-gds: ## Copy the TOP cell GDS from klayout/ to final/gds/
	rm -rf $(GDS_DIR)
	mkdir -p $(GDS_DIR)
	cp $(KLAYOUT_DIR)/$(TOP).gds $(GDS_DIR)/$(TOP).gds
.PHONY: copy-gds

render-image: ## Render an image from the layout of the TOP macro
	rm -rf $(IMG_DIR)/
	mkdir -p $(IMG_DIR)/
	PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) python3 $(MAKEFILE_DIR)/../../scripts/lay2img.py $(KLAYOUT_DIR)/$(TOP).gds $(IMG_DIR)/$(TOP).png --width 2048 --oversampling 4
.PHONY: render-image

build-top: ## Build TOP cell (Verilog, LEF, LIB, copy GDS, and render image)
	$(MAKE) verilog
	$(MAKE) lef
	$(MAKE) lib
	$(MAKE) copy-gds
	$(MAKE) render-image
.PHONY: build-top

all: ## Build and verify the the TOP cell
	$(MAKE) verify-all
	$(MAKE) build-top
.PHONY: all