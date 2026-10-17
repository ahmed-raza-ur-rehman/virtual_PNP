// UVM test sequences for motion controller
class smoke_seq extends motion_base_seq;
    `uvm_object_utils(smoke_seq)
    function new(string name="smoke_seq"); super.new(name); endfunction
    task body();
        motion_seq_item req;
        req = motion_seq_item::type_id::create("req");
        start_item(req);
        req.target = 100; req.v_max = 50; req.a_max = 10;
        finish_item(req);
    endtask
endclass

class stress_seq extends motion_base_seq;
    `uvm_object_utils(stress_seq)
    function new(string name="stress_seq"); super.new(name); endfunction
    task body();
        motion_seq_item req;
        repeat (1000) begin
            req = motion_seq_item::type_id::create("req");
            start_item(req);
            assert(req.randomize());
            finish_item(req);
        end
    endtask
endclass

class regression_seq extends uvm_sequence #(motion_seq_item);
    `uvm_object_utils(regression_seq)
    function new(string name="regression_seq"); super.new(name); endfunction
    task body();
        smoke_seq s = smoke_seq::type_id::create("s");
        stress_seq t = stress_seq::type_id::create("t");
        s.start(m_sequencer);
        t.start(m_sequencer);
    endtask
endclass
