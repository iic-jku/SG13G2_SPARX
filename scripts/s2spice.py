#!/usr/bin/env python3
"""
s2spice.py — S-parameter to lumped-element SPICE model converter
=================================================================

Reads an S-parameter file (.s1p, .s2p, .s3p, …) via scikit-rf and writes an
ngspice-compatible SPICE subcircuit usable in Xschem.

Two extraction methods
----------------------
  pi   Single-frequency RLC π-model  (2-port only, fast, narrowband)
  vf   Vector Fitting rational model  (N-port, wideband) — DEFAULT

Pi-model topology (2-port):
    port1 ──[series R+L or R+C]── port2
      |                              |
  [shunt R|C|L]              [shunt R|C|L]
      |                              |
     GND                           GND

Vector Fitting uses scikit-rf's VectorFitting class to fit the S-parameters
with a rational function, then exports a SPICE subcircuit using controlled
sources (fully supported by ngspice ≥ 37).

Usage
-----
  python s2spice.py mynetwork.s2p                     # VF, default settings
  python s2spice.py mynetwork.s2p -m pi               # π-model at mid-band
  python s2spice.py mynetwork.s2p -m pi -f 2.4e9      # π-model at 2.4 GHz
  python s2spice.py mynetwork.s2p -m vf -p 20         # VF with 20 poles
  python s2spice.py mynetwork.s2p -m vf -o model.sp   # custom output name

Xschem / ngspice integration
-----------------------------
  In your Xschem testbench netlist, load the model with:
    .lib "path/to/model.sp"
  or:
    .include "path/to/model.sp"

  Instantiate the subcircuit as:
    X1 net_in net_out <subckt_name>        ; 2-port
    X1 net_in net_out net_port3 <name>     ; 3-port, etc.

Requirements
------------
  pip install scikit-rf numpy
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np

try:
    import skrf as rf
except ImportError:
    print("scikit-rf not found. Install it with:  pip install scikit-rf", file=sys.stderr)
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def spice_safe(s: str) -> str:
    """Return a SPICE-safe identifier (alphanumeric + underscore only)."""
    out = "".join(c if (c.isalnum() or c == "_") else "_" for c in s)
    # SPICE identifiers must not start with a digit
    if out and out[0].isdigit():
        out = "X" + out
    return out


def load_network(filepath: str) -> rf.Network:
    """
    Load an S-parameter file into a scikit-rf Network object.

    Accepts any Touchstone format scikit-rf supports (.s1p, .s2p, .s3p, …).
    Prints a short summary (port count, frequency range) to stdout and exits
    with a non-zero status if the file cannot be parsed.
    """
    try:
        nw = rf.Network(filepath)
    except Exception as exc:
        print(f"Error loading '{filepath}': {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded  : {filepath}")
    print(f"  Ports : {nw.nports}")
    print(f"  Freq  : {nw.f[0]/1e9:.4f} GHz — {nw.f[-1]/1e9:.4f} GHz  ({len(nw.f)} points)")
    return nw


def _fmt(v: float) -> str:
    """Format a SPICE element value with engineering notation."""
    return f"{v:.6e}"


# ─────────────────────────────────────────────────────────────────────────────
# π-model helpers
# ─────────────────────────────────────────────────────────────────────────────

def _admittance_to_rlc(Y: complex, omega: float) -> dict[str, float]:
    """
    Decompose a shunt admittance Y = G + jB into parallel R, C, or L.

      G = Re(Y) > 0  →  R = 1/G
      B = Im(Y) > 0  →  C = B/ω   (capacitive susceptance)
      B = Im(Y) < 0  →  L = −1/(B·ω) (inductive susceptance)
    """
    out: dict[str, float] = {}
    G, B = Y.real, Y.imag
    if abs(G) > 1e-30:
        out["R"] = 1.0 / G
    if B > 1e-30:
        out["C"] = B / omega
    elif B < -1e-30:
        out["L"] = -1.0 / (B * omega)
    return out


def _impedance_to_rlc(Z: complex, omega: float) -> dict[str, float]:
    """
    Decompose a series impedance Z = R + jX into series R, L, or C.

      R = Re(Z) > 0  →  resistor R
      X = Im(Z) > 0  →  L = X/ω
      X = Im(Z) < 0  →  C = −1/(X·ω)
    """
    out: dict[str, float] = {}
    R, X = Z.real, Z.imag
    if R > 1e-30:
        out["R"] = R
    if X > 1e-30:
        out["L"] = X / omega
    elif X < -1e-30:
        out["C"] = -1.0 / (X * omega)
    return out


def extract_pi_model(nw: rf.Network, freq_hz: float | None) -> dict:
    """
    Extract a π-model from a 2-port network at a single frequency.

    Returns a dict with keys 'freq', 'series', 'shunt1', 'shunt2',
    each RLC branch being a dict of {'R': val, 'L': val, 'C': val}
    (only the keys that are physically present are included).
    """
    if nw.nports != 2:
        raise ValueError(
            f"π-model extraction requires exactly 2 ports, got {nw.nports}."
        )

    freqs = nw.f
    if freq_hz is None:
        freq_hz = float(freqs[len(freqs) // 2])

    idx = int(np.argmin(np.abs(freqs - freq_hz)))
    freq = float(freqs[idx])
    omega = 2.0 * np.pi * freq

    y = nw.y[idx]                     # Y-parameter matrix at this frequency
    Y11, Y12 = y[0, 0], y[0, 1]
    Y21, Y22 = y[1, 0], y[1, 1]

    # Average Y12 and Y21 to handle slightly non-reciprocal networks gracefully
    Y_series = -0.5 * (Y12 + Y21)
    Y_shunt1 = Y11 + Y12              # port-1 shunt (left leg of π)
    Y_shunt2 = Y22 + Y21              # port-2 shunt (right leg of π)

    Z_series = 1.0 / Y_series if abs(Y_series) > 1e-30 else 0j

    return {
        "freq"  : freq,
        "series": _impedance_to_rlc(Z_series, omega),
        "shunt1": _admittance_to_rlc(Y_shunt1, omega),
        "shunt2": _admittance_to_rlc(Y_shunt2, omega),
    }


def _series_elements(lines: list[str], tag: str, n_from: str, n_to: str,
                     rlc: dict[str, float]) -> None:
    """
    Append SPICE element lines for a series R-L-C chain to `lines`.

    Elements are chained from `n_from` to `n_to` in the order R → L → C.
    Intermediate internal nodes are auto-named as N_<tag>_0, N_<tag>_1, …
    If `rlc` is empty (ideal short circuit), a 1 nΩ wire resistor is inserted
    to keep the netlist well-formed.
    """
    items = list(rlc.items())
    if not items:
        # No elements → near short-circuit wire
        lines.append(f"Rwire_{tag} {n_from} {n_to} 1e-9")
        return
    node = n_from
    for k, (elem, val) in enumerate(items):
        is_last = (k == len(items) - 1)
        n_next = n_to if is_last else f"N_{tag}_{k}"
        if elem == "R":
            lines.append(f"R_{tag} {node} {n_next} {_fmt(val)}")
        elif elem == "L":
            lines.append(f"L_{tag} {node} {n_next} {_fmt(val)}")
        elif elem == "C":
            lines.append(f"C_{tag} {node} {n_next} {_fmt(val)}")
        node = n_next


def _shunt_elements(lines: list[str], tag: str, node: str,
                    rlc: dict[str, float]) -> None:
    """
    Append SPICE element lines for parallel shunt R, L, C branches to `lines`.

    Each element in `rlc` is connected individually between `node` and GND (0),
    forming a parallel combination.  The first element uses `tag` as its name;
    subsequent ones get a numeric suffix (_0, _1, …) to avoid name collisions.
    If `rlc` is empty, nothing is emitted (the shunt branch is an open circuit).
    """
    for k, (elem, val) in enumerate(rlc.items()):
        sfx = "" if k == 0 else str(k)
        if elem == "R":
            lines.append(f"R_{tag}{sfx} {node} 0 {_fmt(val)}")
        elif elem == "L":
            lines.append(f"L_{tag}{sfx} {node} 0 {_fmt(val)}")
        elif elem == "C":
            lines.append(f"C_{tag}{sfx} {node} 0 {_fmt(val)}")


def write_pi_spice(model: dict, subckt: str, outpath: Path, nw: rf.Network) -> None:
    """
    Write the π-model as an ngspice-compatible SPICE subcircuit file.

    `model` must be the dict returned by `extract_pi_model`.  The subcircuit is
    written to `outpath` with UTF-8 encoding and a header comment block that
    records the source network name, extraction frequency, and tool version.
    After writing, an element summary (R/L/C values per branch) is printed to
    stdout for quick inspection.
    """
    freq_ghz = model["freq"] / 1e9

    lines = [
        f"* ── Pi-model SPICE subcircuit ────────────────────────────────────",
        f"* Source    : {nw.name}",
        f"* Method    : π-model (single-frequency Y-parameter extraction)",
        f"* Frequency : {freq_ghz:.6f} GHz",
        f"* Tool      : s2spice.py  (scikit-rf {rf.__version__})",
        f"* ──────────────────────────────────────────────────────────────────",
        f"",
        f".subckt {subckt} port1 port2",
        f"",
        f"* Series branch: port1 ──[R+L or R+C]── port2",
    ]
    _series_elements(lines, f"ser_{subckt}", "port1", "port2", model["series"])

    lines += ["", "* Shunt at port1  (parallel to GND)"]
    _shunt_elements(lines, f"sh1_{subckt}", "port1", model["shunt1"])

    lines += ["", "* Shunt at port2  (parallel to GND)"]
    _shunt_elements(lines, f"sh2_{subckt}", "port2", model["shunt2"])

    lines += ["", f".ends {subckt}", ""]
    outpath.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWritten : {outpath}")

    # Human-readable summary
    print(f"\nElement summary at {freq_ghz:.4f} GHz:")
    for branch, label in [
        ("series", "  Series  "),
        ("shunt1",  "  Shunt-1 "),
        ("shunt2",  "  Shunt-2 "),
    ]:
        rlc = model[branch]
        parts = []
        if "R" in rlc:
            parts.append(f"R = {rlc['R']:.4e} Ω")
        if "L" in rlc:
            parts.append(f"L = {rlc['L']:.4e} H")
        if "C" in rlc:
            parts.append(f"C = {rlc['C']:.4e} F")
        print(f"{label}: {', '.join(parts) if parts else '(short / open)'}")


# ─────────────────────────────────────────────────────────────────────────────
# Vector Fitting
# ─────────────────────────────────────────────────────────────────────────────

def write_vf_spice(nw: rf.Network, subckt: str, outpath: Path, n_poles: int) -> None:
    """
    Fit the network with Vector Fitting and write an ngspice-compatible
    SPICE subcircuit using scikit-rf's built-in SPICE exporter.

    The generated subcircuit implements the rational function approximation of
    the S-parameters using voltage sources, current sources, and RC sections —
    all standard SPICE2 / ngspice elements.
    """
    try:
        from skrf.vectorfitting import VectorFitting
    except ImportError:
        print(
            "scikit-rf VectorFitting not available (requires scikit-rf >= 0.20).\n"
            "Upgrade with:  pip install --upgrade scikit-rf",
            file=sys.stderr,
        )
        sys.exit(1)

    n_real  = max(1, n_poles // 2)
    n_cmplx = max(1, n_poles // 2)
    print(
        f"\nRunning Vector Fitting  "
        f"(real poles: {n_real},  complex pairs: {n_cmplx}) …"
    )

    # Give the network the desired subcircuit name so scikit-rf uses it
    nw_fit = nw.copy()
    nw_fit.name = subckt

    vf = VectorFitting(nw_fit)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        vf.vector_fit(n_poles_real=n_real, n_poles_cmplx=n_cmplx)

    # Report fit quality
    try:
        s_model = vf.get_model_response(freqs=nw.f)
        max_err = float(np.max(np.abs(s_model - nw.s)))
        print(f"  Max S-parameter fit error : {max_err:.4e}")
        if max_err > 0.05:
            print(
                "  WARNING: fit error is large — consider increasing --poles (-p)."
            )
    except Exception:
        pass  # non-fatal; fit quality logging is best-effort

    vf.write_spice_subcircuit_s(str(outpath))
    print(f"\nWritten : {outpath}")
    print(
        "\nNote: The VF subcircuit uses the S-parameter port convention.\n"
        "Each port pair (signal + reference) appears in the .subckt port list.\n"
        "Connect the reference ports to your circuit ground (0)."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Verification helper  (optional, requires matplotlib)
# ─────────────────────────────────────────────────────────────────────────────

def plot_comparison(nw_orig: rf.Network, sp_file: Path, method: str) -> None:
    """
    Display a grid of |Sij| (dB) plots comparing measured data to the VF model.

    Opens an NxN subplot grid (one panel per S-parameter) with the original
    Touchstone data overlaid against the Vector Fitting reconstruction.  Only
    the 'vf' method is supported; calling with 'pi' returns silently.
    Requires matplotlib; returns silently if it is not installed.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    if method == "vf":
        try:
            from skrf.vectorfitting import VectorFitting
            vf = VectorFitting(nw_orig)
            vf.vector_fit()
            freqs = nw_orig.f
            s_model = vf.get_model_response(freqs=freqs)
        except Exception:
            return
    else:
        return  # π-model plotting not implemented here

    fig, axes = plt.subplots(nw_orig.nports, nw_orig.nports,
                             figsize=(5 * nw_orig.nports, 4 * nw_orig.nports),
                             squeeze=False)
    freqs_ghz = nw_orig.f / 1e9
    for i in range(nw_orig.nports):
        for j in range(nw_orig.nports):
            ax = axes[i][j]
            ax.plot(freqs_ghz, 20 * np.log10(np.abs(nw_orig.s[:, i, j])),
                    label="Measured", lw=2)
            ax.plot(freqs_ghz, 20 * np.log10(np.abs(s_model[:, i, j])),
                    "--", label="VF model", lw=1.5)
            ax.set_xlabel("Frequency (GHz)")
            ax.set_ylabel(f"|S{i+1}{j+1}| (dB)")
            ax.legend()
            ax.grid(True)
    fig.suptitle(f"Vector Fitting quality check — {nw_orig.name}")
    plt.tight_layout()
    plt.show()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """
    Parse and return command-line arguments.

    Defines the full CLI interface: input file, extraction method, frequency,
    pole count, subcircuit name, output path, and the optional --plot flag.
    The module docstring is used as the argparse description so that
    `--help` shows the full usage guide.
    """
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "input",
        help="Input S-parameter file (.s1p, .s2p, .s3p, …)",
    )
    p.add_argument(
        "-m", "--method", choices=["pi", "vf"], default="vf",
        help="Extraction method: 'pi' (π-model) or 'vf' (Vector Fit)  [default: vf]",
    )
    p.add_argument(
        "-f", "--freq", type=float, default=None, metavar="HZ",
        help=(
            "Extraction frequency in Hz for π-model.  "
            "[default: mid-band frequency]"
        ),
    )
    p.add_argument(
        "-p", "--poles", type=int, default=16, metavar="N",
        help=(
            "Total number of poles for Vector Fitting  "
            "(split evenly between real and complex pairs).  [default: 16]"
        ),
    )
    p.add_argument(
        "-n", "--name", type=str, default=None, metavar="NAME",
        help="SPICE subcircuit name  [default: derived from input filename]",
    )
    p.add_argument(
        "-o", "--output", type=str, default=None, metavar="FILE",
        help=(
            "Output SPICE file  "
            "[default: <input_stem>_pi.sp or <input_stem>_vf.sp]"
        ),
    )
    p.add_argument(
        "--plot", action="store_true",
        help="Show S-parameter comparison plot after VF (requires matplotlib)",
    )
    return p.parse_args()


