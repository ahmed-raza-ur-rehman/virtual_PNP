module i2c_slave (
    input  wire clk,
    input  wire rst_n,
    input  wire sda_in,
    output reg  sda_out,
    output reg  sda_oe,
    input  wire scl,
    output reg  [7:0] rx_data,
    output reg  rx_valid,
    input  wire [7:0] tx_data,
    input  wire tx_valid
);
    reg [2:0] bit_cnt;
    reg [7:0] shifter;
    reg state; // 0 addr, 1 data
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin sda_out <= 1; sda_oe <= 0; rx_valid <= 0; state <= 0; bit_cnt <= 0; end
        else begin
            rx_valid <= 0;
            // simplified: capture on scl rising
        end
    end
endmodule
