import gdsfactory as gf
import ihp
from pathlib import Path

import scipy
from math import sqrt
import klayout.db as kdb

import make_gds

ihp.PDK.activate()


# flag for filling, makes the design laggy in klayout
fill = 1
fill_M5 = 1

c = gf.Component("sparx160_top")

@gf.cell
def fill_cell(layer = ihp.tech.LAYER.Metal5slit, size=(3,3)) -> gf.Component:
    c = gf.Component()
    c << gf.c.rectangle(layer=layer, size=size)
    return c

@gf.cell
def fill_gat_active(size=(3,3), active_extension=(0.18,0.18)) -> gf.Component:
    c = gf.Component()
    gat_ref = c.add_ref(gf.c.rectangle(layer=ihp.tech.LAYER.GatPolyfiller, size=size))
    activ_ref = c.add_ref(gf.c.rectangle(layer=ihp.tech.LAYER.Activfiller, size=(size[0] + 2*active_extension[0], size[1] + 2*active_extension[1])))
    activ_ref.center = gat_ref.center
    return c

@gf.cell
def fill_ground() -> gf.Component:
    c = gf.Component()
    c.add_polygon(layer=ihp.tech.LAYER.Metal5drawing, points=[
        # (0,0),  # used for L
        # (5,0),  # used for L
        # (5,1),  # used for L
        # (1,1),  # used for L
        # (1,5),  # used for L
        # (0,5),  # used for L
        (0,0),
        (1,0),
        (1,1),
        (0,1)
        ])
    return c

@gf.cell
def slit_ground() -> gf.Component:
    c = gf.Component()
    c.add_polygon(layer=ihp.tech.LAYER.Metal5slit, points=[
        (1.1,1.1),
        (4,1.1),
        (4,4.1),
        (1.1,4.1)])
    return c

