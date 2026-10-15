module uart_tx #(
    parameter CLK_FREQ = 100000000,
    parameter BAUD = 115200
)(
    input wire clk,
    input wire rst,
    input wire [7:0] data,
    input wire send,
    output reg tx,
    output reg busy
);
    localparam CLKS_PER_BIT = CLK_FREQ / BAUD;
    reg [31:0] clk_count;
    reg [3:0] bit_index;
    reg [9:0] shifter;
    reg state; // 0 idle, 1 send
    always @(posedge clk or posedge rst) begin
        if (rst) begin tx <= 1; busy <= 0; state <= 0; end
        else if (state == 0) begin
            tx <= 1; busy <= 0;
            if (send) begin
                shifter <= {1'b1, data, 1'b0};
                state <= 1; busy <= 1; clk_count <= 0; bit_index <= 0;
            end
        end else begin
            if (clk_count < CLKS_PER_BIT - 1) clk_count <= clk_count + 1;
            else begin
                clk_count <= 0;
                tx <= shifter[bit_index];
                bit_index <= bit_index + 1;
                if (bit_index == 9) begin state <= 0; busy <= 0; end
            end
        end
    end
endmodule
