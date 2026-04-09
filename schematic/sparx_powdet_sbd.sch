v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {Schottky-diode based RF demodulator} 460 -970 0 0 0.5 0.5 {}
T {- R1 provides a 50 Ohm termination, C1 ac-couples the RF+LO input signal to the demodulating D1.
- M1-2 and R2 form a transimpedance amplifier (TIA), which provides a buffered voltage output signal.
- M3-4, D2, and R3-5 implement a replica bias, whose voltage is decoupled by C2, and provided externally.
- The values of C2-3 can be adapted to layout needs, as long as they stay large enough.
- Layout: Minimize parasitics (RLC) of rfin/rfin_in.
- Layout: Match components of main and replica path.} 140 -900 0 0 0.4 0.4 {}
T {4mA} 790 -270 0 0 0.3 0.3 {}
T {400uA} 1020 -270 0 0 0.3 0.3 {}
T {nom. 1.5V} 220 -660 0 0 0.3 0.3 {}
T {1.1V} 430 -450 0 0 0.2 0.2 {}
T {0.72V} 1100 -450 0 0 0.2 0.2 {}
T {0.72V} 1100 -520 0 0 0.2 0.2 {}
T {0.75V} 550 -450 0 0 0.2 0.2 {}
N 160 -430 210 -430 {lab=rfin}
N 810 -430 810 -400 {lab=vout}
N 810 -460 810 -430 {lab=vout}
N 670 -430 710 -430 {lab=bb_int}
N 670 -490 670 -430 {lab=bb_int}
N 670 -490 770 -490 {lab=bb_int}
N 670 -430 670 -370 {lab=bb_int}
N 670 -370 770 -370 {lab=bb_int}
N 590 -280 810 -280 {lab=vss}
N 1040 -280 1220 -280 {lab=vss}
N 810 -640 1040 -640 {lab=vdd}
N 810 -430 1550 -430 {lab=vout}
N 410 -500 410 -430 {lab=rfin_int}
N 410 -600 410 -560 {lab=bias1}
N 590 -600 590 -360 {lab=bias1}
N 1040 -500 1550 -500 {lab=vref}
N 410 -600 590 -600 {lab=bias1}
N 1040 -500 1040 -360 {lab=vref}
N 940 -500 940 -330 {lab=bias2}
N 770 -430 810 -430 {lab=vout}
N 540 -430 670 -430 {lab=bb_int}
N 270 -430 410 -430 {lab=rfin_int}
N 410 -430 480 -430 {lab=rfin_int}
N 730 -590 730 -540 {lab=sub}
N 370 -600 410 -600 {lab=bias1}
N 210 -640 810 -640 {lab=vdd}
N 210 -600 310 -600 {lab=vdd}
N 160 -640 210 -640 {lab=vdd}
N 940 -600 1000 -600 {lab=bias2}
N 1020 -500 1040 -500 {lab=vref}
N 940 -500 960 -500 {lab=bias2}
N 770 -600 940 -600 {lab=bias2}
N 590 -600 620 -600 {lab=bias1}
N 680 -600 710 -600 {lab=#net1}
N 940 -600 940 -500 {lab=bias2}
N 1040 -570 1040 -500 {lab=vref}
N 810 -280 1040 -280 {lab=vss}
N 940 -330 1000 -330 {lab=bias2}
N 1520 -280 1580 -280 {lab=vss}
N 1220 -640 1320 -640 {lab=vdd}
N 1220 -590 1280 -590 {lab=vdd}
N 1220 -540 1320 -540 {lab=vdd}
N 1220 -590 1220 -540 {lab=vdd}
N 1040 -640 1220 -640 {lab=vdd}
N 1320 -560 1320 -540 {lab=vdd}
N 810 -640 810 -520 {lab=vdd}
N 1040 -640 1040 -630 {lab=vdd}
N 210 -640 210 -600 {lab=vdd}
N 1220 -640 1220 -590 {lab=vdd}
N 1320 -640 1320 -620 {lab=vdd}
N 1380 -590 1430 -590 {lab=nw}
N 1220 -540 1220 -360 {lab=vdd}
N 1490 -640 1490 -620 {lab=vdd}
N 1320 -640 1490 -640 {lab=vdd}
N 1040 -600 1090 -600 {lab=nw}
N 810 -490 860 -490 {lab=nw}
N 1520 -330 1540 -330 {lab=vss}
N 1580 -380 1580 -360 {lab=vss}
N 1520 -380 1580 -380 {lab=vss}
N 1520 -380 1520 -330 {lab=vss}
N 1580 -280 1680 -280 {lab=vss}
N 590 -300 590 -280 {lab=vss}
N 810 -340 810 -280 {lab=vss}
N 1040 -300 1040 -280 {lab=vss}
N 1220 -300 1220 -280 {lab=vss}
N 160 -280 590 -280 {lab=vss}
N 1520 -330 1520 -280 {lab=vss}
N 1580 -300 1580 -280 {lab=vss}
N 1680 -300 1680 -280 {lab=vss}
N 1580 -330 1650 -330 {lab=sub}
N 1040 -330 1090 -330 {lab=sub}
N 810 -370 860 -370 {lab=sub}
N 500 -420 500 -240 {lab=sub}
N 1220 -360 1390 -360 {lab=vdd}
N 1390 -300 1390 -280 {lab=vss}
N 1390 -280 1520 -280 {lab=vss}
N 1220 -280 1390 -280 {lab=vss}
N 1680 -380 1680 -360 {lab=sub}
N 1490 -560 1490 -540 {lab=nw}
N 1430 -590 1430 -540 {lab=nw}
N 1430 -540 1490 -540 {lab=nw}
N 1650 -380 1650 -330 {lab=sub}
N 1650 -380 1680 -380 {lab=sub}
N 860 -680 860 -490 {lab=nw}
N 1090 -680 1380 -680 {lab=nw}
N 1380 -680 1380 -590 {lab=nw}
N 1320 -590 1380 -590 {lab=nw}
N 1090 -680 1090 -600 {lab=nw}
N 860 -680 1090 -680 {lab=nw}
N 1090 -240 1650 -240 {lab=sub}
N 1650 -330 1650 -240 {lab=sub}
N 680 -540 730 -540 {lab=sub}
N 680 -540 680 -240 {lab=sub}
N 500 -240 680 -240 {lab=sub}
N 860 -370 860 -240 {lab=sub}
N 680 -240 860 -240 {lab=sub}
N 1090 -330 1090 -240 {lab=sub}
N 860 -240 1090 -240 {lab=sub}
C {ipin.sym} 160 -430 0 0 {name=p2 lab=rfin}
C {opin.sym} 1550 -430 0 0 {name=p3 lab=vout}
C {iopin.sym} 160 -280 0 1 {name=p4 lab=vss}
C {title.sym} 160 0 0 0 {name=l2 author="(c) 2026 Harald Pretl ICD@JKU"}
C {rsil.sym} 410 -530 0 0 {name=R1
w=0.5e-6
l=2.5e-6
model=rsil
body=VSS
spiceprefix=X
b=0
m=1
}
C {schottky_nbl1.sym} 510 -430 1 0 {name=D1
model=schottky_nbl1
Nx=1
Ny=1
spiceprefix=X
}
C {lab_wire.sym} 360 -430 0 0 {name=p5 sig_type=std_logic lab=rfin_int}
C {ipin.sym} 160 -640 0 0 {name=p6 lab=vdd}
C {cap_cmim.sym} 590 -330 0 0 {name=C2
model=cap_cmim
w=10e-6
l=10e-6
m=30
spiceprefix=X}
C {annotate_fet_params.sym} 670 -200 0 0 {name=annot1 ref=M1}
C {annotate_fet_params.sym} 830 -200 0 0 {name=annot2 ref=M2}
C {opin.sym} 1550 -500 0 0 {name=p12 lab=vref}
C {sg13_lv_pmos.sym} 790 -490 0 0 {name=M2
l=0.13u
w=100u
ng=20
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {sg13_lv_nmos.sym} 790 -370 0 0 {name=M1
l=0.13u
w=50u
ng=20
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {rppd.sym} 740 -430 1 0 {name=R2
w=0.5e-6
l=1.5e-6
model=rppd
body=VSS
spiceprefix=X
b=0
m=1
}
C {sg13_lv_pmos.sym} 1020 -600 0 0 {name=M4
l=0.13u
w=10u
ng=2
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {sg13_lv_nmos.sym} 1020 -330 0 0 {name=M3
l=0.13u
w=5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {cap_cmim.sym} 1220 -330 0 0 {name=C3
model=cap_cmim
w=10e-6
l=10e-6
m=28
spiceprefix=X}
C {lab_wire.sym} 650 -430 0 0 {name=p7 sig_type=std_logic lab=bb_int}
C {annotate_fet_params.sym} 990 -200 0 0 {name=annot3 ref=M3}
C {annotate_fet_params.sym} 1140 -200 0 0 {name=annot4 ref=M4}
C {schottky_nbl1.sym} 740 -600 1 0 {name=D2
model=schottky_nbl1
Nx=1
Ny=1
spiceprefix=X
}
C {rhigh.sym} 340 -600 1 0 {name=R3
w=0.5e-6
l=2e-6
model=rhigh
body=VSS
spiceprefix=X
b=0
m=1
}
C {lab_wire.sym} 500 -600 0 0 {name=p9 sig_type=std_logic lab=bias1}
C {rppd.sym} 990 -500 1 0 {name=R4
w=0.5e-6
l=1.5e-6
model=rppd
body=VSS
spiceprefix=X
b=0
m=1
}
C {rsil.sym} 650 -600 1 0 {name=R5
w=0.5e-6
l=2.5e-6
model=rsil
body=VSS
spiceprefix=X
b=0
m=1
}
C {lab_wire.sym} 940 -600 0 0 {name=p11 sig_type=std_logic lab=bias2}
C {sg13_lv_nmos.sym} 1560 -330 0 0 {name=M5_dummy
l=0.13u
w=5u
ng=2
m=1
model=sg13_lv_nmos
spiceprefix=X
}
C {sg13_lv_pmos.sym} 1300 -590 0 0 {name=M6_dummy
l=0.13u
w=10u
ng=2
m=1
model=sg13_lv_pmos
spiceprefix=X
}
C {cap_cmim.sym} 240 -430 3 0 {name=C1
model=cap_cmim
w=10e-6
l=10e-6
m=1
spiceprefix=X}
C {ntap1_ring.sym} 1490 -590 0 0 {name=Rntap
model=ntap1
spiceprefix=X
w=9.62e-6
l=17.16e-6
lvs_ignore=short
}
C {lab_pin.sym} 1490 -540 3 0 {name=p16 sig_type=std_logic lab=nw lvs_ignore=open}
C {ptap1_ring.sym} 1680 -330 2 1 {name=Rptap
model=ptap1
spiceprefix=X
w=6.86e-6
l=16.54e-6
lvs_ignore=short
}
C {lab_pin.sym} 1680 -380 1 0 {name=p13 sig_type=std_logic lab=sub lvs_ignore=open}
C {cap_cmim.sym} 1390 -330 0 0 {name=C4
model=cap_cmim
w=6.8e-6
l=9e-6
m=2
spiceprefix=X}
