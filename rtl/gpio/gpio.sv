module gpio #(
    parameter N = 32
)(
    input  wire clk,
    input  wire rst_n,
    input  wire [N-1:0] in,
    output reg  [N-1:0] out,
    output reg  [N-1:0] oe,
    input  wire [N-1:0] wdata,
    input  wire         we_out,
    input  wire         we_oe
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin out <= 0; oe <= 0; end
        else begin
            if (we_out) out <= wdata;
            if (we_oe) oe <= wdata;
        end
    end
endmodule
