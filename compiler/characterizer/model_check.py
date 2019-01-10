import sys,re,shutil
import debug
import tech
import math
from .stimuli import *
from .trim_spice import *
from .charutils import *
import utils
from globals import OPTS
from .delay import delay
from .measurements import *

class model_check(delay):
    """Functions to test for the worst case delay in a target SRAM

    The current worst case determines a feasible period for the SRAM then tests
    several bits and record the delay and differences between the bits.

    """

    def __init__(self, sram, spfile, corner):
        delay.__init__(self,sram,spfile,corner)
        self.period = tech.spice["feasible_period"]
        
    def create_measurement_names(self):
        """Create measurement names. The names themselves currently define the type of measurement"""
        #Altering the names will crash the characterizer. TODO: object orientated approach to the measurements.
        self.wl_delay_meas_names = ["delay_wl_en_bar", "delay_wl_en", "delay_dvr_en_bar", "delay_wl"]
        self.wl_slew_meas_names = ["slew_wl_gated_clk_bar","slew_wl_en_bar", "slew_wl_en", "slew_drv_en_bar", "slew_wl"]
        
        self.rbl_delay_meas_names = ["delay_gated_clk_nand", "delay_delay_chain_in", "delay_delay_chain_stage_1", "delay_delay_chain_stage_2"]
        self.rbl_slew_meas_names = ["slew_rbl_gated_clk_bar","slew_gated_clk_nand", "slew_delay_chain_in", "slew_delay_chain_stage_1", "slew_delay_chain_stage_2"]
        self.sae_delay_meas_names = ["delay_pre_sen", "delay_sen_bar", "delay_sen"]
        self.sae_slew_meas_names = ["slew_replica_bl0", "slew_pre_sen", "slew_sen_bar", "slew_sen"]
       
    def create_signal_names(self):
        delay.create_signal_names(self)
        #Signal names are all hardcoded, need to update to make it work for probe address and different configurations.
        self.wl_signal_names = ["Xsram.Xcontrol0.gated_clk_bar", "Xsram.Xcontrol0.Xbuf_wl_en.zb_int", "Xsram.wl_en0", "Xsram.Xbank0.Xwordline_driver0.wl_bar_15", "Xsram.Xbank0.wl_15"]
        self.rbl_en_signal_names = ["Xsram.Xcontrol0.gated_clk_bar", "Xsram.Xcontrol0.Xand2_rbl_in.zb_int", "Xsram.Xcontrol0.rbl_in", "Xsram.Xcontrol0.Xreplica_bitline.Xdelay_chain.dout_1", "Xsram.Xcontrol0.Xreplica_bitline.delayed_en"]
        self.sae_signal_names = ["Xsram.Xcontrol0.Xreplica_bitline.bl0_0", "Xsram.Xcontrol0.pre_s_en", "Xsram.Xcontrol0.Xbuf_s_en.zb_int", "Xsram.s_en0"]
    
    def create_measurement_objects(self):
        """Create the measurements used for read and write ports"""
        self.create_wordline_measurement_objects()
        self.create_sae_measurement_objects()
        self.all_measures = self.wl_meas_objs+self.sae_meas_objs
    
    def create_wordline_measurement_objects(self):
        """Create the measurements to measure the wordline path from the gated_clk_bar signal"""
        self.wl_meas_objs = []
        trig_dir = "RISE"
        targ_dir = "FALL"
        
        for i in range(1, len(self.wl_signal_names)):
            self.wl_meas_objs.append(delay_measure(self.wl_delay_meas_names[i-1], self.wl_signal_names[i-1], self.wl_signal_names[i], trig_dir, targ_dir, measure_scale=1e9))
            self.wl_meas_objs.append(slew_measure(self.wl_slew_meas_names[i-1], self.wl_signal_names[i-1], trig_dir, measure_scale=1e9))
            temp_dir = trig_dir
            trig_dir = targ_dir
            targ_dir = temp_dir
        self.wl_meas_objs.append(slew_measure(self.wl_slew_meas_names[-1], self.wl_signal_names[-1], trig_dir, measure_scale=1e9))
        
    def create_sae_measurement_objects(self):
        """Create the measurements to measure the sense amp enable path from the gated_clk_bar signal. The RBL splits this path into two."""
        
        self.sae_meas_objs = []
        trig_dir = "RISE"
        targ_dir = "FALL"
        #Add measurements from gated_clk_bar to RBL
        for i in range(1, len(self.rbl_en_signal_names)):
            self.sae_meas_objs.append(delay_measure(self.rbl_delay_meas_names[i-1], self.rbl_en_signal_names[i-1], self.rbl_en_signal_names[i], trig_dir, targ_dir, measure_scale=1e9))
            self.sae_meas_objs.append(slew_measure(self.rbl_slew_meas_names[i-1], self.rbl_en_signal_names[i-1], trig_dir, measure_scale=1e9))
            temp_dir = trig_dir
            trig_dir = targ_dir
            targ_dir = temp_dir
        self.sae_meas_objs.append(slew_measure(self.rbl_slew_meas_names[-1], self.rbl_en_signal_names[-1], trig_dir, measure_scale=1e9))
        
        #Add measurements from rbl_out to sae. Trigger directions do not invert from previous stage due to RBL.
        trig_dir = "FALL"
        targ_dir = "RISE"
        #Add measurements from gated_clk_bar to RBL
        for i in range(1, len(self.sae_signal_names)):
            self.sae_meas_objs.append(delay_measure(self.sae_delay_meas_names[i-1], self.sae_signal_names[i-1], self.sae_signal_names[i], trig_dir, targ_dir, measure_scale=1e9))
            self.sae_meas_objs.append(slew_measure(self.sae_slew_meas_names[i-1], self.sae_signal_names[i-1], trig_dir, measure_scale=1e9))
            temp_dir = trig_dir
            trig_dir = targ_dir
            targ_dir = temp_dir
        self.sae_meas_objs.append(slew_measure(self.sae_slew_meas_names[-1], self.sae_signal_names[-1], trig_dir, measure_scale=1e9))
        
    def write_delay_measures(self):
        """
        Write the measure statements to quantify the delay and power results for all targeted ports.
        """
        self.sf.write("\n* Measure statements for delay and power\n")

        # Output some comments to aid where cycles start and what is happening
        for comment in self.cycle_comments:
            self.sf.write("* {}\n".format(comment))
        
        for read_port in self.targ_read_ports:
           self.write_measures_read_port(read_port)

    def get_delay_measure_variants(self, port, measure_obj):
        """Get the measurement values that can either vary from simulation to simulation (vdd, address) or port to port (time delays)"""
        #Return value is intended to match the delay measure format:  trig_td, targ_td, vdd, port
        #Assuming only read 0 for now
        if not (type(measure_obj) is delay_measure or type(measure_obj) is slew_measure):
            debug.error("Measurement not recognized by the model checker.",1)
        meas_cycle_delay = self.cycle_times[self.measure_cycles[port]["read0"]] + self.period/2
        return (meas_cycle_delay, meas_cycle_delay, self.vdd_voltage, port)
    
    def write_measures_read_port(self, port):
        """
        Write the measure statements for all nodes along the wordline path.
        """
        # add measure statements for delays/slews
        for measure in self.all_measures:
            measure_variant_inp_tuple = self.get_delay_measure_variants(port, measure)
            measure.write_measure(self.stim, measure_variant_inp_tuple)
    
    def get_measurement_values(self, meas_objs, port):
        """Gets the delays and slews from a specified port from the spice output file and returns them as lists."""
        delay_meas_list = []  
        slew_meas_list = [] 
        for measure in meas_objs:
            measure_value = measure.retrieve_measure(port=port)
            if type(measure_value) != float:
                debug.error("Failed to Measure Value:\n\t\t{}={}".format(measure.name, measure_value),1) 
            if type(measure) is delay_measure:
                delay_meas_list.append(measure_value)
            elif type(measure)is slew_measure:
                slew_meas_list.append(measure_value)
            else:
                debug.error("Measurement object not recognized.",1)
        return delay_meas_list, slew_meas_list
        
    def run_delay_simulation(self):
        """
        This tries to simulate a period and checks if the result works. If
        so, it returns True and the delays, slews, and powers.  It
        works on the trimmed netlist by default, so powers do not
        include leakage of all cells.
        """
        #Sanity Check
        debug.check(self.period > 0, "Target simulation period non-positive") 
        
        wl_delay_result = [[] for i in self.all_ports]
        wl_slew_result = [[] for i in self.all_ports]
        sae_delay_result = [[] for i in self.all_ports]
        sae_slew_result = [[] for i in self.all_ports]
        # Checking from not data_value to data_value
        self.write_delay_stimulus()

        self.stim.run_sim() #running sim prodoces spice output file.
        
        #Retrieve the results from the output file
        for port in self.targ_read_ports:  
            #Parse and check the voltage measurements
            wl_delay_result[port], wl_slew_result[port] = self.get_measurement_values(self.wl_meas_objs, port)
            sae_delay_result[port], sae_slew_result[port] = self.get_measurement_values(self.sae_meas_objs, port)
        return (True,wl_delay_result, sae_delay_result, wl_slew_result, sae_slew_result)
  
    def get_model_delays(self, port):
        """Get model delays based on port. Currently assumes single RW port."""
        return self.sram.control_logic_rw.get_wl_sen_delays()
            
    def analyze(self, probe_address, probe_data, slews, loads):
        """Measures entire delay path along the wordline and sense amp enable and compare it to the model delays."""
        self.set_probe(probe_address, probe_data)
        self.load=max(loads)
        self.slew=max(slews)
        self.create_measurement_objects()
        
        read_port = self.read_ports[0] #only test the first read port
        self.targ_read_ports = [read_port]
        self.targ_write_ports = [self.write_ports[0]]
        debug.info(1,"Bitline swing test: corner {}".format(self.corner))
        (success, wl_delays, sae_delays, wl_slews, sae_slews)=self.run_delay_simulation()
        debug.check(success, "Model measurements Failed: period={}".format(self.period))
        wl_model_delays, sae_model_delays = self.get_model_delays(read_port)
        
        debug.info(1,"Measured Wordline delays (ns):\n\t {}".format(wl_delays[read_port]))
        debug.info(1,"Wordline model delays:\n\t {}".format(wl_model_delays))
        debug.info(1,"Measured Wordline slews:\n\t {}".format(wl_slews[read_port]))
        debug.info(1,"Measured SAE delays (ns):\n\t {}".format(sae_delays[read_port]))
        debug.info(1,"SAE model delays:\n\t {}".format(sae_model_delays))
        debug.info(1,"Measured SAE slews:\n\t {}".format(sae_slews[read_port]))
        
        return wl_delays, sae_delays

        
    
  