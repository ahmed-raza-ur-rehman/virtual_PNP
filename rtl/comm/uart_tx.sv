// ---------------------------------------------------------------------------
// uart_tx - 8N1 transmitter with a single-cycle accept handshake.
//
// BAUD_DIV is derived by the tooling from CLK_HZ/BAUD_RATE; the RTL keeps the
// division out of the state machine so that a clock change is a parameter
// change, never a code edit.  `ready` is high whenever a byte can be accepted,
// which lets the packet framer stream without an output FIFO.
// ---------------------------------------------------------------------------
module uart_tx #(
    parameter integer CLK_HZ   = 100_000_000,
    parameter integer BAUD     = 115_200,
    parameter integer BAUD_DIV = CLK_HZ / BAUD
) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] data,
    input  wire       valid,
    output reg        ready,
    output reg        tx,
    output reg        busy
);
    localparam [1:0] S_IDLE  = 2'd0, S_START = 2'd1, S_DATA = 2'd2, S_STOP = 2'd3;
    reg [1:0]  state;
    reg [15:0] div_cnt;
    reg [2:0]  bit_idx;
    reg [7:0]  shifter;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; tx <= 1'b1; ready <= 1'b1; busy <= 1'b0;
            div_cnt <= 16'd0; bit_idx <= 3'd0; shifter <= 8'h00;
        end else begin
            case (state)
                S_IDLE: begin
                    tx    <= 1'b1;
                    busy  <= 1'b0;
                    ready <= 1'b1;
                    if (valid && ready) begin
                        shifter <= data;
                        ready   <= 1'b0;
                        busy    <= 1'b1;
                        div_cnt <= 16'd0;
                        state   <= S_START;
                    end
                end
                S_START: begin
                    tx <= 1'b0;
                    if (div_cnt == BAUD_DIV[15:0] - 16'd1) begin
                        div_cnt <= 16'd0;
                        bit_idx <= 3'd0;
                        state   <= S_DATA;
                    end else div_cnt <= div_cnt + 16'd1;
                end
                S_DATA: begin
                    tx <= shifter[bit_idx];
                    if (div_cnt == BAUD_DIV[15:0] - 16'd1) begin
                        div_cnt <= 16'd0;
                        if (bit_idx == 3'd7) state <= S_STOP;
                        else bit_idx <= bit_idx + 3'd1;
                    end else div_cnt <= div_cnt + 16'd1;
                end
                S_STOP: begin
                    tx <= 1'b1;
                    if (div_cnt == BAUD_DIV[15:0] - 16'd1) begin
                        div_cnt <= 16'd0;
                        busy    <= 1'b0;
                        ready   <= 1'b1;
                        state   <= S_IDLE;
                    end else div_cnt <= div_cnt + 16'd1;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
