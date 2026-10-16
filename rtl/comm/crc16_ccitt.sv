// ---------------------------------------------------------------------------
// crc16_ccitt - CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflection).
//
// A single byte is offered with `start`; the register is updated combinationally
// and captured on the following cycle, so back-to-back bytes sustain one byte
// per clock without an internal shift FSM.  `crc` is valid after `done`.
//
// The polynomial, init and bit order are frozen in RTL *and* re-implemented in
// the host tools (pnp/comm/crc.py) with a cross-check test, because a CRC
// mismatch between firmware and FPGA is a classic silent integration failure.
// ---------------------------------------------------------------------------
module crc16_ccitt (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [7:0]  data,
    input  wire        clear,
    output reg  [15:0] crc,
    output reg         done
);
    integer i;
    reg [15:0] c;
    always @(*) begin
        c = crc ^ {data, 8'h00};
        for (i = 0; i < 8; i = i + 1)
            c = c[15] ? ((c << 1) ^ 16'h1021) : (c << 1);
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            crc  <= 16'hFFFF;
            done <= 1'b0;
        end else begin
            done <= 1'b0;
            if (clear) crc <= 16'hFFFF;
            else if (start) begin
                crc  <= c;
                done <= 1'b1;
            end
        end
    end
endmodule