@gf.cell
def power_detector_hbt() -> gf.Component:
    c = gf.Component("power_detector_hbt")
    via_TM1_TM2 = c.add_ref(ihp.cells.via_stack(
        top_layer="TopMetal2",
        bottom_layer="TopMetal1",
        vt2_columns=2,
        vt2_rows=2,
    ))
    cmim = ihp.cells.cmim(width=10, length=10)
    C1_ref = c.add_ref(cmim)
    C1_ref.connect("T", via_TM1_TM2.ports["bottom"], allow_width_mismatch=True)
    
    
    # via cell from Metal1 to Metal5
    via_M1_M5 = ihp.cells.via_stack(
        top_layer="Metal5",
        bottom_layer="Metal1",
        vn_columns=6,
        vn_rows=1,
    )
    
    
    # via from CMIM C1 to XQ1
    via_M1_M5.ports["top"].orientation +=90
    via_M1_M5.ports["bottom"].orientation +=90
    via_M1_M5_ref = c.add_ref(via_M1_M5)
    via_M1_M5_ref.connect("top", C1_ref.ports["B"], allow_width_mismatch=True)
    
    # npn13G2 cell, to be used for references when this transistor is needed
    XQx = ihp.cells.npn13G2()
    
    
    XQx.ports["C"].orientation = 270
    XQ1_ref = c.add_ref(XQx)
    XQ1_ref.connect("B", via_M1_M5.ports["bottom"], allow_width_mismatch=True, allow_layer_mismatch=True)
    # c.add_ports(XQ1_ref.ports, prefix="XQ1_")
    
    via_M1_M2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=6,
        vn_rows=1,
    )
    
    via_M1_M2.ports["top"].orientation = 180
    via_M1_M2_ref = c.add_ref(via_M1_M2)
    via_M1_M2_ref.connect("bottom", XQ1_ref.ports["C"], allow_width_mismatch=True, allow_layer_mismatch=True)

    
    XQx.ports["E"].orientation = 180
    XQx.ports["C"].orientation = 0
    XQ2_ref = c.add_ref(XQx)
    XQ2_ref.center = XQ1_ref.center
    XQ2_ref.xmin = XQ1_ref.xmax +0.31 #min spacing vor pSD 5.10
    
    
    # distance between port centers of the two devices
    distancex = abs(via_M1_M2_ref.ports["top"].center[0] - XQ2_ref.ports["E"].center[0])
    
    route1 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_M1_M2_ref.ports["top"]],
        ports2=[XQ2_ref.ports["E"]],
        route_width=0.2,    # min width for metal2
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        auto_taper=False,
        separation=0,
        start_straight_length=distancex/2-0.1, # half the distance minus half the width
    )
    
    cmim.ports["T"].orientation = 0
    C2_ref = c.add_ref(cmim)
    C2_ref.center = C1_ref.center
    C2_ref.xmin = C1_ref.xmax +0.24 # min spacing according to design rules 5.17
    
    
    connection = c.add_ref(ihp.cells.straight(length=7, cross_section="topmetal1_routing", width=1.64)) # min width TM1
    connection.connect("e1", C2_ref.ports["T"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    via_M2_TM1 = ihp.cells.via_stack(
        top_layer="TopMetal1",
        bottom_layer="Metal2",
        vn_columns=2,
        vn_rows=4,
        vt1_columns=1,
        vt1_rows=2
    )   
    
    via_M2_TM1.ports["top"].orientation = 90
    via_M2_TM1.ports["bottom"].orientation = 90
    via_M2_TM1_ref = c.add_ref(via_M2_TM1)
    via_M2_TM1_ref.connect("top", connection.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
       
    
    route2 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_M2_TM1_ref.ports["bottom"]],
        ports2=[XQ2_ref.ports["E"]],
        layer=ihp.tech.LAYER.Metal2drawing,
        route_width=0.2,    # min width for metal2
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0, 
    )
    
    
    XR1 = ihp.cells.rppd(width=0.5, length=1)
    XR1.ports["e2"].orientation = 180
    XR1_ref = c.add_ref(XR1)
    XR1_ref.xmin = XQ2_ref.xmax+0.31 # min spacing according to design rules 5.10
    XR1_ref.movey((XQ2_ref.ports["C"].center[1] - XR1_ref.ports["e2"].center[1]))
    
    route4 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[XQ2_ref.ports["C"]],
        ports2=[XR1_ref.ports["e2"]],
        route_width=0.2,    # min width for metal1
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )    
    
    C3_ref = c.add_ref(cmim)
    C3_ref.center = C1_ref.center
    C3_ref.ymin = C1_ref.ymax + 0.24 # min spacing according to design rules 5.17
    
    cmim.ports["T"].orientation = 0
    cmim.ports["B"].orientation = 180 # change port direction
    C4_ref = c.add_ref(cmim)
    C4_ref.center = C2_ref.center
    C4_ref.ymin = C2_ref.ymax + 0.24 # min spacing according to design rules 5.17
    
    XQx.ports["C"].orientation = 270
    XQ3_ref = c.add_ref(XQx)
    XQ3_ref.center = XQ1_ref.center
    XQ3_ref.ymin = XQ1_ref.ymax + 0.31 # min spacing according to design rules 5.10
    
    XQx.ports["C"].orientation = 0
    XQ4_ref = c.add_ref(XQx)
    XQ4_ref.center = XQ2_ref.center
    XQ4_ref.ymin = XQ2_ref.ymax + 0.31 # min spacing according to design rules 5.10
    
    route3 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[XQ1_ref.ports["B"]],
        ports2=[XQ3_ref.ports["B"]],
        route_width=0.2,    # min width for metal1
        layer=ihp.tech.LAYER.Metal1drawing,
        start_straight_length=3,
        allow_layer_mismatch=True,
        auto_taper=False,
        separation=0,
    )   
    
    # via for XQ3 to get to M2
    via_M1_M2.ports["bottom"].orientation = 0
    via_M1_M2_ref = c.add_ref(via_M1_M2)
    via_M1_M2_ref.connect("bottom", XQ3_ref.ports["C"], allow_width_mismatch=True, allow_layer_mismatch=True)
   
    
    # distance between port centers of the two devices
    distancex = abs(via_M1_M2_ref.ports["top"].center[0] - XQ2_ref.ports["E"].center[0])
    
    route5 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_M1_M2_ref.ports["top"]],
        ports2=[XQ4_ref.ports["E"]],
        route_width=0.2,    # min width for metal2
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        auto_taper=False,
        separation=0,
        start_straight_length=distancex/2-0.1, # half the distance minus half the width
    )
    
    route6 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[XQ2_ref.ports["B"]],
        ports2=[XQ4_ref.ports["B"]],
        route_width=0.2,    # min width for metal1
        layer=ihp.tech.LAYER.Metal1drawing,
        start_straight_length=3,
        allow_layer_mismatch=True,
        auto_taper=False,
        separation=0,
    ) 
    
    connection = c.add_ref(ihp.cells.straight(length=7, cross_section="topmetal1_routing", width=1.64)) # min width TM1
    connection.connect("e1", C4_ref.ports["T"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    via_M2_TM1.ports["top"].orientation = 270
    via_M2_TM1.ports["bottom"].orientation = 270
    via_M2_TM1_ref = c.add_ref(via_M2_TM1)
    via_M2_TM1_ref.connect("top", connection.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
       
    
    route7 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_M2_TM1_ref.ports["bottom"]],
        ports2=[XQ4_ref.ports["E"]],
        layer=ihp.tech.LAYER.Metal2drawing,
        route_width=0.2,    # min width for metal2
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0, 
    )
    
    XR3 = ihp.cells.rppd(width=0.5, length=1)
    XR3.ports["e1"].orientation = 180
    XR3_ref = c.add_ref(XR1)
    XR3_ref.xmin = XQ4_ref.xmax+0.31 # min spacing according to design rules 5.10
    XR3_ref.movey((XQ4_ref.ports["C"].center[1] - XR3_ref.ports["e1"].center[1]))
    
    route8 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[XQ4_ref.ports["C"]],
        ports2=[XR3_ref.ports["e1"]],
        route_width=0.2,    # min width for metal1
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )    
    
    via_M1_M5_ref = c.add_ref(via_M1_M5)
    via_M1_M5_ref.connect("bottom", XQ3_ref.ports["B"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    
    # create capasitor array for caps 5 and 6
    C5_6 = gf.Component("C5_6")
    bottom_row = C5_6.add_ref(gf.components.array(component=cmim, columns=6, rows=1, column_pitch= 0.24 + 11.2))
    top_row = C5_6.add_ref(gf.components.array(component=cmim, columns=4, rows=1, column_pitch= 0.24 + 11.2))
    top_row.ymin = bottom_row.ymax + 0.24 # min spacing according to design rules 5.17
    C5_6.add_ports(bottom_row.ports, prefix="BR_")
    C5_6.add_ports(top_row.ports, prefix="TR_")
    
    # orient the outer most port of top and bottom row to look inward to make a horizontal connection between each cap
    C5_6.ports["BR_T_1_1"].orientation = 0
    C5_6.ports["TR_T_1_1"].orientation = 0
    C5_6.ports["BR_B_1_1"].orientation = 0
    C5_6.ports["TR_B_1_1"].orientation = 0
    C5_6.ports["BR_T_1_6"].orientation = 180
    C5_6.ports["TR_T_1_4"].orientation = 180
    C5_6.ports["BR_B_1_6"].orientation = 180
    C5_6.ports["TR_B_1_4"].orientation = 180
        
    C5_6_connection_T = gf.routing.route_bundle_electrical(
        component=C5_6,
        ports1=[C5_6.ports["BR_T_1_6"], C5_6.ports["TR_T_1_4"]],
        ports2=[C5_6.ports["BR_T_1_1"], C5_6.ports["TR_T_1_1"]],
        route_width=2,    # min width for metal1
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    C5_6_connection_B = gf.routing.route_bundle_electrical(
        component=C5_6,
        ports1=[C5_6.ports["BR_B_1_6"], C5_6.ports["TR_B_1_4"]],
        ports2=[C5_6.ports["BR_B_1_1"], C5_6.ports["TR_B_1_1"]],
        route_width=2,    # min width for metal1
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    # orient top row ports to face downwards to connect to bottom row ports
    ihp.cells.utils.change_port_orientation(C5_6, ["TR_T_1_1", "TR_T_1_2", "TR_T_1_3", "TR_T_1_4"], 270)
    ihp.cells.utils.change_port_orientation(C5_6, ["TR_B_1_1", "TR_B_1_2", "TR_B_1_3", "TR_B_1_4"], 270)
    
    # orient bottom row ports to face upwards to connect to top row ports
    ihp.cells.utils.change_port_orientation(C5_6, ["BR_T_1_1", "BR_T_1_2", "BR_T_1_3", "BR_T_1_4"], 90)
    ihp.cells.utils.change_port_orientation(C5_6, ["BR_B_1_1", "BR_B_1_2", "BR_B_1_3", "BR_B_1_4"], 90)
    
    C5_6_connection_top = gf.routing.route_bundle_electrical(
        component=C5_6,
        ports1=[C5_6.ports["BR_T_1_1"], C5_6.ports["BR_T_1_2"], C5_6.ports["BR_T_1_3"], C5_6.ports["BR_T_1_4"]],
        ports2=[C5_6.ports["TR_T_1_1"], C5_6.ports["TR_T_1_2"], C5_6.ports["TR_T_1_3"], C5_6.ports["TR_T_1_4"]],
        route_width=2,    # adjust for thicker connections
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    C5_6_connection_bottom = gf.routing.route_bundle_electrical(
        component=C5_6,
        ports1=[C5_6.ports["BR_B_1_1"], C5_6.ports["BR_B_1_2"], C5_6.ports["BR_B_1_3"], C5_6.ports["BR_B_1_4"]],
        ports2=[C5_6.ports["TR_B_1_1"], C5_6.ports["TR_B_1_2"], C5_6.ports["TR_B_1_3"], C5_6.ports["TR_B_1_4"]],
        route_width=2,    # adjust for thicker connections
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    # orient top row ports to face upwards to connect the ground plates to the other caps
    ihp.cells.utils.change_port_orientation(C5_6, ["TR_B_1_1", "TR_B_1_2", "TR_B_1_3", "TR_B_1_4", "BR_B_1_6"], 90)
    
    # reference the array as C5
    C5_ref = c.add_ref(C5_6)
    C5_ref.xmax = C2_ref.xmax
    C5_ref.ymax = C2_ref.ymax 
    
    
    # reference the array as C6
    C6_ref = c.add_ref(C5_6)
    C6_ref.mirror_y()
    C6_ref.xmax = C4_ref.xmax
    C6_ref.ymin = C4_ref.ymin
    
    C5_6_connection_ground = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[C5_ref.ports["TR_B_1_1"], C5_ref.ports["TR_B_1_2"], C5_ref.ports["TR_B_1_3"], C5_ref.ports["TR_B_1_4"], C5_ref.ports["BR_B_1_6"]],
        ports2=[C6_ref.ports["TR_B_1_1"], C6_ref.ports["TR_B_1_2"], C6_ref.ports["TR_B_1_3"], C6_ref.ports["TR_B_1_4"], C6_ref.ports["BR_B_1_6"]],
        route_width=2,    # adjust for thicker connections
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    C4_6_connection_ground = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[C4_ref.ports["B"]],
        ports2=[C6_ref.ports["TR_B_1_1"]],
        route_width=2,    # adjust for thicker connections
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    via_M2_M5 = ihp.cells.via_stack(
        top_layer="Metal5",
        bottom_layer="Metal2",
        vn_columns=2,
        vn_rows=4,
    )
    
    # connect XQ3 Emitter to Ground
    via_M2_M5_ref = c.add_ref(via_M2_M5)
    via_M2_M5_ref.connect("bottom", XQ3_ref.ports["E"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    
    # connect XQ1 Emitter to Ground
    via_M2_M5.ports["bottom"].orientation = 0
    via_M2_M5_ref = c.add_ref(via_M2_M5)
    via_M2_M5_ref.center = (C6_ref.ports["TR_B_1_4"].center[0], XQ1_ref.ports["E"].center[1])
    
    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_M2_M5_ref.ports["bottom"]],
        ports2=[XQ1_ref.ports["E"]],
        route_width=1,    # min width for metal2 0.2
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    
    # c.add_ports(via_M2_M5_ref.ports, prefix="via_")
    # c.add_ports(C4_ref.ports, prefix="C4_")
    # c.add_ports(C5_ref.ports, prefix="C5_")
    # c.add_ports(C6_ref.ports, prefix="C6_")
    
    
   
       
    return c

@gf.cell
def powdet_sbd() -> gf.Component:
    c = gf.Component("powdet_sbd")
    
    # via from rfin on TM2 to C1 on TM1
    via_TM1_TM2 = ihp.cells.via_stack(
        top_layer="TopMetal2",
        bottom_layer="TopMetal1",
        vt2_columns=4,
        vt2_rows=3,
    )
    via_TM1_TM2.ports["bottom"].orientation = 0
    via_TM1_TM2_ref = c.add_ref(via_TM1_TM2)
    # reference cmim capacitor and connect to via
    cmim = ihp.cells.cmim(width=10, length=10)
    C1_ref = c.add_ref(cmim)
    C1_ref.connect("T", via_TM1_TM2_ref.ports["bottom"], allow_width_mismatch=True)
    c.add_label(text="rfin", layer=ihp.tech.LAYER.TopMetal2text, position=via_TM1_TM2_ref.ports["top"].center)
    
    
    # via cell from Metal2 to Metal5
    via_M2_M5 = ihp.cells.via_stack(
        top_layer="Metal5",
        bottom_layer="Metal2",
        vn_columns=6,
        vn_rows=3,
    )
    
    
    # via from CMIM C1 to XQ1
    via_M2_M5.ports["top"].orientation = 0
    via_M2_M5_ref = c.add_ref(via_M2_M5)
    via_M2_M5_ref.connect("top", C1_ref.ports["B"], allow_width_mismatch=True)
    
    # create D1 and connect to rfin via C1 and the vias
    schottky = ihp.cells.schottky()
    schottky.locked = False
    schottky.add_label(text="schottky_nbl1", layer=ihp.tech.LAYER.TEXTdrawing)

    D1_ref = c.add_ref(schottky)
    D1_ref.connect("e4", via_M2_M5_ref.ports["bottom"], allow_width_mismatch=True, allow_layer_mismatch=True)
    # c.add_ref(schottky_text).center = D1_ref.center

    # create D2 and place nearby D1 for better matching
    D2_ref = c.add_ref(schottky)
    D2_ref.ymin = D1_ref.ymin
    D2_ref.xmin = D1_ref.xmax # min spacing according to design rules 5.10
    # c.add_ref(schottky_text).center = D2_ref.center
    
    # create capasitor array for cap 2
    C2 = gf.Component("C2")
    cmim = ihp.cells.cmim(width=10, length=10)
    cap_connection_thickness = 4 # thickness of the metal connection between caps, adjust as needed
    # create 3 * 4 array of cmim capacitors with column pitch of 0.52 + 11.2 to fit the required spacing for TM1 and the size of the caps
    # with one missing cap to fit C1 in there
    spacing_between_caps = 0.52
    top_row = C2.add_ref(gf.components.array(component=cmim, columns=6, rows=1, column_pitch= spacing_between_caps + 11.2))
    
    middle_row = C2.add_ref(gf.components.array(component=cmim, columns=6, rows=1, column_pitch= spacing_between_caps + 11.2))
    bottom_row = C2.add_ref(gf.components.array(component=cmim, columns=6, rows=3, column_pitch= spacing_between_caps + 11.2, row_pitch= -(spacing_between_caps + 11.2)))
    top_row.ymin = middle_row.ymax + spacing_between_caps # min spacing according to design rules 5.17
    bottom_row.ymax = middle_row.ymin - spacing_between_caps # min spacing according to design rules 5.17
    C2.add_ports(top_row.ports, prefix="TR_")
    C2.add_ports(middle_row.ports, prefix="MR_")
    C2.add_ports(bottom_row.ports, prefix="BR_")
  
    C2.add_label(text="vss", layer=ihp.tech.LAYER.Metal5text, position=C2.ports["BR_T_1_1"].center)
    # orient the outer most port of top and bottom row to look inward to make a horizontal connection between each cap

    C2.ports["TR_T_1_1"].orientation = 0
    C2.ports["TR_B_1_1"].orientation = 0
    C2.ports["MR_T_1_1"].orientation = 0
    C2.ports["MR_B_1_1"].orientation = 0
    C2.ports["BR_T_1_1"].orientation = 0
    C2.ports["BR_B_1_1"].orientation = 0
    C2.ports["BR_T_2_1"].orientation = 0
    C2.ports["BR_B_2_1"].orientation = 0
    C2.ports["BR_T_3_1"].orientation = 0
    C2.ports["BR_B_3_1"].orientation = 0

    C2.ports["TR_T_1_6"].orientation = 180
    C2.ports["TR_B_1_6"].orientation = 180
    C2.ports["MR_T_1_6"].orientation = 180
    C2.ports["MR_B_1_6"].orientation = 180
    C2.ports["BR_T_1_6"].orientation = 180
    C2.ports["BR_B_1_6"].orientation = 180
    C2.ports["BR_T_2_6"].orientation = 180
    C2.ports["BR_B_2_6"].orientation = 180
    C2.ports["BR_T_3_6"].orientation = 180
    C2.ports["BR_B_3_6"].orientation = 180
    
    
    C2_connection_T = gf.routing.route_bundle_electrical(
        component=C2,
        ports1=[C2.ports["TR_T_1_1"],C2.ports["BR_T_2_1"],C2.ports["BR_T_3_1"], C2.ports["MR_T_1_1"], C2.ports["BR_T_1_1"]],
        ports2=[C2.ports["TR_T_1_6"],C2.ports["BR_T_2_6"],C2.ports["BR_T_3_6"], C2.ports["MR_T_1_6"], C2.ports["BR_T_1_6"]],
        route_width=cap_connection_thickness,   
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    C2_connection_B = gf.routing.route_bundle_electrical(
        component=C2,
        ports1=[C2.ports["TR_B_1_1"],C2.ports["BR_B_2_1"],C2.ports["BR_B_3_1"], C2.ports["MR_B_1_1"], C2.ports["BR_B_1_1"]],
        ports2=[C2.ports["TR_B_1_6"],C2.ports["BR_B_2_6"],C2.ports["BR_B_3_6"], C2.ports["MR_B_1_6"], C2.ports["BR_B_1_6"]],
        route_width=cap_connection_thickness,    # min width for metal1
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    # orient top row ports to face downwards to connect to bottom row ports
    ihp.cells.utils.change_port_orientation(C2, ["TR_T_1_1", "TR_T_1_2", "TR_T_1_3", "TR_T_1_4", "TR_T_1_5", "TR_T_1_6"], 270)
    ihp.cells.utils.change_port_orientation(C2, ["TR_B_1_1", "TR_B_1_2", "TR_B_1_3", "TR_B_1_4", "TR_B_1_5", "TR_B_1_6"], 270)
    
    # orient bottom row ports to face downwards to connect to top row ports
    ihp.cells.utils.change_port_orientation(C2, ["BR_T_3_1", "BR_T_3_2", "BR_T_3_3", "BR_T_3_4", "BR_T_3_5", "BR_T_3_6"], 90)
    ihp.cells.utils.change_port_orientation(C2, ["BR_B_3_1", "BR_B_3_2", "BR_B_3_3", "BR_B_3_4", "BR_B_3_5", "BR_B_3_6"], 90)
    
    C2_connection_top = gf.routing.route_bundle_electrical(
        component=C2,
        ports1=[C2.ports["BR_T_3_1"], C2.ports["BR_T_3_2"], C2.ports["BR_T_3_3"], C2.ports["BR_T_3_4"], C2.ports["BR_T_3_5"], C2.ports["BR_T_3_6"]],
        ports2=[C2.ports["TR_T_1_1"], C2.ports["TR_T_1_2"], C2.ports["TR_T_1_3"], C2.ports["TR_T_1_4"], C2.ports["TR_T_1_5"], C2.ports["TR_T_1_6"]],
        route_width=cap_connection_thickness,    # adjust for thicker connections
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    C2_connection_bottom = gf.routing.route_bundle_electrical(
        component=C2,
        ports1=[C2.ports["BR_B_3_1"], C2.ports["BR_B_3_2"], C2.ports["BR_B_3_3"], C2.ports["BR_B_3_4"], C2.ports["BR_B_3_5"], C2.ports["BR_B_3_6"]],
        ports2=[C2.ports["TR_B_1_1"], C2.ports["TR_B_1_2"], C2.ports["TR_B_1_3"], C2.ports["TR_B_1_4"], C2.ports["TR_B_1_5"], C2.ports["TR_B_1_6"]],
        route_width=cap_connection_thickness,    # adjust for thicker connections
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    # orient top row ports to face upwards to connect the ground plates to the other caps
    ihp.cells.utils.change_port_orientation(C2, ["TR_B_1_1", "TR_B_1_2", "TR_B_1_3", "TR_B_1_6"], 90)
    ihp.cells.utils.change_port_orientation(C2, ["TR_T_1_6"], 0) # for connection to bias1
    ihp.cells.utils.change_port_orientation(C2, ["BR_B_3_4", "BR_B_3_5"], 270)
    
    C2_ref = c.add_ref(C2)
    C2_ref.rotate(-90)
    C2_ref.center = C1_ref.center
    C2_ref.ymin = C1_ref.ymax + 10
    C2_ref.xmax = C1_ref.xmax + C1_ref.xsize + 0.52 
    
    

    ## end of C2 generation
    
    r_sil = ihp.cells.rsil(
        width=0.5, 
        length=2.5)
    
    # let the ports of XR1 and XR5 face each other for easier routing 
    r_sil.ports["e2"].orientation = 0
    XR1_ref = c.add_ref(r_sil.copy())
    
    r_sil.ports["e2"].orientation = 180
    XR5 = r_sil.copy()
    XR5_ref = c.add_ref(XR5)
    
    
    # spacing between D1 and XR1/XR5
    spacing = 1
    XR1_ref.xmax = D1_ref.xmax - 1.88
    XR1_ref.ymax = D1_ref.ymin - spacing
    
    XR5_ref.xmin = D2_ref.xmin + 1.88
    XR5_ref.ymin = XR1_ref.ymin
    
    route_XR1_XR5 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[XR1_ref.ports["e2"]],
        ports2=[XR5_ref.ports["e2"]],
        route_width=0.26,    # min width for metal1
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    # via for connection D1 to XR1 and XR5 to D2
    via_M1_M2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=6,
        vn_rows=2,
    )
    
    # via D1 -> XR1
    via_M1_M2.ports["top"].orientation = 90
    via_M1_M2.ports["bottom"].orientation = 0
    via_M1_M2_ref = c.add_ref(via_M1_M2.copy())
    via_M1_M2_ref.center = D1_ref.center
    via_M1_M2_ref.ymax = D1_ref.ymin
    
    # route from D1 to via
    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[D1_ref.ports["e4"]],
        ports2=[via_M1_M2_ref.ports["top"]],
        route_width=max(via_M1_M2_ref.xsize, via_M1_M2_ref.ysize),
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    
    # route from via to XR1
    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_M1_M2_ref.ports["bottom"]],
        ports2=[XR1_ref.ports["e1"]],
        route_width=min(via_M1_M2_ref.xsize, via_M1_M2_ref.ysize),
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    # connect second diode to input resistors
    # via D2 -> XR5
    via_M1_M2.ports["top"].orientation = 90
    via_M1_M2.ports["bottom"].orientation = 180
    via_M1_M2_ref = c.add_ref(via_M1_M2.copy())
    via_M1_M2_ref.center = D2_ref.center
    via_M1_M2_ref.ymax = D2_ref.ymin
    
    # route from D2 to via
    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[D2_ref.ports["e4"]],
        ports2=[via_M1_M2_ref.ports["top"]],
        route_width=max(via_M1_M2_ref.xsize, via_M1_M2_ref.ysize),
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    # route from via to XR5
    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_M1_M2_ref.ports["bottom"]],
        ports2=[XR5_ref.ports["e1"]],
        route_width=min(via_M1_M2_ref.xsize, via_M1_M2_ref.ysize),
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    
                
    ## build transimpedance amplifier with the schottky diode as input device 
    # M1 nmos and M2 pmos each have 10 gates, M3 and M4 have one gate each, all nmos are placed together and so are the pmos
    
    ng_mos = 13 # 10 + 1 = 11, plus 2 dummy transistors for better matching
    ng_mos = 24 # 20 + 2 + 2 = 24, M1 + M3 + 2 dummy for nmos, M2 + M4 + 2 dummy for pmos
    width_nmos = 60 # um
    width_pmos = 120 
    
    c_output = gf.Component("output_stage")
    
    M1_3 = ihp.cells.nmos(
        w=width_nmos, 
        l=0.13,
        ng=ng_mos,
        guardRingType="psub",
        guardRingDistance=2,
    )
    
    via_gat_M1 = ihp.cells.via_stack(
            top_layer="Metal1",
            bottom_layer="GatPoly",
            vn_columns=1,
            vn_rows=2,
        )

    via_gat_M2 = ihp.cells.via_stack(
            top_layer="Metal2",
            bottom_layer="GatPoly",
            vn_columns=1,
            vn_rows=3,
        )
    
    via_gat_M3 = ihp.cells.via_stack(
            top_layer="Metal3",
            bottom_layer="GatPoly",
            vn_columns=1,
            vn_rows=3,
        )
    
    M1_3.locked=False
    via_gat_M1.ports["bottom"].orientation = 90
    via_gat_M2.ports["bottom"].orientation = 90
    via_gat_M3.ports["bottom"].orientation = 90
    via_gat_M3.ports["top"].orientation = 270 # turn top port for later connection
    gate_ports = M1_3.get_ports_list(layer=ihp.tech.LAYER.GatPolydrawing)
    gate_straight = ihp.cells.straight(
        length= 2.15,
        cross_section="gatpoly_routing",
        width=0.13 # manual meassure of the heigth of the via
    )    
    gate_via_refs_nmos = []
    for i, p in enumerate(gate_ports):
        if p.name in ["G_1", "G_24"]: # these gates will be connected to metal1
            gate_via_refs_nmos.append(M1_3.add_ref(via_gat_M2))
        elif p.name in ["G_12", "G_13"]: # these gates will be connected to metal2
            gate_via_refs_nmos.append(M1_3.add_ref(via_gat_M2))
        else: # all others to metal3
            gate_via_refs_nmos.append(M1_3.add_ref(via_gat_M3))
        gate_straight_ref = M1_3.add_ref(gate_straight)
        gate_straight_ref.connect("e1", M1_3.ports[p.name], allow_width_mismatch=True, allow_layer_mismatch=True)
        via_gat_M2_ref = gate_via_refs_nmos[-1]
        via_gat_M2_ref.connect("bottom", gate_straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    # connect gates 1 and 24 with metal1 to ground
    via_gat_M2.ports["top"].orientation = 0
    start_point = gate_via_refs_nmos[0].ports["top"].center[0]
    end_point = M1_3.ports["DS_29"].center[0] 
    straight_ref = M1_3.add_ref(ihp.cells.straight(
        length=abs(end_point-start_point), 
        cross_section="metal2_routing", 
        width=1.11 # manual meassure of the heigth of the via
        ))
    straight_ref.connect("e1", gate_via_refs_nmos[0].ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    via_M1_M2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=3,   
        vn_rows=1,
    )
    via_M1_M2_ref = M1_3.add_ref(via_M1_M2)
    via_M1_M2_ref.connect("top", straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    via_gat_M2.ports["top"].orientation = 180
    straight_ref = M1_3.add_ref(ihp.cells.straight(
        length=abs(end_point-start_point), 
        cross_section="metal2_routing", 
        width=1.11 # manual meassure of the heigth of the via
        ))
    straight_ref.connect("e1", gate_via_refs_nmos[23].ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    via_M1_M2_ref = M1_3.add_ref(via_M1_M2)
    via_M1_M2_ref.connect("top", straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    # connect Gates 2-11 and 14-23 (all 20 gates) together with metal3
    start_point = M1_3.ports["G_2"].center
    end_point = M1_3.ports["G_23"].center
    straight_ref = M1_3.add_ref(ihp.cells.straight(
        length=abs(end_point[0]-start_point[0]), 
        cross_section="metal3_routing", 
        width=max(gate_via_refs_nmos[1].xsize, gate_via_refs_nmos[1].ysize) # manual meassure of the heigth of the via
        ))
    straight_ref.center = ((start_point[0]+end_point[0])/2, gate_via_refs_nmos[1].center[1]) # align with the via of the first M1 gate
    
    
    # connect Gates 12-13 (2 gates) together with metal2
    start_point = M1_3.ports["G_12"].center
    end_point = M1_3.ports["G_13"].center
    straight_ref = M1_3.add_ref(ihp.cells.straight(
        length=abs(end_point[0]-start_point[0]), 
        cross_section="metal2_routing", 
        width=0.6 # manual meassure of the heigth of the via
        ))
    straight_ref.center = ((start_point[0]+end_point[0])/2, gate_via_refs_nmos[11].center[1]) # align with the via of the first M3 gate
    
    # connect Gates 14-23 (10 gates) together with metal1
    # start_point = M1_3.ports["G_14"].center
    # end_point = M1_3.ports["G_23"].center
    # straight_ref = M1_3.add_ref(ihp.cells.straight(
    #     length=abs(end_point[0]-start_point[0]), 
    #     cross_section="metal2_routing", 
    #     width=0.6 # manual meassure of the heigth of the via
    #     ))
    # straight_ref.center = ((start_point[0]+end_point[0])/2, gate_via_refs_nmos[13].center[1]) # align with the via of the 13th M1 gate


    # connect source to GND
    M1_3_ds_ports = M1_3.get_ports_list(layer=ihp.tech.LAYER.Metal1drawing)
    M1_3_source_ports = []
    M1_3_drain_ports = []
    for i in range(3, len(M1_3_ds_ports)-1): # filter out unwanted ports
        # print(M1_3_ds_ports[i].name)
        if i == 3 or i == len(M1_3_ds_ports)-2 or i % 2 == 0:
            M1_3_source_ports.append(M1_3_ds_ports[i])
        else: 
            M1_3_drain_ports.append(M1_3_ds_ports[i])
            
    
    # source ground connection
    source_straight = ihp.cells.straight(
        length= abs(M1_3.ports["DS_1"].center[1] - M1_3.ports["DS_27"].center[1]), # any source port to the the center of the top guardring segment
        cross_section="metal2_routing",
        width=0.26 # manual meassure of the heigth of the via
    )
    via_M1_M2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=7,
        vn_rows=1,
    )
    via_M1_M2.ports["bottom"].orientation = 0
    via_M1_M2.ports["top"].orientation = 180
    for p in M1_3_source_ports:
        p.orientation = 90 # orient ports to face the top
        via_M1_M2_ref = M1_3.add_ref(via_M1_M2)
        via_M1_M2_ref.connect("bottom", p, allow_width_mismatch=True, allow_layer_mismatch=True)
        source_straight_ref = M1_3.add_ref(source_straight)
        source_straight_ref.connect("e1", via_M1_M2_ref.ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    # connect drains to M3
    via_M1_M4 = ihp.cells.via_stack(
        top_layer="Metal4",
        bottom_layer="Metal1",
        vn_columns=1,
        vn_rows=7,
    )
    

    drain_via_refs_nmos = []
    for p in M1_3_drain_ports:
        if p.name in ["DS_13"]:
            via_M1_M4_short = ihp.cells.via_stack(
                top_layer="Metal4",
                bottom_layer="Metal1",
                vn_columns=1,
                vn_rows=3,
            )
            via_M1_M4_short.ports["top"].orientation = 270
            drain_via_refs_nmos.append(M1_3.add_ref(via_M1_M4_short))
            drain_via_refs_nmos[-1].center = p.center
            drain_via_refs_nmos[-1].ymax = p.center[1] -0.245 # manual meassurement to align with metal1 below
        else:
            via_M1_M4.ports["bottom"].orientation = 90
            via_M1_M4.ports["top"].orientation = 90
            via_M1_M4_ref = M1_3.add_ref(via_M1_M4)
            via_M1_M4_ref.connect("bottom", p, allow_width_mismatch=True, allow_layer_mismatch=True)
            drain_via_refs_nmos.append(via_M1_M4_ref)


    # horizontal drain connection for nmos
    straight_drain_connection = ihp.cells.straight(
        length= abs(drain_via_refs_nmos[0].center[0] - drain_via_refs_nmos[-1].center[0]), # any drain via to the the center of the top guardring segment
        cross_section="metal4_routing",
        width=2 # manual meassure of the heigth of the via
    )
    straight_drain_connection_ref = M1_3.add_ref(straight_drain_connection)
    straight_drain_connection_ref.xmin = drain_via_refs_nmos[-1].center[0] 
    straight_drain_connection_ref.ymin = drain_via_refs_nmos[-1].center[1]

    M1_3.add_ports(gate_via_refs_nmos[17].ports, prefix="gate_M1_")
    M1_3.add_port(name="drain_connection_M1", port=drain_via_refs_nmos[2].ports["top"])
    M1_3.add_port(name="drain_connection_M3", port=drain_via_refs_nmos[5].ports["top"])
    M1_3.add_port(name="gate_connection_M3", center=((gate_via_refs_nmos[11].center[0] + gate_via_refs_nmos[12].center[0]) /2, gate_via_refs_nmos[11].center[1]), cross_section="metal2_routing", orientation=270, port_type="electrical")
    M1_3_ref = c_output.add_ref(M1_3)
    M1_3_ref.move((0,30))
    # c_output.add(gate_via_refs_nmos)

    # c_output.add_port(name="drain_connection_M1", port=drain_via_refs_nmos[2].ports["top"])
   

    
    M2_4 = ihp.cells.pmos(
        w=width_pmos, 
        l=0.13,
        ng=ng_mos,
        guardRingType="nwell",
        guardRingDistance=2,
    )
    
    # connect gates of M2 and M4 together
    
    M2_4.locked=False
    gate_ports = M2_4.get_ports_list(layer=ihp.tech.LAYER.GatPolydrawing)
    gate_straight = ihp.cells.straight(
        length= 3.55,
        cross_section="gatpoly_routing",
        width=0.13 # manual meassure of the heigth of the via
    )    
    gate_via_refs_pmos = []
    for i, p in enumerate(gate_ports):
        p.orientation += 180 # orient gates to face downwards for easier connection to nmos gates
        if p.name in ["G_1", "G_25"]: # these gates will be connected to metal1
            gate_via_refs_pmos.append(M2_4.add_ref(via_gat_M2))
        elif p.name in ["G_13", "G_14"]: # these gates will be connected to meta2
            gate_via_refs_pmos.append(M2_4.add_ref(via_gat_M2))
        else: # all others to metal3
            gate_via_refs_pmos.append(M2_4.add_ref(via_gat_M3))
        gate_straight_ref = M2_4.add_ref(gate_straight)
        gate_straight_ref.connect("e1", M2_4.ports[p.name], allow_width_mismatch=True, allow_layer_mismatch=True)
        gate_via_refs_pmos[-1].connect("bottom", gate_straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)


    
    ## Gate numbers are shifted by 1 after G1, e.g. G1 G3 G4 G5 .. dont know why... similar for DS, DS1 DS3 DS5 DS6 DS7 ... maybe guardrings are intereering even though they are disabled
    # connect gates 1 and 24 with metal1 to ground
    via_gat_M2.ports["top"].orientation = 180
    start_point = gate_via_refs_pmos[0].ports["top"].center[0]
    end_point = M2_4.ports["DS_31"].center[0] 
    straight_ref = M2_4.add_ref(ihp.cells.straight(
        length=abs(end_point-start_point), 
        cross_section="metal2_routing", 
        width=1.11 # manual meassure of the heigth of the via
        ))
    
    straight_ref.connect("e1", gate_via_refs_pmos[0].ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    via_M1_M2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=3,   
        vn_rows=1,
    )
    via_M1_M2_ref = M2_4.add_ref(via_M1_M2)
    via_M1_M2_ref.connect("top", straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    straight_ref.connect("e2", via_M1_M2_ref.ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)


    via_gat_M2.ports["bottom"].orientation = 0
    straight_ref.connect("e1", gate_via_refs_pmos[0].ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    straight_ref = M2_4.add_ref(ihp.cells.straight(
        length=abs(end_point-start_point), 
        cross_section="metal2_routing", 
        width=1.11 # manual meassure of the heigth of the via
        ))
    straight_ref.connect("e1", gate_via_refs_pmos[23].ports["bottom"], allow_width_mismatch=True, allow_layer_mismatch=True)

    via_M1_M2_ref = M2_4.add_ref(via_M1_M2)
    via_M1_M2_ref.connect("top", straight_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    
    
    
    # connect Gates 2-11 and 14-23 (20 gates) together with metal3
    start_point = M2_4.ports["G_3"].center
    end_point = M2_4.ports["G_24"].center
    straight_ref = M2_4.add_ref(ihp.cells.straight(
        length=abs(end_point[0]-start_point[0]), 
        cross_section="metal3_routing", 
        width=max(gate_via_refs_pmos[1].xsize, gate_via_refs_pmos[1].ysize) # manual meassure of the heigth of the via
        ))
    straight_ref.center = ((start_point[0]+end_point[0])/2, gate_via_refs_pmos[1].center[1]) # align with the via of the first M1 gate
    
    
    # connect Gates 12-13 (2 gates) together with metal2
    start_point = M2_4.ports["G_13"].center
    end_point = M2_4.ports["G_14"].center
    straight_ref = M2_4.add_ref(ihp.cells.straight(
        length=abs(end_point[0]-start_point[0]), 
        cross_section="metal2_routing", 
        width=0.6 # manual meassure of the heigth of the via
        ))
    straight_ref.center = ((start_point[0]+end_point[0])/2, gate_via_refs_pmos[11].center[1]) # align with the via of the first M3 gate
    
    
    # connect source to vdd
    M2_4_ds_ports = M2_4.get_ports_list(layer=ihp.tech.LAYER.Metal1drawing)
    M2_4_source_ports = []
    M2_4_drain_ports = []
    for i in range(3, len(M2_4_ds_ports)-1): # filter out unwanted ports
        # print(M2_4_ds_ports[i].name)
        if i == 3 or i == len(M2_4_ds_ports)-2 or i % 2 == 0:
            M2_4_source_ports.append(M2_4_ds_ports[i])
        else: 
            M2_4_drain_ports.append(M2_4_ds_ports[i])
            
    
    # source vdd connection
    source_straight = ihp.cells.straight(
        length= abs(M2_4.ports["DS_1"].center[1] - M2_4.ports["DS_29"].center[1]), # any source port to the the center of the top guardring segment
        cross_section="metal2_routing",
        width=0.26 # manual meassure of the heigth of the via
    )
    via_M1_M2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=13,
        vn_rows=1,
    )
    via_M1_M2.ports["bottom"].orientation = 180
    via_M1_M2.ports["top"].orientation = 0
    for p in M2_4_source_ports:
        p.orientation = 270 # orient ports to face the top
        via_M1_M2_ref = M2_4.add_ref(via_M1_M2)
        via_M1_M2_ref.connect("bottom", p, allow_width_mismatch=True, allow_layer_mismatch=True)
        source_straight_ref = M2_4.add_ref(source_straight)
        source_straight_ref.connect("e1", via_M1_M2_ref.ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    # connect drains to metal4
    via_M1_M4 = ihp.cells.via_stack(
        top_layer="Metal4",
        bottom_layer="Metal1",
        vn_columns=1,
        vn_rows=13,
    )
    drain_via_refs_pmos = []
    for p in M2_4_drain_ports:
        if p.name in ["DS_15"]:
            via_M1_M4_short = ihp.cells.via_stack(
                top_layer="Metal4",
                bottom_layer="Metal1",
                vn_columns=1,
                vn_rows=6,
            )
            via_M1_M4_short.ports["top"].orientation = 90
            drain_via_refs_pmos.append(M2_4.add_ref(via_M1_M4_short))
            drain_via_refs_pmos[-1].center = p.center
            drain_via_refs_pmos[-1].ymin = p.center[1] + 0.245 # manual meassurement to align with metal1 below
        else:
            via_M1_M4.ports["bottom"].orientation = 90
            via_M1_M4.ports["top"].orientation = 270
            via_M1_M4_ref = M2_4.add_ref(via_M1_M4)
            via_M1_M4_ref.connect("bottom", p, allow_width_mismatch=True, allow_layer_mismatch=True)
            drain_via_refs_pmos.append(via_M1_M4_ref)

    # horizontal drain connection for nmos
    straight_drain_connection = ihp.cells.straight(
        length= abs(drain_via_refs_pmos[0].center[0] - drain_via_refs_pmos[-1].center[0]), # any drain via to the the center of the top guardring segment
        cross_section="metal4_routing",
        width=2.61 #  manual measurement
    )
    straight_drain_connection_ref = M2_4.add_ref(straight_drain_connection)
    straight_drain_connection_ref.xmin = drain_via_refs_pmos[-1].center[0] 
    straight_drain_connection_ref.ymin = drain_via_refs_pmos[-1].ymin
    
    
    M2_4.add_ports(gate_via_refs_pmos[17].ports, prefix="gate_M2_")
    M2_4.add_port(name="drain_connection_M2", port=drain_via_refs_pmos[2].ports["top"])
    M2_4.add_port(name="drain_connection_M4", port=drain_via_refs_pmos[5].ports["top"])
    M2_4.add_port(name="gate_connection_M4", center=((gate_via_refs_pmos[11].center[0] + gate_via_refs_pmos[12].center[0]) /2, gate_via_refs_pmos[11].center[1]), cross_section="metal2_routing", orientation=90, port_type="electrical")
    
    
    M2_4_ref = c_output.add_ref(M2_4)

    spacing_between_nmos_pmos = 15 # manual meassurement of the spacing between the drain vias of M1 and M2, used to set the length of the connection between M1 and M2 drains
    drain_connection_M1_M2 = c_output.add_ref(ihp.cells.straight(
        length= spacing_between_nmos_pmos, # manual measurement, used to set the distance between M1 and M2
        cross_section="metal4_routing",
        width=4.28 #  manual measurement
    ))
        
    drain_connection_M1_M2.connect("e1", M1_3_ref.ports["drain_connection_M1"], allow_width_mismatch=True, allow_layer_mismatch=True)
    M2_4_ref.connect("drain_connection_M2", drain_connection_M1_M2.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    

    # drain connection for replica circuit
    routing_drain_M1_M3 = gf.routing.route_bundle_electrical(
        component=c_output,
        ports1=[M1_3_ref.ports["drain_connection_M3"]],
        ports2=[M2_4_ref.ports["drain_connection_M4"]],
        route_width=0.61,
        layer=ihp.tech.LAYER.Metal4drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    
    # vias for resistor XR2 and XR4 connections
    via_M1_M2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=2,
        vn_rows=2,
    )
    via_M1_M2.ports["top"].orientation = 90
    via_M1_M3 = ihp.cells.via_stack(
        top_layer="Metal3",
        bottom_layer="Metal1",
        vn_columns=2,
        vn_rows=2,
    )
    via_M1_M4 = ihp.cells.via_stack(
        top_layer="Metal4",
        bottom_layer="Metal1",
        vn_columns=2,
        vn_rows=2,
    )
    
    XR4 = ihp.cells.rppd(width=0.5, length=1.5)
    XR4_ref = c_output.add_ref(XR4).rotate(90)
    XR4_ref.center = M1_3_ref.ports["DS_15"].center
    XR4_ref.movex(0.01) # manual meassurement to align with the gate connection
    XR4_ref.ymax =  M1_3_ref.ymin - 2 # manual meassurement to set the spacing between the nmos and the resistors 
    
    via_M1_M4_ref = c_output.add_ref(via_M1_M4)
    via_M1_M4_ref.connect("bottom", XR4_ref.ports["e1"], allow_width_mismatch=True, allow_layer_mismatch=True)
    c_output.add_label(text="vref", layer=ihp.tech.LAYER.Metal4text, position=via_M1_M4_ref.ports["top"].center)
    c_output.add_port(name="vref", port=via_M1_M4_ref.ports["top"])
    
    via_M1_M2.ports["top"].orientation = 180
    via_M1_M2_ref = c_output.add_ref(via_M1_M2)
    via_M1_M2_ref.connect("bottom", XR4_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    c_output.add_ports(via_M1_M2_ref.ports, prefix="XR4_")
    
    
    XR2 = ihp.cells.rppd(width=0.5, length=1.5)
    XR2_ref = c_output.add_ref(XR2).rotate(90)
    XR2_ref.ymax = XR4_ref.ymin -1 # manual meassurement to set the spacing between the two resistors to 0
    XR2_ref.xmax = XR4_ref.xmax
    
    via_M1_M4_ref = c_output.add_ref(via_M1_M4)
    via_M1_M4_ref.connect("bottom", XR2_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    c_output.add_label(text="vout", layer=ihp.tech.LAYER.Metal4text, position=via_M1_M4_ref.ports["top"].center)
    c_output.add_port(name="vout", port=via_M1_M4_ref.ports["top"])
    via_M1_M3_ref = c_output.add_ref(via_M1_M3)
    via_M1_M3_ref.connect("bottom", XR2_ref.ports["e1"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    # bias2
    route_gates_M3_M4 = gf.routing.route_bundle_electrical(
        component=c_output,
        ports1=[M1_3_ref.ports["gate_connection_M3"]],
        ports2=[via_M1_M2_ref.ports["top"]],
        route_width=0.5,
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
        steps=[
            {"dy": -2.46, "dx": 0.5},
            {"dx": 1},
        ]
    )
   
    
    # node bb_int routing
    route_gates_M1_M2 = gf.routing.route_bundle_electrical(
        component=c_output,
        ports1=[M1_3_ref.ports["gate_M1_top"]],
        ports2=[M2_4_ref.ports["gate_M2_top"]],
        route_width=0.6,
        layer=ihp.tech.LAYER.Metal3drawing,
        start_straight_length=0.5,
        end_straight_length=0.5,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    route_gates_M1_M2 = gf.routing.route_bundle_electrical(
        component=c_output,
        ports1=[M1_3_ref.ports["gate_M1_top"]],
        ports2=[XR2_ref.ports["e1"]],
        route_width=0.6,
        layer=ihp.tech.LAYER.Metal3drawing,
        start_straight_length=0.5,
        end_straight_length=0.5,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    c_output.add_ports(M1_3_ref.ports, prefix="M1_")
    c_output.add_ports(M2_4_ref.ports, prefix="M2_")
    output_stage_ref = c.add_ref(c_output.rotate(90))
    output_stage_ref.center = C2_ref.center
    output_stage_ref.ymin = C2_ref.ymin
    output_stage_ref.move((17.99 + 1.64, 9.02 + 5.23))
    
    
    # create capasitor array for cap 3
    C3 = gf.Component("C3")
    # create 3 * 4 array of cmim capacitors with column pitch of 0.52 + 11.2 to fit the required spacing for TM1 and the size of the caps
    # with one missing cap to fit C1 in there
    spacing_between_caps = 0.52
    left_col = C3.add_ref(gf.components.array(component=cmim, columns=3, rows=5, column_pitch= spacing_between_caps + 11.2, row_pitch= -(spacing_between_caps + 11.2)))
    middle_col = C3.add_ref(gf.components.array(component=cmim, columns=2, rows=4, column_pitch= spacing_between_caps + 11.2, row_pitch= -(spacing_between_caps + 11.2)))
    right_col = C3.add_ref(gf.components.array(component=cmim, columns=1, rows=5, column_pitch= spacing_between_caps + 11.2, row_pitch= -(spacing_between_caps + 11.2)))
    left_col.xmax = middle_col.xmin - spacing_between_caps # min spacing according to design rules 5.17
    right_col.xmin = middle_col.xmax + spacing_between_caps # min spacing according to design rules 5.17
    C3.add_ports(left_col.ports, prefix="LC_")
    C3.add_ports(middle_col.ports, prefix="MC_")
    C3.add_ports(right_col.ports, prefix="RC_")
    
    # orient the outer most port of for horizontal connection
    ihp.cells.utils.change_port_orientation(C3, ["LC_T_1_1", "LC_T_2_1", "LC_T_3_1", "LC_T_4_1", "LC_T_5_1"], 0)
    ihp.cells.utils.change_port_orientation(C3, ["LC_B_1_1", "LC_B_2_1", "LC_B_3_1", "LC_B_4_1", "LC_B_5_1"], 0)

    ihp.cells.utils.change_port_orientation(C3, ["RC_T_1_1", "RC_T_2_1", "RC_T_3_1", "RC_T_4_1", "LC_T_5_3"], 180)
    ihp.cells.utils.change_port_orientation(C3, ["RC_B_1_1", "RC_B_2_1", "RC_B_3_1", "RC_B_4_1", "LC_B_5_3"], 180)
    
    
    C3_connection_T = gf.routing.route_bundle_electrical(
        component=C3,
        ports1=[C3.ports["LC_T_1_1"], C3.ports["LC_T_2_1"], C3.ports["LC_T_3_1"], C3.ports["LC_T_4_1"], C3.ports["LC_T_5_1"]],
        ports2=[C3.ports["RC_T_1_1"], C3.ports["RC_T_2_1"], C3.ports["RC_T_3_1"], C3.ports["RC_T_4_1"], C3.ports["LC_T_5_3"]],
        route_width=cap_connection_thickness,   
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    C3_connection_B = gf.routing.route_bundle_electrical(
        component=C3,
        ports1=[C3.ports["LC_B_1_1"], C3.ports["LC_B_2_1"], C3.ports["LC_B_3_1"], C3.ports["LC_B_4_1"], C3.ports["LC_B_5_1"]],
        ports2=[C3.ports["RC_B_1_1"], C3.ports["RC_B_2_1"], C3.ports["RC_B_3_1"], C3.ports["RC_B_4_1"], C3.ports["LC_B_5_3"]],
        route_width=cap_connection_thickness,    
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    # orient top row ports to face downwards to connect to bottom row ports
    ihp.cells.utils.change_port_orientation(C3, ["LC_T_1_1", "LC_T_1_2", "LC_T_1_3", "MC_T_1_1", "MC_T_1_2", "RC_T_1_1"], 270)
    ihp.cells.utils.change_port_orientation(C3, ["LC_B_1_1", "LC_B_1_2", "LC_B_1_3", "MC_B_1_1", "MC_B_1_2", "RC_B_1_1"], 270)
    
    # orient bottom row ports to face downwards to connect to top row ports
    ihp.cells.utils.change_port_orientation(C3, ["LC_T_5_1", "LC_T_5_2", "LC_T_5_3", "MC_T_4_1", "MC_T_4_2", "RC_T_5_1"], 90)
    ihp.cells.utils.change_port_orientation(C3, ["LC_B_5_1", "LC_B_5_2", "LC_B_5_3", "MC_B_4_1", "MC_B_4_2", "RC_B_5_1"], 90)
    

    C3_connection_top = gf.routing.route_bundle_electrical(
        component=C3,
        ports1=[C3.ports["LC_T_1_1"], C3.ports["LC_T_1_2"], C3.ports["LC_T_1_3"], C3.ports["MC_T_1_1"], C3.ports["MC_T_1_2"], C3.ports["RC_T_1_1"]],
        ports2=[C3.ports["LC_T_5_1"], C3.ports["LC_T_5_2"], C3.ports["LC_T_5_3"], C3.ports["MC_T_4_1"], C3.ports["MC_T_4_2"], C3.ports["RC_T_5_1"]],
        route_width=cap_connection_thickness,    
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    C3_connection_bottom = gf.routing.route_bundle_electrical(
        component=C3,
        ports1=[C3.ports["LC_B_1_1"], C3.ports["LC_B_1_2"], C3.ports["LC_B_1_3"], C3.ports["MC_B_1_1"], C3.ports["MC_B_1_2"], C3.ports["RC_B_1_1"]],
        ports2=[C3.ports["LC_B_5_1"], C3.ports["LC_B_5_2"], C3.ports["LC_B_5_3"], C3.ports["MC_B_4_1"], C3.ports["MC_B_4_2"], C3.ports["RC_B_5_1"]],
        route_width=cap_connection_thickness,    
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    
    # orient top row ports to face downwards to connect to face the middle for connection purposes
    ihp.cells.utils.change_port_orientation(C3, ["MC_T_4_1", "MC_T_4_2", "LC_T_5_1", "LC_T_5_2", "LC_T_5_3"], 270)
    # orient top row ports to face downwards to connect to face C2 for connection purposes
    ihp.cells.utils.change_port_orientation(C3, ["MC_B_4_1", "MC_B_4_2", "LC_B_5_1", "LC_B_5_2", "LC_B_5_3", "RC_B_5_1"], 270)
    
    
    C3.add_label(text="vdd", layer=ihp.tech.LAYER.TopMetal1text, position=C3.ports["LC_T_1_1"].center)
    C3_ref = c.add_ref(C3)
    
    C3_ref.rotate(-90)
    C3_ref.xmin = C2_ref.xmax + 0.52 # manual meassurement to set the spacing between C2 and C3
    C3_ref.ymin = C2_ref.ymin

    C_fill = ihp.cells.cmim(width=6.8, length=9)
    C_fill.ports["B"].orientation = 0
    C_fill_1_ref = c.add_ref(C_fill)
    C_fill_2_ref = c.add_ref(C_fill)

    straight_M5 = ihp.cells.straight(
        length=10.12,
        cross_section="metal5_routing",
        width=cap_connection_thickness, # manual meassurement to align with the via
    )
    straight_M5_ref = c.add_ref(straight_M5)
    straight_M5_ref.connect("e1", C3_ref.ports["MC_B_4_1"], allow_width_mismatch=True, allow_layer_mismatch=True)
    C_fill_1_ref.connect("B", straight_M5_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    straight_M5_ref = c.add_ref(straight_M5)
    straight_M5_ref.connect("e1", C3_ref.ports["MC_B_4_2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    C_fill_2_ref.connect("B", straight_M5_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    
    route_C2_C3_VSS = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[C2_ref.ports["TR_B_1_1"], C2_ref.ports["TR_B_1_2"], C2_ref.ports["TR_B_1_3"], C2_ref.ports["TR_B_1_6"]],
        ports2=[C3_ref.ports["LC_B_5_1"], C3_ref.ports["LC_B_5_2"], C3_ref.ports["LC_B_5_3"], C3_ref.ports["RC_B_5_1"]],
        route_width=cap_connection_thickness,    # adjust for thicker connections
        layer=ihp.tech.LAYER.Metal5drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    
    
    # connect nmos source/bulk to vss
    via_M1_M5 = ihp.cells.via_stack(
        top_layer="Metal5",
        bottom_layer="Metal1",
        vn_columns=3,
        vn_rows=35,
    )
    via_M1_M5.ports["bottom"].orientation = 0
    via_M1_M5_ref = c.add_ref(via_M1_M5)
    via_M1_M5_ref.connect("bottom", output_stage_ref.ports["M1_DS_27"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    # connect nmos source/bulk to vdd
    via_M1_TM1 = ihp.cells.via_stack(
        top_layer="TopMetal1",
        bottom_layer="Metal1",
        vn_columns=3,
        vn_rows=35,
        vt1_columns=1,
        vt1_rows=17,
    )
    via_M1_TM1.ports["bottom"].orientation = 90
    via_M1_TM1_ref = c.add_ref(via_M1_TM1)
    via_M1_TM1_ref.connect("bottom", output_stage_ref.ports["M2_DS_28"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    
    tm1_straight = ihp.cells.straight(
        length=abs(output_stage_ref.ports["M2_DS_28"].center[0] - C3_ref.ports["MC_T_4_1"].center[0]), 
        cross_section="topmetal1_routing",
        width=2 # manual meassurement to align with the via
    )
    tm1_straight_ref = c.add_ref(tm1_straight)
    tm1_straight_ref.connect("e1", C3_ref.ports["MC_T_4_1"], allow_width_mismatch=True, allow_layer_mismatch=True)
    tm1_straight_ref = c.add_ref(tm1_straight)
    tm1_straight_ref.connect("e1", C3_ref.ports["MC_T_4_2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    

    # connect C2 to bias1 network
    via_M1_TM1 = ihp.cells.via_stack(
        top_layer="TopMetal1",
        bottom_layer="Metal1",
        vn_columns=3,
        vn_rows=4,
        vt1_columns=1,
        vt1_rows=2,
        )
    via_M1_TM1.ports["top"].orientation = 0
    via_M1_TM1.ports["bottom"].orientation = 180
    via_M1_TM1_ref = c.add_ref(via_M1_TM1).rotate(90)
    via_M1_TM1_ref.xmax = C2_ref.xmax - 4.55
    via_M1_TM1_ref.ymax = C3_ref.ymin - 5 # min M5 spacing
    
    route_C2_bias = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[C2_ref.ports["TR_T_1_6"]],
        ports2=[via_M1_TM1_ref.ports["top"]],
        route_width=max(via_M1_TM1_ref.xsize, via_M1_TM1_ref.ysize),    # manual change to fit width
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    route = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_M1_TM1_ref.ports["bottom"]],
        ports2=[XR1_ref.ports["e2"]],
        route_width=0.46,    
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    via_M1_TM1.ports["bottom"].orientation = 270
    XR3 = ihp.cells.rhigh(width=0.5, length=2)
    XR3_ref = c.add_ref(XR3).rotate(90)
    XR3_ref.center = via_M1_TM1_ref.center
    XR3_ref.xmin = C3_ref.xmin
    rotute_XR3 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[via_M1_TM1_ref.ports["bottom"]],
        ports2=[XR3_ref.ports["e1"]],
        route_width=0.46,    
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    via_M1_TM1 = ihp.cells.via_stack(
        top_layer="TopMetal1",
        bottom_layer="Metal1",
        vn_columns=4,
        vn_rows=3,
        vt1_columns=2,
        vt1_rows=1,
        )
    via_M1_TM1.ports["bottom"].orientation = 0
    via_M1_TM1_ref = c.add_ref(via_M1_TM1)
    via_M1_TM1_ref.connect("bottom", XR3_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    route_C2_bias = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[C3_ref.ports["RC_T_5_1"]],
        ports2=[via_M1_TM1_ref.ports["top"]],
        route_width=max(via_M1_TM1_ref.xsize, via_M1_TM1_ref.ysize),    # manual change to fit width
        layer=ihp.tech.LAYER.TopMetal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    
    # bb_int connect D1 to network
    via_M1_M3 = ihp.cells.via_stack(
        top_layer="Metal3",
        bottom_layer="Metal1",
        vn_columns=6,
        vn_rows=3,
    )
    via_M1_M3.ports["top"].orientation = 90
    via_M1_M3.ports["bottom"].orientation = 270
    via_M1_M3_ref = c.add_ref(via_M1_M3)
    via_M1_M3_ref.connect("bottom", D1_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    
    # bb_int
    routing_bb_int = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[output_stage_ref.ports["M1_gate_M1_top"]],
        ports2=[via_M1_M3_ref.ports["top"]],
        route_width=0.6,    
        layer=ihp.tech.LAYER.Metal3drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        end_straight_length=2,
        auto_taper=False,
        separation=0,
        steps=[
            {"dx": 3.65, "dy": -1}, # strange behavior without the dy direction
            {"dy": -6},
            {"dx": -4, "dy": 0},
        ],
        # layer_marker=(41, 0), # Mark the steps with a layer
    )
    
    # bias2 connect D2 to network
    via_M1_M2 = ihp.cells.via_stack(
        top_layer="Metal2",
        bottom_layer="Metal1",
        vn_columns=6,
        vn_rows=3,
    )
    via_M1_M2.ports["top"].orientation = 90
    via_M1_M2.ports["bottom"].orientation = 270
    via_M1_M2_ref = c.add_ref(via_M1_M2)
    via_M1_M2_ref.connect("bottom", D2_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

    # bias2 connection from gate of M3 to D2
    routing_bias2 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[output_stage_ref.ports["M1_gate_connection_M3"]],
        ports2=[via_M1_M2_ref.ports["top"]],
        route_width=0.5,    
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        end_straight_length=3,
        auto_taper=False,
        separation=0,
        steps=[
            {"dx": 2.46, "dy": -1}, # strange behavior without the dy direction
            {"dy": -1},
            {"dx": 2.17, "dy": 0},
            {"dy": -2},
        ],
        # layer_marker=(41, 0), # Mark the steps with a layer
    )
    # bias2 connection from gate of M4 to D2
    routing_bias2 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[output_stage_ref.ports["M2_gate_connection_M4"]],
        ports2=[via_M1_M2_ref.ports["top"]],
        route_width=0.5,    
        layer=ihp.tech.LAYER.Metal2drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        end_straight_length=3,
        auto_taper=False,
        separation=0,
        steps=[
            {"dx": -2.46, "dy": -1}, # strange behavior without the dy direction
            {"dy": -1},
            {"dx": -2.21, "dy": 0},
            {"dy": -2},
        ],
        # layer_marker=(41, 0), # Mark the steps with a layer
    )

    
    
    
    # SBD D1 D2 sub connection
    route_D1_D2 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[D1_ref.ports["e3"]],
        ports2=[D2_ref.ports["e1"]],
        route_width=5.7,
        layer=ihp.tech.LAYER.Metal1drawing,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )
    via_M1_M3 = ihp.cells.via_stack(
        top_layer="Metal3",
        bottom_layer="Metal1",
        vn_columns=1,
        vn_rows=5,
    )
    via_M1_M3.ports["bottom"].orientation = 0
    via_M1_M3.ports["top"].orientation = 180
    via_M1_M3_ref = c.add_ref(via_M1_M3)
    via_M1_M3_ref.connect("bottom", D2_ref.ports["e3"], allow_width_mismatch=True, allow_layer_mismatch=True)

    straight_M3 = ihp.cells.straight(
        length=18,
        cross_section="metal3_routing",
        width=max(via_M1_M3_ref.xsize, via_M1_M3_ref.ysize),
    )
    straight_M3_ref = c.add_ref(straight_M3)
    straight_M3_ref.connect("e1", via_M1_M3_ref.ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    via_M3_M5 = ihp.cells.via_stack(
        top_layer="Metal5",
        bottom_layer="Metal3",
        vn_columns=1,
        vn_rows=5,
    )
    via_M3_M5.ports["bottom"].orientation = 180
    via_M3_M5_ref = c.add_ref(via_M3_M5)
    via_M3_M5_ref.connect("bottom", straight_M3_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    

    schottky.ports["e1"].orientation = 90
    # connect D1 and D2 sub connection together
    schottky.ports["e3"].orientation = 90
    route_SBD_D1_D2 = gf.routing.route_bundle_electrical(
        component=c,
        ports1=[D1_ref.ports["e1"]],
        ports2=[D2_ref.ports["e3"]],
        route_width=0.3,
        layer=ihp.tech.LAYER.Metal1drawing,
        start_straight_length=2.85,
        allow_layer_mismatch=True,
        allow_width_mismatch=True,
        auto_taper=False,
        separation=0,
    )

    # input_antenna_interuption_TM1 = ihp.cells.straight(
    #     length=10,
    #     cross_section="topmetal1_routing",
    #     width=7.2,
    # )
    # input_antenna_interuption_TM2 = ihp.cells.straight(
    #     length=10,
    #     cross_section="topmetal2_routing",
    #     width=7.2,
    # )
    # input_antenna_interuption_TM2_ref = c.add_ref(input_antenna_interuption_TM2)
    # input_antenna_interuption_TM2_ref.connect("e1", via_TM1_TM2_ref.ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)
    # via_TM1_TM2.ports["top"].orientation = 90
    # via_TM1_TM2.ports["bottom"].orientation = 270
    # via_TM1_TM2_ref = c.add_ref(via_TM1_TM2)
    # via_TM1_TM2_ref.connect("top", input_antenna_interuption_TM2_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    # input_antenna_interuption_TM1_ref = c.add_ref(input_antenna_interuption_TM1)
    # input_antenna_interuption_TM1_ref.connect("e1", via_TM1_TM2_ref.ports["bottom"], allow_width_mismatch=True, allow_layer_mismatch=True)
    # via_TM1_TM2_ref = c.add_ref(via_TM1_TM2)
    # via_TM1_TM2_ref.connect("bottom", input_antenna_interuption_TM1_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
    # c_output.pprint_ports()
    
    straight_M3 = ihp.cells.straight(
        length=10,
        cross_section="metal3_routing",
        width=2,
    )
    straight_M3_ref = c.add_ref(straight_M3)
    straight_M3_ref.connect("e1", output_stage_ref.ports["vref"], allow_width_mismatch=True, allow_layer_mismatch=True)
    # add ports to the powerdetector
    c.add_port(name="vout", port=output_stage_ref.ports["vout"])
    c.ports["vout"].orientation = 90
    c.add_port(name="vref", port=straight_M3_ref.ports["e2"])
    c.ports["vref"].center = (c.ports["vref"].center[0], c.ports["vref"].center[1]-0.1) # preventing notch
    c.ports["vref"].orientation = 90
    c.add_port(name="rfin", port=via_TM1_TM2_ref.ports["top"])
    c.ports["rfin"].orientation = 270
    c.add_port(name="vss", port=C3_ref.ports["LC_B_1_1"])
    c.ports["vss"].orientation = 90
    c.add_port(name="vdd", port=C3_ref.ports["LC_T_1_1"])
    c.ports["vdd"].orientation = 0
    c.pprint_ports()
    
    c.center = (0, 0)
    c.add_ref(gf.components.rectangle(size=(c.xsize + 2, c.ysize + 2), layer=ihp.tech.LAYER.Activnofill, centered=True))
    c.add_ref(gf.components.rectangle(size=(c.xsize, c.ysize), layer=ihp.tech.LAYER.GatPolynofill, centered=True))
    c.add_ref(gf.components.rectangle(size=(c.xsize, c.ysize), layer=ihp.tech.LAYER.Metal1nofill, centered=True))
    c.add_ref(gf.components.rectangle(size=(c.xsize, c.ysize), layer=ihp.tech.LAYER.Metal2nofill, centered=True))
    c.add_ref(gf.components.rectangle(size=(c.xsize, c.ysize), layer=ihp.tech.LAYER.Metal3nofill, centered=True))
    c.add_ref(gf.components.rectangle(size=(c.xsize, c.ysize), layer=ihp.tech.LAYER.Metal4nofill, centered=True))
    # c.add_ref(gf.components.rectangle(size=(c.xsize, c.ysize), layer=ihp.tech.LAYER.Metal5nofill, centered=True))
    M5_nofill = c.add_ref(gf.components.rectangle(size=(C1_ref.xsize+40, C1_ref.ysize+20), layer=ihp.tech.LAYER.Metal5nofill)).center = C1_ref.center
    
    sizex = C2_ref.xsize + C3_ref.xsize
    sizey = C2_ref.ysize 
    x = C2_ref.xmin + sizex/2
    y = C2_ref.ymin + sizey/2
    cap_M5_nofill = c.add_ref(gf.components.rectangle(size=(sizex-10, sizey-10), layer=ihp.tech.LAYER.Metal5nofill)).center = (x,y)
    # c.add_ports(output_stage_ref.ports, prefix="output_stage_")
    # c.add_ports(via_M1_M2_ref.ports, prefix="via_")
    # c.add_ports(XR1_ref.ports, prefix="XR1_")
    # c.add_ports(XR5_ref.ports, prefix="XR5_")
    # c.add_ports(D1_ref.ports, prefix="SBD1_")
    # c.add_ports(D2_ref.ports, prefix="SBD2_")
    # c.add_ports(M1_3_ref.ports, prefix="M1_")
    # c.add_ports(output_stage_ref.ports)
    # c.add_ports(C2_ref.ports, prefix="C2_")
    # c.add_ports(C3_ref.ports, prefix="C3_")
    
    
    # c.pprint_ports()
    
    return c
# ----------------------------------------------------
# define design parameters

e_r = 4.1  # relative permittivity
Z0 = 50  # characteristic impedance
f = 160e9  # frequency


# signal and ground layers
signal_cross_section = "topmetal2_routing"
ground_cross_section = "metal5_routing"

# calculate effective dielectric constant and wavelength
e_eff = ihp.cells.waveguides._calculate_effective_dielectric_constant(
    signal_cross_section=signal_cross_section, 
    ground_cross_section=ground_cross_section, 
    e_r=e_r)


c0 = scipy.constants.c  # speed of light
wavelength = c0 / f *1e6 / sqrt(e_eff)   # wavelength
wavelength_4 = wavelength / 4  # quarter wavelength

wavelength = round(wavelength - wavelength % (ihp.tech.nm), 3) # snap to grid
wavelength_4 = round(wavelength_4 - (wavelength_4 % (ihp.tech.nm)), 3)  # quarter wavelength snap to grid
wavelength_8 = round(wavelength / 8 - (wavelength / 8) % (ihp.tech.nm), 3)  # eighth wavelength snap to grid


# filter parameters
order = 3                   # order of the band pass filter
bandwidth = 1e9        # 5% bandwidth for input band pass filter
filter_type = "butter"      # type of the band pass filter, can be "butter", "cheby",
connection_length_bpf = 10  # length of the connection piece between the band pass filter and the rest of the circuit
ripple_dB = 3               # ripple in dB for the cheby filter, ignored if the filter type is Butter

# wilkinson power divider parameters
connection_length_wpd = 0  # length of the connection piece of the wilkinson power divider ports
connection_length_bpf_wpd = wavelength_4*3.5/5  # length of the connection piece between the branch line couplers and the rest of the circuit

# branch line coupler parameters
connection_length_blc = 0  # length of the connection piece between the branch line couplers and the rest of the circuit




# ----------------------------------------------------
# begin design

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
    Z0=Z0*1.314,
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


connection_length_wpd_blc_one_leg = blc_1_ref.ports["e1"].center[1] - blc_2_ref.ports["e4"].center[1] - (wpd_ref.ports["e2"].center[1] - wpd_ref.ports["e3"].center[1])


connection_wpd_blc = ihp.cells.tline(
    length=connection_length_wpd_blc_one_leg/2,
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

connection_bpf_wpd = c.add_ref(ihp.cells.tline(
    length=connection_length_bpf_wpd,
    signal_cross_section=signal_cross_section,
    ground_cross_section=ground_cross_section,
    Z0=Z0,
))

connection_bpf_wpd.connect("e1", wpd_ref.ports["e1"])


connection_blc_R_termination = ihp.cells.straight(
    length=30, # manual meassurement to fit the design
    cross_section=signal_cross_section,
    width=ihp.cells.waveguides._calculate_width_from_Z0(Z0=Z0, e_r=e_r, signal_cross_section=signal_cross_section, ground_cross_section=ground_cross_section),
)
connection_blc_R_termination_ref = c.add_ref(connection_blc_R_termination)
connection_blc_R_termination_ref.connect("e1", blc_3_ref.ports["e3"])

via_M1_TM2 = ihp.cells.via_stack(
    top_layer="TopMetal2",
    bottom_layer="Metal1",
    vn_columns=2,
    vn_rows=2,
    vt1_columns=2,
    vt1_rows=2,
    vt2_columns=1,
    vt2_rows=4,
)
via_M1_TM2.ports["top"].orientation = 180
via_M1_TM2.ports["bottom"].orientation = 180
via_M1_TM2_ref = c.add_ref(via_M1_TM2)
via_M1_TM2_ref.connect("top", connection_blc_R_termination_ref.ports["e2"], allow_width_mismatch=True)

R_termination = ihp.cells.rsil(
    resistance=Z0,
    width=0.5,
    length=2.5,
)
R_termination_ref = c.add_ref(R_termination)
R_termination_ref.connect("e1", via_M1_TM2_ref.ports["bottom"], allow_width_mismatch=True, allow_layer_mismatch=True)

via_M1_M5 = ihp.cells.via_stack(
    top_layer="Metal5",
    bottom_layer="Metal1",
    vn_columns=2,
    vn_rows=2,
)
via_M1_M5.ports["top"].orientation = 180
via_M1_M5.ports["bottom"].orientation = 0
via_M1_M5_ref = c.add_ref(via_M1_M5)
via_M1_M5_ref.connect("bottom", R_termination_ref.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)

connection_R_termination_vss = ihp.cells.straight(
    length=10, # manual meassurement to fit the design
    cross_section=ground_cross_section,
    width=2, # manual meassurement to fit the design
)
connection_R_termination_vss_ref = c.add_ref(connection_R_termination_vss)
connection_R_termination_vss_ref.connect("e1", via_M1_M5_ref.ports["top"], allow_width_mismatch=True, allow_layer_mismatch=True)

# r termination metal5 nofill
c.add_ref(gf.components.rectangle(size=(connection_R_termination_vss_ref.xsize+20, connection_R_termination_vss_ref.ysize+20), layer=ihp.tech.LAYER.Metal5nofill)).center = connection_R_termination_vss_ref.center

# bandpass_filter = c.add_ref(ihp.cells.coupled_line_bandpass_filter(
#     frequency=f,
#     bandwidth=bandwidth,
#     order=order,
#     filter_type=filter_type,
#     ripple_dB=ripple_dB,
#     connection_length=connection_length_bpf,
#     signal_cross_section=signal_cross_section,
#     ground_cross_section=ground_cross_section,
#     Z0=Z0,
#     e_r=e_r,
# ))

bandpass_filter = c.add_ref(ihp.cells.hairpin_coupled_line_bandpass_filter(
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
))

bandpass_filter.connect("e1", connection_bpf_wpd.ports["e2"])

connection_bpd_pad = c.add_ref(ihp.cells.straight(
    length=32,
    cross_section=signal_cross_section,
    width=ihp.cells.waveguides._calculate_width_from_Z0(Z0=Z0, e_r=e_r, signal_cross_section=signal_cross_section, ground_cross_section=ground_cross_section),
))
connection_bpd_pad.connect("e1", bandpass_filter.ports["e2"], allow_width_mismatch=True)
# c.add_ports(wpd_ref.ports, prefix="wpd_")
# c.add_ports(blc_1_ref.ports, prefix="blc1_")
# c.add_ports(blc_2_ref.ports, prefix="blc2_")
# c.add_ports(blc_3_ref.ports, prefix="blc3_")


# probe pads left
probe_left = c.add_ref(ihp.cells.bondpad_array(config="GSG", pitch= 125, width_ground=120, width_signal=65, length_signal=65, signal_cross_section="topmetal1_routing", ground_cross_section="metal1_routing", ground_connection='psub')).rotate(-90)
probe_left.center = bandpass_filter.ports["e2"].center
probe_left.xmax = bandpass_filter.ports["e2"].center[0]-15
probe_left.connect("e1", connection_bpd_pad.ports["e2"], allow_width_mismatch=True)

c.add_ref(gf.components.rectangle(size=(105, 105), layer=ihp.tech.LAYER.Metal5nofill)).center = probe_left.center


connection_blc_pad = c.add_ref(ihp.cells.straight(
    length=42,
    cross_section=signal_cross_section,
    width=ihp.cells.waveguides._calculate_width_from_Z0(Z0=Z0, e_r=e_r, signal_cross_section=signal_cross_section, ground_cross_section=ground_cross_section),
))
connection_blc_pad.connect("e1", blc_3_ref.ports["e2"])

# probe pads right
probe_right = c.add_ref(ihp.cells.bondpad_array(config="GSG", pitch= 125, width_ground=125, width_signal=65, length_signal=65, signal_cross_section="topmetal1_routing", ground_cross_section="metal1_routing", ground_connection='psub')).rotate(-90)
probe_right.connect("e1", connection_blc_pad.ports["e2"], allow_width_mismatch=True)

c.add_ref(gf.components.rectangle(size=(105, 105), layer=ihp.tech.LAYER.Metal5nofill)).center = probe_right.center


# probe pads top
_ = c.center
probe_top = c.add_ref(ihp.cells.bondpad_array(config="SSGSGSS", signal_cross_section="topmetal1_routing", ground_cross_section="metal1_routing", ground_connection='psub'))
probe_top.center = _
probe_top.ymax = c.ymax + 225

# no fill VDD
c.add_ref(gf.components.rectangle(size=(110, 110), layer=ihp.tech.LAYER.Metal5nofill)).center = probe_top.center

# no fill top
no_fill_top_left = c.add_ref(gf.components.rectangle(size=(85+125+25, 110), layer=ihp.tech.LAYER.Metal5nofill))
no_fill_top_left.xmin = probe_top.xmin-(110-85)/2
no_fill_top_left.ymin = probe_top.ymin-(110-85)/2

no_fill_top_right = c.add_ref(gf.components.rectangle(size=(85+125+25, 110), layer=ihp.tech.LAYER.Metal5nofill))
no_fill_top_right.xmax = probe_top.xmax+(110-85)/2
no_fill_top_right.ymin = probe_top.ymin-(110-85)/2



# probe pads bottom
probe_bottom = c.add_ref(ihp.cells.bondpad_array(config="SSGSGSS", signal_cross_section="topmetal1_routing", ground_cross_section="metal1_routing", ground_connection='psub')).rotate(180)
probe_bottom.center = _
probe_bottom.ymin = c.ymin - 225

# no fill VDD
c.add_ref(gf.components.rectangle(size=(110, 110), layer=ihp.tech.LAYER.Metal5nofill)).center = probe_bottom.center

# no fill bottom
no_fill_bottom_left = c.add_ref(gf.components.rectangle(size=(85+125+25, 110), layer=ihp.tech.LAYER.Metal5nofill))
no_fill_bottom_left.xmin = probe_bottom.xmin-(110-85)/2
no_fill_bottom_left.ymin = probe_bottom.ymin-(110-85)/2

no_fill_bottom_right = c.add_ref(gf.components.rectangle(size=(85+125+25, 110), layer=ihp.tech.LAYER.Metal5nofill))
no_fill_bottom_right.xmax = probe_bottom.xmax+(110-85)/2
no_fill_bottom_right.ymin = probe_bottom.ymin-(110-85)/2

print(c.xsize, c.ysize)

detector_square = gf.components.rectangle(size=(200, 200), layer=ihp.tech.LAYER.TEXTdrawing)

pd1_center=(-346.14+5.225, 445)
pd2_center=(-137.165-5.225, 445)
pd3_center=(-346.14+5.225, -445)
pd4_center=(-137.165-5.225, -445)

# detector_square_1_ref = c.add_ref(detector_square)
# detector_square_1_ref.center = pd1_center
# c.add_ref(gf.components.text("PD1", size=70, layer=ihp.tech.LAYER.Metal1text)).center = detector_square_1_ref.center

# detector_square_2_ref = c.add_ref(detector_square)
# detector_square_2_ref.center = pd2_center
# c.add_ref(gf.components.text("PD2", size=70, layer=ihp.tech.LAYER.Metal1text)).center = detector_square_2_ref.center


# detector_square_3_ref = c.add_ref(detector_square)
# detector_square_3_ref.center = pd3_center
# c.add_ref(gf.components.text("PD3", size=70, layer=ihp.tech.LAYER.Metal1text)).center = detector_square_3_ref.center


# detector_square_4_ref = c.add_ref(detector_square)
# detector_square_4_ref.center = pd4_center
# c.add_ref(gf.components.text("PD4", size=70, layer=ihp.tech.LAYER.Metal1text)).center = detector_square_4_ref.center


c.add_ref(ihp.cells.sealring(width=1000, height=1300)).center = c.center




# c.flatten()  # flatten the cell to reduce the number of references and speed up rendering
# c.draw_ports()

# pd = power_detector_hbt()

gds_filename = "layout/sparx160_top.gds"

# c = gf.Component("powdet_sbd")
# gds_filename = "powdet_sbd.gds"


# create powerdetector
pd = powdet_sbd()
pd.write_gds("layout/sparx160_powdet_sbd.gds")

# PD1 reference, position and route
pd1_ref = c.add_ref(pd)
pd1_ref.center = pd1_center



# vdd connection of pd1 to probe top
route_pd1_vdd = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd1_ref.ports["vdd"]],
    ports2=[probe_top.ports["e4"]],
    route_width=8,    # adjust for thicker connections
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
    route_width=2,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal5drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# vout connection of pd1 to probe top
via_M4_TM1 = ihp.cells.via_stack(
    top_layer="TopMetal1",
    bottom_layer="Metal4",
    vn_columns=10,
    vn_rows=3,
    vt1_columns=5,
    vt1_rows=1,
)
via_M4_TM1.ports["top"].orientation = 90
via_M4_TM1.ports["bottom"].orientation = 270
via_M4_TM1_ref = c.add_ref(via_M4_TM1)
via_M4_TM1_ref.connect("top", probe_top.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_M4_TM1_ref.move((0, via_M4_TM1_ref.ysize/2))
route_pd1_vout = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd1_ref.ports["vout"]],
    ports2=[via_M4_TM1_ref.ports["bottom"]],
    route_width=4,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal4drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# vref connection of pd1 to probe top
via_M3_TM1 = ihp.cells.via_stack(
    top_layer="TopMetal1",
    bottom_layer="Metal3",
    vn_columns=10,
    vn_rows=3,
    vt1_columns=5,
    vt1_rows=1,
)
via_M3_TM1.ports["top"].orientation = 90
via_M3_TM1.ports["bottom"].orientation = 270
via_M3_TM1_ref = c.add_ref(via_M3_TM1)
via_M3_TM1_ref.connect("top", probe_top.ports["e1"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_M3_TM1_ref.move((0, via_M3_TM1_ref.ysize/2))
route_pd1_vref = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd1_ref.ports["vref"]],
    ports2=[via_M3_TM1_ref.ports["bottom"]],
    route_width=4,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal3drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# rfin connection of pd1 to blc
route_pd1_rfin = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd1_ref.ports["rfin"]],
    ports2=[blc_1_ref.ports["e2"]],
    route_width=blc_1_ref.ports["e2"].width,    
    layer=ihp.tech.LAYER.TopMetal2drawing,
    start_straight_length=6, 
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)


# PD2 reference, position and route
pd2_ref = c.add_ref(pd).mirror_x()
pd2_ref.center = pd2_center

# vdd connection of pd2 to probe top
route_pd2_vdd = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd2_ref.ports["vdd"]],
    ports2=[probe_top.ports["e4"]],
    route_width=8,    # adjust for thicker connections
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
    route_width=2,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal5drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vout connection of pd2 to probe top
via_M4_TM1_ref = c.add_ref(via_M4_TM1)
via_M4_TM1_ref.connect("top", probe_top.ports["e6"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_M4_TM1_ref.move((0, via_M4_TM1_ref.ysize/2))
route_pd2_vout = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd2_ref.ports["vout"]],
    ports2=[via_M4_TM1_ref.ports["bottom"]],
    route_width=4,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal4drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vref connection of pd2 to probe top
via_M3_TM1_ref = c.add_ref(via_M3_TM1)
via_M3_TM1_ref.connect("top", probe_top.ports["e7"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_M3_TM1_ref.move((0, via_M3_TM1_ref.ysize/2))
route_pd2_vref = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd2_ref.ports["vref"]],
    ports2=[via_M3_TM1_ref.ports["bottom"]],
    route_width=4,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal3drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# rfin connection of pd2 to blc
route_pd2_rfin = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd2_ref.ports["rfin"]],
    ports2=[blc_1_ref.ports["e3"]],
    route_width=blc_1_ref.ports["e2"].width,    
    layer=ihp.tech.LAYER.TopMetal2drawing,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# PD3 reference, position and route
pd3_ref = c.add_ref(pd).mirror_y()
pd3_ref.center = pd3_center

# vdd connection of pd3 to probe bottom
route_pd3_vdd = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd3_ref.ports["vdd"]],
    ports2=[probe_bottom.ports["e4"]],
    route_width=8,    # adjust for thicker connections
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
    route_width=2,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal5drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vout connection of pd3 to probe bottom
via_M4_TM1_ref = c.add_ref(via_M4_TM1)
via_M4_TM1_ref.connect("top", probe_bottom.ports["e6"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_M4_TM1_ref.move((0, -via_M4_TM1_ref.ysize/2))

route_pd3_vout = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd3_ref.ports["vout"]],
    ports2=[via_M4_TM1_ref.ports["bottom"]],
    route_width=4,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal4drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vref connection of pd3 to probe bottom
via_M3_TM1_ref = c.add_ref(via_M3_TM1)
via_M3_TM1_ref.connect("top", probe_bottom.ports["e7"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_M3_TM1_ref.move((0, -via_M3_TM1_ref.ysize/2))
route_pd3_vref = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd3_ref.ports["vref"]],
    ports2=[via_M3_TM1_ref.ports["bottom"]],
    route_width=4,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal3drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# rfin connection of pd3 to blc
route_pd3_rfin = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd3_ref.ports["rfin"]],
    ports2=[blc_2_ref.ports["e3"]],
    route_width=blc_2_ref.ports["e2"].width,    
    layer=ihp.tech.LAYER.TopMetal2drawing,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)


# PD4 reference, position and route
pd4_ref = c.add_ref(pd).mirror_x().mirror_y()
pd4_ref.center = pd4_center

# vdd connection of pd4 to probe bottom
route_pd4_vdd = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd4_ref.ports["vdd"]],
    ports2=[probe_bottom.ports["e4"]],
    route_width=8,    # adjust for thicker connections
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
    route_width=2,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal5drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vout connection of pd4 to probe bottom
via_M4_TM1_ref = c.add_ref(via_M4_TM1)
via_M4_TM1_ref.connect("top", probe_bottom.ports["e2"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_M4_TM1_ref.move((0, -via_M4_TM1_ref.ysize/2))
route_pd4_vout = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd4_ref.ports["vout"]],
    ports2=[via_M4_TM1_ref.ports["bottom"]],
    route_width=4,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal4drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)
# vref connection of pd4 to probe bottom
via_M3_TM1_ref = c.add_ref(via_M3_TM1)
via_M3_TM1_ref.connect("top", probe_bottom.ports["e1"], allow_width_mismatch=True, allow_layer_mismatch=True)
via_M3_TM1_ref.move((0, -via_M3_TM1_ref.ysize/2))
route_pd4_vref = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd4_ref.ports["vref"]],
    ports2=[via_M3_TM1_ref.ports["bottom"]],
    route_width=4,    # adjust for thicker connections
    layer=ihp.tech.LAYER.Metal3drawing,
    start_straight_length=10, # 10 or longer, to avoid routing through itself
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)

# rfin connection of pd4 to blc
route_pd4_rfin = gf.routing.route_bundle_electrical(
    component=c,
    ports1=[pd4_ref.ports["rfin"]],
    ports2=[blc_2_ref.ports["e2"]],
    route_width=blc_2_ref.ports["e2"].width,    
    layer=ihp.tech.LAYER.TopMetal2drawing,
    allow_layer_mismatch=True,
    allow_width_mismatch=True,
    auto_taper=False,
    separation=0,
)




if fill == 1:
    # active/gat poly fill
    gatpoly_activ_fill_space = 1
    c.fill(
        fill_cell=fill_gat_active( size=(3, 3)),
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
if fill_M5 == 1:
    # metal5 fill (groundplate)
    c.fill(fill_cell=fill_ground(),
        fill_layers=[(ihp.tech.LAYER.EdgeSealboundary, -50)],
        exclude_layers=[(ihp.tech.LAYER.Passivdrawing, 0), 
        (ihp.tech.LAYER.Metal5nofill, 0)],
        x_space=0,
        y_space=0,
    )
    c.fill(fill_cell=slit_ground(),
        fill_layers=[(ihp.tech.LAYER.Metal5drawing, -2)],
        exclude_layers=[(ihp.tech.LAYER.TopMetal2drawing, 5), (ihp.tech.LAYER.MIMdrawing, 1), (ihp.tech.LAYER.Metal5slit, 1)],
        x_space=1.1,
        y_space=1.2,
    )
if fill == 1:
    # topmetal1 fill
    c.fill(
        fill_cell=fill_cell(layer=ihp.tech.LAYER.TopMetal1filler, size=(9, 9)),
        fill_layers=[(ihp.tech.LAYER.EdgeSealboundary, -50)],
        exclude_layers=[(ihp.tech.LAYER.TopMetal1drawing, 10), (ihp.tech.LAYER.TopMetal2drawing, 20)],
        x_space=3,
        y_space=3,
    )


# place logos
logo_dir = Path(__file__).parent / "assets"

logo_png_path = logo_dir / "jku_logo.png"
logo_gds_path = logo_dir / "jku_logo_m5.gds"

kellerer_png_path = logo_dir / "D_Kellerer.png"
kellerer_gds_path = logo_dir / "D_Kellerer.gds"

iws_png_path = logo_dir / "IWS.png"
iws_gds_path = logo_dir / "IWS.gds"

helper_png_path = logo_dir / "helper.png"
helper_gds_path = logo_dir / "helper.gds"

tm1_layer = ihp.tech.LAYER.TopMetal2drawing
tm1_foreground = f"{tm1_layer[0]}/{tm1_layer[1]}"


pxl_size = 2
if not logo_gds_path.exists():
    make_gds.convert_to_gds(
        input_filepath=str(logo_png_path),
        output_filepath=str(logo_gds_path),
        cellname="JKU_LOGO",
        scale=0.15,
        threshold=128,
        invert=True,
        merge=True,
        pixel_size=pxl_size,
        foreground=tm1_foreground,
        boundaries=[],
    )

if not kellerer_gds_path.exists():
    make_gds.convert_to_gds(
        input_filepath=str(kellerer_png_path),
        output_filepath=str(kellerer_gds_path),
        cellname="Name_D",
        scale=0.15,
        threshold=128,
        invert=True,
        merge=True,
        pixel_size=pxl_size,
        foreground=tm1_foreground,
        boundaries=[],
    )

if not iws_gds_path.exists():
    make_gds.convert_to_gds(
        input_filepath=str(iws_png_path),
        output_filepath=str(iws_gds_path),
        cellname="Logo_IWS",
        scale=0.3,
        threshold=128,
        invert=True,
        merge=True,
        pixel_size=pxl_size,
        foreground=tm1_foreground,
        boundaries=[],
    )

if not helper_gds_path.exists():
    make_gds.convert_to_gds(
        input_filepath=str(helper_png_path),
        output_filepath=str(helper_gds_path),
        cellname="helper",
        scale=0.15,
        threshold=128,
        invert=True,
        merge=True,
        pixel_size=pxl_size,
        foreground=tm1_foreground,
        boundaries=[],
    )

logo_jku = c.add_ref(gf.import_gds(str(logo_gds_path), cellname="JKU_LOGO"))

logo_jku.move((-50,-420))

kellerer = c.add_ref(gf.import_gds(str(kellerer_gds_path), cellname="Name_D"))

iws = c.add_ref(gf.import_gds(str(iws_gds_path), cellname="Logo_IWS"))


kellerer.rotate(-90)

kellerer.move((-690, 430))

iws.move((-120,130))

helper = c.add_ref(gf.import_gds(str(helper_gds_path), cellname="helper")).rotate(-90)
helper.xmin = kellerer.xmin
helper.ymax = kellerer.ymin - 550

if fill == 1:
    # topmetal2 fill
    c.fill(
        fill_cell=fill_cell(layer=ihp.tech.LAYER.TopMetal2filler, size=(9, 9)),
        fill_layers=[(ihp.tech.LAYER.EdgeSealboundary, -50)],
        exclude_layers=[(ihp.tech.LAYER.TopMetal2drawing, 20)],
        x_space=3,
        y_space=3,
    )

# c.add_ports(pd1_ref.ports, prefix="PD1_")
# c.add_ports(probe_left.ports, prefix="probebottom_")
# c.add_ports(pd1_ref.ports, prefix="PD1_")
# c.draw_ports()
# c.flatten()
c.xmin = 0
c.ymin = 0
c.move((-25, -25))





c.write_gds(gds_filename)
c.show()

# pd.draw_ports()
# pd.show()



