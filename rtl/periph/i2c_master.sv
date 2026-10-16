module i2c_master (
    input  wire clk,
    input  wire rst_n,
    input  wire [7:0] tx_data,
    input  wire start,
    output reg  sda,
    output reg  scl,
    output reg  busy
);
    // simplified I2C master (bit-bang style state machine placeholder)
    reg [3:0] state;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin sda <= 1; scl <= 1; busy <= 0; state <= 0; end
        else if (start && !busy) begin busy <= 1; state <= 1; end
        else if (busy) begin
            // toggle scl
            scl <= ~scl;
            if (state == 4'd8) begin busy <= 0; state <= 0; sda <= 1; end
            else state <= state + 1;
        end
    end
endmodule
