v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {This is only need for .sp simulation,
as two ports are required. However, we
are only interested in S11.} 1390 -120 0 0 0.3 0.3 {}
N 580 -190 580 -170 {
lab=GND}
N 580 -370 580 -250 {lab=gnd_local}
N 1400 -390 1400 -370 {lab=gnd_local}
N 1470 -210 1630 -210 {lab=rfdummy}
N 1180 -690 1180 -370 {lab=gnd_local}
N 800 -450 800 -370 {lab=gnd_local}
N 800 -530 800 -510 {lab=#net1}
N 800 -740 800 -590 {lab=rfin}
N 800 -370 1180 -370 {lab=gnd_local}
N 800 -740 1070 -740 {lab=rfin}
N 1300 -370 1400 -370 {lab=gnd_local}
N 580 -420 580 -370 {lab=gnd_local}
N 580 -880 1180 -880 {lab=vdd}
N 1180 -880 1180 -790 {lab=vdd}
N 580 -880 580 -480 {lab=vdd}
N 580 -370 800 -370 {lab=gnd_local}
N 1240 -740 1400 -740 {lab=out_cm}
N 1300 -390 1300 -370 {lab=gnd_local}
N 1180 -370 1300 -370 {lab=gnd_local}
N 1240 -710 1300 -710 {lab=ref}
N 1400 -590 1540 -590 {lab=out_cm}
N 1400 -740 1400 -590 {lab=out_cm}
N 1580 -540 1580 -370 {lab=gnd_local}
N 1580 -660 1580 -600 {lab=out}
N 1300 -710 1300 -550 {lab=ref}
N 1300 -550 1540 -550 {lab=ref}
N 1400 -370 1580 -370 {lab=gnd_local}
N 1300 -550 1300 -450 {lab=ref}
N 1400 -590 1400 -450 {lab=out_cm}
C {title.sym} 160 0 0 0 {name=l1 author="(c) 2026 Harald Pretl /// ICD@JKU"}
C {devices/vsource.sym} 580 -220 0 0 {name=Vss value=0}
C {devices/gnd.sym} 580 -170 0 0 {name=l2 lab=GND}
C {devices/lab_pin.sym} 580 -270 0 1 {name=p1 sig_type=std_logic lab=gnd_local}
C {devices/vsource.sym} 800 -560 0 0 {name=Vin3 value="dc 0 ac 0 portnum 1 sin(0 \{rf_lev\} \{rf_freq\})"}
C {devices/lab_pin.sym} 800 -740 0 0 {name=p4 sig_type=std_logic lab=rfin}
C {devices/code_shown.sym} 0 -140 0 0 {name=MODEL only_toplevel=true
format="tcleval( @value )"
value="
.lib cornerDIO.lib dio_tt
.lib cornerMOSlv.lib mos_tt
.lib cornerRES.lib res_typ
.lib cornerCAP.lib cap_typ
"}
C {devices/code_shown.sym} 0 -1100 0 0 {name=NGSPICE only_toplevel=true 
value="
.include ../../netlist/pex/sparx160_powdet_sbd_magic_pex.spice
* .include ../../netlist/pex/sparx160_powdet_sbd_klayout_pex.spice
.temp 27
.option method=gear
.save all
.include powdet_sbd_tb.save
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
write powdet_sbd_tb.raw
set appendwrite

sp lin 31 100G 200G 0
write powdet_sbd_tb.raw

ac dec 1001 1MEG 10G
write powdet_sbd_tb.raw

tran 0.05p 22n 20n
write powdet_sbd_tb.raw

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
C {devices/launcher.sym} 820 -190 0 0 {name=h2
descr="simulate" 
tclcommand="xschem save; xschem netlist; xschem simulate"
}
C {devices/launcher.sym} 1060 -190 0 0 {name=h3
descr="annotate OP" 
tclcommand="set show_hidden_texts 1; xschem annotate_op"
}
C {devices/lab_pin.sym} 1400 -740 0 1 {name=p6 sig_type=std_logic lab=out_cm}
C {devices/vsource.sym} 1470 -180 0 0 {name=Vin1 value="dc 0 ac 0 portnum 2"}
C {devices/lab_pin.sym} 1470 -210 0 0 {name=p7 sig_type=std_logic lab=rfdummy}
C {devices/gnd.sym} 1470 -150 0 0 {name=l5 lab=GND}
C {capa.sym} 1630 -180 0 0 {name=C3
m=1
value=1f}
C {devices/gnd.sym} 1630 -150 0 0 {name=l6 lab=GND}
C {spice_probe.sym} 800 -740 0 0 {name=p8 attrs=""}
C {spice_probe.sym} 1400 -740 0 0 {name=p9 attrs=""}
C {devices/vsource.sym} 800 -480 0 0 {name=Vin2 value="dc 0 ac 0 sin(0 \{lo_lev\} \{lo_freq\})"}
C {devices/vsource.sym} 580 -450 0 0 {name=Vdd value=1.5}
C {devices/lab_pin.sym} 1300 -710 0 1 {name=p2 sig_type=std_logic lab=ref}
C {spice_probe.sym} 1300 -710 0 0 {name=p3 attrs=""}
C {capa.sym} 1400 -420 0 0 {name=C1
m=1
value=5p}
C {capa.sym} 1300 -420 0 0 {name=C2
m=1
value=5p}
C {devices/lab_pin.sym} 580 -880 0 0 {name=p5 sig_type=std_logic lab=vdd}
C {vcvs.sym} 1580 -570 0 0 {name=E1 value=1}
C {spice_probe.sym} 1580 -660 0 0 {name=p10 attrs=""}
C {devices/lab_pin.sym} 1580 -660 0 1 {name=p11 sig_type=std_logic lab=out}
C {noconn.sym} 1580 -630 0 0 {name=l3}
C {sparx160_powdet_sbd.sym} 1070 -690 0 0 {name=x1
}
C {sparx160_powdet_sbd_pex.sym} 1350 -920 0 0 {name=x2
spice_ignore=true}
