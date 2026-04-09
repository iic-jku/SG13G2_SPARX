"""Six-port receiver GDS layout generator using IHP SG13G2 PDK.

Builds a complete six-port network comprising branch-line couplers,
a Wilkinson power divider, a hairpin bandpass filter, four Schottky-diode
power detectors with transimpedance amplifiers, probe pads, sealring,
and metal fill.
"""

import argparse
from math import sqrt
from pathlib import Path

import gdsfactory as gf
import ihp
import scipy

ihp.PDK.activate()

# ============================================================
# CLI parameters
# ============================================================
parser = argparse.ArgumentParser(description="Six-port receiver GDS generator")
parser.add_argument("--frequency", type=float, default=160e9, help="Design frequency in Hz (default: 160e9)")
parser.add_argument("--no-fill", action="store_true", help="Disable metal fill (faster for layout preview)")
parser.add_argument("--no-fill-m5", action="store_true", help="Disable Metal5 ground fill")
args = parser.parse_args()

FREQUENCY = args.frequency
do_fill = not args.no_fill
do_fill_m5 = not args.no_fill_m5

# ============================================================
# Design constants
# ============================================================

# CMIM capacitor dimensions (um)
CMIM_SIZE = 10  # width and length of standard CMIM cap
CMIM_PITCH = 11.2  # center-to-center pitch in cap arrays
CMIM_SPACING_TM1 = 0.52  # min TM1 spacing between caps (design rule 5.17)
CMIM_FILL_WIDTH = 6.8  # fill capacitor width
CMIM_FILL_LENGTH = 9  # fill capacitor length
CAP_BUS_WIDTH = 4  # metal bus width connecting cap plates

# MOSFET output stage parameters
NUM_GATES = 24  # total gate fingers per transistor (incl. dummies)
NMOS_WIDTH = 60  # nmos finger width (um)
PMOS_WIDTH = 120  # pmos finger width (um)
GATE_LENGTH = 0.13  # drawn gate length (um)
GUARD_RING_DISTANCE = 2  # guard ring distance (um)
GATE_EXTENSION_NMOS = 2.15  # gate poly extension for nmos via connection
GATE_EXTENSION_PMOS = 3.55  # gate poly extension for pmos via connection
NMOS_PMOS_SPACING = 15  # vertical gap between nmos and pmos drain vias

# Resistor dimensions (um)
RSIL_WIDTH = 0.5  # rsil resistor width (XR1, XR5, termination)
RSIL_LENGTH = 2.5  # rsil resistor length
RPPD_WIDTH = 0.5  # rppd resistor width (XR2, XR4)
RPPD_LENGTH = 1.5  # rppd resistor length
RHIGH_WIDTH = 0.5  # rhigh resistor width (XR3)
RHIGH_LENGTH = 2  # rhigh resistor length

# Routing widths (um)
ROUTE_WIDTH_VDD = 8  # VDD power bus (TM1)
ROUTE_WIDTH_VSS = 2  # VSS ground bus (M5)
ROUTE_WIDTH_SIGNAL = 4  # signal lines to probe pads (M3/M4)
ROUTE_WIDTH_MIN_M1 = 0.26  # minimum Metal1 route width
ROUTE_WIDTH_BIAS = 0.5  # bias network routing
ROUTE_WIDTH_BIAS_M1 = 0.46  # bias Metal1 routing
ROUTE_WIDTH_GATE = 0.6  # gate connection routing (M2/M3)
ROUTE_WIDTH_REPLICA = 0.61  # replica circuit drain routing
ROUTE_WIDTH_SBD_SUB = 5.7  # Schottky diode substrate connection
ROUTE_WIDTH_SBD_GUARD = 0.3  # SBD D1-D2 guard ring connection
ROUTE_MIN_STRAIGHT = 10  # minimum straight length to avoid self-routing

# Probe pad parameters (um)
PROBE_PITCH = 125  # probe pad pitch
PROBE_GROUND_WIDTH = 120  # ground pad width (left probe)
PROBE_GROUND_WIDTH_RIGHT = 125  # ground pad width (right probe)
PROBE_SIGNAL_SIZE = 65  # signal pad width and length

# Nofill exclusion zones (um)
NOFILL_GSG_SIZE = 105  # nofill square around GSG probes
NOFILL_VDD_SIZE = 110  # nofill square around VDD pads
NOFILL_SIDE_WIDTH = 235  # side nofill width (85 + pitch + 25)
NOFILL_SIDE_OFFSET = 12.5  # side nofill centering offset ((110 - 85) / 2)

# Layout spacing (um)
RFIN_GAP = 20  # gap between BLC port and PD rfin
PD_HALF_HEIGHT = 105  # approximate half-height of power detector cell
PROBE_PD_GAP = 50  # gap between PD edge and probe edge
SEALRING_MARGIN = 50  # margin around circuit for sealring

# Six-port network geometry
CORNER_Z_FACTOR = 1.314  # impedance scaling for tline corners
CONNECTION_LEN_TERM = 30  # termination connection (before freq_scale, um)
CONNECTION_LEN_BPF_PAD = 30  # BPF-to-pad connection (before freq_scale, um)
CONNECTION_LEN_BLC_PAD = 40  # BLC-to-pad connection (before freq_scale, um)
CONNECTION_LEN_BLC_EXTRA = 25  # extra pad clearance added to BLC-to-pad (um)

# ============================================================
# Helper cells for metal fill
# ============================================================

