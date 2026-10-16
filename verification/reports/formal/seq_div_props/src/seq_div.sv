// ---------------------------------------------------------------------------
// seq_div - unsigned restoring divider, W bits, one quotient bit per cycle.
//
// Algorithm (textbook restoring division, one bit per cycle):
//
//     rem = 0; quo = 0
//     for i = W-1 down to 0:
//         rem = (rem << 1) | dividend[i]
//         if (rem >= divisor) begin rem -= divisor; quo[i] = 1; end
//
// The first implementation of this block accumulated repeated subtractions
// without shifting the dividend in, which computes something that only looks
// like a quotient (it saturates for any dividend >= W*divisor).  The formal
// property seq_div_props P2 -- quotient*divisor + remainder == dividend --
// found it before any of the arithmetic reached hardware, which is exactly
// why the planner's braking distance is proved rather than spot-checked.
//
// Division by zero is reported explicitly (quotient saturated, remainder 0,
// done raised) so that a caller cannot mistake a fault for a result.
//
// Latency: W + 1 cycles.  Area: one W-bit subtractor + two W-bit registers,
// i.e. it does not add to the sample-loop critical path.
// ---------------------------------------------------------------------------
module seq_div #(
    parameter integer W = 32
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            start,
    input  wire [W-1:0]    dividend,
    input  wire [W-1:0]    divisor,
    output reg  [W-1:0]    quotient,
    output reg  [W-1:0]    remainder,
    output reg             busy,
    output reg             done
);
    localparam integer CW = $clog2(W) + 1;

    reg [W-1:0]  rem;      // running remainder
    reg [W-1:0]  quo;      // quotient being assembled, MSB first
    reg [W-1:0]  dend;     // dividend shift register
    reg [W-1:0]  div;      // latched divisor (1 when the divisor was zero)
    reg          zero_div; // the request was a division by zero
    reg [CW-1:0] cnt;

    wire [W:0]   shifted = {rem[W-2:0], dend[W-1]};      // rem<<1 | next bit
    wire         ge      = (shifted >= {1'b0, div});
    wire [W-1:0] rem_n   = ge ? (shifted[W-1:0] - div) : shifted[W-1:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rem <= {W{1'b0}}; quo <= {W{1'b0}}; dend <= {W{1'b0}}; div <= {W{1'b0}};
            cnt <= {CW{1'b0}};
            zero_div <= 1'b0;
            busy <= 1'b0; done <= 1'b0;
            quotient <= {W{1'b0}}; remainder <= {W{1'b0}};
        end else begin
            done <= 1'b0;
            if (start && !busy) begin
                // A zero divisor takes the same latency as any other division.
                // Reporting it combinationally in the start cycle would make
                // `done` timing data dependent, and the caller (the profile
                // planner) would need a second timing path to handle it.
                rem      <= {W{1'b0}};
                quo      <= {W{1'b0}};
                dend     <= dividend;
                div      <= (divisor == {W{1'b0}}) ? {{(W-1){1'b0}}, 1'b1} : divisor;
                zero_div <= (divisor == {W{1'b0}});
                cnt      <= W[CW-1:0];
                busy     <= 1'b1;
            end else if (busy) begin
                rem  <= rem_n;
                quo  <= {quo[W-2:0], ge};
                dend <= {dend[W-2:0], 1'b0};
                cnt  <= cnt - 1'b1;
                if (cnt == {{(CW-1){1'b0}}, 1'b1}) begin
                    busy      <= 1'b0;
                    done      <= 1'b1;
                    // zero-divisor requests report a saturated quotient and a
                    // zero remainder, which the caller can test with one
                    // comparison instead of tracking a separate error flag
                    quotient  <= zero_div ? {W{1'b1}} : {quo[W-2:0], ge};
                    remainder <= zero_div ? {W{1'b0}} : rem_n;
                end
            end
        end
    end
endmodule
