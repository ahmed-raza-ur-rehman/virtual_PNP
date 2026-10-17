module can_ctrl (
    input  wire clk,
    input  wire rst_n,
    input  wire [10:0] tx_id,
    input  wire [7:0]  tx_data [0:7],
    input  wire [3:0]  tx_len,
    input  wire        tx_start,
    output reg         tx_done,
    output reg         tx_error,
    input  wire        can_rx,
    output reg         can_tx
);
    // simplified CAN controller
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin tx_done <= 0; tx_error <= 0; can_tx <= 1; end
        else if (tx_start) begin tx_done <= 1; can_tx <= 0; end
        else begin tx_done <= 0; can_tx <= 1; end
    end
endmodule
