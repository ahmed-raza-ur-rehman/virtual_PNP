// ---------------------------------------------------------------------------
// uart_rx - 8N1 receiver with 16x oversampling and mid-bit sampling.
//
// Sampling in the middle of each bit window is what buys noise margin: the
// start-bit edge aligns the counter, and every subsequent decision is taken
// 8 sub-cycles after the bit boundary.  A stop-bit that is not high is
// reported as a framing error and the byte is dropped, so a corrupted frame
// can never look like valid data.
// ---------------------------------------------------------------------------
module uart_rx #(
    parameter integer CLK_HZ   = 100_000_000,
    parameter integer BAUD     = 115_200,
    parameter integer BAUD_DIV = CLK_HZ / BAUD,
    parameter         OVERSAMPLE = 16
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rx,
    output reg  [7:0] data,
    output reg        valid,
    output reg        frame_error
);
    localparam integer OS_DIV = BAUD_DIV / OVERSAMPLE;
    localparam [2:0] S_IDLE = 3'd0, S_START = 3'd1, S_DATA = 3'd2, S_STOP = 3'd3;

    reg [2:0]  state;
    reg [2:0]  bit_idx;
    reg [3:0]  os_cnt;
    reg [7:0]  shifter;
    reg [2:0]  rx_sync;
    reg [15:0] tick_cnt;

    wire rx_bit = rx_sync[2];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_sync <= 3'b111;
        end else begin
            rx_sync <= {rx_sync[1:0], rx};
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; valid <= 1'b0; frame_error <= 1'b0;
            bit_idx <= 3'd0; os_cnt <= 4'd0; shifter <= 8'h00; tick_cnt <= 16'd0; data <= 8'h00;
        end else begin
            valid <= 1'b0;
            case (state)
                S_IDLE: begin
                    frame_error <= 1'b0;
                    if (!rx_bit) begin          // falling edge of the start bit
                        os_cnt  <= 4'd0;
                        state   <= S_START;
                    end
                end
                S_START: begin
                    // confirm the start bit at its centre before committing
                    if (os_cnt == 4'd7) begin
                        if (!rx_bit) begin
                            os_cnt <= 4'd0;
                            tick_cnt <= 16'd0;
                            bit_idx <= 3'd0;
                            state <= S_DATA;
                        end else begin
                            state <= S_IDLE;     // glitch, not a frame
                        end
                    end else if (tick_cnt == OS_DIV - 1) begin
                        tick_cnt <= 16'd0;
                        os_cnt <= os_cnt + 4'd1;
                    end else tick_cnt <= tick_cnt + 16'd1;
                end
                S_DATA: begin
                    if (tick_cnt == OS_DIV - 1) begin
                        tick_cnt <= 16'd0;
                        if (os_cnt == 4'd15) begin
                            os_cnt <= 4'd0;
                            shifter[bit_idx] <= rx_bit;
                            if (bit_idx == 3'd7) state <= S_STOP;
                            else bit_idx <= bit_idx + 3'd1;
                        end else os_cnt <= os_cnt + 4'd1;
                    end else tick_cnt <= tick_cnt + 16'd1;
                end
                S_STOP: begin
                    if (tick_cnt == OS_DIV - 1) begin
                        tick_cnt <= 16'd0;
                        if (os_cnt == 4'd15) begin
                            os_cnt <= 4'd0;
                            if (rx_bit) begin
                                data  <= shifter;
                                valid <= 1'b1;
                            end else frame_error <= 1'b1;
                            state <= S_IDLE;
                        end else os_cnt <= os_cnt + 4'd1;
                    end else tick_cnt <= tick_cnt + 16'd1;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
