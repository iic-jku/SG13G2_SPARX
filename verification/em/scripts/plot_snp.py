#!/usr/bin/env python3

"""Plot the first-column S-parameters from a Touchstone file.

For an input like ``network.s4p``, this plots:
  - top row: magnitude of S11, S21, S31, S41
  - bottom row: phase of S11, S21, S31, S41

Each S-parameter gets its own column so the magnitude and phase are stacked
vertically while the different responses are shown next to each other.
"""

import argparse
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import skrf as rf



def _ports_from_extension(path: Path) -> int | None:
	match = re.search(r"\.s(\d+)p$", path.name, re.IGNORECASE)
	if match:
		return int(match.group(1))
	return None


def _center_frequency_from_filename(path: Path) -> float | None:
	match = re.search(r"(\d+(?:\.\d+)?)\s*GHz", path.name, re.IGNORECASE)
	if match:
		return float(match.group(1)) * 1e9
	return None


def _format_phase(values: np.ndarray) -> np.ndarray:
	return np.degrees(np.unwrap(np.angle(values)))


def plot_touchstone(filepath: Path, output: Path | None = None) -> None:
	network = rf.Network(str(filepath))
	ports_from_name = _ports_from_extension(filepath)
	port_count = ports_from_name or network.nports
	fcenter_hz = _center_frequency_from_filename(filepath)

	if network.nports != port_count:
		raise ValueError(
			f"Port count mismatch: filename suggests {port_count} ports, but the file contains {network.nports} ports"
		)

	if port_count < 1:
		raise ValueError("Touchstone file must contain at least one port")

	frequencies_ghz = network.f / 1e9
	if fcenter_hz:
		x_values = network.f / fcenter_hz
		x_label = "Frequency / fcenter"
	else:
		x_values = frequencies_ghz
		x_label = "Frequency (GHz)"
	s = network.s

	fig, axes = plt.subplots(2, port_count, figsize=(4.0 * port_count, 6.5), sharex="col", squeeze=False)
	fig.suptitle(filepath.name, fontsize=14)

	for column in range(port_count):
		response = s[:, column, 0]
		magnitude_db = 20.0 * np.log10(np.maximum(np.abs(response), 1e-30))
		phase_deg = _format_phase(response)
		label = f"S{column + 1}1"

		magnitude_axis = axes[0, column]
		phase_axis = axes[1, column]

		magnitude_axis.plot(x_values, magnitude_db, color="tab:blue", linewidth=1.5)
		phase_axis.plot(x_values, phase_deg, color="tab:orange", linewidth=1.5)

		magnitude_axis.set_title(label)
		magnitude_axis.grid(True, alpha=0.3)
		phase_axis.grid(True, alpha=0.3)

		if column == 0:
			magnitude_axis.set_ylabel("Magnitude (dB)")
			phase_axis.set_ylabel("Phase (deg)")

		phase_axis.set_xlabel(x_label)

	fig.tight_layout(rect=(0, 0, 1, 0.96))

	if output is not None:
		output.parent.mkdir(parents=True, exist_ok=True)
		fig.savefig(output, dpi=200, bbox_inches="tight")
		print(f"Saved plot to {output}")

	plt.show()


def main() -> None:
	parser = argparse.ArgumentParser(description="Plot S11 ... SN1 from a Touchstone file")
	parser.add_argument("input", type=Path, help="Input Touchstone file, for example network.s4p")
	parser.add_argument(
		"-o",
		"--output",
		type=Path,
		help="Optional image file to save, for example plot.png",
	)

	args = parser.parse_args()

	try:
		plot_touchstone(args.input, args.output)
	except Exception as exc:
		print(f"Error: {exc}", file=sys.stderr)
		raise SystemExit(1)


if __name__ == "__main__":
	main()
