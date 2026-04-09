# SPARX: An Automated, Programmatically Generated Frequency-Scalable Six-Port Receiver in 130-nm CMOS

(c) 2025-2026 David Kellerer-Pirklbauer, Simon Dorrer and Harald Pretl

<p align="center">
  <a href="img/sparx160_top_white_wo_M5.png">
    <img src="img/sparx160_top_white_wo_M5.png" alt="Render of the Six-Port Receiver for 160GHz without M5 GND plane" width=70%>
  </a>
  <br>
  <em>Render of the Six-Port Receiver for 160GHz without M5 GND plane.</em>
</p>


## Overview
SPARX stands for Six-Port Automated Receiver. The whole layout is generated in Python with self-made RF devices as a GDSFactory IHP PDK add-on. S-Parameter simulation of the passive RF structures is done with AWS Palace. With KLayout, Magic and Netgen, a whole LVS, DRC and RCX verification flow is implemented. The SBD-based power detector is designed in Xschem and simulated with ngpsice and VACASK. This whole repo is controlled by a Makefile. Just clone it, and `make all`. To build and verify a six-port receiver at a target frequency of 160 GHz. If you need another target frequency, for example, 77 GHz, just `make all FREQ=77e9`. In the following video, the generation of six-port receivers from 60 GHz to 300 GHz under one minute is demonstrated.

https://github.com/user-attachments/assets/d6d2d47e-5059-4160-81d7-d421cda29d1a
<p align="center">
  <em>Generation of Six-Port Receivers from 60 GHz to 300 GHz.</em>
</p>


## Block Diagramm
- Six-Port
  - Branch Line Coupler (BLC)
  - Wilkinson Divider
  - Hairpin Coupled-Line Bandpass Filter
- Power Detector (PD)
  - Schottky Barrier Diode (SBD)
- Metal Stack
  - TopMetal2 (TM2): RF traces
  - Metal5 (M5): GND plane

<p align="center">
  <a href="doc/sparx_blockdiagram.png">
    <img src="doc/sparx_blockdiagram.png" alt="Block Diagram of the Six-Port Receiver" width=70%>
  </a>
  <br>
  <em>Block Diagram of the Six-Port Receiver.</em>
</p>


## Chip Specifications

| Parameter           | Value                                                                             |
| ------------------- | --------------------------------------------------------------------------------- |
| Technology          | IHP SG13G2 (130nm CMOS)                                                           |
| Die Area            | 1000 × 1400 µm (1.4 mm²)                                                          |
| Supply Voltage      | 1.5 V                                                                             |


## ToDos
- [ ] KLayout LVS --> CMIM issues with PWell.block layer (@klayoutmatthias)
- [ ] KLayout PEX (2.5D) --> work in progress (@martinjanköhler)
- [ ] Change DBU from 5nm to 1nm in code: @davkel99
- [ ] Add an additional pin layer to the pin label for correct netlist extraction in code: @davkel99
- [ ] Update GDSFactory IHP PDK `main` branch from `IHP-TO` branch: @davkel99
- [ ] Add new SPARX Python script with improved frequency scaling by @hpretl: @simi1505
- [ ] Top-level Six-Port simulation in Xschem: @simi1505


## Makefile Targets

### Export Schematic Netlist for LVS

Exports the schematic netlist for LVS from Xschem and places it in `netlist/schematic/`.

The `EV_PRECISION` parameter sets the number of significant digits used by Xschem's `ev` function when calculating device properties (default: 5). Increase this to avoid LVS mismatches caused by floating-point rounding differences between Xschem and KLayout (see [xschem#465](https://github.com/StefanSchippers/xschem/issues/465)).

Note that currently, for the KLayout LVS `ntap` and `ptap` devices are extracted, and therefore the schematic netlist also needs to provide them. However, for the Magic + Netgen LVS `ntap` and `ptap` devices are not extracted. Therefore, in the schematic, the `lvs_ignore = short` command is used for these devices. To make these settings also effective for the schematic netlist export, the option `set lvs_ignore 1` must be set in the target `magic-lvs-netlist`.
Note that KLayout works with CDL netlists and Magic works with SPICE netlists. On the other hand, the target `klayout-lvs-netlist` uses the Xschem commands `set spiceprefix 1`, `set lvs_netlist 1`, `set top_is_subckt 1` and `set lvs_ignore 0`. However, the target `magic-lvs-netlist` uses the Xschem commands `set spiceprefix 1`, `set lvs_netlist 0`, `set top_is_subckt 1` and `set lvs_ignore 1`.

To extract a CDL schematic netlist for KLayout LVS, use the following target:
```sh
make klayout-lvs-netlist
make klayout-lvs-netlist CELL=sparx_powdet_sbd
make klayout-lvs-netlist EV_PRECISION=5
```

To extract a SPICE schematic netlist for Magic + Netgen LVS, use the following target:
```sh
make magic-lvs-netlist
make magic-lvs-netlist CELL=sparx_powdet_sbd
make magic-lvs-netlist EV_PRECISION=5
```

### Layout Versus Schematic (LVS)

