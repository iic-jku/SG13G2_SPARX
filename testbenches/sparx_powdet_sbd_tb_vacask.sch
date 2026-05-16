v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {VACASK Testbench for SBD-Based Power Detector} 600 -1720 0 0 1 1 {}
T {SPDX-FileCopyrightText: 2025-2026 The SPARX Team
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1} 1920 -220 0 0 0.4 0.4 {}
N 800 -300 800 -280 {
lab=GND}
N 1020 -380 1020 -300 {lab=GND}
N 1020 -460 1020 -440 {lab=#net1}
N 1020 -660 1020 -520 {lab=rfin}
N 1400 -300 1560 -300 {lab=GND}
N 1400 -800 1400 -720 {lab=vdd}
N 800 -300 1020 -300 {lab=GND}
N 1660 -520 1800 -520 {lab=out_cm}
N 1840 -470 1840 -300 {lab=GND}
N 1840 -590 1840 -530 {lab=out}
N 1560 -640 1560 -480 {lab=ref}
N 1560 -480 1800 -480 {lab=ref}
N 800 -380 800 -300 {lab=GND}
N 800 -800 800 -440 {lab=vdd}
N 1660 -300 1840 -300 {lab=GND}
N 1660 -360 1660 -300 {lab=GND}
N 1560 -300 1660 -300 {lab=GND}
N 1560 -360 1560 -300 {lab=GND}
N 1560 -480 1560 -420 {lab=ref}
N 1660 -520 1660 -420 {lab=out_cm}
N 1660 -680 1660 -520 {lab=out_cm}
N 1020 -660 1320 -660 {lab=rfin}
N 1400 -600 1400 -300 {lab=GND}
N 1020 -300 1400 -300 {lab=GND}
N 800 -800 1400 -800 {lab=vdd}
N 1480 -680 1660 -680 {lab=out_cm}
N 1480 -640 1560 -640 {lab=ref}
C {devices/vsource.sym} 800 -410 0 0 {name=vdd value="dc=1.5"}
C {devices/vsource.sym} 1020 -490 0 0 {name=vin3 value="type=\\"sine\\" sinedc=0 ampl=1m freq="freq_rf""}
C {devices/vsource.sym} 1020 -410 0 0 {name=vin2 value="type=\\"sine\\" sinedc=0 ampl=300m freq="freq_lo""}
C {simulator_commands_shown.sym} 1880 -1310 0 0 {
name=Libs_VACASK
simulator=vacask
only_toplevel=false
value="
include \\"sg13g2_vacask_common.lib\\"
include \\"cornerMOSlv.lib\\" section=mos_tt
include \\"cornerRES.lib\\" section=res_typ
include \\"cornerCAP.lib\\" section=cap_typ
include \\"cornerDIO.lib\\" section=dio_tt
"
      }
C {launcher.sym} 1620 -1200 0 0 {name=h1
descr=simulateVACASK
tclcommand="
# Setup the default simulation commands if not already set up
# for example by already launched simulations.
set_sim_defaults
puts $sim(spectre,0,cmd) 

# change the simulator to be used (#0 in spectre category is VACASK)
set sim(spectre,default) 0

# Create FET and BIP .save file
mkdir -p $netlist_dir
write_data [save_params] $netlist_dir/[file rootname [file tail [xschem get current_name]]].save

# run netlist and simulation
xschem netlist
simulate
"}
C {simulator_commands_shown.sym} 100 -1350 0 0 {
name=Script_VACASK
simulator=vacask
only_toplevel=false
value="
control
  // Input frequencies (set here, used by sources and HB analysis)
  var freq_lo=149G
  var freq_rf=151G

  // Save operating point data
  include \\"sparx_powdet_sbd_tb_vacask.save\\"
  save default

  analysis sparx_powdet_sbd_tb_vacask op

  // HB convergence options
  //options hb_skipinitial=0
  //options nr_force=1e1

  // Outer sweep: LO tone amplitude (3 values)
  // Inner sweep: RF tone amplitude (log sweep)
  sweep ampl_lo instance=\\"vin2\\" parameter=\\"ampl\\" values=[30m, 100m, 300m]
    sweep ampl_rf instance=\\"vin3\\" parameter=\\"ampl\\" from=10u to=30m mode=\\"dec\\" points=5
      analysis powdet_hb1 hb freq=[freq_lo, freq_rf] truncate=\\"diamond\\" nharm=[9, 5]

  postprocess(PYTHON, \\"../../scripts/sparx_powdet_sbd_eval.py\\")
endc
"}
C {sparx_powdet_sbd.sym} 1400 -660 0 0 {name=xdemod1}
C {capa.sym} 1560 -390 0 0 {name=C1
m=1
value=5p}
C {capa.sym} 1660 -390 0 0 {name=C2
m=1
value=5p}
C {title-3.sym} 0 0 0 0 {name=l4 author="(c) 2026 H. Pretl, ICD@JKU" rev=1.0 lock=true}
C {devices/launcher.sym} 1620 -1320 0 0 {name=h4
descr="simulate" 
tclcommand="xschem save; xschem netlist; xschem simulate"
}
C {devices/launcher.sym} 1620 -1260 0 0 {name=h5
descr="annotate OP" 
tclcommand="set show_hidden_texts 1; xschem annotate_op"
}
C {devices/gnd.sym} 800 -280 0 0 {name=l1 lab=GND}
C {devices/lab_pin.sym} 1020 -660 0 0 {name=p11 sig_type=std_logic lab=rfin}
C {devices/lab_pin.sym} 1660 -680 0 1 {name=p12 sig_type=std_logic lab=out_cm}
C {spice_probe.sym} 1020 -660 0 0 {name=p14 attrs=""}
C {spice_probe.sym} 1660 -680 0 0 {name=p15 attrs=""}
C {devices/lab_pin.sym} 1560 -640 0 1 {name=p16 sig_type=std_logic lab=ref}
C {spice_probe.sym} 1560 -640 0 0 {name=p17 attrs=""}
C {devices/lab_pin.sym} 800 -800 0 0 {name=p18 sig_type=std_logic lab=vdd}
C {vcvs.sym} 1840 -500 0 0 {name=E2 value=1}
C {spice_probe.sym} 1840 -590 0 0 {name=p19 attrs=""}
C {devices/lab_pin.sym} 1840 -590 0 1 {name=p20 sig_type=std_logic lab=out}
C {noconn.sym} 1840 -560 0 0 {name=l7}
C {sparx_powdet_sbd_pex.sym} 1400 -920 0 0 {name=xdemod2
spice_ignore=true}
