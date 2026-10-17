module eth_mac (
    input  wire clk,
    input  wire rst_n,
    input  wire [7:0] tx_data,
    input  wire tx_valid,
    output reg  tx_ready,
    output reg  [7:0] rx_data,
    output reg  rx_valid,
    input  wire rx_ready,
    // PHY interface
    output reg  eth_tx,
    input  wire eth_rx
);
    // simplified MAC
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin tx_ready <= 1; rx_valid <= 0; end
        else begin
            tx_ready <= 1;
            rx_data <= eth_rx ? 8'hFF : 8'h00;
            rx_valid <= eth_rx;
        end
    end
endmodule
