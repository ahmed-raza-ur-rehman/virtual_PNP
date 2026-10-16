class motion_base_seq extends uvm_sequence #(motion_seq_item);
    `uvm_object_utils(motion_base_seq)
    function new(string name="motion_base_seq"); super.new(name); endfunction
    task body();
        motion_seq_item req;
        repeat (10) begin
            req = motion_seq_item::type_id::create("req");
            start_item(req);
            assert(req.randomize());
            finish_item(req);
        end
    endtask
endclass
