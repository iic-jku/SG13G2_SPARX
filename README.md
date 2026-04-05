# SPARX160: A Programmatically Generated 160-GHz Six-Port Receiver in 130-nm CMOS

(c) 2025-2026 David Kellerer-Pirklbauer, Simon Dorrer and Harald Pretl

<p align="center">
  <a href="img/sparx160_top_white_wo_M5.png">
    <img src="img/sparx160_top_white_wo_M5.png" alt="Render of the Six-Port Receiver without M5 GND plane" width=70%>
  </a>
  <br>
  <em>Render of the Six-Port Receiver without M5 GND plane.</em>
</p>

---

## Overview

- Six-Port
    - Branch Line Coupler (BLC)
        - ToDo
    - Wilkinson Divider
        - ToDo
    - Hairpin Coupled-Line Bandpass Filter
        - ToDo
- Power Detector (PD)
    - Schottky Barrier Diode (SBD)
        - ToDo

<p align="center">
  <a href="doc/sparx160_blockdiagram.png">
    <img src="doc/sparx160_blockdiagram.png" alt="Block Diagram of the Six-Port Receiver" width=70%>
  </a>
  <br>
  <em>Block Diagram of the Six-Port Receiver.</em>
</p>

---

## Chip Specifications

| Parameter           | Value                                                                             |
| ------------------- | --------------------------------------------------------------------------------- |
| Technology          | IHP SG13G2 (130nm CMOS)                                                           |
| Die Area            | 1000 × 1400 µm (1.4 mm²)                                                          |
| Supply Voltage      | 1.5 V                                                                             |

---

## Makefile Targets

### Export LVS Netlist

Exports the LVS netlist from Xschem and places it in `netlist/schematic/`.

The `EV_PRECISION` parameter sets the number of significant digits used by Xschem's `ev` function when calculating device properties (default: 5). Increase this to avoid LVS mismatches caused by floating-point rounding differences between Xschem and KLayout (see [xschem#465](https://github.com/StefanSchippers/xschem/issues/465)).

```sh
make klayout-lvs-netlist
make klayout-lvs-netlist CELL=sparx160_powdet_sbd
make klayout-lvs-netlist EV_PRECISION=5
```

### Layout Versus Schematic (LVS)

Exports the schematic netlist from Xschem, then runs LVS. Compares the GDS layout in `layout/` against the schematic netlist in `netlist/schematic/`. Reports are saved to `verification/lvs/`. The extracted layout netlist is moved to `netlist/layout/`.

**KLayout LVS** uses `run_lvs.py` from the IHP Open-PDK:

```sh
make klayout-lvs
make klayout-lvs CELL=sparx160_powdet_sbd
```

**Magic LVS** uses `sak-lvs.sh` (Magic VLSI + Netgen):

```sh
make magic-lvs
make magic-lvs CELL=sparx160_powdet_sbd
```

### Design Rule Check (DRC)

Runs DRC on the GDS layout in `layout/`. Reports are saved to `verification/drc/`.

**KLayout DRC** uses `run_drc.py` from the IHP Open-PDK:

```sh
make klayout-drc
make klayout-drc CELL=sparx160_powdet_sbd
```

**KLayout DRC (regular)** runs the full DRC rule set on the top-level cell:

```sh
make klayout-drc-regular
```

**Magic DRC** uses `sak-drc.sh` (Magic VLSI):

```sh
make magic-drc
make magic-drc CELL=sparx160_powdet_sbd
```

### Parasitic Extraction (PEX)

Runs parasitic extraction on the GDS layout in `layout/`. The extracted SPICE netlist is written to `netlist/rcx/`.

The `PEX_MODE` parameter selects the extraction mode:
- `1` = C-decoupled
- `2` = C-coupled
- `3` = full-RC (default)

If a matching Xschem symbol (`schematic/<CELL>_pex.sym`) exists, the `.subckt` pin order in the extracted SPICE file is automatically reordered to match the symbol's pin positions. This ensures the PEX netlist can be used directly with the corresponding Xschem symbol for simulation.

**Magic PEX** uses `sak-pex.sh` (Magic VLSI):

```sh
make magic-rcx
make magic-rcx CELL=sparx160_powdet_sbd
make magic-rcx CELL=sparx160_powdet_sbd PEX_MODE=3
```

### Verify a Specific Cell

Runs LVS, DRC, and PEX for a specific cell:

```sh
make klayout-verify-cell CELL=sparx160_powdet_sbd
make magic-verify-cell CELL=sparx160_powdet_sbd
```

### Verify Top Cell

Runs LVS, DRC, and PEX for the top cell:

```sh
make klayout-verify-top
make magic-verify-top
```

### Verify All

Runs verification for a specific cell and the top cell (KLayout LVS + DRC, Magic PEX):

```sh
make verify-all
make verify-all CELL=sparx160_powdet_sbd
```

### Render Layout of the Design

Renders the top-level GDS layout and saves it in the `img/` folder:

```sh
make render-image
```

### Build Top Cell

Builds the top-level cell: six-port layout generation and image rendering:

```sh
make build-top
```

### Build All

Builds the complete design by first verifying all cells (`verify-all`), then building the top-level cell (`build-top`):

```sh
make all
```

---

## Cite This Work

```
@software{2026_SPARX160,
	author = {Kellerer-Pirklbauer, David and Dorrer, Simon and Pretl, Harald},
	month = April,
	title = {{GitHub Repository for SPARX160: A Programmatically Generated 160-GHz Six-Port Receiver in 130-nm CMOS}},
	url = {https://github.com/iic-jku/SG13G2_SPARX160},
	doi = {ToDo},
	year = {2026}
}
```

---

## Acknowledgements

This project is funded by the JKU/SAL [IWS Lab](https://research.jku.at/de/projects/jku-lit-sal-intelligent-wireless-systems-lab-iws-lab/), a collaboration of [Johannes Kepler University](https://jku.at) and [Silicon Austria Labs](https://silicon-austria-labs.com).

<p align="center">
  <a href="https://silicon-austria-labs.com" target="_blank">
    <img src="https://github.com/iic-jku/klayout-pex-website/raw/main/figures/funding/silicon-austria-labs-logo.svg" alt="Silicon Austria Labs" width="300"/>
  </a>
</p>

---