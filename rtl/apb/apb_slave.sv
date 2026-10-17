// Generic APB Slave with register file
module apb_slave #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32,
    parameter NUM_REGS = 16
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    psel,
    input  logic                    penable,
    input  logic                    pwrite,
    input  logic [ADDR_WIDTH-1:0]   paddr,
    input  logic [DATA_WIDTH-1:0]   pwdata,
    output logic [DATA_WIDTH-1:0]   prdata,
    output logic                    pready,
    output logic                    pslverr
);
    logic [DATA_WIDTH-1:0] regs [0:NUM_REGS-1];
    logic [3:0] addr_idx;

    assign addr_idx = paddr[5:2];
    assign pready = 1'b1;
    assign pslverr = 1'b0;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < NUM_REGS; i++) regs[i] <= 0;
        end else if (psel && penable && pwrite) begin
            if (addr_idx < NUM_REGS)
                regs[addr_idx] <= pwdata;
        end
    end

    always_comb begin
        if (psel && !pwrite && addr_idx < NUM_REGS)
            prdata = regs[addr_idx];
        else
            prdata = 0;
    end
endmodule
