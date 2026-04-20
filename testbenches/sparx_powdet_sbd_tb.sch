v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {This is only need for .sp simulation,
as two ports are required. However, we
are only interested in S11.} 1000 -340 0 0 0.3 0.3 {}
T {Ngspice Testbench for SBD-Based Power Detector} 600 -1720 0 0 1 1 {}
T {SPDX-FileCopyrightText: 2025-2026 The SPARX Team
SPDX-License-Identifier: Apache-2.0} 1920 -220 0 0 0.4 0.4 {}
N 800 -400 800 -380 {
lab=GND}
N 1080 -480 1240 -480 {lab=rfdummy}
N 1020 -620 1020 -540 {lab=gnd_local}
N 1020 -700 1020 -680 {lab=#net1}
N 1020 -900 1020 -760 {lab=rfin}
N 1400 -540 1560 -540 {lab=gnd_local}
N 1400 -1040 1400 -960 {lab=vdd}
N 800 -540 1020 -540 {lab=gnd_local}
N 1660 -760 1800 -760 {lab=out_cm}
N 1840 -710 1840 -540 {lab=gnd_local}
N 1840 -830 1840 -770 {lab=out}
N 1560 -880 1560 -720 {lab=ref}
N 1560 -720 1800 -720 {lab=ref}
N 800 -620 800 -540 {lab=gnd_local}
N 800 -1040 800 -680 {lab=vdd}
N 1660 -540 1840 -540 {lab=gnd_local}
N 1660 -600 1660 -540 {lab=gnd_local}
N 1560 -540 1660 -540 {lab=gnd_local}
N 1560 -600 1560 -540 {lab=gnd_local}
N 1560 -720 1560 -660 {lab=ref}
N 1660 -760 1660 -660 {lab=out_cm}
N 1660 -920 1660 -760 {lab=out_cm}
N 1020 -900 1320 -900 {lab=rfin}
N 1400 -840 1400 -540 {lab=gnd_local}
N 1020 -540 1400 -540 {lab=gnd_local}
N 800 -540 800 -460 {lab=gnd_local}
N 1080 -400 1080 -380 {lab=GND}
N 1240 -400 1240 -380 {lab=GND}
N 1240 -480 1240 -460 {lab=rfdummy}
N 1080 -480 1080 -460 {lab=rfdummy}
N 800 -1040 1400 -1040 {lab=vdd}
N 1480 -920 1660 -920 {lab=out_cm}
N 1480 -880 1560 -880 {lab=ref}
C {devices/vsource.sym} 800 -430 0 0 {name=Vss value=0}
C {devices/gnd.sym} 800 -380 0 0 {name=l2 lab=GND}
C {devices/lab_pin.sym} 800 -480 0 1 {name=p1 sig_type=std_logic lab=gnd_local}
C {devices/vsource.sym} 1020 -730 0 0 {name=Vin3 value="dc 0 ac 0 portnum 1 sin(0 \{rf_lev\} \{rf_freq\})"}
C {devices/lab_pin.sym} 1020 -900 0 0 {name=p4 sig_type=std_logic lab=rfin}
C {devices/code_shown.sym} 2000 -1350 0 0 {name=MODEL only_toplevel=true
format="tcleval( @value )"
value="
.lib cornerDIO.lib dio_tt
.lib cornerMOSlv.lib mos_tt
.lib cornerRES.lib res_typ
.lib cornerCAP.lib cap_typ
"}
C {devices/code_shown.sym} 100 -1330 0 0 {name=NGSPICE only_toplevel=true 
value="
.include ../../netlist/pex/sparx_powdet_sbd_magic_pex.spice
* .include ../../netlist/pex/sparx_powdet_sbd_klayout_pex.spice
.temp 27
.option method=gear
.save all
.include sparx_powdet_sbd_tb.save
.param lo_freq=149G
.param lo_lev=100m
.param rf_freq=151G
.param rf_lev=1m
.control
set num_threads=8
*set specwindow=blackman

let lo_freq = 149G
let rf_freq = 151G
let if_freq = rf_freq - lo_freq

op
write sparx_powdet_sbd_tb.raw
set appendwrite

sp lin 31 100G 200G 0
write sparx_powdet_sbd_tb.raw

ac dec 1001 1MEG 10G
write sparx_powdet_sbd_tb.raw

tran 0.05p 22n 20n
write sparx_powdet_sbd_tb.raw

linearize rfin out
setplot tran2
fft rfin
plot db(rfin)
meas sp lo_tone FIND v(rfin) AT=$&lo_freq
meas sp rf_tone FIND v(rfin) AT=$&rf_freq
print lo_tone > result.txt
print rf_tone >> result.txt
setplot tran2
fft out
plot db(out)
meas sp if_tone FIND v(out) AT=$&if_freq
print if_tone >> result.txt

*exit
.endc
"
}
C {devices/launcher.sym} 1780 -1360 0 0 {name=h2
descr="simulate" 
tclcommand="xschem save; xschem netlist; xschem simulate"
}
C {devices/launcher.sym} 1780 -1300 0 0 {name=h3
descr="annotate OP" 
tclcommand="set show_hidden_texts 1; xschem annotate_op"
}
C {devices/lab_pin.sym} 1660 -920 0 1 {name=p6 sig_type=std_logic lab=out_cm}
C {devices/vsource.sym} 1080 -430 0 0 {name=Vin1 value="dc 0 ac 0 portnum 2"}
C {devices/lab_pin.sym} 1080 -480 0 0 {name=p7 sig_type=std_logic lab=rfdummy}
C {devices/gnd.sym} 1080 -380 0 0 {name=l5 lab=GND}
C {capa.sym} 1240 -430 0 0 {name=C3
m=1
value=1f}
C {devices/gnd.sym} 1240 -380 0 0 {name=l6 lab=GND}
C {spice_probe.sym} 1020 -900 0 0 {name=p8 attrs=""}
C {spice_probe.sym} 1660 -920 0 0 {name=p9 attrs=""}
C {devices/vsource.sym} 1020 -650 0 0 {name=Vin2 value="dc 0 ac 0 sin(0 \{lo_lev\} \{lo_freq\})"}
C {devices/vsource.sym} 800 -650 0 0 {name=Vdd value=1.5}
C {devices/lab_pin.sym} 1560 -880 0 1 {name=p2 sig_type=std_logic lab=ref}
C {spice_probe.sym} 1560 -880 0 0 {name=p3 attrs=""}
C {capa.sym} 1660 -630 0 0 {name=C1
m=1
value=5p}
C {capa.sym} 1560 -630 0 0 {name=C2
m=1
value=5p}
C {devices/lab_pin.sym} 800 -1040 0 0 {name=p5 sig_type=std_logic lab=vdd}
C {vcvs.sym} 1840 -740 0 0 {name=E1 value=1}
C {spice_probe.sym} 1840 -830 0 0 {name=p10 attrs=""}
C {devices/lab_pin.sym} 1840 -830 0 1 {name=p11 sig_type=std_logic lab=out}
C {noconn.sym} 1840 -800 0 0 {name=l3}
C {sparx_powdet_sbd.sym} 1400 -900 0 0 {name=x1
}
C {sparx_powdet_sbd_pex.sym} 1400 -1160 0 0 {name=x2
spice_ignore=true}
C {title-3.sym} 0 0 0 0 {name=l4 author="(c) 2026 H. Pretl, ICD@JKU" rev=1.0 lock=true}
