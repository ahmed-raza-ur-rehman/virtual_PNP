module sram_ctrl #(
    parameter ADDR_W = 16,
    parameter DATA_W = 32
)(
    input  wire clk,
    input  wire rst_n,
    input  wire ce,
    input  wire we,
    input  wire [ADDR_W-1:0] addr,
    input  wire [DATA_W-1:0] wdata,
    output reg  [DATA_W-1:0] rdata
);
    reg [DATA_W-1:0] mem [0:(1<<ADDR_W)-1];
    always @(posedge clk) begin
        if (ce) begin
            if (we) mem[addr] <= wdata;
            rdata <= mem[addr];
        end
    end
endmodule
