import os
import re
import sys
import subprocess
from gds2palace import *
import gdspy
import argparse



def _get_number_of_ports(gds_filename):
    """Get number of ports from GDSII file, by counting layers with layer number > 200"""
    lib = gdspy.GdsLibrary()
    lib.read_gds(gds_filename)
    cell = lib.top_level()[0]
    layers = _get_layers(cell)
    return sum(1 for layer, _ in layers if layer > 200)


def _get_ghz_from_filename(gds_filename):
    """Extract the integer GHz value from a filename like 'tline_l4_for_10GHz.gds'."""
    base_name = os.path.basename(gds_filename)
    match = re.search(r"(\d+(?:\.\d+)?)\s*GHz", base_name, re.IGNORECASE)
    if not match:
        raise ValueError(f"No GHz value found in filename: {gds_filename}")
    ghz_value = float(match.group(1))
    if not ghz_value.is_integer():
        raise ValueError(f"GHz value must be an integer: {gds_filename}")
    return int(ghz_value)


def _get_layer_names_from_filename(gds_filename):
    """Extract signal and ground layer names from filename.
    
    Returns:
        tuple: (signal_layer, ground_layer) e.g., ('TM2', 'M5')
    
    Raises:
        ValueError: If layer names are not found in filename
    """
    base_name = os.path.basename(gds_filename)
    layer_options = ['TM2', 'TM1', 'M5', 'M4', 'M3', 'M2', 'M1']
    
    # Find all layer names in the filename
    found_layers = []
    for layer in layer_options:
        if layer in base_name:
            found_layers.append(layer)
    
    if len(found_layers) < 2:
        raise ValueError(f"Could not extract both signal and ground layer names from: {gds_filename}")
    
    # First occurrence is signal layer, second is ground layer
    signal_layer = found_layers[0]
    ground_layer = found_layers[1]
    
    return signal_layer, ground_layer


def _get_impedance_from_filename(gds_filename):
    """Extract the impedance value from filename.
    
    The impedance is expected to appear directly before 'Ohm'.
    Example: 'blc_160GHz_50Ohm_TM2_M5_...' extracts 50
    
    Returns:
        float: Impedance value in Ohms
    
    Raises:
        ValueError: If impedance value is not found in filename
    """
    base_name = os.path.basename(gds_filename)
    match = re.search(r"(\d+(?:\.\d+)?)\s*Ohm", base_name, re.IGNORECASE)
    if not match:
        raise ValueError(f"No impedance value found in filename: {gds_filename}")
    impedance = float(match.group(1))
    return impedance

# helper to find number of ports
def _get_layers(cell, layers=None):
    if layers is None:
        layers = set()
    for poly in cell.polygons:
        for layer, datatype in zip(poly.layers, poly.datatypes):
            layers.add((int(layer), int(datatype)))
    for ref in cell.references:
        _get_layers(ref.ref_cell, layers)
    return layers


# ===================== input files and path settings =======================

gds_filename = sys.argv[1]   # geometries
XML_filename = "SG13G2_nosub.xml"          # stackup

# preprocess GDSII for safe handling of cutouts/holes?
preprocess_gds = False

# merge via polygons with distance less than .. microns, set to 0 to disable via merging.
merge_polygon_size = 0

# get path for this simulation file
script_path = utilities.get_script_path(__file__)

# use script filename as model basename
model_basename = utilities.get_basename(__file__)

# set and create directory for simulation output
sim_path = utilities.create_sim_path (script_path,model_basename, dirname="../palace_model/" +str.split(gds_filename.split('/')[-1], ".")[0])
print('Simulation data directory: ', sim_path)

f_center = _get_ghz_from_filename(gds_filename) * 1e9


# change path to models script path
modelDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(modelDir)

# ======================== simulation settings ================================

settings = {}

settings['unit']   = 1e-6  # geometry is in microns
settings['margin'] = 50    # distance in microns from GDSII geometry boundary to simulation boundary 

settings['fstart']  = f_center * 0.5
settings['fstop']   = f_center * 1.5
settings['fstep']   = f_center * 0.01

settings['refined_cellsize'] = 2  # mesh cell size in conductor region
settings['cells_per_wavelength'] = 10   # how many mesh cells per wavelength, must be 10 or more

settings['meshsize_max'] = 70  # microns, override cells_per_wavelength 
settings['adaptive_mesh_iterations'] = 0

settings['no_gui'] = True  # create files without showing 3D model
# settings['no_gui'] = ('nogui' in sys.argv)  # check if nogui specified on command line, then create files without showing 3D model

# Ports from GDSII Data, polygon geometry from specified special layer
# Excitations can be switched off by voltage=0, those S-parameter will be incomplete then

simulation_ports = simulation_setup.all_simulation_ports()

num_ports = _get_number_of_ports(gds_filename)

print(f"Number of ports found: {num_ports}")

layer_dict = {
    "TM2": "TopMetal2",
    "TM1": "TopMetal1",
    "M5": "Metal5",
    "M4": "Metal4",
    "M3": "Metal3",
    "M2": "Metal2",
    "M1": "Metal1",
}
signal_layer, ground_layer = _get_layer_names_from_filename(gds_filename)

for portnumber in range(1, num_ports + 1):
    simulation_ports.add_port(
        simulation_setup.simulation_port(
            portnumber=portnumber,
            voltage=1,
            port_Z0=_get_impedance_from_filename(gds_filename),
            source_layernum=200 + portnumber,
            from_layername=layer_dict.get(signal_layer),
            to_layername=layer_dict.get(ground_layer),
            direction='z'
        )
    )
 

# ======================== simulation ================================

# get technology stackup data
materials_list, dielectrics_list, metals_list = stackup_reader.read_substrate (XML_filename)
# get list of layers from technology
layernumbers = metals_list.getlayernumbers()
layernumbers.extend(simulation_ports.portlayers)

# read geometries from GDSII, only purpose 0
allpolygons = gds_reader.read_gds(gds_filename, layernumbers, purposelist=[0], metals_list=metals_list, preprocess=preprocess_gds, merge_polygon_size=merge_polygon_size)


########### create model ###########

settings['simulation_ports'] = simulation_ports
settings['materials_list'] = materials_list
settings['dielectrics_list'] = dielectrics_list
settings['metals_list'] = metals_list
settings['layernumbers'] = layernumbers
settings['allpolygons'] = allpolygons
settings['sim_path'] = sim_path
settings['model_basename'] = model_basename


# list of ports that are excited (set voltage to zero in port excitation to skip an excitation!)
excite_ports = simulation_ports.all_active_excitations()
config_name, data_dir = simulation_setup.create_palace (excite_ports, settings)