# Common keyword arguments shared by almost every routing call
ROUTING_DEFAULTS = dict(
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

c = gf.Component("six_port_flex")


@gf.cell
def fill_cell(layer=ihp.tech.LAYER.Metal5slit, size=(3, 3)) -> gf.Component:
    """Simple rectangular fill cell for a given layer and size."""
    c = gf.Component()
    c << gf.c.rectangle(layer=layer, size=size)
    return c


@gf.cell
def fill_gat_active(size=(3, 3), active_extension=(0.18, 0.18)) -> gf.Component:
    """Gate-poly + active filler cell with centred Activ region."""
    c = gf.Component()
    gat_ref = c.add_ref(gf.c.rectangle(layer=ihp.tech.LAYER.GatPolyfiller, size=size))
    activ_ref = c.add_ref(
        gf.c.rectangle(
            layer=ihp.tech.LAYER.Activfiller,
            size=(size[0] + 2 * active_extension[0], size[1] + 2 * active_extension[1]),
        )
    )
    activ_ref.center = gat_ref.center
    return c


@gf.cell
def fill_ground() -> gf.Component:
    """1 x 1 um Metal5 ground fill tile."""
    c = gf.Component()
    c.add_polygon(
        layer=ihp.tech.LAYER.Metal5drawing,
        points=[
            (0, 0),
            (1, 0),
            (1, 1),
            (0, 1),
        ],
    )
    return c


@gf.cell
def slit_ground() -> gf.Component:
    """Metal5 slit opening for ground fill."""
    c = gf.Component()
    c.add_polygon(
        layer=ihp.tech.LAYER.Metal5slit,
        points=[
            (1.1, 1.1),
            (4, 1.1),
            (4, 4.1),
            (1.1, 4.1),
        ],
    )
    return c


# ============================================================
# Power detector cell (HBT-based — kept for reference)
# ============================================================


@gf.cell
def power_detector_hbt() -> gf.Component:
    """HBT-based power detector (unused, kept for reference)."""
    c = gf.Component("power_detector_hbt")
    via_tm1_tm2 = c.add_ref(
        ihp.cells.via_stack(
            top_layer="TopMetal2",
            bottom_layer="TopMetal1",
            vt2_columns=2,
            vt2_rows=2,
        )
    )
    cmim = ihp.cells.cmim(width=CMIM_SIZE, length=CMIM_SIZE)
    c1_ref = c.add_ref(cmim)
    c1_ref.connect("T", via_tm1_tm2.ports["bottom"], allow_width_mismatch=True)

    # via cell from Metal1 to Metal5
    via_m1_m5 = ihp.cells.via_stack(
        top_layer="Metal5",
        bottom_layer="Metal1",
        vn_columns=6,
        vn_rows=1,
    )

    # via from CMIM C1 to XQ1
    via_m1_m5.ports["top"].orientation += 90
    via_m1_m5.ports["bottom"].orientation += 90
    via_m1_m5_ref = c.add_ref(via_m1_m5)
    via_m1_m5_ref.connect("top", c1_ref.ports["B"], allow_width_mismatch=True)

    # npn13G2 cell, to be used for references when this transistor is needed
    xqx = ihp.cells.npn13G2()

    xqx.ports["C"].orientation = 270
    xq1_ref = c.add_ref(xqx)
    xq1_ref.connect("B", via_m1_m5.ports["bottom"], allow_width_mismatch=True, allow_layer_mismatch=True)

    via_m1_m2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=6,
        vn_rows=1,
    )

    via_m1_m2.ports["top"].orientation = 180
    via_m1_m2_ref = c.add_ref(via_m1_m2)
    via_m1_m2_ref.connect("bottom", xq1_ref.ports["C"], allow_width_mismatch=True, allow_layer_mismatch=True)

    xqx.ports["E"].orientation = 180
    xqx.ports["C"].orientation = 0
    xq2_ref = c.add_ref(xqx)
    xq2_ref.center = xq1_ref.center
    xq2_ref.xmin = xq1_ref.xmax + 0.31  # min spacing for pSD 5.10

    # distance between port centers of the two devices
    distance_x = abs(via_m1_m2_ref.ports["top"].center[0] - xq2_ref.ports["E"].center[0])

    route1 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_m1_m2_ref.ports["top"]],
        ports2=[xq2_ref.ports["E"]],
        route_width=0.2,  # min width for metal2
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        auto_taper=False,
        separation=0,
        start_straight_length=distance_x / 2 - 0.1,  # half the distance minus half the width
    )

    cmim.ports["T"].orientation = 0
    c2_ref = c.add_ref(cmim)
    c2_ref.center = c1_ref.center
    c2_ref.xmin = c1_ref.xmax + 0.24  # min spacing according to design rules 5.17

    connection = c.add_ref(ihp.cells.straight(length=7, cross_section="topmetal1_routing", width=1.64))  # min width TM1
    connection.connect("e1", c2_ref.ports["T"], allow_width_mismatch=True, allow_layer_mismatch=True)

    via_m2_tm1 = ihp.cells.via_stack(
        top_layer="TopMetal1", bottom_layer="Metal2", vn_columns=2, vn_rows=4, vt1_columns=1, vt1_rows=2
    )

    via_m2_tm1.ports["top"].orientation = 90
    via_m2_tm1.ports["bottom"].orientation = 90
    via_m2_tm1_ref = c.add_ref(via_m2_tm1)
    via_m2_tm1_ref.connect("top", connection.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    route2 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_m2_tm1_ref.ports["bottom"]],
        ports2=[xq2_ref.ports["E"]],
        layer=ihp.tech.LAYER.Metal2drawing,
        route_width=0.2,  # min width for metal2
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    xr1 = ihp.cells.rppd(width=0.5, length=1)
    xr1.ports["e2"].orientation = 180
    xr1_ref = c.add_ref(xr1)
    xr1_ref.xmin = xq2_ref.xmax + 0.31  # min spacing according to design rules 5.10
    xr1_ref.movey((xq2_ref.ports["C"].center[1] - xr1_ref.ports["e2"].center[1]))

    route4 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[xq2_ref.ports["C"]],
        ports2=[xr1_ref.ports["e2"]],
        route_width=0.2,  # min width for metal1
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    c3_ref = c.add_ref(cmim)
    c3_ref.center = c1_ref.center
    c3_ref.ymin = c1_ref.ymax + 0.24  # min spacing according to design rules 5.17

    cmim.ports["T"].orientation = 0
    cmim.ports["B"].orientation = 180  # change port direction
    c4_ref = c.add_ref(cmim)
    c4_ref.center = c2_ref.center
    c4_ref.ymin = c2_ref.ymax + 0.24  # min spacing according to design rules 5.17

    xqx.ports["C"].orientation = 270
    xq3_ref = c.add_ref(xqx)
    xq3_ref.center = xq1_ref.center
    xq3_ref.ymin = xq1_ref.ymax + 0.31  # min spacing according to design rules 5.10

    xqx.ports["C"].orientation = 0
    xq4_ref = c.add_ref(xqx)
    xq4_ref.center = xq2_ref.center
    xq4_ref.ymin = xq2_ref.ymax + 0.31  # min spacing according to design rules 5.10

    route3 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[xq1_ref.ports["B"]],
        ports2=[xq3_ref.ports["B"]],
        route_width=0.2,  # min width for metal1
        layer=ihp.tech.LAYER.Metal1drawing,
        start_straight_length=3,
        allow_layer_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # via for XQ3 to get to M2
    via_m1_m2.ports["bottom"].orientation = 0
    via_m1_m2_ref = c.add_ref(via_m1_m2)
    via_m1_m2_ref.connect("bottom", xq3_ref.ports["C"], allow_width_mismatch=True, allow_layer_mismatch=True)

    # distance between port centers of the two devices
    distance_x = abs(via_m1_m2_ref.ports["top"].center[0] - xq2_ref.ports["E"].center[0])

    route5 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_m1_m2_ref.ports["top"]],
        ports2=[xq4_ref.ports["E"]],
        route_width=0.2,  # min width for metal2
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        auto_taper=False,
        separation=0,
        start_straight_length=distance_x / 2 - 0.1,  # half the distance minus half the width
    )

    route6 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[xq2_ref.ports["B"]],
        ports2=[xq4_ref.ports["B"]],
        route_width=0.2,  # min width for metal1
        layer=ihp.tech.LAYER.Metal1drawing,
        start_straight_length=3,
        allow_layer_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    connection = c.add_ref(ihp.cells.straight(length=7, cross_section="topmetal1_routing", width=1.64))  # min width TM1
    connection.connect("e1", c4_ref.ports["T"], allow_width_mismatch=True, allow_layer_mismatch=True)

    via_m2_tm1.ports["top"].orientation = 270
    via_m2_tm1.ports["bottom"].orientation = 270
    via_m2_tm1_ref = c.add_ref(via_m2_tm1)
    via_m2_tm1_ref.connect("top", connection.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    route7 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_m2_tm1_ref.ports["bottom"]],
        ports2=[xq4_ref.ports["E"]],
        layer=ihp.tech.LAYER.Metal2drawing,
        route_width=0.2,  # min width for metal2
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    xr3 = ihp.cells.rppd(width=0.5, length=1)
    xr3.ports["e1"].orientation = 180
    xr3_ref = c.add_ref(xr1)
    xr3_ref.xmin = xq4_ref.xmax + 0.31  # min spacing according to design rules 5.10
    xr3_ref.movey((xq4_ref.ports["C"].center[1] - xr3_ref.ports["e1"].center[1]))

    route8 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[xq4_ref.ports["C"]],
        ports2=[xr3_ref.ports["e1"]],
        route_width=0.2,  # min width for metal1
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    via_m1_m5_ref = c.add_ref(via_m1_m5)
    via_m1_m5_ref.connect("bottom", xq3_ref.ports["B"], allow_width_mismatch=True, allow_layer_mismatch=True)

    # create capacitor array for caps 5 and 6
    c5_6 = gf.Component("C5_6")
    bottom_row = c5_6.add_ref(gf.components.array(component=cmim, columns=6, rows=1, column_pitch=0.24 + 11.2))
    top_row = c5_6.add_ref(gf.components.array(component=cmim, columns=4, rows=1, column_pitch=0.24 + 11.2))
    top_row.ymin = bottom_row.ymax + 0.24  # min spacing according to design rules 5.17
    c5_6.add_ports(bottom_row.ports, prefix="BR_")
    c5_6.add_ports(top_row.ports, prefix="TR_")

    # Orient outermost ports inward for horizontal cap connections
    for name in ["BR_T_1_1", "TR_T_1_1", "BR_B_1_1", "TR_B_1_1"]:
        c5_6.ports[name].orientation = 0
    for name in ["BR_T_1_6", "TR_T_1_4", "BR_B_1_6", "TR_B_1_4"]:
        c5_6.ports[name].orientation = 180

    c5_6_connection_t = gf.routing.route_bundle_electrical(
        component=c5_6,
        ports1=[c5_6.ports["BR_T_1_6"], c5_6.ports["TR_T_1_4"]],
        ports2=[c5_6.ports["BR_T_1_1"], c5_6.ports["TR_T_1_1"]],
        route_width=2,  # min width for metal1
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    c5_6_connection_b = gf.routing.route_bundle_electrical(
        component=c5_6,
        ports1=[c5_6.ports["BR_B_1_6"], c5_6.ports["TR_B_1_4"]],
        ports2=[c5_6.ports["BR_B_1_1"], c5_6.ports["TR_B_1_1"]],
        route_width=2,  # min width for metal1
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # orient top row ports to face downwards to connect to bottom row ports
    ihp.cells.utils.change_port_orientation(c5_6, ["TR_T_1_1", "TR_T_1_2", "TR_T_1_3", "TR_T_1_4"], 270)
    ihp.cells.utils.change_port_orientation(c5_6, ["TR_B_1_1", "TR_B_1_2", "TR_B_1_3", "TR_B_1_4"], 270)

    # orient bottom row ports to face upwards to connect to top row ports
    ihp.cells.utils.change_port_orientation(c5_6, ["BR_T_1_1", "BR_T_1_2", "BR_T_1_3", "BR_T_1_4"], 90)
    ihp.cells.utils.change_port_orientation(c5_6, ["BR_B_1_1", "BR_B_1_2", "BR_B_1_3", "BR_B_1_4"], 90)

    c5_6_connection_top = gf.routing.route_bundle_electrical(
        component=c5_6,
        ports1=[c5_6.ports["BR_T_1_1"], c5_6.ports["BR_T_1_2"], c5_6.ports["BR_T_1_3"], c5_6.ports["BR_T_1_4"]],
        ports2=[c5_6.ports["TR_T_1_1"], c5_6.ports["TR_T_1_2"], c5_6.ports["TR_T_1_3"], c5_6.ports["TR_T_1_4"]],
        route_width=2,  # adjust for thicker connections
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    c5_6_connection_bottom = gf.routing.route_bundle_electrical(
        component=c5_6,
        ports1=[c5_6.ports["BR_B_1_1"], c5_6.ports["BR_B_1_2"], c5_6.ports["BR_B_1_3"], c5_6.ports["BR_B_1_4"]],
        ports2=[c5_6.ports["TR_B_1_1"], c5_6.ports["TR_B_1_2"], c5_6.ports["TR_B_1_3"], c5_6.ports["TR_B_1_4"]],
        route_width=2,  # adjust for thicker connections
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # orient top row ports to face upwards to connect the ground plates to the other caps
    ihp.cells.utils.change_port_orientation(c5_6, ["TR_B_1_1", "TR_B_1_2", "TR_B_1_3", "TR_B_1_4", "BR_B_1_6"], 90)

    # reference the array as C5
    c5_ref = c.add_ref(c5_6)
    c5_ref.xmax = c2_ref.xmax
    c5_ref.ymax = c2_ref.ymax

    # reference the array as C6
    c6_ref = c.add_ref(c5_6)
    c6_ref.mirror_y()
    c6_ref.xmax = c4_ref.xmax
    c6_ref.ymin = c4_ref.ymin

    c5_6_connection_ground = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[
            c5_ref.ports["TR_B_1_1"],
            c5_ref.ports["TR_B_1_2"],
            c5_ref.ports["TR_B_1_3"],
            c5_ref.ports["TR_B_1_4"],
            c5_ref.ports["BR_B_1_6"],
        ],
        ports2=[
            c6_ref.ports["TR_B_1_1"],
            c6_ref.ports["TR_B_1_2"],
            c6_ref.ports["TR_B_1_3"],
            c6_ref.ports["TR_B_1_4"],
            c6_ref.ports["BR_B_1_6"],
        ],
        route_width=2,  # adjust for thicker connections
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    c4_6_connection_ground = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[c4_ref.ports["B"]],
        ports2=[c6_ref.ports["TR_B_1_1"]],
        route_width=2,  # adjust for thicker connections
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    via_m2_m5 = ihp.cells.via_stack(
        top_layer="Metal5",
        bottom_layer="Metal2",
        vn_columns=2,
        vn_rows=4,
    )

    # connect XQ3 Emitter to Ground
    via_m2_m5_ref = c.add_ref(via_m2_m5)
    via_m2_m5_ref.connect("bottom", xq3_ref.ports["E"], allow_width_mismatch=True, allow_layer_mismatch=True)

    # connect XQ1 Emitter to Ground
    via_m2_m5.ports["bottom"].orientation = 0
    via_m2_m5_ref = c.add_ref(via_m2_m5)
    via_m2_m5_ref.center = (c6_ref.ports["TR_B_1_4"].center[0], xq1_ref.ports["E"].center[1])

    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_m2_m5_ref.ports["bottom"]],
        ports2=[xq1_ref.ports["E"]],
        route_width=1,  # min width for metal2 0.2
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    return c


# ============================================================
# Power detector cell (Schottky diode-based)
# ============================================================


@gf.cell
def powdet_sbd() -> gf.Component:
    """Schottky-diode power detector with transimpedance amplifier.

    Ports: rfin (TM2), vout (M4), vref (M4), vss (M5), vdd (TM1).
    """
    c = gf.Component("powdet_sbd")

    # via from rfin on TM2 to C1 on TM1
    via_tm1_tm2 = ihp.cells.via_stack(
        top_layer="TopMetal2",
        bottom_layer="TopMetal1",
        vt2_columns=4,
        vt2_rows=3,
    )

    via_tm1_tm2.ports["bottom"].orientation = 0
    via_tm1_tm2_ref = c.add_ref(via_tm1_tm2)
    # reference cmim capacitor and connect to via
    cmim = ihp.cells.cmim(width=CMIM_SIZE, length=CMIM_SIZE)
    c1_ref = c.add_ref(cmim)
    c1_ref.connect("T", via_tm1_tm2_ref.ports["bottom"], allow_width_mismatch=True)
    c.add_label(text="rfin", layer=ihp.tech.LAYER.TopMetal2text, position=via_tm1_tm2_ref.ports["top"].center)

    # via cell from Metal2 to Metal5
    via_m2_m5 = ihp.cells.via_stack(
        top_layer="Metal5",
        bottom_layer="Metal2",
        vn_columns=6,
        vn_rows=3,
    )

    # via from CMIM C1 to XQ1
    via_m2_m5.ports["top"].orientation = 0
    via_m2_m5_ref = c.add_ref(via_m2_m5)
    via_m2_m5_ref.connect("top", c1_ref.ports["B"], allow_width_mismatch=True)

    # create D1 and connect to rfin via C1 and the vias
    schottky = ihp.cells.schottky()
    schottky.locked = False
    schottky.add_label(text="schottky_nbl1", layer=ihp.tech.LAYER.TEXTdrawing)

    d1_ref = c.add_ref(schottky)
    d1_ref.connect("e4", via_m2_m5_ref.ports["bottom"], allow_width_mismatch=True, allow_layer_mismatch=True)

    # Create D2 nearby D1 for better matching
    d2_ref = c.add_ref(schottky)
    d2_ref.ymin = d1_ref.ymin
    d2_ref.xmin = d1_ref.xmax  # min spacing according to design rules 5.10

    # Create capacitor array for c2
    c2 = gf.Component("C2")
    cmim = ihp.cells.cmim(width=CMIM_SIZE, length=CMIM_SIZE)
    cap_connection_thickness = CAP_BUS_WIDTH  # thickness of the metal connection between caps
    # create 3 * 4 array of cmim capacitors with column pitch of 0.52 + 11.2 to fit the required spacing for TM1 and the size of the caps
    # with one missing cap to fit C1 in there
    spacing_between_caps = CMIM_SPACING_TM1
    top_row = c2.add_ref(
        gf.components.array(component=cmim, columns=6, rows=1, column_pitch=spacing_between_caps + CMIM_PITCH)
    )

    middle_row = c2.add_ref(
        gf.components.array(component=cmim, columns=6, rows=1, column_pitch=spacing_between_caps + CMIM_PITCH)
    )
    bottom_row = c2.add_ref(
        gf.components.array(
            component=cmim,
            columns=6,
            rows=3,
            column_pitch=spacing_between_caps + CMIM_PITCH,
            row_pitch=-(spacing_between_caps + CMIM_PITCH),
        )
    )
    top_row.ymin = middle_row.ymax + spacing_between_caps  # min spacing according to design rules 5.17
    bottom_row.ymax = middle_row.ymin - spacing_between_caps  # min spacing according to design rules 5.17
    c2.add_ports(top_row.ports, prefix="TR_")
    c2.add_ports(middle_row.ports, prefix="MR_")
    c2.add_ports(bottom_row.ports, prefix="BR_")

    c2.add_label(text="vss", layer=ihp.tech.LAYER.Metal5text, position=c2.ports["BR_T_1_1"].center)

    # Orient outermost ports inward for horizontal cap-to-cap connection
    for prefix in [
        "TR_T_1_",
        "TR_B_1_",
        "MR_T_1_",
        "MR_B_1_",
        "BR_T_1_",
        "BR_B_1_",
        "BR_T_2_",
        "BR_B_2_",
        "BR_T_3_",
        "BR_B_3_",
    ]:
        c2.ports[f"{prefix}1"].orientation = 0
        c2.ports[f"{prefix}6"].orientation = 180

    c2_connection_t = gf.routing.route_bundle_electrical(
        component=c2,
        ports1=[
            c2.ports["TR_T_1_1"],
            c2.ports["BR_T_2_1"],
            c2.ports["BR_T_3_1"],
            c2.ports["MR_T_1_1"],
            c2.ports["BR_T_1_1"],
        ],
        ports2=[
            c2.ports["TR_T_1_6"],
            c2.ports["BR_T_2_6"],
            c2.ports["BR_T_3_6"],
            c2.ports["MR_T_1_6"],
            c2.ports["BR_T_1_6"],
        ],
        route_width=cap_connection_thickness,
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    c2_connection_b = gf.routing.route_bundle_electrical(
        component=c2,
        ports1=[
            c2.ports["TR_B_1_1"],
            c2.ports["BR_B_2_1"],
            c2.ports["BR_B_3_1"],
            c2.ports["MR_B_1_1"],
            c2.ports["BR_B_1_1"],
        ],
        ports2=[
            c2.ports["TR_B_1_6"],
            c2.ports["BR_B_2_6"],
            c2.ports["BR_B_3_6"],
            c2.ports["MR_B_1_6"],
            c2.ports["BR_B_1_6"],
        ],
        route_width=cap_connection_thickness,
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # orient top row ports to face downwards to connect to bottom row ports
    ihp.cells.utils.change_port_orientation(
        c2, ["TR_T_1_1", "TR_T_1_2", "TR_T_1_3", "TR_T_1_4", "TR_T_1_5", "TR_T_1_6"], 270
    )
    ihp.cells.utils.change_port_orientation(
        c2, ["TR_B_1_1", "TR_B_1_2", "TR_B_1_3", "TR_B_1_4", "TR_B_1_5", "TR_B_1_6"], 270
    )

    # orient bottom row ports to face downwards to connect to top row ports
    ihp.cells.utils.change_port_orientation(
        c2, ["BR_T_3_1", "BR_T_3_2", "BR_T_3_3", "BR_T_3_4", "BR_T_3_5", "BR_T_3_6"], 90
    )
    ihp.cells.utils.change_port_orientation(
        c2, ["BR_B_3_1", "BR_B_3_2", "BR_B_3_3", "BR_B_3_4", "BR_B_3_5", "BR_B_3_6"], 90
    )

    c2_connection_top = gf.routing.route_bundle_electrical(
        component=c2,
        ports1=[
            c2.ports["BR_T_3_1"],
            c2.ports["BR_T_3_2"],
            c2.ports["BR_T_3_3"],
            c2.ports["BR_T_3_4"],
            c2.ports["BR_T_3_5"],
            c2.ports["BR_T_3_6"],
        ],
        ports2=[
            c2.ports["TR_T_1_1"],
            c2.ports["TR_T_1_2"],
            c2.ports["TR_T_1_3"],
            c2.ports["TR_T_1_4"],
            c2.ports["TR_T_1_5"],
            c2.ports["TR_T_1_6"],
        ],
        route_width=cap_connection_thickness,  # adjust for thicker connections
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    c2_connection_bottom = gf.routing.route_bundle_electrical(
        component=c2,
        ports1=[
            c2.ports["BR_B_3_1"],
            c2.ports["BR_B_3_2"],
            c2.ports["BR_B_3_3"],
            c2.ports["BR_B_3_4"],
            c2.ports["BR_B_3_5"],
            c2.ports["BR_B_3_6"],
        ],
        ports2=[
            c2.ports["TR_B_1_1"],
            c2.ports["TR_B_1_2"],
            c2.ports["TR_B_1_3"],
            c2.ports["TR_B_1_4"],
            c2.ports["TR_B_1_5"],
            c2.ports["TR_B_1_6"],
        ],
        route_width=cap_connection_thickness,  # adjust for thicker connections
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # orient top row ports to face upwards to connect the ground plates to the other caps
    ihp.cells.utils.change_port_orientation(c2, ["TR_B_1_1", "TR_B_1_2", "TR_B_1_3", "TR_B_1_6"], 90)
    ihp.cells.utils.change_port_orientation(c2, ["TR_T_1_6"], 0)  # for connection to bias1
    ihp.cells.utils.change_port_orientation(c2, ["BR_B_3_4", "BR_B_3_5"], 270)

    c2_ref = c.add_ref(c2)
    c2_ref.rotate(-90)
    c2_ref.center = c1_ref.center
    c2_ref.ymin = c1_ref.ymax + 10
    c2_ref.xmax = c1_ref.xmax + c1_ref.xsize + CMIM_SPACING_TM1

    ## end of c2 generation

    r_sil = ihp.cells.rsil(width=RSIL_WIDTH, length=RSIL_LENGTH)

    # let the ports of xr1 and xr5 face each other for easier routing
    r_sil.ports["e2"].orientation = 0
    xr1_ref = c.add_ref(r_sil.copy())

    r_sil.ports["e2"].orientation = 180
    xr5 = r_sil.copy()
    xr5_ref = c.add_ref(xr5)

    # spacing between D1 and xr1/xr5
    spacing = 1
    xr1_ref.xmax = d1_ref.xmax - 1.88
    xr1_ref.ymax = d1_ref.ymin - spacing

    xr5_ref.xmin = d2_ref.xmin + 1.88
    xr5_ref.ymin = xr1_ref.ymin

    route_xr1_xr5 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[xr1_ref.ports["e2"]],
        ports2=[xr5_ref.ports["e2"]],
        route_width=ROUTE_WIDTH_MIN_M1,
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # via for connection D1 to xr1 and xr5 to D2
    via_m1_m2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=6,
        vn_rows=2,
    )

    # via D1 -> xr1
    via_m1_m2.ports["top"].orientation = 90
    via_m1_m2.ports["bottom"].orientation = 0
    via_m1_m2_ref = c.add_ref(via_m1_m2.copy())
    via_m1_m2_ref.center = d1_ref.center
    via_m1_m2_ref.ymax = d1_ref.ymin

    # route from D1 to via
    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[d1_ref.ports["e4"]],
        ports2=[via_m1_m2_ref.ports["top"]],
        route_width=max(via_m1_m2_ref.xsize, via_m1_m2_ref.ysize),
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # route from via to xr1
    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_m1_m2_ref.ports["bottom"]],
        ports2=[xr1_ref.ports["e1"]],
        route_width=min(via_m1_m2_ref.xsize, via_m1_m2_ref.ysize),
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # connect second diode to input resistors
    # via D2 -> xr5
    via_m1_m2.ports["top"].orientation = 90
    via_m1_m2.ports["bottom"].orientation = 180
    via_m1_m2_ref = c.add_ref(via_m1_m2.copy())
    via_m1_m2_ref.center = d2_ref.center
    via_m1_m2_ref.ymax = d2_ref.ymin

    # route from D2 to via
    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[d2_ref.ports["e4"]],
        ports2=[via_m1_m2_ref.ports["top"]],
        route_width=max(via_m1_m2_ref.xsize, via_m1_m2_ref.ysize),
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # route from via to xr5
    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_m1_m2_ref.ports["bottom"]],
        ports2=[xr5_ref.ports["e1"]],
        route_width=min(via_m1_m2_ref.xsize, via_m1_m2_ref.ysize),
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    ## Build transimpedance amplifier with Schottky diode as input device.
    # M1 (nmos, 20 gates) + M3 (nmos, 2 gates) + 2 dummy gates = 24
    # M2 (pmos, 20 gates) + M4 (pmos, 2 gates) + 2 dummy gates = 24
    ng_mos = NUM_GATES
    width_nmos = NMOS_WIDTH  # um
    width_pmos = PMOS_WIDTH  # um

    c_output = gf.Component("output_stage")

    m1_3 = ihp.cells.nmos(
        w=width_nmos,
        l=GATE_LENGTH,
        ng=ng_mos,
        guardRingType="psub",
        guardRingDistance=GUARD_RING_DISTANCE,
    )

    via_gat_m1 = ihp.cells.via_stack(
        top_layer="Metal1",
        bottom_layer="GatPoly",
        vn_columns=1,
        vn_rows=2,
    )

    via_gat_m2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="GatPoly",
        vn_columns=1,
        vn_rows=3,
    )

    via_gat_m3 = ihp.cells.via_stack(
        top_layer="Metal3",
        bottom_layer="GatPoly",
        vn_columns=1,
        vn_rows=3,
    )

    m1_3.locked = False
    via_gat_m1.ports["bottom"].orientation = 90
    via_gat_m2.ports["bottom"].orientation = 90
    via_gat_m3.ports["bottom"].orientation = 90
    via_gat_m3.ports["top"].orientation = 270  # turn top port for later connection
    gate_ports = m1_3.get_ports_list(layer=ihp.tech.LAYER.GatPolydrawing)
    gate_straight = ihp.cells.straight(
        length=GATE_EXTENSION_NMOS, cross_section="gatpoly_routing", width=GATE_LENGTH  # gate poly width
    )
    gate_via_refs_nmos = []
    for i, p in enumerate(gate_ports):
        if p.name in ["G_1", "G_24"]:  # these gates will be connected to metal1
            gate_via_refs_nmos.append(m1_3.add_ref(via_gat_m2))
        elif p.name in ["G_12", "G_13"]:  # these gates will be connected to metal2
            gate_via_refs_nmos.append(m1_3.add_ref(via_gat_m2))
        else:  # all others to metal3
            gate_via_refs_nmos.append(m1_3.add_ref(via_gat_m3))
        gate_straight_ref = m1_3.add_ref(gate_straight)
        gate_straight_ref.connect("e1", m1_3.ports[p.name], allow_width_mismatch=True, allow_layer_mismatch=True)
        via_gat_m2_ref = gate_via_refs_nmos[-1]
        via_gat_m2_ref.connect(
            "bottom", gate_straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True
        )

    # connect gates 1 and 24 with metal1 to ground
    via_gat_m2.ports["top"].orientation = 0
    start_point = gate_via_refs_nmos[0].ports["top"].center[0]
    end_point = m1_3.ports["DS_29"].center[0]
    straight_ref = m1_3.add_ref(
        ihp.cells.straight(
            length=abs(end_point - start_point),
            cross_section="metal2_routing",
            width=1.11,  # manual measure of the height of the via
        )
    )
    straight_ref.connect("e1", gate_via_refs_nmos[0].ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    via_m1_m2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=3,
        vn_rows=1,
    )
    via_m1_m2_ref = m1_3.add_ref(via_m1_m2)
    via_m1_m2_ref.connect("top", straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    via_gat_m2.ports["top"].orientation = 180
    straight_ref = m1_3.add_ref(
        ihp.cells.straight(
            length=abs(end_point - start_point),
            cross_section="metal2_routing",
            width=1.11,  # manual measure of the height of the via
        )
    )
    straight_ref.connect(
        "e1", gate_via_refs_nmos[23].ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True
    )
    via_m1_m2_ref = m1_3.add_ref(via_m1_m2)
    via_m1_m2_ref.connect("top", straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    # connect Gates 2-11 and 14-23 (all 20 gates) together with metal3
    start_point = m1_3.ports["G_2"].center
    end_point = m1_3.ports["G_23"].center
    straight_ref = m1_3.add_ref(
        ihp.cells.straight(
            length=abs(end_point[0] - start_point[0]),
            cross_section="metal3_routing",
            width=max(
                gate_via_refs_nmos[1].xsize, gate_via_refs_nmos[1].ysize
            ),  # manual measure of the height of the via
        )
    )
    straight_ref.center = (
        (start_point[0] + end_point[0]) / 2,
        gate_via_refs_nmos[1].center[1],
    )  # align with the via of the first M1 gate

    # connect Gates 12-13 (2 gates) together with metal2
    start_point = m1_3.ports["G_12"].center
    end_point = m1_3.ports["G_13"].center
    straight_ref = m1_3.add_ref(
        ihp.cells.straight(
            length=abs(end_point[0] - start_point[0]),
            cross_section="metal2_routing",
            width=0.6,  # manual measure of the height of the via
        )
    )
    straight_ref.center = (
        (start_point[0] + end_point[0]) / 2,
        gate_via_refs_nmos[11].center[1],
    )  # align with the via of the first M3 gate

    # connect source to GND
    m1_3_ds_ports = m1_3.get_ports_list(layer=ihp.tech.LAYER.Metal1drawing)
    m1_3_source_ports = []
    m1_3_drain_ports = []
    for i in range(3, len(m1_3_ds_ports) - 1):  # filter out unwanted ports
        if i == 3 or i == len(m1_3_ds_ports) - 2 or i % 2 == 0:
            m1_3_source_ports.append(m1_3_ds_ports[i])
        else:
            m1_3_drain_ports.append(m1_3_ds_ports[i])

    # source ground connection
    source_straight = ihp.cells.straight(
        length=abs(
            m1_3.ports["DS_1"].center[1] - m1_3.ports["DS_27"].center[1]
        ),  # any source port to the the center of the top guardring segment
        cross_section="metal2_routing",
        width=0.26,  # manual measure of the height of the via
    )
    via_m1_m2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=7,
        vn_rows=1,
    )
    via_m1_m2.ports["bottom"].orientation = 0
    via_m1_m2.ports["top"].orientation = 180
    for p in m1_3_source_ports:
        p.orientation = 90  # orient ports to face the top
        via_m1_m2_ref = m1_3.add_ref(via_m1_m2)
        via_m1_m2_ref.connect("bottom", p, allow_width_mismatch=True, allow_layer_mismatch=True)
        source_straight_ref = m1_3.add_ref(source_straight)
        source_straight_ref.connect(
            "e1", via_m1_m2_ref.ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True
        )

    # connect drains to M3
    via_m1_m4 = ihp.cells.via_stack(
        top_layer="Metal4",
        bottom_layer="Metal1",
        vn_columns=1,
        vn_rows=7,
    )

    drain_via_refs_nmos = []
    for p in m1_3_drain_ports:
        if p.name in ["DS_13"]:
            via_m1_m4_short = ihp.cells.via_stack(
                top_layer="Metal4",
                bottom_layer="Metal1",
                vn_columns=1,
                vn_rows=3,
            )
            via_m1_m4_short.ports["top"].orientation = 270
            drain_via_refs_nmos.append(m1_3.add_ref(via_m1_m4_short))
            drain_via_refs_nmos[-1].center = p.center
            drain_via_refs_nmos[-1].ymax = p.center[1] - 0.245  # manual measurement to align with metal1 below
        else:
            via_m1_m4.ports["bottom"].orientation = 90
            via_m1_m4.ports["top"].orientation = 90
            via_m1_m4_ref = m1_3.add_ref(via_m1_m4)
            via_m1_m4_ref.connect("bottom", p, allow_width_mismatch=True, allow_layer_mismatch=True)
            drain_via_refs_nmos.append(via_m1_m4_ref)

    # horizontal drain connection for nmos
    straight_drain_connection = ihp.cells.straight(
        length=abs(
            drain_via_refs_nmos[0].center[0] - drain_via_refs_nmos[-1].center[0]
        ),  # any drain via to the the center of the top guardring segment
        cross_section="metal4_routing",
        width=2,  # manual measure of the height of the via
    )
    straight_drain_connection_ref = m1_3.add_ref(straight_drain_connection)
    straight_drain_connection_ref.xmin = drain_via_refs_nmos[-1].center[0]
    straight_drain_connection_ref.ymin = drain_via_refs_nmos[-1].center[1]

    m1_3.add_ports(gate_via_refs_nmos[17].ports, prefix="gate_M1_")
    m1_3.add_port(name="drain_connection_M1", port=drain_via_refs_nmos[2].ports["top"])
    m1_3.add_port(name="drain_connection_M3", port=drain_via_refs_nmos[5].ports["top"])
    m1_3.add_port(
        name="gate_connection_M3",
        center=(
            (gate_via_refs_nmos[11].center[0] + gate_via_refs_nmos[12].center[0]) / 2,
            gate_via_refs_nmos[11].center[1],
        ),
        cross_section="metal2_routing",
        orientation=270,
        port_type="electrical",
    )
    m1_3_ref = c_output.add_ref(m1_3)
    m1_3_ref.move((0, 30))

    m2_4 = ihp.cells.pmos(
        w=width_pmos,
        l=GATE_LENGTH,
        ng=ng_mos,
        guardRingType="nwell",
        guardRingDistance=GUARD_RING_DISTANCE,
    )

    # connect gates of M2 and M4 together

    m2_4.locked = False
    gate_ports = m2_4.get_ports_list(layer=ihp.tech.LAYER.GatPolydrawing)
    gate_straight = ihp.cells.straight(
        length=GATE_EXTENSION_PMOS, cross_section="gatpoly_routing", width=GATE_LENGTH  # gate poly width
    )
    gate_via_refs_pmos = []
    for i, p in enumerate(gate_ports):
        p.orientation += 180  # orient gates to face downwards for easier connection to nmos gates
        if p.name in ["G_1", "G_25"]:  # these gates will be connected to metal1
            gate_via_refs_pmos.append(m2_4.add_ref(via_gat_m2))
        elif p.name in ["G_13", "G_14"]:  # these gates will be connected to metal2
            gate_via_refs_pmos.append(m2_4.add_ref(via_gat_m2))
        else:  # all others to metal3
            gate_via_refs_pmos.append(m2_4.add_ref(via_gat_m3))
        gate_straight_ref = m2_4.add_ref(gate_straight)
        gate_straight_ref.connect("e1", m2_4.ports[p.name], allow_width_mismatch=True, allow_layer_mismatch=True)
        gate_via_refs_pmos[-1].connect(
            "bottom", gate_straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True
        )

    ## Gate numbers are shifted by 1 after G1, e.g. G1 G3 G4 G5 ... don't know why...
    ## Similar for DS: DS1 DS3 DS5 DS6 DS7 ... maybe guard rings are interfering
    ## even though they are disabled
    # connect gates 1 and 24 with metal1 to ground
    via_gat_m2.ports["top"].orientation = 180
    start_point = gate_via_refs_pmos[0].ports["top"].center[0]
    end_point = m2_4.ports["DS_31"].center[0]
    straight_ref = m2_4.add_ref(
        ihp.cells.straight(
            length=abs(end_point - start_point),
            cross_section="metal2_routing",
            width=1.11,  # manual measure of the height of the via
        )
    )

    straight_ref.connect("e1", gate_via_refs_pmos[0].ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    via_m1_m2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=3,
        vn_rows=1,
    )
    via_m1_m2_ref = m2_4.add_ref(via_m1_m2)
    via_m1_m2_ref.connect("top", straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    straight_ref.connect("e2", via_m1_m2_ref.ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)

    via_gat_m2.ports["bottom"].orientation = 0
    straight_ref.connect("e1", gate_via_refs_pmos[0].ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    straight_ref = m2_4.add_ref(
        ihp.cells.straight(
            length=abs(end_point - start_point),
            cross_section="metal2_routing",
            width=1.11,  # manual measure of the height of the via
        )
    )
    straight_ref.connect(
        "e1", gate_via_refs_pmos[23].ports["bottom"], allow_width_mismatch=True, allow_layer_mismatch=True
    )

    via_m1_m2_ref = m2_4.add_ref(via_m1_m2)
    via_m1_m2_ref.connect("top", straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    # connect Gates 2-11 and 14-23 (20 gates) together with metal3
    start_point = m2_4.ports["G_3"].center
    end_point = m2_4.ports["G_24"].center
    straight_ref = m2_4.add_ref(
        ihp.cells.straight(
            length=abs(end_point[0] - start_point[0]),
            cross_section="metal3_routing",
            width=max(
                gate_via_refs_pmos[1].xsize, gate_via_refs_pmos[1].ysize
            ),  # manual measure of the height of the via
        )
    )
    straight_ref.center = (
        (start_point[0] + end_point[0]) / 2,
        gate_via_refs_pmos[1].center[1],
    )  # align with the via of the first M1 gate

    # connect Gates 12-13 (2 gates) together with metal2
    start_point = m2_4.ports["G_13"].center
    end_point = m2_4.ports["G_14"].center
    straight_ref = m2_4.add_ref(
        ihp.cells.straight(
            length=abs(end_point[0] - start_point[0]),
            cross_section="metal2_routing",
            width=0.6,  # manual measure of the height of the via
        )
    )
    straight_ref.center = (
        (start_point[0] + end_point[0]) / 2,
        gate_via_refs_pmos[11].center[1],
    )  # align with the via of the first M3 gate

    # connect source to vdd
    m2_4_ds_ports = m2_4.get_ports_list(layer=ihp.tech.LAYER.Metal1drawing)
    m2_4_source_ports = []
    m2_4_drain_ports = []
    for i in range(3, len(m2_4_ds_ports) - 1):  # filter out unwanted ports
        if i == 3 or i == len(m2_4_ds_ports) - 2 or i % 2 == 0:
            m2_4_source_ports.append(m2_4_ds_ports[i])
        else:
            m2_4_drain_ports.append(m2_4_ds_ports[i])

    # source vdd connection
    source_straight = ihp.cells.straight(
        length=abs(
            m2_4.ports["DS_1"].center[1] - m2_4.ports["DS_29"].center[1]
        ),  # any source port to the the center of the top guardring segment
        cross_section="metal2_routing",
        width=0.26,  # manual measure of the height of the via
    )
    via_m1_m2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=13,
        vn_rows=1,
    )
    via_m1_m2.ports["bottom"].orientation = 180
    via_m1_m2.ports["top"].orientation = 0
    for p in m2_4_source_ports:
        p.orientation = 270  # orient ports to face the top
        via_m1_m2_ref = m2_4.add_ref(via_m1_m2)
        via_m1_m2_ref.connect("bottom", p, allow_width_mismatch=True, allow_layer_mismatch=True)
        source_straight_ref = m2_4.add_ref(source_straight)
        source_straight_ref.connect(
            "e1", via_m1_m2_ref.ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True
        )

    # connect drains to metal4
    via_m1_m4 = ihp.cells.via_stack(
        top_layer="Metal4",
        bottom_layer="Metal1",
        vn_columns=1,
        vn_rows=13,
    )
    drain_via_refs_pmos = []
    for p in m2_4_drain_ports:
        if p.name in ["DS_15"]:
            via_m1_m4_short = ihp.cells.via_stack(
                top_layer="Metal4",
                bottom_layer="Metal1",
                vn_columns=1,
                vn_rows=6,
            )
            via_m1_m4_short.ports["top"].orientation = 90
            drain_via_refs_pmos.append(m2_4.add_ref(via_m1_m4_short))
            drain_via_refs_pmos[-1].center = p.center
            drain_via_refs_pmos[-1].ymin = p.center[1] + 0.245  # manual measurement to align with metal1 below
        else:
            via_m1_m4.ports["bottom"].orientation = 90
            via_m1_m4.ports["top"].orientation = 270
            via_m1_m4_ref = m2_4.add_ref(via_m1_m4)
            via_m1_m4_ref.connect("bottom", p, allow_width_mismatch=True, allow_layer_mismatch=True)
            drain_via_refs_pmos.append(via_m1_m4_ref)

    # horizontal drain connection for pmos
    straight_drain_connection = ihp.cells.straight(
        length=abs(
            drain_via_refs_pmos[0].center[0] - drain_via_refs_pmos[-1].center[0]
        ),  # any drain via to the the center of the top guardring segment
        cross_section="metal4_routing",
        width=2.61,  #  manual measurement
    )
    straight_drain_connection_ref = m2_4.add_ref(straight_drain_connection)
    straight_drain_connection_ref.xmin = drain_via_refs_pmos[-1].center[0]
    straight_drain_connection_ref.ymin = drain_via_refs_pmos[-1].ymin

    m2_4.add_ports(gate_via_refs_pmos[17].ports, prefix="gate_M2_")
    m2_4.add_port(name="drain_connection_M2", port=drain_via_refs_pmos[2].ports["top"])
    m2_4.add_port(name="drain_connection_M4", port=drain_via_refs_pmos[5].ports["top"])
    m2_4.add_port(
        name="gate_connection_M4",
        center=(
            (gate_via_refs_pmos[11].center[0] + gate_via_refs_pmos[12].center[0]) / 2,
            gate_via_refs_pmos[11].center[1],
        ),
        cross_section="metal2_routing",
        orientation=90,
        port_type="electrical",
    )

    m2_4_ref = c_output.add_ref(m2_4)

    spacing_between_nmos_pmos = NMOS_PMOS_SPACING  # manual measurement of the spacing between the drain vias of M1 and M2, used to set the length of the connection between M1 and M2 drains
    drain_connection_m1_m2 = c_output.add_ref(
        ihp.cells.straight(
            length=spacing_between_nmos_pmos,  # manual measurement, used to set the distance between M1 and M2
            cross_section="metal4_routing",
            width=4.28,  #  manual measurement
        )
    )

    drain_connection_m1_m2.connect(
        "e1", m1_3_ref.ports["drain_connection_M1"], allow_width_mismatch=True, allow_layer_mismatch=True
    )
    m2_4_ref.connect(
        "drain_connection_M2", drain_connection_m1_m2.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True
    )

    # drain connection for replica circuit
    routing_drain_m1_m3 = gf.routing.route_bundle_electrical(
        component=c_output,
        ports1=[m1_3_ref.ports["drain_connection_M3"]],
        ports2=[m2_4_ref.ports["drain_connection_M4"]],
        route_width=ROUTE_WIDTH_REPLICA,
        layer=ihp.tech.LAYER.Metal4drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # vias for resistor xr2 and xr4 connections
    via_m1_m2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=2,
        vn_rows=2,
    )
    via_m1_m2.ports["top"].orientation = 90
    via_m1_m3 = ihp.cells.via_stack(
        top_layer="Metal3",
        bottom_layer="Metal1",
        vn_columns=2,
        vn_rows=2,
    )
    via_m1_m4 = ihp.cells.via_stack(
        top_layer="Metal4",
        bottom_layer="Metal1",
        vn_columns=2,
        vn_rows=2,
    )

    xr4 = ihp.cells.rppd(width=RPPD_WIDTH, length=RPPD_LENGTH)
    xr4_ref = c_output.add_ref(xr4).rotate(90)
    xr4_ref.center = m1_3_ref.ports["DS_15"].center
    xr4_ref.movex(0.01)  # manual measurement to align with the gate connection
    xr4_ref.ymax = m1_3_ref.ymin - 2  # manual measurement to set the spacing between the nmos and the resistors

    via_m1_m4_ref = c_output.add_ref(via_m1_m4)
    via_m1_m4_ref.connect("bottom", xr4_ref.ports["e1"], allow_width_mismatch=True, allow_layer_mismatch=True)
    c_output.add_label(text="vref", layer=ihp.tech.LAYER.Metal4text, position=via_m1_m4_ref.ports["top"].center)
    c_output.add_port(name="vref", port=via_m1_m4_ref.ports["top"])

    via_m1_m2.ports["top"].orientation = 180
    via_m1_m2_ref = c_output.add_ref(via_m1_m2)
    via_m1_m2_ref.connect("bottom", xr4_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    c_output.add_ports(via_m1_m2_ref.ports, prefix="XR4_")

    xr2 = ihp.cells.rppd(width=RPPD_WIDTH, length=RPPD_LENGTH)
    xr2_ref = c_output.add_ref(xr2).rotate(90)
    xr2_ref.ymax = xr4_ref.ymin - 1  # manual measurement to set the spacing between the two resistors to 0
    xr2_ref.xmax = xr4_ref.xmax

    via_m1_m4_ref = c_output.add_ref(via_m1_m4)
    via_m1_m4_ref.connect("bottom", xr2_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    c_output.add_label(text="vout", layer=ihp.tech.LAYER.Metal4text, position=via_m1_m4_ref.ports["top"].center)
    c_output.add_port(name="vout", port=via_m1_m4_ref.ports["top"])
    via_m1_m3_ref = c_output.add_ref(via_m1_m3)
    via_m1_m3_ref.connect("bottom", xr2_ref.ports["e1"], allow_width_mismatch=True, allow_layer_mismatch=True)

    # bias2
    route_gates_m3_m4 = gf.routing.route_bundle_electrical(
        component=c_output,
        ports1=[m1_3_ref.ports["gate_connection_M3"]],
        ports2=[via_m1_m2_ref.ports["top"]],
        route_width=ROUTE_WIDTH_BIAS,
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
        steps=[
            {"dy": -2.46, "dx": 0.5},
            {"dx": 1},
        ],
    )

    # node bb_int routing
    route_gates_m1_m2 = gf.routing.route_bundle_electrical(
        component=c_output,
        ports1=[m1_3_ref.ports["gate_M1_top"]],
        ports2=[m2_4_ref.ports["gate_M2_top"]],
        route_width=ROUTE_WIDTH_GATE,
        layer=ihp.tech.LAYER.Metal3drawing,
        start_straight_length=0.5,
        end_straight_length=0.5,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    route_gates_m1_m2 = gf.routing.route_bundle_electrical(
        component=c_output,
        ports1=[m1_3_ref.ports["gate_M1_top"]],
        ports2=[xr2_ref.ports["e1"]],
        route_width=ROUTE_WIDTH_GATE,
        layer=ihp.tech.LAYER.Metal3drawing,
        start_straight_length=0.5,
        end_straight_length=0.5,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    c_output.add_ports(m1_3_ref.ports, prefix="M1_")
    c_output.add_ports(m2_4_ref.ports, prefix="M2_")
    output_stage_ref = c.add_ref(c_output.rotate(90))
    output_stage_ref.center = c2_ref.center
    output_stage_ref.ymin = c2_ref.ymin
    output_stage_ref.move((17.99 + 1.64, 9.02 + 5.23))

    # create capacitor array for cap 3
    c3 = gf.Component("C3")
    # create 3 * 4 array of cmim capacitors with column pitch of 0.52 + 11.2 to fit the required spacing for TM1 and the size of the caps
    # with one missing cap to fit C1 in there
    spacing_between_caps = CMIM_SPACING_TM1
    left_col = c3.add_ref(
        gf.components.array(
            component=cmim,
            columns=3,
            rows=5,
            column_pitch=spacing_between_caps + CMIM_PITCH,
            row_pitch=-(spacing_between_caps + CMIM_PITCH),
        )
    )
    middle_col = c3.add_ref(
        gf.components.array(
            component=cmim,
            columns=2,
            rows=4,
            column_pitch=spacing_between_caps + CMIM_PITCH,
            row_pitch=-(spacing_between_caps + CMIM_PITCH),
        )
    )
    right_col = c3.add_ref(
        gf.components.array(
            component=cmim,
            columns=1,
            rows=5,
            column_pitch=spacing_between_caps + CMIM_PITCH,
            row_pitch=-(spacing_between_caps + CMIM_PITCH),
        )
    )
    left_col.xmax = middle_col.xmin - spacing_between_caps  # min spacing according to design rules 5.17
    right_col.xmin = middle_col.xmax + spacing_between_caps  # min spacing according to design rules 5.17
    c3.add_ports(left_col.ports, prefix="LC_")
    c3.add_ports(middle_col.ports, prefix="MC_")
    c3.add_ports(right_col.ports, prefix="RC_")

    # orient the outer most port of for horizontal connection
    ihp.cells.utils.change_port_orientation(c3, ["LC_T_1_1", "LC_T_2_1", "LC_T_3_1", "LC_T_4_1", "LC_T_5_1"], 0)
    ihp.cells.utils.change_port_orientation(c3, ["LC_B_1_1", "LC_B_2_1", "LC_B_3_1", "LC_B_4_1", "LC_B_5_1"], 0)

    ihp.cells.utils.change_port_orientation(c3, ["RC_T_1_1", "RC_T_2_1", "RC_T_3_1", "RC_T_4_1", "LC_T_5_3"], 180)
    ihp.cells.utils.change_port_orientation(c3, ["RC_B_1_1", "RC_B_2_1", "RC_B_3_1", "RC_B_4_1", "LC_B_5_3"], 180)

    c3_connection_t = gf.routing.route_bundle_electrical(
        component=c3,
        ports1=[
            c3.ports["LC_T_1_1"],
            c3.ports["LC_T_2_1"],
            c3.ports["LC_T_3_1"],
            c3.ports["LC_T_4_1"],
            c3.ports["LC_T_5_1"],
        ],
        ports2=[
            c3.ports["RC_T_1_1"],
            c3.ports["RC_T_2_1"],
            c3.ports["RC_T_3_1"],
            c3.ports["RC_T_4_1"],
            c3.ports["LC_T_5_3"],
        ],
        route_width=cap_connection_thickness,
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    c3_connection_b = gf.routing.route_bundle_electrical(
        component=c3,
        ports1=[
            c3.ports["LC_B_1_1"],
            c3.ports["LC_B_2_1"],
            c3.ports["LC_B_3_1"],
            c3.ports["LC_B_4_1"],
            c3.ports["LC_B_5_1"],
        ],
        ports2=[
            c3.ports["RC_B_1_1"],
            c3.ports["RC_B_2_1"],
            c3.ports["RC_B_3_1"],
            c3.ports["RC_B_4_1"],
            c3.ports["LC_B_5_3"],
        ],
        route_width=cap_connection_thickness,
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # orient top row ports to face downwards to connect to bottom row ports
    ihp.cells.utils.change_port_orientation(
        c3, ["LC_T_1_1", "LC_T_1_2", "LC_T_1_3", "MC_T_1_1", "MC_T_1_2", "RC_T_1_1"], 270
    )
    ihp.cells.utils.change_port_orientation(
        c3, ["LC_B_1_1", "LC_B_1_2", "LC_B_1_3", "MC_B_1_1", "MC_B_1_2", "RC_B_1_1"], 270
    )

    # orient bottom row ports to face downwards to connect to top row ports
    ihp.cells.utils.change_port_orientation(
        c3, ["LC_T_5_1", "LC_T_5_2", "LC_T_5_3", "MC_T_4_1", "MC_T_4_2", "RC_T_5_1"], 90
    )
    ihp.cells.utils.change_port_orientation(
        c3, ["LC_B_5_1", "LC_B_5_2", "LC_B_5_3", "MC_B_4_1", "MC_B_4_2", "RC_B_5_1"], 90
    )

    c3_connection_top = gf.routing.route_bundle_electrical(
        component=c3,
        ports1=[
            c3.ports["LC_T_1_1"],
            c3.ports["LC_T_1_2"],
            c3.ports["LC_T_1_3"],
            c3.ports["MC_T_1_1"],
            c3.ports["MC_T_1_2"],
            c3.ports["RC_T_1_1"],
        ],
        ports2=[
            c3.ports["LC_T_5_1"],
            c3.ports["LC_T_5_2"],
            c3.ports["LC_T_5_3"],
            c3.ports["MC_T_4_1"],
            c3.ports["MC_T_4_2"],
            c3.ports["RC_T_5_1"],
        ],
        route_width=cap_connection_thickness,
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    c3_connection_bottom = gf.routing.route_bundle_electrical(
        component=c3,
        ports1=[
            c3.ports["LC_B_1_1"],
            c3.ports["LC_B_1_2"],
            c3.ports["LC_B_1_3"],
            c3.ports["MC_B_1_1"],
            c3.ports["MC_B_1_2"],
            c3.ports["RC_B_1_1"],
        ],
        ports2=[
            c3.ports["LC_B_5_1"],
            c3.ports["LC_B_5_2"],
            c3.ports["LC_B_5_3"],
            c3.ports["MC_B_4_1"],
            c3.ports["MC_B_4_2"],
            c3.ports["RC_B_5_1"],
        ],
        route_width=cap_connection_thickness,
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # orient top row ports to face downwards to connect to face the middle for connection purposes
    ihp.cells.utils.change_port_orientation(c3, ["MC_T_4_1", "MC_T_4_2", "LC_T_5_1", "LC_T_5_2", "LC_T_5_3"], 270)
    # orient top row ports to face downwards to connect to face c2 for connection purposes
    ihp.cells.utils.change_port_orientation(
        c3, ["MC_B_4_1", "MC_B_4_2", "LC_B_5_1", "LC_B_5_2", "LC_B_5_3", "RC_B_5_1"], 270
    )

    c3.add_label(text="vdd", layer=ihp.tech.LAYER.TopMetal1text, position=c3.ports["LC_T_1_1"].center)
    c3_ref = c.add_ref(c3)

    c3_ref.rotate(-90)
    c3_ref.xmin = c2_ref.xmax + CMIM_SPACING_TM1  # manual measurement to set the spacing between c2 and c3
    c3_ref.ymin = c2_ref.ymin

    c_fill = ihp.cells.cmim(width=CMIM_FILL_WIDTH, length=CMIM_FILL_LENGTH)
    c_fill.ports["B"].orientation = 0
    c_fill_1_ref = c.add_ref(c_fill)
    c_fill_2_ref = c.add_ref(c_fill)

    straight_m5 = ihp.cells.straight(
        length=10.12,
        cross_section="metal5_routing",
        width=cap_connection_thickness,  # manual measurement to align with the via
    )
    straight_m5_ref = c.add_ref(straight_m5)
    straight_m5_ref.connect("e1", c3_ref.ports["MC_B_4_1"], allow_width_mismatch=True, allow_layer_mismatch=True)
    c_fill_1_ref.connect("B", straight_m5_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    straight_m5_ref = c.add_ref(straight_m5)
    straight_m5_ref.connect("e1", c3_ref.ports["MC_B_4_2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    c_fill_2_ref.connect("B", straight_m5_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    route_c2_c3_vss = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[c2_ref.ports["TR_B_1_1"], c2_ref.ports["TR_B_1_2"], c2_ref.ports["TR_B_1_3"], c2_ref.ports["TR_B_1_6"]],
        ports2=[c3_ref.ports["LC_B_5_1"], c3_ref.ports["LC_B_5_2"], c3_ref.ports["LC_B_5_3"], c3_ref.ports["RC_B_5_1"]],
        route_width=cap_connection_thickness,  # adjust for thicker connections
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # connect nmos source/bulk to vss
    via_m1_m5 = ihp.cells.via_stack(
        top_layer="Metal5",
        bottom_layer="Metal1",
        vn_columns=3,
        vn_rows=35,
    )
    via_m1_m5.ports["bottom"].orientation = 0
    via_m1_m5_ref = c.add_ref(via_m1_m5)
    via_m1_m5_ref.connect(
        "bottom", output_stage_ref.ports["M1_DS_27"], allow_width_mismatch=True, allow_layer_mismatch=True
    )

    # connect nmos source/bulk to vdd
    via_m1_tm1 = ihp.cells.via_stack(
        top_layer="TopMetal1",
        bottom_layer="Metal1",
        vn_columns=3,
        vn_rows=35,
        vt1_columns=1,
        vt1_rows=17,
    )
    via_m1_tm1.ports["bottom"].orientation = 90
    via_m1_tm1_ref = c.add_ref(via_m1_tm1)
    via_m1_tm1_ref.connect(
        "bottom", output_stage_ref.ports["M2_DS_28"], allow_width_mismatch=True, allow_layer_mismatch=True
    )

    tm1_straight = ihp.cells.straight(
        length=abs(output_stage_ref.ports["M2_DS_28"].center[0] - c3_ref.ports["MC_T_4_1"].center[0]),
        cross_section="topmetal1_routing",
        width=2,  # manual measurement to align with the via
    )
    tm1_straight_ref = c.add_ref(tm1_straight)
    tm1_straight_ref.connect("e1", c3_ref.ports["MC_T_4_1"], allow_width_mismatch=True, allow_layer_mismatch=True)
    tm1_straight_ref = c.add_ref(tm1_straight)
    tm1_straight_ref.connect("e1", c3_ref.ports["MC_T_4_2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    # connect c2 to bias1 network
    via_m1_tm1 = ihp.cells.via_stack(
        top_layer="TopMetal1",
        bottom_layer="Metal1",
        vn_columns=3,
        vn_rows=4,
        vt1_columns=1,
        vt1_rows=2,
    )
    via_m1_tm1.ports["top"].orientation = 0
    via_m1_tm1.ports["bottom"].orientation = 180
    via_m1_tm1_ref = c.add_ref(via_m1_tm1).rotate(90)
    via_m1_tm1_ref.xmax = c2_ref.xmax - 4.55
    via_m1_tm1_ref.ymax = c3_ref.ymin - 5  # min M5 spacing

    route_c2_bias = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[c2_ref.ports["TR_T_1_6"]],
        ports2=[via_m1_tm1_ref.ports["top"]],
        route_width=max(via_m1_tm1_ref.xsize, via_m1_tm1_ref.ysize),  # manual change to fit width
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_m1_tm1_ref.ports["bottom"]],
        ports2=[xr1_ref.ports["e2"]],
        route_width=ROUTE_WIDTH_BIAS_M1,
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    via_m1_tm1.ports["bottom"].orientation = 270
    xr3 = ihp.cells.rhigh(width=RHIGH_WIDTH, length=RHIGH_LENGTH)
    xr3_ref = c.add_ref(xr3).rotate(90)
    xr3_ref.center = via_m1_tm1_ref.center
    xr3_ref.xmin = c3_ref.xmin
    route_xr3 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_m1_tm1_ref.ports["bottom"]],
        ports2=[xr3_ref.ports["e1"]],
        route_width=ROUTE_WIDTH_BIAS_M1,
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    via_m1_tm1 = ihp.cells.via_stack(
        top_layer="TopMetal1",
        bottom_layer="Metal1",
        vn_columns=4,
        vn_rows=3,
        vt1_columns=2,
        vt1_rows=1,
    )
    via_m1_tm1.ports["bottom"].orientation = 0
    via_m1_tm1_ref = c.add_ref(via_m1_tm1)
    via_m1_tm1_ref.connect("bottom", xr3_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    route_c2_bias = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[c3_ref.ports["RC_T_5_1"]],
        ports2=[via_m1_tm1_ref.ports["top"]],
        route_width=max(via_m1_tm1_ref.xsize, via_m1_tm1_ref.ysize),  # manual change to fit width
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # bb_int connect D1 to network
    via_m1_m3 = ihp.cells.via_stack(
        top_layer="Metal3",
        bottom_layer="Metal1",
        vn_columns=6,
        vn_rows=3,
    )
    via_m1_m3.ports["top"].orientation = 90
    via_m1_m3.ports["bottom"].orientation = 270
    via_m1_m3_ref = c.add_ref(via_m1_m3)
    via_m1_m3_ref.connect("bottom", d1_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    # bb_int
    routing_bb_int = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[output_stage_ref.ports["M1_gate_M1_top"]],
        ports2=[via_m1_m3_ref.ports["top"]],
        route_width=ROUTE_WIDTH_GATE,
        layer=ihp.tech.LAYER.Metal3drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        end_straight_length=2,
        auto_taper=False,
        separation=0,
        steps=[
            {"dx": 3.65, "dy": -1},  # strange behavior without the dy direction
            {"dy": -6},
            {"dx": -4, "dy": 0},
        ],
    )

    # bias2 connect D2 to network
    via_m1_m2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=6,
        vn_rows=3,
    )
    via_m1_m2.ports["top"].orientation = 90
    via_m1_m2.ports["bottom"].orientation = 270
    via_m1_m2_ref = c.add_ref(via_m1_m2)
    via_m1_m2_ref.connect("bottom", d2_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    # bias2 connection from gate of M3 to D2
    routing_bias2 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[output_stage_ref.ports["M1_gate_connection_M3"]],
        ports2=[via_m1_m2_ref.ports["top"]],
        route_width=ROUTE_WIDTH_BIAS,
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        end_straight_length=3,
        auto_taper=False,
        separation=0,
        steps=[
            {"dx": 2.46, "dy": -1},  # strange behavior without the dy direction
            {"dy": -1},
            {"dx": 2.17, "dy": 0},
            {"dy": -2},
        ],
    )
    # bias2 connection from gate of M4 to D2
    routing_bias2 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[output_stage_ref.ports["M2_gate_connection_M4"]],
        ports2=[via_m1_m2_ref.ports["top"]],
        route_width=ROUTE_WIDTH_BIAS,
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        end_straight_length=3,
        auto_taper=False,
        separation=0,
        steps=[
            {"dx": -2.46, "dy": -1},  # strange behavior without the dy direction
            {"dy": -1},
            {"dx": -2.21, "dy": 0},
            {"dy": -2},
        ],
    )

    # SBD D1 D2 sub connection
    route_d1_d2 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[d1_ref.ports["e3"]],
        ports2=[d2_ref.ports["e1"]],
        route_width=ROUTE_WIDTH_SBD_SUB,
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    via_m1_m3 = ihp.cells.via_stack(
        top_layer="Metal3",
        bottom_layer="Metal1",
        vn_columns=1,
        vn_rows=5,
    )
    via_m1_m3.ports["bottom"].orientation = 0
    via_m1_m3.ports["top"].orientation = 180
    via_m1_m3_ref = c.add_ref(via_m1_m3)
    via_m1_m3_ref.connect("bottom", d2_ref.ports["e3"], allow_width_mismatch=True, allow_layer_mismatch=True)

    straight_m3 = ihp.cells.straight(
        length=18,
        cross_section="metal3_routing",
        width=max(via_m1_m3_ref.xsize, via_m1_m3_ref.ysize),
    )
    straight_m3_ref = c.add_ref(straight_m3)
    straight_m3_ref.connect("e1", via_m1_m3_ref.ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    via_m3_m5 = ihp.cells.via_stack(
        top_layer="Metal5",
        bottom_layer="Metal3",
        vn_columns=1,
        vn_rows=5,
    )
    via_m3_m5.ports["bottom"].orientation = 180
    via_m3_m5_ref = c.add_ref(via_m3_m5)
    via_m3_m5_ref.connect("bottom", straight_m3_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    schottky.ports["e1"].orientation = 90
    # connect D1 and D2 sub connection together
    schottky.ports["e3"].orientation = 90
    route_sbd_d1_d2 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[d1_ref.ports["e1"]],
        ports2=[d2_ref.ports["e3"]],
        route_width=ROUTE_WIDTH_SBD_GUARD,
        layer=ihp.tech.LAYER.Metal1drawing,
        start_straight_length=2.85,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    straight_m3 = ihp.cells.straight(
        length=10,
        cross_section="metal3_routing",
        width=2,
    )
    straight_m3_ref = c.add_ref(straight_m3)
    straight_m3_ref.connect("e1", output_stage_ref.ports["vref"], allow_width_mismatch=True, allow_layer_mismatch=True)
    # add ports to the powerdetector
    c.add_port(name="vout", port=output_stage_ref.ports["vout"])
    c.ports["vout"].orientation = 90
    c.add_port(name="vref", port=straight_m3_ref.ports["e2"])
    c.ports["vref"].center = (c.ports["vref"].center[0], c.ports["vref"].center[1] - 0.1)  # preventing notch
    c.ports["vref"].orientation = 90
    c.add_port(name="rfin", port=via_tm1_tm2_ref.ports["top"])
    c.ports["rfin"].orientation = 270
    c.add_port(name="vss", port=c3_ref.ports["LC_B_1_1"])
    c.ports["vss"].orientation = 90
    c.add_port(name="vdd", port=c3_ref.ports["LC_T_1_1"])
    c.ports["vdd"].orientation = 0
    c.pprint_ports()

    # No-fill exclusion zones for each metal layer
    c.center = (0, 0)
    c.add_ref(gf.components.rectangle(size=(c.xsize + 2, c.ysize + 2), layer=ihp.tech.LAYER.Activnofill, centered=True))
    for nofill_layer in [
        ihp.tech.LAYER.GatPolynofill,
        ihp.tech.LAYER.Metal1nofill,
        ihp.tech.LAYER.Metal2nofill,
        ihp.tech.LAYER.Metal3nofill,
        ihp.tech.LAYER.Metal4nofill,
    ]:
        c.add_ref(gf.components.rectangle(size=(c.xsize, c.ysize), layer=nofill_layer, centered=True))

    c.add_ref(
        gf.components.rectangle(size=(c1_ref.xsize + 40, c1_ref.ysize + 20), layer=ihp.tech.LAYER.Metal5nofill)
    ).center = c1_ref.center

    size_x = c2_ref.xsize + c3_ref.xsize
    size_y = c2_ref.ysize
    x = c2_ref.xmin + size_x / 2
    y = c2_ref.ymin + size_y / 2
    cap_m5_nofill = c.add_ref(
        gf.components.rectangle(size=(size_x - 10, size_y - 10), layer=ihp.tech.LAYER.Metal5nofill)
    ).center = (x, y)

    return c


# ============================================================
# Design parameters
# ============================================================

e_r = 4.1  # relative permittivity
Z0 = 50  # characteristic impedance
f = FREQUENCY  # frequency (set at top of file)

FREQ_REF = 160e9  # reference frequency for which layout dimensions were optimized
freq_scale = FREQ_REF / FREQUENCY  # >1 when frequency is lower (structures get bigger)


# signal and ground layers
signal_cross_section = "topmetal2_routing"
ground_cross_section = "metal5_routing"

# calculate effective dielectric constant and wavelength
e_eff = ihp.cells.waveguides._calculate_effective_dielectric_constant(
    signal_cross_section=signal_cross_section, ground_cross_section=ground_cross_section, e_r=e_r
)


c0 = scipy.constants.c  # speed of light
wavelength = c0 / f * 1e6 / sqrt(e_eff)  # wavelength
wavelength_4 = wavelength / 4  # quarter wavelength

wavelength = round(wavelength - wavelength % (ihp.tech.nm), 3)  # snap to grid
wavelength_4 = round(wavelength_4 - (wavelength_4 % (ihp.tech.nm)), 3)  # quarter wavelength snap to grid
wavelength_8 = round(wavelength / 8 - (wavelength / 8) % (ihp.tech.nm), 3)  # eighth wavelength snap to grid


# filter parameters
order = 3  # order of the band pass filter
bandwidth = 1e9  # 5% bandwidth for input band pass filter
filter_type = "butter"  # type of the band pass filter, can be "butter", "cheby",
connection_length_bpf = 10  # length of the connection piece between the band pass filter and the rest of the circuit
ripple_dB = 3  # ripple in dB for the cheby filter, ignored if the filter type is Butter

# wilkinson power divider parameters
connection_length_wpd = 0  # length of the connection piece of the wilkinson power divider ports
connection_length_bpf_wpd = (
    wavelength_4 * 3.5 / 5
)  # length of the connection piece between the branch line couplers and the rest of the circuit

# branch line coupler parameters
connection_length_blc = 0  # length of the connection piece between the branch line couplers and the rest of the circuit


# ============================================================
# Six-port network assembly
# ============================================================

blc = ihp.cells.branch_line_coupler(
    frequency=f,
    connection_length=connection_length_blc,
    signal_cross_section=signal_cross_section,
    ground_cross_section=ground_cross_section,
    Z0=Z0,
    e_r=e_r,
)

blc_1_ref = c.add_ref(blc)

blc_2_ref = c.add_ref(blc)

blc_3_ref = c.add_ref(blc)

corner = ihp.cells.tline_corner(
    signal_cross_section=signal_cross_section,
    ground_cross_section=ground_cross_section,
    Z0=Z0 * CORNER_Z_FACTOR,
)

corner_top_ref = c.add_ref(corner)
corner_bot_ref = c.add_ref(corner)

blc_3_ref.center = (0, 0)
corner_top_ref.connect("e1", blc_3_ref.ports["e1"], allow_width_mismatch=True)

blc_1_ref.connect("e4", corner_top_ref.ports["e4"], allow_width_mismatch=True)

corner_bot_ref.connect("e1", blc_3_ref.ports["e4"], allow_width_mismatch=True)

blc_2_ref.connect("e1", corner_bot_ref.ports["e2"], allow_width_mismatch=True)


wpd = ihp.cells.wilkinson_power_divider(
    frequency=f,
    connection_length=connection_length_wpd,
    signal_cross_section=signal_cross_section,
    ground_cross_section=ground_cross_section,
    Z0=Z0,
    e_r=e_r,
    shape="U",
)

wpd.ports["e1"].orientation = 0
wpd_ref = c.add_ref(wpd)


connection_length_wpd_blc_one_leg = (
    blc_1_ref.ports["e1"].center[1]
    - blc_2_ref.ports["e4"].center[1]
    - (wpd_ref.ports["e2"].center[1] - wpd_ref.ports["e3"].center[1])
)


connection_wpd_blc = ihp.cells.tline(
    length=connection_length_wpd_blc_one_leg / 2,
    signal_cross_section=signal_cross_section,
    ground_cross_section=ground_cross_section,
    Z0=Z0,
)

connection_wpd_blc_top_ref = c.add_ref(connection_wpd_blc)
connection_wpd_blc_top_ref.connect("e1", blc_1_ref.ports["e1"])


wpd_ref.connect("e3", connection_wpd_blc_top_ref.ports["e2"])

connection_wpd_blc_bot_ref = c.add_ref(connection_wpd_blc)
connection_wpd_blc_bot_ref.connect("e1", blc_2_ref.ports["e4"])

wpd_ref.connect("e2", connection_wpd_blc_bot_ref.ports["e2"])

connection_bpf_wpd = c.add_ref(
    ihp.cells.tline(
        length=connection_length_bpf_wpd,
        signal_cross_section=signal_cross_section,
        ground_cross_section=ground_cross_section,
        Z0=Z0,
    )
)

connection_bpf_wpd.connect("e1", wpd_ref.ports["e1"])


connection_blc_r_termination = ihp.cells.straight(
    length=round(CONNECTION_LEN_TERM * freq_scale, 3),  # scales with frequency
    cross_section=signal_cross_section,
    width=ihp.cells.waveguides._calculate_width_from_Z0(
        Z0=Z0, e_r=e_r, signal_cross_section=signal_cross_section, ground_cross_section=ground_cross_section
    ),
)
connection_blc_r_termination_ref = c.add_ref(connection_blc_r_termination)
connection_blc_r_termination_ref.connect("e1", blc_3_ref.ports["e3"])

via_m1_tm2 = ihp.cells.via_stack(
    top_layer="TopMetal2",
    bottom_layer="Metal1",
    vn_columns=2,
    vn_rows=2,
    vt1_columns=2,
    vt1_rows=2,
    vt2_columns=1,
    vt2_rows=4,
)
via_m1_tm2.ports["top"].orientation = 180
via_m1_tm2.ports["bottom"].orientation = 180
via_m1_tm2_ref = c.add_ref(via_m1_tm2)
via_m1_tm2_ref.connect("top", connection_blc_r_termination_ref.ports["e2"], allow_width_mismatch=True)

r_termination = ihp.cells.rsil(
    resistance=Z0,
    width=RSIL_WIDTH,
    length=RSIL_LENGTH,
)
r_termination_ref = c.add_ref(r_termination)
r_termination_ref.connect("e1", via_m1_tm2_ref.ports["bottom"], allow_width_mismatch=True, allow_layer_mismatch=True)

via_m1_m5 = ihp.cells.via_stack(
    top_layer="Metal5",
    bottom_layer="Metal1",
    vn_columns=2,
    vn_rows=2,
)
via_m1_m5.ports["top"].orientation = 180
via_m1_m5.ports["bottom"].orientation = 0
via_m1_m5_ref = c.add_ref(via_m1_m5)
via_m1_m5_ref.connect("bottom", r_termination_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

connection_r_termination_vss = ihp.cells.straight(
    length=10,  # manual measurement to fit the design
    cross_section=ground_cross_section,
    width=2,  # manual measurement to fit the design
)
connection_r_termination_vss_ref = c.add_ref(connection_r_termination_vss)
connection_r_termination_vss_ref.connect(
    "e1", via_m1_m5_ref.ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True
)

# R-termination Metal5 nofill
c.add_ref(
    gf.components.rectangle(
        size=(connection_r_termination_vss_ref.xsize + 20, connection_r_termination_vss_ref.ysize + 20),
        layer=ihp.tech.LAYER.Metal5nofill,
    )
).center = connection_r_termination_vss_ref.center

bandpass_filter = c.add_ref(
    ihp.cells.hairpin_coupled_line_bandpass_filter(
        frequency=f,
        bandwidth=bandwidth,
        order=order,
        filter_type=filter_type,
        ripple_dB=ripple_dB,
        connection_length=connection_length_bpf,
        signal_cross_section=signal_cross_section,
        ground_cross_section=ground_cross_section,
        Z0=Z0,
        e_r=e_r,
    )
)

bandpass_filter.connect("e1", connection_bpf_wpd.ports["e2"])

connection_bpd_pad = c.add_ref(
    ihp.cells.straight(
        length=round(CONNECTION_LEN_BPF_PAD * freq_scale, 3),  # scales with frequency
        cross_section=signal_cross_section,
        width=ihp.cells.waveguides._calculate_width_from_Z0(
            Z0=Z0, e_r=e_r, signal_cross_section=signal_cross_section, ground_cross_section=ground_cross_section
        ),
    )
)
connection_bpd_pad.connect("e1", bandpass_filter.ports["e2"], allow_width_mismatch=True)


# probe pads left
probe_left = c.add_ref(
    ihp.cells.bondpad_array(
        config="GSG",
        pitch=PROBE_PITCH,
        width_ground=PROBE_GROUND_WIDTH,
        width_signal=PROBE_SIGNAL_SIZE,
        length_signal=PROBE_SIGNAL_SIZE,
        signal_cross_section="topmetal1_routing",
        ground_cross_section="metal1_routing",
        ground_connection="psub",
    )
).rotate(-90)
probe_left.center = bandpass_filter.ports["e2"].center
probe_left.xmax = bandpass_filter.ports["e2"].center[0] - 15
probe_left.connect("e1", connection_bpd_pad.ports["e2"], allow_width_mismatch=True)

c.add_ref(
    gf.components.rectangle(size=(NOFILL_GSG_SIZE, NOFILL_GSG_SIZE), layer=ihp.tech.LAYER.Metal5nofill)
).center = probe_left.center


connection_blc_pad = c.add_ref(
    ihp.cells.straight(
        length=round(
            CONNECTION_LEN_BLC_PAD * freq_scale + CONNECTION_LEN_BLC_EXTRA, 3
        ),  # scales with frequency + extra pad clearance
        cross_section=signal_cross_section,
        width=ihp.cells.waveguides._calculate_width_from_Z0(
            Z0=Z0, e_r=e_r, signal_cross_section=signal_cross_section, ground_cross_section=ground_cross_section
        ),
    )
)
connection_blc_pad.connect("e1", blc_3_ref.ports["e2"])

# probe pads right
probe_right = c.add_ref(
    ihp.cells.bondpad_array(
        config="GSG",
        pitch=PROBE_PITCH,
        width_ground=PROBE_GROUND_WIDTH_RIGHT,
        width_signal=PROBE_SIGNAL_SIZE,
        length_signal=PROBE_SIGNAL_SIZE,
        signal_cross_section="topmetal1_routing",
        ground_cross_section="metal1_routing",
        ground_connection="psub",
    )
).rotate(-90)
probe_right.connect("e1", connection_blc_pad.ports["e2"], allow_width_mismatch=True)

c.add_ref(
    gf.components.rectangle(size=(NOFILL_GSG_SIZE, NOFILL_GSG_SIZE), layer=ihp.tech.LAYER.Metal5nofill)
).center = probe_right.center


# ============================================================
# Power detector positioning and probe pad placement
# ============================================================

# Compute PD positions so rfin aligns straight with BLC ports.
# Place each PD so its rfin port is directly above/below the BLC port,
# with only a short straight gap (rfin_gap) in between.
rfin_gap = RFIN_GAP  # straight T-line gap between BLC port and PD rfin port

# create powerdetector (needed here to read rfin port offset)
pd = powdet_sbd()

# rfin port offset from PD center (in the un-mirrored PD cell)
rfin_offset_x = pd.ports["rfin"].center[0] - pd.center[0]
rfin_offset_y = pd.ports["rfin"].center[1] - pd.center[1]

# PD1: connected to blc_1 e2 (top side, PD above BLC → rfin points down)
# PD1 is un-mirrored, rfin orientation=270 (pointing down)
blc1_e2 = blc_1_ref.ports["e2"].center
pd1_center = (blc1_e2[0] - rfin_offset_x, blc1_e2[1] + rfin_gap - rfin_offset_y)

# PD2: connected to blc_1 e3 (top side, mirrored_x → rfin_offset_x flips sign)
blc1_e3 = blc_1_ref.ports["e3"].center
pd2_center = (blc1_e3[0] + rfin_offset_x, blc1_e3[1] + rfin_gap - rfin_offset_y)

# PD3: connected to blc_2 e3 (bottom side, mirrored_y → rfin_offset_y flips sign)
blc2_e3 = blc_2_ref.ports["e3"].center
pd3_center = (blc2_e3[0] - rfin_offset_x, blc2_e3[1] - rfin_gap + rfin_offset_y)

# PD4: connected to blc_2 e2 (bottom side, mirrored_x + mirrored_y → both flip)
blc2_e2 = blc_2_ref.ports["e2"].center
pd4_center = (blc2_e2[0] + rfin_offset_x, blc2_e2[1] - rfin_gap + rfin_offset_y)

print(f"PD centers: PD1={pd1_center}, PD2={pd2_center}, PD3={pd3_center}, PD4={pd4_center}")

# probe pads top — positioned to clear PD extent
pd_half_height = PD_HALF_HEIGHT  # approximate half-height of power detector cell
probe_pd_gap = PROBE_PD_GAP  # gap between PD edge and probe edge
chip_center = c.center
probe_top = c.add_ref(
    ihp.cells.bondpad_array(
        config="SSGSGSS",
        signal_cross_section="topmetal1_routing",
        ground_cross_section="metal1_routing",
        ground_connection="psub",
    )
)
probe_top.center = chip_center
probe_top.ymax = max(pd1_center[1], pd2_center[1]) + pd_half_height + probe_pd_gap

# no fill VDD
c.add_ref(
    gf.components.rectangle(size=(NOFILL_VDD_SIZE, NOFILL_VDD_SIZE), layer=ihp.tech.LAYER.Metal5nofill)
).center = probe_top.center

# no fill top
no_fill_top_left = c.add_ref(
    gf.components.rectangle(size=(NOFILL_SIDE_WIDTH, NOFILL_VDD_SIZE), layer=ihp.tech.LAYER.Metal5nofill)
)
no_fill_top_left.xmin = probe_top.xmin - NOFILL_SIDE_OFFSET
no_fill_top_left.ymin = probe_top.ymin - NOFILL_SIDE_OFFSET

no_fill_top_right = c.add_ref(
    gf.components.rectangle(size=(NOFILL_SIDE_WIDTH, NOFILL_VDD_SIZE), layer=ihp.tech.LAYER.Metal5nofill)
)
no_fill_top_right.xmax = probe_top.xmax + NOFILL_SIDE_OFFSET
no_fill_top_right.ymin = probe_top.ymin - NOFILL_SIDE_OFFSET


# probe pads bottom
probe_bottom = c.add_ref(
    ihp.cells.bondpad_array(
        config="SSGSGSS",
        signal_cross_section="topmetal1_routing",
        ground_cross_section="metal1_routing",
        ground_connection="psub",
    )
).rotate(180)
probe_bottom.center = chip_center
probe_bottom.ymin = min(pd3_center[1], pd4_center[1]) - pd_half_height - probe_pd_gap

# no fill VDD
c.add_ref(
    gf.components.rectangle(size=(NOFILL_VDD_SIZE, NOFILL_VDD_SIZE), layer=ihp.tech.LAYER.Metal5nofill)
).center = probe_bottom.center

# no fill bottom
no_fill_bottom_left = c.add_ref(
    gf.components.rectangle(size=(NOFILL_SIDE_WIDTH, NOFILL_VDD_SIZE), layer=ihp.tech.LAYER.Metal5nofill)
)
no_fill_bottom_left.xmin = probe_bottom.xmin - NOFILL_SIDE_OFFSET
no_fill_bottom_left.ymin = probe_bottom.ymin - NOFILL_SIDE_OFFSET

no_fill_bottom_right = c.add_ref(
    gf.components.rectangle(size=(NOFILL_SIDE_WIDTH, NOFILL_VDD_SIZE), layer=ihp.tech.LAYER.Metal5nofill)
)
no_fill_bottom_right.xmax = probe_bottom.xmax + NOFILL_SIDE_OFFSET
no_fill_bottom_right.ymin = probe_bottom.ymin - NOFILL_SIDE_OFFSET

print(c.xsize, c.ysize)

freq_ghz = int(FREQUENCY / 1e9)
gds_filename = f"Six-Port/RFFE6027_{freq_ghz}GHz.gds"


pd.write_gds("Six-Port/powdet_sbd.gds")

# ============================================================
# Power detector instances and routing
# ============================================================

# PD1 reference, position and route
pd1_ref = c.add_ref(pd)
pd1_ref.center = pd1_center


# vdd connection of pd1 to probe top
route_pd1_vdd = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd1_ref.ports["vdd"]],
    ports2=[probe_top.ports["e4"]],
    route_width=ROUTE_WIDTH_VDD,
    layer=ihp.tech.LAYER.TopMetal1drawing,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vss connection of pd1 to probe top
route_pd1_vss = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd1_ref.ports["vss"]],
    ports2=[probe_top.ports["e3"]],
    route_width=ROUTE_WIDTH_VSS,
    layer=ihp.tech.LAYER.Metal5drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# vout connection of pd1 to probe top
via_m4_tm1 = ihp.cells.via_stack(
    top_layer="TopMetal1",
    bottom_layer="Metal4",
    vn_columns=10,
    vn_rows=3,
    vt1_columns=5,
    vt1_rows=1,
)
via_m4_tm1.ports["top"].orientation = 90
via_m4_tm1.ports["bottom"].orientation = 270
via_m4_tm1_ref = c.add_ref(via_m4_tm1)
via_m4_tm1_ref.connect("top", probe_top.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_m4_tm1_ref.move((0, via_m4_tm1_ref.ysize / 2))
route_pd1_vout = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd1_ref.ports["vout"]],
    ports2=[via_m4_tm1_ref.ports["bottom"]],
    route_width=ROUTE_WIDTH_SIGNAL,
    layer=ihp.tech.LAYER.Metal4drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# vref connection of pd1 to probe top
via_m3_tm1 = ihp.cells.via_stack(
    top_layer="TopMetal1",
    bottom_layer="Metal3",
    vn_columns=10,
    vn_rows=3,
    vt1_columns=5,
    vt1_rows=1,
)
via_m3_tm1.ports["top"].orientation = 90
via_m3_tm1.ports["bottom"].orientation = 270
via_m3_tm1_ref = c.add_ref(via_m3_tm1)
via_m3_tm1_ref.connect("top", probe_top.ports["e1"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_m3_tm1_ref.move((0, via_m3_tm1_ref.ysize / 2))
route_pd1_vref = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd1_ref.ports["vref"]],
    ports2=[via_m3_tm1_ref.ports["bottom"]],
    route_width=ROUTE_WIDTH_SIGNAL,
    layer=ihp.tech.LAYER.Metal3drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# rfin connection of pd1 to blc — straight connection
rfin_connection_pd1 = c.add_ref(
    ihp.cells.straight(
        length=rfin_gap,
        cross_section=signal_cross_section,
        width=blc_1_ref.ports["e2"].width,
    )
)
rfin_connection_pd1.connect("e1", blc_1_ref.ports["e2"], allow_width_mismatch=True)


# PD2 reference, position and route
pd2_ref = c.add_ref(pd).mirror_x()
pd2_ref.center = pd2_center

# vdd connection of pd2 to probe top
route_pd2_vdd = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd2_ref.ports["vdd"]],
    ports2=[probe_top.ports["e4"]],
    route_width=ROUTE_WIDTH_VDD,
    layer=ihp.tech.LAYER.TopMetal1drawing,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vss connection of pd2 to probe top
route_pd2_vss = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd2_ref.ports["vss"]],
    ports2=[probe_top.ports["e5"]],
    route_width=ROUTE_WIDTH_VSS,
    layer=ihp.tech.LAYER.Metal5drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vout connection of pd2 to probe top
via_m4_tm1_ref = c.add_ref(via_m4_tm1)
via_m4_tm1_ref.connect("top", probe_top.ports["e6"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_m4_tm1_ref.move((0, via_m4_tm1_ref.ysize / 2))
route_pd2_vout = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd2_ref.ports["vout"]],
    ports2=[via_m4_tm1_ref.ports["bottom"]],
    route_width=ROUTE_WIDTH_SIGNAL,
    layer=ihp.tech.LAYER.Metal4drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vref connection of pd2 to probe top
via_m3_tm1_ref = c.add_ref(via_m3_tm1)
via_m3_tm1_ref.connect("top", probe_top.ports["e7"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_m3_tm1_ref.move((0, via_m3_tm1_ref.ysize / 2))
route_pd2_vref = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd2_ref.ports["vref"]],
    ports2=[via_m3_tm1_ref.ports["bottom"]],
    route_width=ROUTE_WIDTH_SIGNAL,
    layer=ihp.tech.LAYER.Metal3drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# rfin connection of pd2 to blc — straight connection
rfin_connection_pd2 = c.add_ref(
    ihp.cells.straight(
        length=rfin_gap,
        cross_section=signal_cross_section,
        width=blc_1_ref.ports["e3"].width,
    )
)
rfin_connection_pd2.connect("e1", blc_1_ref.ports["e3"], allow_width_mismatch=True)

# PD3 reference, position and route
pd3_ref = c.add_ref(pd).mirror_y()
pd3_ref.center = pd3_center

# vdd connection of pd3 to probe bottom
route_pd3_vdd = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd3_ref.ports["vdd"]],
    ports2=[probe_bottom.ports["e4"]],
    route_width=ROUTE_WIDTH_VDD,
    layer=ihp.tech.LAYER.TopMetal1drawing,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vss connection of pd3 to probe bottom
route_pd3_vss = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd3_ref.ports["vss"]],
    ports2=[probe_bottom.ports["e5"]],
    route_width=ROUTE_WIDTH_VSS,
    layer=ihp.tech.LAYER.Metal5drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vout connection of pd3 to probe bottom
via_m4_tm1_ref = c.add_ref(via_m4_tm1)
via_m4_tm1_ref.connect("top", probe_bottom.ports["e6"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_m4_tm1_ref.move((0, -via_m4_tm1_ref.ysize / 2))

route_pd3_vout = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd3_ref.ports["vout"]],
    ports2=[via_m4_tm1_ref.ports["bottom"]],
    route_width=ROUTE_WIDTH_SIGNAL,
    layer=ihp.tech.LAYER.Metal4drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vref connection of pd3 to probe bottom
via_m3_tm1_ref = c.add_ref(via_m3_tm1)
via_m3_tm1_ref.connect("top", probe_bottom.ports["e7"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_m3_tm1_ref.move((0, -via_m3_tm1_ref.ysize / 2))
route_pd3_vref = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd3_ref.ports["vref"]],
    ports2=[via_m3_tm1_ref.ports["bottom"]],
    route_width=ROUTE_WIDTH_SIGNAL,
    layer=ihp.tech.LAYER.Metal3drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# rfin connection of pd3 to blc — straight connection
rfin_connection_pd3 = c.add_ref(
    ihp.cells.straight(
        length=rfin_gap,
        cross_section=signal_cross_section,
        width=blc_2_ref.ports["e3"].width,
    )
)
rfin_connection_pd3.connect("e1", blc_2_ref.ports["e3"], allow_width_mismatch=True)


# PD4 reference, position and route
pd4_ref = c.add_ref(pd).mirror_x().mirror_y()
pd4_ref.center = pd4_center

# vdd connection of pd4 to probe bottom
route_pd4_vdd = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd4_ref.ports["vdd"]],
    ports2=[probe_bottom.ports["e4"]],
    route_width=ROUTE_WIDTH_VDD,
    layer=ihp.tech.LAYER.TopMetal1drawing,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vss connection of pd4 to probe bottom
route_pd4_vss = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd4_ref.ports["vss"]],
    ports2=[probe_bottom.ports["e3"]],
    route_width=ROUTE_WIDTH_VSS,
    layer=ihp.tech.LAYER.Metal5drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vout connection of pd4 to probe bottom
via_m4_tm1_ref = c.add_ref(via_m4_tm1)
via_m4_tm1_ref.connect("top", probe_bottom.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_m4_tm1_ref.move((0, -via_m4_tm1_ref.ysize / 2))
route_pd4_vout = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd4_ref.ports["vout"]],
    ports2=[via_m4_tm1_ref.ports["bottom"]],
    route_width=ROUTE_WIDTH_SIGNAL,
    layer=ihp.tech.LAYER.Metal4drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vref connection of pd4 to probe bottom
via_m3_tm1_ref = c.add_ref(via_m3_tm1)
via_m3_tm1_ref.connect("top", probe_bottom.ports["e1"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_m3_tm1_ref.move((0, -via_m3_tm1_ref.ysize / 2))
route_pd4_vref = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd4_ref.ports["vref"]],
    ports2=[via_m3_tm1_ref.ports["bottom"]],
    route_width=ROUTE_WIDTH_SIGNAL,
    layer=ihp.tech.LAYER.Metal3drawing,
    start_straight_length=ROUTE_MIN_STRAIGHT,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# rfin connection of pd4 to blc — straight connection
rfin_connection_pd4 = c.add_ref(
    ihp.cells.straight(
        length=rfin_gap,
        cross_section=signal_cross_section,
        width=blc_2_ref.ports["e2"].width,
    )
)
rfin_connection_pd4.connect("e1", blc_2_ref.ports["e2"], allow_width_mismatch=True)


# ============================================================
# Sealring, logo, and metal fill
# ============================================================

sealring_margin = SEALRING_MARGIN  # margin around circuit for sealring
sealring_width = round(c.xsize + 2 * sealring_margin)
sealring_height = round(c.ysize + 2 * sealring_margin)
print(f"Sealring: {sealring_width} x {sealring_height} um (freq_scale={freq_scale:.2f})")
sealring_center = c.center  # save before adding more refs
c.add_ref(ihp.cells.sealring(width=sealring_width, height=sealring_height)).center = sealring_center

# JKU logo — lower right corner, relative to right chip edge, just above south pads
jku_logo = gf.import_gds(str(Path(__file__).parent / "assets" / "jku_logo_m5.gds"))
jku_logo_ref = c.add_ref(jku_logo)
chip_right = sealring_center[0] + sealring_width / 2
jku_logo_ref.xmax = chip_right - sealring_margin
jku_logo_ref.ymin = probe_bottom.ymax + 10


if do_fill:
    # active/gat poly fill
    gatpoly_activ_fill_space = 1
    c.fill(
        fill_cell=fill_gat_active(size=(3, 3)),
        fill_layers=[(ihp.tech.LAYER.EdgeSealboundary, -50)],
        exclude_layers=[
            (ihp.tech.LAYER.Activdrawing, 1.1),
            (ihp.tech.LAYER.pSDdrawing, 1.1),
            (ihp.tech.LAYER.nSDblock, 1.1),
            (ihp.tech.LAYER.SalBlockdrawing, 1.1),
            (ihp.tech.LAYER.NWelldrawing, 1.1),
            (ihp.tech.LAYER.nBuLaydrawing, 1.1),
            (ihp.tech.LAYER.PWellblock, 1.5),
            (ihp.tech.LAYER.GatPolydrawing, 2),
            (ihp.tech.LAYER.Contdrawing, 1.2),
            (ihp.tech.LAYER.Passivdrawing, 12),
            (ihp.tech.LAYER.GatPolynofill, 1),
            (ihp.tech.LAYER.Activnofill, 1),
        ],
        x_space=gatpoly_activ_fill_space,
        y_space=gatpoly_activ_fill_space,
    )
    # metal1 fill
    metal_fill_space = 1
    c.fill(
        fill_cell=fill_cell(layer=ihp.tech.LAYER.Metal1filler),
        fill_layers=[(ihp.tech.LAYER.EdgeSealboundary, -50)],
        exclude_layers=[
            (ihp.tech.LAYER.Metal1drawing, 10),
            (ihp.tech.LAYER.Passivdrawing, 10),
            (ihp.tech.LAYER.Metal1nofill, 1),
        ],
        x_space=metal_fill_space,
        y_space=metal_fill_space,
    )
    # metal2 fill
    c.fill(
        fill_cell=fill_cell(layer=ihp.tech.LAYER.Metal2filler),
        fill_layers=[(ihp.tech.LAYER.EdgeSealboundary, -50)],
        exclude_layers=[
            (ihp.tech.LAYER.Metal2drawing, 10),
            (ihp.tech.LAYER.Passivdrawing, 10),
            (ihp.tech.LAYER.Metal2nofill, 1),
        ],
        x_space=metal_fill_space,
        y_space=metal_fill_space,
    )
    # metal3 fill
    c.fill(
        fill_cell=fill_cell(layer=ihp.tech.LAYER.Metal3filler),
        fill_layers=[(ihp.tech.LAYER.EdgeSealboundary, -50)],
        exclude_layers=[
            (ihp.tech.LAYER.Metal3drawing, 10),
            (ihp.tech.LAYER.Passivdrawing, 10),
            (ihp.tech.LAYER.Metal3nofill, 1),
        ],
        x_space=metal_fill_space,
        y_space=metal_fill_space,
    )
    # metal4 fill
    c.fill(
        fill_cell=fill_cell(layer=ihp.tech.LAYER.Metal4filler),
        fill_layers=[(ihp.tech.LAYER.EdgeSealboundary, -50)],
        exclude_layers=[
            (ihp.tech.LAYER.Metal4drawing, 10),
            (ihp.tech.LAYER.Passivdrawing, 10),
            (ihp.tech.LAYER.Metal4nofill, 1),
        ],
        x_space=metal_fill_space,
        y_space=metal_fill_space,
    )

if do_fill_m5:
    # metal5 fill (groundplate)
    c.fill(
        fill_cell=fill_ground(),
        fill_layers=[(ihp.tech.LAYER.EdgeSealboundary, -50)],
        exclude_layers=[(ihp.tech.LAYER.Passivdrawing, 0), (ihp.tech.LAYER.Metal5nofill, 0)],
        x_space=0,
        y_space=0,
    )
    c.fill(
        fill_cell=slit_ground(),
        fill_layers=[(ihp.tech.LAYER.Metal5drawing, -2)],
        exclude_layers=[
            (ihp.tech.LAYER.TopMetal2drawing, 5),
            (ihp.tech.LAYER.MIMdrawing, 1),
            (ihp.tech.LAYER.Metal5slit, 1),
        ],
        x_space=1.1,
        y_space=1.2,
    )

if do_fill:
    # topmetal1 fill
    c.fill(
        fill_cell=fill_cell(layer=ihp.tech.LAYER.TopMetal1filler, size=(9, 9)),
        fill_layers=[(ihp.tech.LAYER.EdgeSealboundary, -50)],
        exclude_layers=[(ihp.tech.LAYER.TopMetal1drawing, 10), (ihp.tech.LAYER.TopMetal2drawing, 20)],
        x_space=3,
        y_space=3,
    )

if do_fill:
    # topmetal2 fill
    c.fill(
        fill_cell=fill_cell(layer=ihp.tech.LAYER.TopMetal2filler, size=(9, 9)),
        fill_layers=[(ihp.tech.LAYER.EdgeSealboundary, -50)],
        exclude_layers=[(ihp.tech.LAYER.TopMetal2drawing, 20)],
        x_space=3,
        y_space=3,
    )

c.xmin = 0
c.ymin = 0
c.move((-25, -25))

c.write_gds(gds_filename)
c.show()
