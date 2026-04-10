v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 70 -310 70 -270 {lab=GND}
N 1030 -290 1030 -270 {lab=GND}
N 670 -680 670 -640 {lab=vdd}
N 70 -270 290 -270 {lab=GND}
N 290 -380 290 -360 {lab=#net1}
N 290 -270 670 -270 {lab=GND}
N 70 -680 670 -680 {lab=vdd}
N 290 -590 560 -590 {lab=rfin}
N 730 -590 1030 -590 {lab=out_cm}
N 880 -290 880 -270 {lab=GND}
N 670 -270 880 -270 {lab=GND}
N 730 -560 880 -560 {lab=ref}
N 1030 -270 1130 -270 {lab=GND}
N 880 -270 1030 -270 {lab=GND}
N 1030 -430 1090 -430 {lab=out_cm}
N 1030 -590 1030 -430 {lab=out_cm}
N 880 -390 1090 -390 {lab=ref}
N 880 -560 880 -390 {lab=ref}
N 1130 -520 1130 -440 {lab=out}
N 670 -540 670 -270 {lab=GND}
N 290 -300 290 -270 {lab=GND}
N 1130 -380 1130 -270 {lab=GND}
N 880 -390 880 -350 {lab=ref}
N 1030 -430 1030 -350 {lab=out_cm}
N 70 -680 70 -370 {lab=vdd}
N 290 -590 290 -440 {lab=rfin}
C {title.sym} 160 0 0 0 {name=l1 author="(c) 2026 Harald Pretl /// ICD@JKU"}
C {devices/gnd.sym} 70 -270 0 0 {name=l2 lab=GND}
C {devices/vsource.sym} 70 -340 0 0 {name=vdd value="dc=1.5"}
C {devices/vsource.sym} 290 -410 0 0 {name=vin3 value="type=\\"sine\\" sinedc=0 ampl=1m freq="freq_rf""}
C {devices/lab_pin.sym} 70 -680 0 0 {name=p3 sig_type=std_logic lab=vdd}
C {devices/lab_pin.sym} 290 -590 0 0 {name=p4 sig_type=std_logic lab=rfin}
C {devices/launcher.sym} 310 -150 0 0 {name=h2
descr="simulate" 
tclcommand="xschem save; xschem netlist; xschem simulate"
}
C {devices/launcher.sym} 550 -150 0 0 {name=h3
descr="annotate OP" 
tclcommand="set show_hidden_texts 1; xschem annotate_op"
}
C {devices/lab_pin.sym} 1030 -590 0 1 {name=p6 sig_type=std_logic lab=out_cm}
C {spice_probe.sym} 290 -590 0 0 {name=p8 attrs=""}
C {spice_probe.sym} 1030 -590 0 0 {name=p9 attrs=""}
C {devices/vsource.sym} 290 -330 0 0 {name=vin2 value="type=\\"sine\\" sinedc=0 ampl=300m freq="freq_lo""}
C {simulator_commands_shown.sym} 780 -200 0 0 {
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
C {launcher.sym} 310 -100 0 0 {name=h1
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
C {simulator_commands_shown.sym} 160 -1140 0 0 {
name=Script_VACASK
simulator=vacask
only_toplevel=false
value="
control
  // Input frequencies (set here, used by sources and HB analysis)
  var freq_lo=149G
  var freq_rf=151G

  // Save operating point data
  include \\"powdet_sbd_tb_vacask.save\\"
  save default

  analysis powdet_sbd_tb_vacask op

  // HB convergence options
  //options hb_skipinitial=0
  //options nr_force=1e1

  // Outer sweep: LO tone amplitude (3 values)
  // Inner sweep: RF tone amplitude (log sweep)
  sweep ampl_lo instance=\\"vin2\\" parameter=\\"ampl\\" values=[30m, 100m, 300m]
    sweep ampl_rf instance=\\"vin3\\" parameter=\\"ampl\\" from=10u to=30m mode=\\"dec\\" points=5
      analysis powdet_hb1 hb freq=[freq_lo, freq_rf] truncate=\\"diamond\\" nharm=[9, 5]

  postprocess(PYTHON, \\"../powdet_eval.py\\")
endc
"}
C {sparx_powdet_sbd.sym} 560 -540 0 0 {name=xdemod}
C {devices/lab_pin.sym} 880 -560 0 1 {name=p5 sig_type=std_logic lab=ref}
C {spice_probe.sym} 880 -560 0 0 {name=p7 attrs=""}
C {capa.sym} 880 -320 0 0 {name=C1
m=1
value=5p}
C {capa.sym} 1030 -320 0 0 {name=C2
m=1
value=5p}
C {vcvs.sym} 1130 -410 0 0 {name=E1 value=1}
C {devices/lab_pin.sym} 1130 -520 0 1 {name=p2 sig_type=std_logic lab=out}
C {spice_probe.sym} 1130 -520 0 0 {name=p10 attrs=""}
C {noconn.sym} 1130 -520 0 0 {name=l3}
