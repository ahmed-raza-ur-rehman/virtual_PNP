// Layered testbench: unit-level for motion controller
`timescale 1ns/1ps
module motion_controller_tb;
    import uvm_pkg::*;
    `include "uvm_macros.svh"

    logic clk = 0;
    always #5 clk = ~clk;

    pnp_if vif(clk);

    motion_controller #(.DATA_W(32)) dut (
        .clk(clk), .rst(vif.rst_n == 0 ? 1 : 0),
        .target(vif.target_pos), .v_max(vif.v_max), .a_max(vif.a_max),
        .position(vif.position), .velocity(vif.velocity)
    );

    // Simple directed test
    initial begin
        vif.rst_n = 0;
        vif.target_pos = 0;
        vif.v_max = 100;
        vif.a_max = 10;
        #20 vif.rst_n = 1;
        #10 vif.target_pos = 500;
        #2000;
        $display("FINAL POS = %0d", vif.position);
        if (vif.position >= 490 && vif.position <= 510)
            $display("TEST PASSED");
        else
            $display("TEST FAILED");
        $finish;
    end

    // SVA: position never exceeds target+margin during motion
    property p_no_overshoot;
        @(posedge clk) disable iff (!vif.rst_n)
            (vif.target_pos > vif.position) |-> (vif.position <= vif.target_pos + 5);
    endproperty
    a_no_overshoot: assert property (p_no_overshoot) else $error("Overshoot detected");
endmodule
