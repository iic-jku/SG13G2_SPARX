from rawfile import rawread
import numpy as np
import matplotlib.pyplot as plt
import re, glob

# ANALYZE HB SWEEP RESULTS for down-conversion mixer
# Outer sweep: ampl_lo (LO tone amplitude)
# Inner sweep: ampl_rf (RF tone amplitude)
# Extract IF mixing product at node 'out'

# Parse LO and RF frequencies from spectre netlist
spectre_file = glob.glob('*.spectre')[0]
with open(spectre_file) as f:
	netlist = f.read()
freq_lo = float(re.search(r'var\s+freq_lo\s*=\s*([\d.eE+\-]+[GMKkT]?)', netlist).group(1).replace('G', 'e9').replace('M', 'e6').replace('K', 'e3').replace('k', 'e3').replace('T', 'e12'))
freq_rf = float(re.search(r'var\s+freq_rf\s*=\s*([\d.eE+\-]+[GMKkT]?)', netlist).group(1).replace('G', 'e9').replace('M', 'e6').replace('K', 'e3').replace('k', 'e3').replace('T', 'e12'))
freq_if = abs(freq_rf - freq_lo)

hb = rawread('../testbenches/simulations/sparx_powdet_sbd_hb1.raw').get(sweeps=2)

# Collect data grouped by LO amplitude
data = {}
for g in range(hb.sweepGroups):
	sd = hb.sweepData(g)
	a_lo = np.abs(sd['ampl_lo'])
	a_rf = np.abs(sd['ampl_rf'])

	freq = np.real(hb[g, 'frequency'])
	out = hb[g, 'out']

	# Find IF bin at |f_rf - f_lo|
	idx_if = np.argmin(np.abs(freq - freq_if))

	if a_lo not in data:
		data[a_lo] = {'a_rf': [], 'mag_if': []}

	data[a_lo]['a_rf'].append(a_rf)
	data[a_lo]['mag_if'].append(np.abs(out[idx_if]))

# Plot
fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
fig.suptitle(f'Power Detector SBD — IF at {freq_if/1e9:.1f} GHz')

for a_lo in sorted(data.keys()):
	d = data[a_lo]
	a_rf = np.array(d['a_rf'])
	mag_if = np.array(d['mag_if'])

	order = np.argsort(a_rf)
	a_rf = a_rf[order]
	mag_if = mag_if[order]

	a_rf_db = 20 * np.log10(a_rf + 1e-30)
	mag_if_db = 20 * np.log10(mag_if + 1e-30)
	label = f'A(LO {freq_lo/1e9:.0f} GHz) = {a_lo*1e3:.0f} mV'
	ax.plot(a_rf_db, mag_if_db, 'o-', label=label)

ax.set_xlabel(f'RF Input Amplitude at {freq_rf/1e9:.0f} GHz (dBV)')
ax.set_ylabel(f'IF Output at {freq_if/1e9:.1f} GHz (dBV)')

# Draw 1 dB/dB reference slope
a_rf_all = []
for a_lo in sorted(data.keys()):
	d = data[a_lo]
	a_rf_all.extend(d['a_rf'])
a_rf_ref = np.array(sorted(set(a_rf_all)))
a_rf_ref_db = 20 * np.log10(a_rf_ref + 1e-30)
first_key = sorted(data.keys())[0]
d0 = data[first_key]
a0 = np.array(d0['a_rf'])
m0 = np.array(d0['mag_if'])
idx0 = np.argmin(a0)
ref_offset = 20 * np.log10(m0[idx0] + 1e-30) - 20 * np.log10(a0[idx0] + 1e-30)
ref_db = a_rf_ref_db + ref_offset
ax.plot(a_rf_ref_db, ref_db, 'k--', alpha=0.5, label='1 dB/dB slope')

ax.legend()
ax.grid(True)

plt.savefig('../doc/figures/sparx_sim/sparx_powdet_sbd_hb_sweep.png', dpi=150)
plt.show()
