v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
B 4 80 -1040 2060 -960 {fill = false}
B 4 1020 -800 1660 -420 {dash = 8
fill = false}
B 4 260 -800 820 -420 {dash = 8
fill = false}
B 4 1680 -800 2220 -420 {dash = 8
fill = false}
B 4 2240 -800 2460 -420 {dash = 8
fill = false}
T {Schottky Barrier Diode Based Power Detector} 620 -1720 0 0 1 1 {}
T {Circuit Operation:
- R1 provides a 50 Ω input termination.
- C1 ac-couples the RF + LO signal to the demodulating SBD D1 and is implemented as a MIM capacitor.
- M1–M2 and R2 form a transimpedance amplifier (TIA) that delivers a buffered voltage output.
- M3–M4, D2, and R3–R5 implement a replica bias. With this replica circuit, it is now possible to measure the demodulated output signal differentially.
- C2-C4 are MIM capacitor arrays which provide proper supply-rail decoupling.

Layout Considerations:
- Minimize RF input parasitics (R, L, C):
    - Route TopMetal2 directly down to the top plate (TopMetal1) of C1with a VIA.
    - Use a VIA-stack from the bottom plate (Metal5) of C1 directly down to the SBD.
- Apply Metal5 no-fill regions to reduce parasitic capacitance.
- Match components of the main and replica paths.
- C2–C4 values may be adapted to layout requirements, provided they remain large enough for sufficient supply-rail decoupling.} 80 -1600 0 0 0.6 0.6 {}
T {4mA} 680 -390 0 0 0.3 0.3 {}
T {400uA} 1170 -390 0 1 0.3 0.3 {}
T {nom. 1.5V} 100 -910 0 0 0.3 0.3 {}
T {1.128V} 350 -640 0 0 0.2 0.2 {}
T {0.737V} 1125 -640 0 1 0.2 0.2 {}
T {0.730V} 750 -640 0 1 0.2 0.2 {}
T {0.756V} 470 -640 0 0 0.2 0.2 {}
T {Note that the nw and sub nets are using conditional net labels! Adding further labels also needs to have these options set!!!} 90 -1020 0 0 0.6 0.6 {}
T {Replica Circuit} 1502.5 -450 0 0 0.4 0.4 {}
T {Power Detector Circuit} 267.5 -450 0 0 0.4 0.4 {}
T {Decoupling
Capacitors} 1962.5 -475 0 0 0.4 0.4 {}
T {Dummy
Transistors} 2262.5 -645 0 0 0.4 0.4 {}
T {1.129V} 350 -830 0 0 0.2 0.2 {}
T {0.761V} 1275 -640 0 1 0.2 0.2 {}
N 320 -690 320 -620 {lab=rfin_int}
N 320 -620 400 -620 {lab=rfin_int}
N 140 -880 700 -880 {lab=vdd}
N 2260 -760 2300 -760 {lab=vdd}
N 700 -760 760 -760 {lab=nw}
N 700 -480 760 -480 {lab=sub}
N 560 -620 560 -480 {lab=bb_int}
N 660 -620 700 -620 {lab=vout}
N 700 -620 700 -510 {lab=vout}
N 700 -730 700 -620 {lab=vout}
N 700 -450 700 -400 {lab=vss}
N 560 -620 600 -620 {lab=bb_int}
N 560 -760 560 -620 {lab=bb_int}
N 560 -760 660 -760 {lab=bb_int}
N 560 -480 660 -480 {lab=bb_int}
N 700 -620 840 -620 {lab=vout}
N 460 -620 560 -620 {lab=bb_int}
N 700 -880 700 -790 {lab=vdd}
N 1140 -620 1140 -510 {lab=vref}
N 1080 -760 1140 -760 {lab=nw}
N 1080 -480 1140 -480 {lab=sub}
N 1140 -730 1140 -620 {lab=vref}
N 1140 -620 1180 -620 {lab=vref}
N 1240 -620 1280 -620 {lab=bias2}
N 1180 -760 1280 -760 {lab=bias2}
N 1280 -760 1280 -620 {lab=bias2}
N 1280 -620 1280 -480 {lab=bias2}
N 1180 -480 1280 -480 {lab=bias2}
N 1140 -450 1140 -400 {lab=vss}
N 1140 -880 1140 -790 {lab=vdd}
N 1280 -620 1380 -620 {lab=bias2}
N 1440 -620 1520 -620 {lab=#net1}
N 1520 -690 1520 -620 {lab=#net1}
N 1000 -620 1140 -620 {lab=vref}
N 1760 -560 1760 -400 {lab=vss}
N 1760 -400 1940 -400 {lab=vss}
N 1940 -560 1940 -400 {lab=vss}
N 2120 -560 2120 -400 {lab=vss}
N 2260 -880 2340 -880 {lab=vdd}
N 1940 -880 1940 -620 {lab=vdd}
N 2120 -880 2120 -620 {lab=vdd}
N 140 -880 140 -840 {lab=vdd}
N 1760 -840 1760 -620 {lab=bias1}
N 1520 -840 1520 -750 {lab=bias1}
N 320 -840 1520 -840 {lab=bias1}
N 320 -840 320 -750 {lab=bias1}
N 260 -840 320 -840 {lab=bias1}
N 140 -840 200 -840 {lab=vdd}
N 920 -880 1140 -880 {lab=vdd}
N 920 -400 1140 -400 {lab=vss}
N 920 -740 920 -720 {lab=nw}
N 920 -880 920 -800 {lab=vdd}
N 700 -880 920 -880 {lab=vdd}
N 920 -520 920 -500 {lab=sub}
N 920 -440 920 -400 {lab=vss}
N 700 -400 920 -400 {lab=vss}
N 1420 -610 1420 -540 {lab=sub}
N 420 -610 420 -540 {lab=sub}
N 1140 -880 1940 -880 {lab=vdd}
N 1520 -840 1760 -840 {lab=bias1}
N 1940 -880 2120 -880 {lab=vdd}
N 1940 -400 2120 -400 {lab=vss}
N 2340 -480 2400 -480 {lab=sub}
N 2340 -760 2400 -760 {lab=nw}
N 2260 -480 2300 -480 {lab=vss}
N 2260 -400 2340 -400 {lab=vss}
N 2340 -880 2340 -790 {lab=vdd}
N 2340 -730 2340 -700 {lab=vdd}
N 2260 -700 2340 -700 {lab=vdd}
N 2260 -760 2260 -700 {lab=vdd}
N 2340 -540 2340 -510 {lab=vss}
N 2260 -540 2340 -540 {lab=vss}
N 2260 -540 2260 -480 {lab=vss}
N 2260 -480 2260 -400 {lab=vss}
N 2340 -450 2340 -400 {lab=vss}
N 2120 -400 2260 -400 {lab=vss}
N 2260 -880 2260 -760 {lab=vdd}
N 2120 -880 2260 -880 {lab=vdd}
N 100 -620 160 -620 {lab=rfin}
N 100 -880 140 -880 {lab=vdd}
N 220 -620 320 -620 {lab=rfin_int}
N 100 -400 700 -400 {lab=vss}
N 1140 -400 1760 -400 {lab=vss}
C {ipin.sym} 100 -620 0 0 {name=p2 lab=rfin}
C {opin.sym} 840 -620 0 0 {name=p3 lab=vout}
C {iopin.sym} 100 -400 0 1 {name=p4 lab=vss}
C {rsil.sym} 320 -720 0 0 {name=R1
w=0.5e-6
l=2.5e-6
model=rsil
body="tcleval([expr \{$lvs_ignore ? \{vss\} : \{sub\}\}])"
spiceprefix=X
b=0
m=1
}
C {schottky_nbl1.sym} 430 -620 1 0 {name=D1
model=schottky_nbl1
Nx=1
Ny=1
spiceprefix=X
}
C {lab_wire.sym} 320 -620 0 0 {name=p5 sig_type=std_logic lab=rfin_int}
C {ipin.sym} 100 -880 0 0 {name=p6 lab=vdd}
C {cap_cmim.sym} 1760 -590 0 0 {name=C2
model=cap_cmim
w=10e-6
l=10e-6
m=30
spiceprefix=X}
C {annotate_fet_params.sym} 570 -340 0 0 {name=annot1 ref=M1}
C {annotate_fet_params.sym} 730 -340 0 0 {name=annot2 ref=M2}
C {opin.sym} 1000 -620 0 1 {name=p12 lab=vref}
C {sg13_lv_pmos.sym} 680 -760 0 0 {name=M2
l=0.13u
w=100u
ng=20
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {sg13_lv_nmos.sym} 680 -480 0 0 {name=M1
l=0.13u
w=50u
ng=20
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {rppd.sym} 630 -620 1 0 {name=R2
w=0.5e-6
l=1.5e-6
model=rppd
body="tcleval([expr \{$lvs_ignore ? \{vss\} : \{sub\}\}])"
spiceprefix=X
b=0
m=1
}
C {sg13_lv_pmos.sym} 1160 -760 0 1 {name=M4
l=0.13u
w=10u
ng=2
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {sg13_lv_nmos.sym} 1160 -480 0 1 {name=M3
l=0.13u
w=5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {cap_cmim.sym} 1940 -590 0 0 {name=C3
model=cap_cmim
w=10e-6
l=10e-6
m=28
spiceprefix=X}
C {lab_wire.sym} 560 -620 0 0 {name=p7 sig_type=std_logic lab=bb_int}
C {annotate_fet_params.sym} 1030 -340 0 0 {name=annot3 ref=M3}
C {annotate_fet_params.sym} 1180 -340 0 0 {name=annot4 ref=M4}
C {schottky_nbl1.sym} 1410 -620 3 1 {name=D2
model=schottky_nbl1
Nx=1
Ny=1
spiceprefix=X
}
C {rhigh.sym} 230 -840 1 0 {name=R3
w=0.5e-6
l=2e-6
model=rhigh
body="tcleval([expr \{$lvs_ignore ? \{vss\} : \{sub\}\}])"
spiceprefix=X
b=0
m=1
}
C {lab_wire.sym} 320 -840 0 1 {name=p9 sig_type=std_logic lab=bias1}
C {rppd.sym} 1210 -620 3 1 {name=R4
w=0.5e-6
l=1.5e-6
model=rppd
body="tcleval([expr \{$lvs_ignore ? \{vss\} : \{sub\}\}])"
spiceprefix=X
b=0
m=1
}
C {rsil.sym} 1520 -720 0 0 {name=R5
w=0.5e-6
l=2.5e-6
model=rsil
body="tcleval([expr \{$lvs_ignore ? \{vss\} : \{sub\}\}])"
spiceprefix=X
b=0
m=1
}
C {lab_wire.sym} 1280 -620 0 1 {name=p11 sig_type=std_logic lab=bias2}
C {sg13_lv_nmos.sym} 2320 -480 0 0 {name=Mdummy1
l=0.13u
w=5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 2320 -760 0 0 {name=Mdummy2
l=0.13u
w=10u
ng=2
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {cap_cmim.sym} 190 -620 3 1 {name=C1
model=cap_cmim
w=10e-6
l=10e-6
m=1
spiceprefix=X}
C {ntap1_ring.sym} 920 -770 0 0 {name=Rntap
model=ntap1
spiceprefix=X
w=9.62e-6
l=17.16e-6
lvs_ignore=short
}
C {lab_pin.sym} 920 -720 0 0 {name=p16 sig_type=std_logic lab="tcleval([expr \{$lvs_ignore ? \{vdd\} : \{nw\}\}])"}
C {lab_pin.sym} 2400 -760 2 0 {name=p8 sig_type=std_logic lab="tcleval([expr \{$lvs_ignore ? \{vdd\} : \{nw\}\}])"}
C {lab_pin.sym} 1080 -760 2 1 {name=p10 sig_type=std_logic lab="tcleval([expr \{$lvs_ignore ? \{vdd\} : \{nw\}\}])"}
C {lab_pin.sym} 760 -760 2 0 {name=p14 sig_type=std_logic lab="tcleval([expr \{$lvs_ignore ? \{vdd\} : \{nw\}\}])"}
C {ptap1_ring.sym} 920 -470 2 1 {name=Rptap
model=ptap1
spiceprefix=X
w=6.86e-6
l=16.54e-6
lvs_ignore=short
}
C {lab_pin.sym} 920 -520 0 0 {name=p13 sig_type=std_logic lab="tcleval([expr \{$lvs_ignore ? \{vss\} : \{sub\}\}])"}
C {lab_pin.sym} 2400 -480 2 0 {name=p15 sig_type=std_logic lab="tcleval([expr \{$lvs_ignore ? \{vss\} : \{sub\}\}])"}
C {lab_pin.sym} 1080 -480 2 1 {name=p17 sig_type=std_logic lab="tcleval([expr \{$lvs_ignore ? \{vss\} : \{sub\}\}])"}
C {lab_pin.sym} 760 -480 2 0 {name=p18 sig_type=std_logic lab="tcleval([expr \{$lvs_ignore ? \{vss\} : \{sub\}\}])"}
C {lab_pin.sym} 420 -540 0 0 {name=p19 sig_type=std_logic lab="tcleval([expr \{$lvs_ignore ? \{vss\} : \{sub\}\}])"
}
C {lab_pin.sym} 1420 -540 0 1 {name=p1 sig_type=std_logic lab="tcleval([expr \{$lvs_ignore ? \{vss\} : \{sub\}\}])"}
C {cap_cmim.sym} 2120 -590 0 0 {name=C4
model=cap_cmim
w=6.8e-6
l=9e-6
m=2
spiceprefix=X}
C {title-3.sym} 0 0 0 0 {name=l4 author="(c) 2026 H. Pretl, ICD@JKU" rev=1.0 lock=true}
