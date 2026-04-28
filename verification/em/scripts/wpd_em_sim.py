import argparse
import gdsfactory as gf
import ihp
from pathlib import Path
import gds2palace



ihp.PDK.activate()


DEFAULT_FREQUENCY = 160e9
DEFAULT_SIGNAL_CROSS_SECTION = "TM2"
DEFAULT_GROUND_CROSS_SECTION = "M5"
DEFAULT_Z0 = 50
DEFAULT_E_R = 4.1
DEFAULT_CONFIG = "C"

GDS_DIR = Path(__file__).resolve().parent.parent / "layout"
# argparse
parser = argparse.ArgumentParser(description="EM simulation of BLC")
parser.add_argument("--frequency", type=float, default=DEFAULT_FREQUENCY, help="Frequency in Hz")
parser.add_argument("--signal_cross_section", type=str, default=DEFAULT_SIGNAL_CROSS_SECTION, help="Cross section for signal line")
parser.add_argument("--ground_cross_section", type=str, default=DEFAULT_GROUND_CROSS_SECTION, help="Cross section for ground line")
parser.add_argument("--Z0", type=float, default=DEFAULT_Z0, help="Characteristic impedance in Ohms")
parser.add_argument("--e_r", type=float, default=DEFAULT_E_R, help="Relative permittivity of the substrate")
parser.add_argument("--config", type=str, default=DEFAULT_CONFIG, help="Configuration of the BLC (C, U)")
args = parser.parse_args()

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


c = gf.Component("wpd_em_sim")
wpd_ref = c.add_ref(ihp.cells.wilkinson_power_divider(
    connection_length=0,
    frequency= args.frequency,
    signal_cross_section=signal_cross_section,
    ground_cross_section=ground_cross_section,
    Z0=args.Z0,
    e_r=args.e_r,
    shape=args.config,
))

port1 = c.add_ref(gf.components.rectangle(size=(0.1, wpd_ref.ports["e1"].width), layer=(201,0)))
port1.center = (wpd_ref.ports["e1"].center)
port1.move((0.05,0))

port2 = c.add_ref(gf.components.rectangle(size=(0.1, wpd_ref.ports["e2"].width), layer=(202,0)))
port2.center = (wpd_ref.ports["e2"].center)
port2.move((-0.05,0))

port3 = c.add_ref(gf.components.rectangle(size=(0.1, wpd_ref.ports["e3"].width), layer=(203,0)))
port3.center = (wpd_ref.ports["e3"].center)
port3.move((-0.05,0))



filename = f"wpd_{args.frequency/1e9:.0f}GHz_{args.Z0:.0f}Ohm_{args.signal_cross_section}_{args.ground_cross_section}_e_r_{str(args.e_r).replace('.', '_')}_config_{args.config}.gds"
gds_path = GDS_DIR / filename
# c.show()
c.write_gds(str(gds_path), with_metadata=False)
