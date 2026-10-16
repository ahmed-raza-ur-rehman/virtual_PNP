// ---------------------------------------------------------------------------
// packet_if - framed command parser (the machine's wire protocol decoder).
//
// Frame layout (docs/ICD.md, "host protocol"):
//
//   | 0xAA | 0x55 | CMD | LEN(1..8) | PAYLOAD[LEN] | CRC16 hi | CRC16 lo |
//
// The CRC covers CMD, LEN and PAYLOAD.  The parser is a byte-level receiver:
// it is fed by either the SPI slave or the UART receiver through a mux, so the
// same framing and the same CRC protect both links.  Errors are reported as a
// one-hot code rather than dropped silently:
//
//   err_bad_crc    payload arrived but the CRC did not match
//   err_bad_len    length field outside [1..MAX_PAYLOAD]
//   err_timeout    bytes stopped arriving mid-frame (watchdog on the link)
//
// A frame is only forwarded once the CRC has been verified, which means a
// glitch on a long cable cannot inject a motion command.
// ---------------------------------------------------------------------------
`include "pnp_defs.svh"
module packet_if #(
    parameter integer MAX_PAYLOAD = 8,
    parameter integer LEN_W       = 4,
    parameter integer TIMEOUT     = 1000      // link watchdog, in clocks
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [7:0]           rx_byte,
    input  wire                 rx_valid,
    output reg                  cmd_valid,
    output reg  [7:0]           cmd,
    output reg  [LEN_W-1:0]     payload_len,
    output reg  [MAX_PAYLOAD*8-1:0] payload,
    output reg                  err_bad_crc,
    output reg                  err_bad_len,
    output reg                  err_timeout,
    output reg  [7:0]           frames_ok,
    output reg  [7:0]           frames_err
);
    localparam [2:0] S_SYNC1 = 3'd0, S_SYNC2 = 3'd1, S_CMD = 3'd2,
                     S_LEN  = 3'd3, S_PAYLOAD = 3'd4, S_CRC1 = 3'd5,
                     S_CRC2 = 3'd6;

    reg [2:0]  state;
    reg [7:0]  len_reg, idx;
    reg        tick_en;
    reg [15:0] crc;
    reg        crc_start, crc_clear;
    reg [7:0]  crc_data;
    reg [15:0] timeout_cnt;
    reg [7:0]  payload_buf [0:MAX_PAYLOAD-1];
    reg [7:0]  cmd_reg;
    reg [15:0] crc_calc;
    integer    i;
    wire       crc_done;
    wire [15:0] crc_out;

    crc16_ccitt u_crc (
        .clk(clk), .rst_n(rst_n), .start(crc_start), .data(crc_data),
        .clear(crc_clear), .crc(crc_out), .done(crc_done)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_SYNC1; cmd_valid <= 1'b0; cmd <= 8'h00; payload_len <= {LEN_W{1'b0}};
            payload <= {(MAX_PAYLOAD*8){1'b0}}; err_bad_crc <= 1'b0; err_bad_len <= 1'b0;
            err_timeout <= 1'b0; frames_ok <= 8'h00; frames_err <= 8'h00;
            len_reg <= 8'h00; idx <= 8'h00; tick_en <= 1'b0; timeout_cnt <= 16'd0;
            crc_start <= 1'b0; crc_clear <= 1'b0; cmd_reg <= 8'h00;
        end else begin
            crc_start <= 1'b0;
            crc_clear <= 1'b0;
            cmd_valid <= 1'b0;

            // link watchdog: a frozen link in the middle of a frame is an error
            if (state != S_SYNC1 && rx_valid) timeout_cnt <= 16'd0;
            else if (state != S_SYNC1) begin
                if (timeout_cnt == TIMEOUT-1) begin
                    err_timeout <= 1'b1;
                    frames_err  <= frames_err + 8'd1;
                    state       <= S_SYNC1;
                    timeout_cnt <= 16'd0;
                end else timeout_cnt <= timeout_cnt + 16'd1;
            end

            if (rx_valid) begin
                // Only CMD/LEN/PAYLOAD feed the CRC.  The two CRC bytes must
                // not be folded back into the register, otherwise the value
                // being compared has already absorbed the value it is compared
                // against and every frame fails verification - found by the
                // spi_packet_link and packet_if_vectors testbenches.
                crc_data  <= rx_byte;
                crc_start <= (state != S_CRC1) && (state != S_CRC2);
                case (state)
                    S_SYNC1: begin
                        crc_clear <= 1'b1;
                        idx       <= 8'h00;
                        state     <= (rx_byte == 8'hAA) ? S_SYNC2 : S_SYNC1;
                    end
                    S_SYNC2: begin
                        if (rx_byte == 8'h55) begin
                            // The CRC covers CMD, LEN and PAYLOAD only, so the
                            // running CRC is cleared on the *second* sync byte.
                            // Letting 0x55 leak into the CRC (the first
                            // implementation did) makes every well-formed frame
                            // fail verification on the host - found by the
                            // spi_packet_link testbench.
                            crc_clear <= 1'b1;
                            crc_start <= 1'b0;
                            state     <= S_CMD;
                        end else state <= S_SYNC1;
                    end
                    S_CMD: begin
                        cmd_reg <= rx_byte;
                        state   <= S_LEN;
                    end
                    S_LEN: begin
                        if (rx_byte == 8'h00 || rx_byte > MAX_PAYLOAD[7:0]) begin
                            err_bad_len <= 1'b1;
                            frames_err  <= frames_err + 8'd1;
                            state       <= S_SYNC1;
                        end else begin
                            len_reg <= rx_byte;
                            state   <= S_PAYLOAD;
                        end
                    end
                    S_PAYLOAD: begin
                        payload_buf[idx[LEN_W-1:0]] <= rx_byte;
                        idx <= idx + 8'd1;
                        if (idx + 8'd1 >= len_reg) state <= S_CRC1;
                    end
                    S_CRC1: begin
                        crc_calc[15:8] <= rx_byte;
                        state <= S_CRC2;
                    end
                    S_CRC2: begin
                        crc_calc[7:0] <= rx_byte;
                        // compare against the CRC that has been computed over
                        // CMD/LEN/PAYLOAD; the two sync bytes were cleared out
                        if ({crc_calc[15:8], rx_byte} == crc_out) begin
                            cmd         <= cmd_reg;
                            payload_len <= len_reg[LEN_W-1:0];
                            for (i = 0; i < MAX_PAYLOAD; i = i + 1)
                                payload[i*8 +: 8] <= (i < len_reg) ? payload_buf[i] : 8'h00;
                            cmd_valid  <= 1'b1;
                            frames_ok  <= frames_ok + 8'd1;
                        end else begin
                            err_bad_crc <= 1'b1;
                            frames_err  <= frames_err + 8'd1;
                        end
                        state <= S_SYNC1;
                    end
                    default: state <= S_SYNC1;
                endcase
            end
        end
    end
endmodule
