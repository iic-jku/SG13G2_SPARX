crashbackups stop
drc off
gds read /foss/designs/SG13G2_SPARX160/layout/sparx160_powdet_sbd.gds
load sparx160_powdet_sbd
select top cell
extract path /foss/designs/SG13G2_SPARX160/verification/lvs
extract no capacitance
extract no coupling
extract no resistance
extract no length
extract all
ext2spice lvs
ext2spice -p /foss/designs/SG13G2_SPARX160/verification/lvs -o /foss/designs/SG13G2_SPARX160/verification/lvs/sparx160_powdet_sbd.ext.spc
quit -noprompt
