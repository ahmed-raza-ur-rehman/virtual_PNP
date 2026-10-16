// UVM agent skeleton for motion controller
`ifndef UVM_MOTION_AGENT_SV
`define UVM_MOTION_AGENT_SV
import uvm_pkg::*;
`include "uvm_macros.svh"

class motion_seq_item extends uvm_sequence_item;
    rand bit [31:0] target;
    rand bit [31:0] v_max;
    rand bit [31:0] a_max;
    `uvm_object_utils(motion_seq_item)
    function new(string name="motion_seq_item"); super.new(name); endfunction
endclass

class motion_driver extends uvm_driver #(motion_seq_item);
    virtual pnp_if vif;
    `uvm_component_utils(motion_driver)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    task run_phase(uvm_phase phase);
        motion_seq_item req;
        forever begin
            seq_item_port.get_next_item(req);
            vif.target_pos <= req.target;
            vif.v_max <= req.v_max;
            vif.a_max <= req.a_max;
            #100;
            seq_item_port.item_done();
        end
    endtask
endclass

class motion_monitor extends uvm_monitor;
    virtual pnp_if vif;
    uvm_analysis_port #(motion_seq_item) ap;
    `uvm_component_utils(motion_monitor)
    function new(string name, uvm_component parent); super.new(name, parent); ap = new("ap", this); endfunction
    task run_phase(uvm_phase phase);
        forever begin
            @(posedge vif.clk);
            // sample
        end
    endtask
endclass

class motion_agent extends uvm_agent;
    motion_driver drv;
    motion_monitor mon;
    uvm_sequencer #(motion_seq_item) seqr;
    `uvm_component_utils(motion_agent)
    function new(string name, uvm_component parent); super.new(name, parent); endfunction
    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        mon = motion_monitor::type_id::create("mon", this);
        if (get_is_active() == UVM_ACTIVE) begin
            drv = motion_driver::type_id::create("drv", this);
            seqr = uvm_sequencer#(motion_seq_item)::type_id::create("seqr", this);
        end
    endfunction
    function void connect_phase(uvm_phase phase);
        if (get_is_active() == UVM_ACTIVE) drv.seq_item_port.connect(seqr.seq_item_export);
    endfunction
endclass
`endif
