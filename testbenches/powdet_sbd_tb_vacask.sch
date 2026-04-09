v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 220 -190 220 -170 {
lab=GND}
N 220 -370 220 -250 {lab=gnd_local}
N 220 -410 220 -370 {lab=gnd_local}
N 1180 -390 1180 -370 {lab=gnd_local}
N 220 -830 220 -470 {lab=vdd}
N 820 -690 820 -370 {lab=gnd_local}
N 820 -830 820 -790 {lab=vdd}
N 440 -450 440 -370 {lab=gnd_local}
N 220 -370 440 -370 {lab=gnd_local}
N 440 -530 440 -510 {lab=#net1}
N 440 -740 440 -590 {lab=rfin}
N 1180 -580 1180 -450 {lab=out_cm}
N 440 -370 820 -370 {lab=gnd_local}
N 220 -830 820 -830 {lab=vdd}
N 440 -740 710 -740 {lab=rfin}
N 880 -740 1180 -740 {lab=out_cm}
N 1030 -390 1030 -370 {lab=gnd_local}
N 820 -370 1030 -370 {lab=gnd_local}
N 880 -710 1030 -710 {lab=ref}
N 1030 -540 1030 -450 {lab=ref}
N 1280 -530 1280 -370 {lab=gnd_local}
N 1180 -370 1280 -370 {lab=gnd_local}
N 1030 -370 1180 -370 {lab=gnd_local}
N 1180 -580 1240 -580 {lab=out_cm}
N 1180 -740 1180 -580 {lab=out_cm}
N 1030 -540 1240 -540 {lab=ref}
N 1030 -710 1030 -540 {lab=ref}
N 1280 -670 1280 -590 {lab=out}
C {title.sym} 160 0 0 0 {name=l1 author="(c) 2026 Harald Pretl /// ICD@JKU"}
C {devices/vsource.sym} 220 -220 0 0 {name=vss value="dc=0"}
C {devices/gnd.sym} 220 -170 0 0 {name=l2 lab=GND}
C {devices/lab_pin.sym} 220 -270 0 1 {name=p1 sig_type=std_logic lab=gnd_local}
C {devices/vsource.sym} 220 -440 0 0 {name=vdd value="dc=1.5"}
C {devices/vsource.sym} 440 -560 0 0 {name=vin3 value="type=\\"sine\\" sinedc=0 ampl=1m freq="freq_rf""}
C {devices/lab_pin.sym} 220 -830 0 0 {name=p3 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 440 -740 0 0 {name=p4 sig_type=std_logic lab=rfin}
C {devices/launcher.sym} 460 -190 0 0 {name=h2
descr="simulate" 
tclcommand="xschem save; xschem netlist; xschem simulate"
}
C {devices/launcher.sym} 700 -190 0 0 {name=h3
descr="annotate OP" 
tclcommand="set show_hidden_texts 1; xschem annotate_op"
}
C {devices/lab_pin.sym} 1180 -740 0 1 {name=p6 sig_type=std_logic lab=out_cm}
C {spice_probe.sym} 440 -740 0 0 {name=p8 attrs=""}
C {spice_probe.sym} 1180 -740 0 0 {name=p9 attrs=""}
C {devices/vsource.sym} 440 -480 0 0 {name=vin2 value="type=\\"sine\\" sinedc=0 ampl=300m freq="freq_lo""}
C {simulator_commands_shown.sym} 1410 -260 0 0 {
name=Libs_VACASK
simulator=vacask
only_toplevel=false
value="
include \\"sg13g2_vacask_common.lib\\"
include \\"cornerMOSlv.lib\\" section=mos_tt
include \\"cornerMOShv.lib\\" section=mos_tt
include \\"cornerHBT.lib\\" section=hbt_typ
include \\"cornerRES.lib\\" section=res_typ
include \\"cornerCAP.lib\\" section=cap_typ
include \\"cornerDIO.lib\\" section=dio_tt
"
      }
C {launcher.sym} 460 -140 0 0 {name=h1
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
C {simulator_commands_shown.sym} 1390 -930 0 0 {
name=Script_VACASK
simulator=vacask
only_toplevel=false
value="
// Use single quotes where possible (Python)
// If double quotes are needed, escape them. 

control

  // Input frequencies (set here, used by sources and HB analysis)
  var freq_lo=149G
  var freq_rf=151G

  // Save operating point data
  include \\"powdet_sbd_tb_vacask.save\\"
  save default

  analysis powdet_sbd_tb_vacask op

  // HB convergence options
  options hb_skipinitial=0
  options nr_force=1e1

  // Outer sweep: LO tone amplitude (3 values)
  // Inner sweep: RF tone amplitude (log sweep)
  sweep ampl_lo instance=\\"vin2\\" parameter=\\"ampl\\" values=[30m, 100m, 300m]
    sweep ampl_rf instance=\\"vin3\\" parameter=\\"ampl\\" from=10u to=30m mode=\\"dec\\" points=5
      analysis powdet_hb1 hb freq=[freq_lo, freq_rf] truncate=\\"diamond\\" nharm=[9, 5]

  postprocess(PYTHON, \\"../powdet_eval.py\\")
  
endc
"}
C {devices/lab_pin.sym} 1030 -710 0 1 {name=p5 sig_type=std_logic lab=ref}
C {spice_probe.sym} 1030 -710 0 0 {name=p7 attrs=""}
C {capa.sym} 1030 -420 0 0 {name=C1
m=1
value=5p}
C {capa.sym} 1180 -420 0 0 {name=C2
m=1
value=5p}
C {vcvs.sym} 1280 -560 0 0 {name=E1 value=1}
C {devices/lab_pin.sym} 1280 -670 0 1 {name=p2 sig_type=std_logic lab=out}
C {spice_probe.sym} 1280 -670 0 0 {name=p10 attrs=""}
C {noconn.sym} 1280 -670 0 0 {name=l3}
C {sparx_powdet_sbd.sym} 710 -690 0 0 {name=x1}
