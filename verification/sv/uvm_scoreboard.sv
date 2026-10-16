class motion_scoreboard extends uvm_scoreboard;
    `uvm_component_utils(motion_scoreboard)
    uvm_analysis_imp #(motion_seq_item, motion_scoreboard) imp;
    function new(string name, uvm_component parent); super.new(name, parent); imp = new("imp", this); endfunction
    function void write(motion_seq_item t);
        // check position reached target
    endfunction
endclass

class motion_coverage extends uvm_subscriber #(motion_seq_item);
    `uvm_component_utils(motion_coverage)
    covergroup cg;
        coverpoint ...; // placeholder
    endgroup
    function new(string name, uvm_component parent); super.new(name, parent); cg = new(); endfunction
    function void write(motion_seq_item t); cg.sample(); endfunction
endclass
