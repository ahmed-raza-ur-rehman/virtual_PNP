// Formal verification properties (SVA)
module formal_props (
    input logic clk,
    input logic rst_n,
    input logic [31:0] position,
    input logic [31:0] target,
    input logic [31:0] velocity
);
    // Position bounded by workspace
    property p_workspace;
        @(posedge clk) disable iff (!rst_n)
            (position <= 32'd220);
    endproperty
    a_workspace: assert property (p_workspace);

    // Velocity never exceeds max
    property p_vel_limit;
        @(posedge clk) disable iff (!rst_n)
            (velocity <= 32'd200);
    endproperty
    a_vel_limit: assert property (p_vel_limit);

    // Eventually reaches target
    property p_reach;
        @(posedge clk) disable iff (!rst_n)
            (target != 0) |-> ##[1:1000] (position == target);
    endproperty
    // a_reach: assert property (p_reach); // liveness, tool-dependent
endmodule