def main() -> None:
    """
    Entry point: orchestrate argument parsing, network loading, and SPICE export.

    Resolves the output path, delegates to either `write_pi_spice` (π-model) or
    `write_vf_spice` (Vector Fitting) depending on --method, and optionally
    calls `plot_comparison` when --plot is set.  Prints Xschem instantiation
    hints on success.  Exits with status 1 on any unrecoverable error.
    """
    args = parse_args()

    inpath = Path(args.input)
    if not inpath.exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    subckt  = spice_safe(args.name or inpath.stem)
    outpath = (
        Path(args.output)
        if args.output
        else inpath.with_name(f"{inpath.stem}_{args.method}.sp")
    )

    nw = load_network(str(inpath))

    if args.method == "pi":
        if nw.nports != 2:
            print(
                f"Error: π-model extraction requires a 2-port network, "
                f"but '{inpath.name}' has {nw.nports} ports.\n"
                f"Use --method vf for N-port networks.",
                file=sys.stderr,
            )
            sys.exit(1)
        model = extract_pi_model(nw, args.freq)
        write_pi_spice(model, subckt, outpath, nw)

    else:  # vf
        write_vf_spice(nw, subckt, outpath, args.poles)
        if args.plot:
            plot_comparison(nw, outpath, "vf")

    print(f"\nDone.  Subcircuit name: {subckt}")
    print(
        f"\nXschem usage:\n"
        f"  .lib \"{outpath.name}\"   (or .include)\n"
        f"  X1 <net1> ... <netN> {subckt}"
    )


if __name__ == "__main__":
    main()
