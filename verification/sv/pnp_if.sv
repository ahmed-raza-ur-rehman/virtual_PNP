interface pnp_if (input logic clk);
    logic        rst_n;
    logic [31:0] target_pos;
    logic [31:0] v_max, a_max;
    logic [31:0] position;
    logic [31:0] velocity;
    logic        done;
    modport dut (input clk, rst_n, target_pos, v_max, a_max, output position, velocity, done);
    modport tb  (input clk, output rst_n, target_pos, v_max, a_max, input position, velocity, done);
endinterface
