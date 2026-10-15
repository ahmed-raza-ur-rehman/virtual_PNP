module trajectory_buffer #(
    parameter DEPTH = 256,
    parameter WIDTH = 32
)(
    input wire clk,
    input wire we,
    input wire [$clog2(DEPTH)-1:0] addr,
    input wire [WIDTH-1:0] din,
    output reg [WIDTH-1:0] dout
);
    reg [WIDTH-1:0] mem [0:DEPTH-1];
    always @(posedge clk) begin
        if (we) mem[addr] <= din;
        dout <= mem[addr];
    end
endmodule
