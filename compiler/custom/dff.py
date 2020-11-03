# See LICENSE for licensing information.
#
# Copyright (c) 2016-2019 Regents of the University of California and The Board
# of Regents for the Oklahoma Agricultural and Mechanical College
# (acting for and on behalf of Oklahoma State University)
# All rights reserved.
#
import design
from tech import GDS, layer, spice, parameter
from tech import cell_properties as props
import utils


class dff(design.design):
    """
    Memory address flip-flop
    """
    if not props.dff.use_custom_ports:
        pin_names = ["D", "Q", "clk", "vdd", "gnd"]
        type_list = ["INPUT", "OUTPUT", "INPUT", "POWER", "GROUND"]
        clk_pin = "clk"
    else:
        pin_names = props.dff.custom_port_list
        type_list = props.dff.custom_type_list
        clk_pin = props.dff.clk_pin
    cell_size_layer = "boundary"
    
    def __init__(self, name="dff"):
        design.design.__init__(self, name)

        (width, height) = utils.get_libcell_size(name,
                                                 GDS["unit"],
                                                 layer[self.cell_size_layer])
        
        pin_map = utils.get_libcell_pins(self.pin_names,
                                         name,
                                         GDS["unit"])
        
        self.width = width
        self.height = height
        self.pin_map = pin_map
        self.add_pin_types(self.type_list)
    
    def analytical_power(self, corner, load):
        """Returns dynamic and leakage power. Results in nW"""
        c_eff = self.calculate_effective_capacitance(load)
        freq = spice["default_event_frequency"]
        power_dyn = self.calc_dynamic_power(corner, c_eff, freq)
        power_leak = spice["dff_leakage"]
        
        total_power = self.return_power(power_dyn, power_leak)
        return total_power
        
    def calculate_effective_capacitance(self, load):
        """Computes effective capacitance. Results in fF"""
        from tech import parameter
        c_load = load
        c_para = spice["dff_out_cap"]#ff
        transition_prob = 0.5
        return transition_prob*(c_load + c_para) 

    def build_graph(self, graph, inst_name, port_nets):
        """Adds edges based on inputs/outputs. Overrides base class function."""
        self.add_graph_edges(graph, port_nets)
        
