import argparse
import gdsfactory as gf
import ihp
from pathlib import Path
import gds2palace



ihp.PDK.activate()


DEFAULT_FREQUENCY = 160e9
DEFAULT_BANDWIDTH = 20e9
DEFAULT_SIGNAL_CROSS_SECTION = "TM2"
DEFAULT_GROUND_CROSS_SECTION = "M5"
DEFAULT_Z0 = 50
DEFAULT_E_R = 4.1
DEFAULT_FILTER_TYPE = "butter"
DEFAULT_FILTER_ORDER = 3
DEFAULT_RIPPLE_DB = 3


GDS_DIR = Path(__file__).resolve().parent.parent / "layout"
# argparse
parser = argparse.ArgumentParser(description="EM simulation of BLC")
parser.add_argument("--frequency", type=float, default=DEFAULT_FREQUENCY, help="Frequency in Hz")
parser.add_argument("--bandwidth", type=float, default=DEFAULT_BANDWIDTH, help="Bandwidth in Hz")
parser.add_argument("--signal_cross_section", type=str, default=DEFAULT_SIGNAL_CROSS_SECTION, help="Cross section for signal line")
parser.add_argument("--ground_cross_section", type=str, default=DEFAULT_GROUND_CROSS_SECTION, help="Cross section for ground line")
parser.add_argument("--Z0", type=float, default=DEFAULT_Z0, help="Characteristic impedance in Ohms")
parser.add_argument("--e_r", type=float, default=DEFAULT_E_R, help="Relative permittivity of the substrate")
parser.add_argument("--filter_type", type=str, default=DEFAULT_FILTER_TYPE, help="Type of the filter (butter, cheby)")
parser.add_argument("--filter_order", type=int, default=DEFAULT_FILTER_ORDER, help="Order of the filter")
parser.add_argument("--ripple_dB", type=float, default=DEFAULT_RIPPLE_DB, help="Ripple in dB for Chebyshev and Elliptic filters")


args = parser.parse_args()
filter_type = args.filter_type.lower()

# format filter ripple
def format_ripple(value):
    text = str(value)
    if text.endswith(".0"):
        text = text[:-2]
    return text.replace(".", "_")


ripple_tag = f"_rip_{format_ripple(args.ripple_dB)}dB" if filter_type != "butter" else ""

layer_dict = {
    "TM2": "topmetal2_routing",
    "TM1": "topmetal1_routing",
    "M5": "metal5_routing",
    "M4": "metal4_routing",
    "M3": "metal3_routing",
    "M2": "metal2_routing",
    "M1": "metal1_routing",
}

signal_cross_section = layer_dict[args.signal_cross_section]
ground_cross_section = layer_dict[args.ground_cross_section]


c = gf.Component("bpf_em_sim")
hbpf_ref = c.add_ref(ihp.cells.hairpin_coupled_line_bandpass_filter(
    connection_length=0,
    frequency= args.frequency,
    bandwidth=args.bandwidth,
    signal_cross_section=signal_cross_section,
    ground_cross_section=ground_cross_section,
    Z0=args.Z0,
    e_r=args.e_r,
    filter_type=filter_type,
    order=args.filter_order,
    ripple_dB=args.ripple_dB,
))

port1 = c.add_ref(gf.components.rectangle(size=(0.1, hbpf_ref.ports["e1"].width), layer=(201,0)))
port1.center = (hbpf_ref.ports["e1"].center)
port1.move((0.05,0))

port2 = c.add_ref(gf.components.rectangle(size=(0.1, hbpf_ref.ports["e2"].width), layer=(202,0)))
port2.center = (hbpf_ref.ports["e2"].center)
port2.move((-0.05,0))



filename = (
    f"bpf_"
    f"f_{args.frequency/1e9:.0f}GHz_"
    f"bw_{args.bandwidth/1e9:.0f}GHz_"
    f"sig_{args.signal_cross_section}_"
    f"gnd_{args.ground_cross_section}_"
    f"z0_{args.Z0:.0f}Ohm_"
    f"er_{str(args.e_r).replace('.', '_')}_"
    f"{filter_type}_"
    f"ord_{args.filter_order}"
    f"{ripple_tag}.gds"
)
gds_path = GDS_DIR / filename
# c.show()
c.write_gds(str(gds_path), with_metadata=False)
