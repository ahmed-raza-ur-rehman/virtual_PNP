module spi_master #(
    parameter CLK_DIV = 4
)(
    input  wire clk,
    input  wire rst_n,
    input  wire [7:0] tx_data,
    input  wire tx_valid,
    output reg  tx_ready,
    output reg  [7:0] rx_data,
    output reg  rx_valid,
    input  wire rx_ready,
    output reg  sclk,
    output reg  mosi,
    input  wire miso,
    output reg  cs_n
);
    reg [2:0] bit_cnt;
    reg [7:0] shifter;
    reg [1:0] state; // 0 idle, 1 transfer
    reg [31:0] clk_cnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= 0; tx_ready <= 1; rx_valid <= 0; sclk <= 0; cs_n <= 1; mosi <= 0;
        end else begin
            case (state)
                0: begin
                    tx_ready <= 1; cs_n <= 1;
                    if (tx_valid) begin
                        shifter <= tx_data; bit_cnt <= 0; clk_cnt <= 0;
                        cs_n <= 0; state <= 1; tx_ready <= 0;
                    end
                end
                1: begin
                    if (clk_cnt < CLK_DIV - 1) clk_cnt <= clk_cnt + 1;
                    else begin
                        clk_cnt <= 0; sclk <= ~sclk;
                        if (sclk == 0) begin
                            mosi <= shifter[7];
                            shifter <= {shifter[6:0], miso};
                            bit_cnt <= bit_cnt + 1;
                            if (bit_cnt == 7) begin
                                rx_data <= {shifter[6:0], miso}; rx_valid <= 1;
                                state <= 0; cs_n <= 1; sclk <= 0;
                            end
                        end
                    end
                end
            endcase
        end
    end
endmodule
