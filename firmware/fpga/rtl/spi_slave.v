module spi_slave (
    input  wire sclk,
    input  wire mosi,
    output reg  miso,
    input  wire cs_n,
    input  wire [7:0] tx_data,
    output reg  [7:0] rx_data,
    output reg        rx_valid
);
    reg [2:0] bitcnt;
    reg [7:0] shifter;
    always @(posedge sclk or posedge cs_n) begin
        if (cs_n) begin bitcnt <= 0; rx_valid <= 0; end
        else begin
            shifter <= {shifter[6:0], mosi};
            bitcnt <= bitcnt + 1;
            if (bitcnt == 3'd7) begin
                rx_data <= {shifter[6:0], mosi};
                rx_valid <= 1;
            end
        end
    end
    // miso simple
    always @(*) miso = tx_data[7 - bitcnt];
endmodule