Exports the schematic netlist from Xschem, then runs LVS. Compares the GDS layout in `layout/` against the schematic netlist in `netlist/schematic/`. Reports are saved to `verification/lvs/`. The extracted layout netlist is moved to `netlist/layout/`.

**KLayout LVS** uses `run_lvs.py` from the IHP Open-PDK:

```sh
make klayout-lvs
make klayout-lvs CELL=sparx_powdet_sbd
```

**Magic + Netgen LVS** uses `sak-lvs.sh`:

```sh
make magic-lvs
make magic-lvs CELL=sparx_powdet_sbd
```

### Design Rule Check (DRC)

Runs DRC on the GDS layout in `layout/`. Reports are saved to `verification/drc/`.

**KLayout DRC** uses `run_drc.py` from the IHP Open-PDK with relaxed rules (FEOL, density checks, and extra rules disabled):

```sh
make klayout-drc
make klayout-drc CELL=sparx_powdet_sbd
```

**KLayout DRC (regular)** runs the full DRC rule set on the top-level cell:

```sh
make klayout-drc-regular
```

**Magic DRC** uses `sak-drc.sh`:

```sh
make magic-drc
make magic-drc CELL=sparx_powdet_sbd
```

### Parasitic Extraction (PEX)

Runs parasitic extraction on the GDS layout in `layout/`. The extracted SPICE netlist is written to `netlist/pex/`.

The `EXT_MODE` parameter selects the extraction mode:
- `1` = C-decoupled
- `2` = C-coupled
- `3` = full-RC (default)

> **Note:** For `klayout-pex`, `EXT_MODE=1` (C-decoupled) is not yet supported by kpex and automatically falls back to `EXT_MODE=2` (CC) with a warning.

The `.subckt` name in the extracted SPICE file is automatically renamed from `<CELL>_flat` (kpex) or `<CELL>` (Magic) to `<CELL>_pex`.

If a matching Xschem symbol (`schematic/<CELL>_pex.sym`) exists, the `.subckt` pin order in the extracted SPICE file is automatically reordered to match the symbol's pin positions. This ensures the PEX netlist can be used directly with the corresponding Xschem symbol for simulation.

**KLayout PEX** uses `kpex` with the Magic extraction engine currently (2.5D engine is work in progress):

```sh
make klayout-pex
make klayout-pex CELL=sparx_powdet_sbd
make klayout-pex CELL=sparx_powdet_sbd EXT_MODE=3
```

**Magic PEX** uses `sak-pex.sh`:

```sh
make magic-pex
make magic-pex CELL=sparx_powdet_sbd
make magic-pex CELL=sparx_powdet_sbd EXT_MODE=3
```

### Verify a Specific Cell

Runs LVS, DRC, and PEX for a specific cell:

```sh
make klayout-verify-cell CELL=sparx_powdet_sbd
make magic-verify-cell CELL=sparx_powdet_sbd
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
make verify-all CELL=sparx_powdet_sbd
```

### Render Layout of the Design

Renders the top-level GDS layout and saves it in the `img/` folder:

```sh
make render-image
```

### Build PDK

Clones and installs the IHP-Open-PDK repository with GDSFactory cells:

```sh
make build-pdk
```

### Build Layout

Generates the six-port layout GDS files (`layout/sparx_top.gds` and `layout/sparx_powdet_sbd.gds`):

```sh
make build-layout
make build-layout FREQ=77e9
```

The `FREQ` parameter sets the design frequency in Hz (default: 160 GHz = `160e9`).

### Build Top Cell

Builds the top-level cell by running `build-pdk`, `build-layout`, and `render-image`:

```sh
make build-top
make build-top FREQ=77e9
```

The `FREQ` parameter sets the design frequency in Hz (default: 160 GHz = `160e9`).

### Build All

Builds the complete design by first verifying all cells (`verify-all`), then building the top-level cell (`build-top`):

```sh
make all
make all FREQ=77e9
```

The `FREQ` parameter sets the design frequency in Hz (default: 160 GHz = `160e9`).

## Cite This Work

```
@software{2026_SPARX,
	author = {Kellerer-Pirklbauer, David and Dorrer, Simon and Pretl, Harald},
	month = April,
	title = {{GitHub Repository for SPARX: An Automated, Programmatically Generated Frequency-Scalable Six-Port Receiver in 130-nm CMOS}},
	url = {https://github.com/iic-jku/SG13G2_SPARX},
	doi = {ToDo},
	year = {2026}
}
```


## Acknowledgements

This project is funded by the JKU/SAL [IWS Lab](https://research.jku.at/de/projects/jku-lit-sal-intelligent-wireless-systems-lab-iws-lab/), a collaboration of [Johannes Kepler University](https://jku.at) and [Silicon Austria Labs](https://silicon-austria-labs.com).

<p align="center">
  <a href="https://silicon-austria-labs.com" target="_blank">
    <img src="https://github.com/iic-jku/klayout-pex-website/raw/main/figures/funding/silicon-austria-labs-logo.svg" alt="Silicon Austria Labs" width="300"/>
  </a>
</p>
