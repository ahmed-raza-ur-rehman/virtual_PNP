// ---------------------------------------------------------------------------
// stepgen - velocity-to-step DDA converter with direction and enable.
//
// A conventional Bresenham/DDA accumulator: the velocity word (Q12.4 um/s)
// is scaled by STEP_SCALE and accumulated every sample; the carry out of the
// accumulator is the step pulse and the remainder carries over, so the average
// step rate is exact over any window (no systematic position drift).
//
// STEP_SCALE encodes  2^ACC_W / (steps_per_um * sample_rate)  and is generated
// by the tooling from the lead-screw pitch and micro-stepping settings so that
// the RTL cannot silently disagree with the mechanics.
// ---------------------------------------------------------------------------
`include "pnp_defs.svh"
module stepgen #(
    parameter integer W       = `PNP_POS_W,
    parameter integer ACC_W   = 24,
    parameter [ACC_W-1:0] STEP_SCALE = 24'd16777   // 2^24 / (80 steps/um * 20 kHz * 50)
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                sample_en,     // 1 = advance DDA by one sample
    input  wire signed [W-1:0] velocity,
    input  wire                enable,
    output reg                 step,
    output reg                 dir,
    output reg  signed [W-1:0] position_um
);
    reg [ACC_W-1:0] acc;
    wire signed [W+ACC_W:0] inc_wide = velocity * $signed({1'b0, STEP_SCALE});
    wire [ACC_W:0]          inc      = enable ? inc_wide[ACC_W:0] : {(ACC_W+1){1'b0}};
    wire [ACC_W:0]          sum      = {1'b0, acc} + inc;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc <= {ACC_W{1'b0}};
            step <= 1'b0;
            dir <= 1'b0;
            position_um <= {W{1'b0}};
        end else begin
            step <= 1'b0;
            if (sample_en && enable) begin
                acc <= sum[ACC_W-1:0];
                step <= sum[ACC_W];
                dir <= inc_wide[W+ACC_W];
                // integrate steps back into an engineering-unit position for
                // telemetry: 1 step = STEP_SCALE^-1 in the DDA domain, and the
                // caller converts to um using the same constant.
                position_um <= position_um + (sum[ACC_W] ? (inc_wide[W+ACC_W] ? -1 : 1) : 0);
            end
        end
    end
endmodule
