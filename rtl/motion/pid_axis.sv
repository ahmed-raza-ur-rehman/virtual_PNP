// ---------------------------------------------------------------------------
// pid_axis - fixed-point PID with anti-windup and derivative-on-measurement.
//
// * derivative is taken on the measurement, not on the error, so that a step
//   change of the setpoint cannot produce a derivative kick - the standard
//   cure for nozzle "slap" on a head that is already settling.
// * the integrator is frozen while the output saturates (conditional
//   integration), which removes wind-up without a separate clamp loop.
// * gains are Q4.12 and can be re-written at run time through the CSA.
// ---------------------------------------------------------------------------
`include "pnp_defs.svh"
module pid_axis #(
    parameter integer W = `PNP_POS_W
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                sample_en,
    input  wire signed [W-1:0] setpoint,
    input  wire signed [W-1:0] measured,
    input  wire signed [15:0]  kp,           // Q4.12
    input  wire signed [15:0]  ki,           // Q4.12
    input  wire signed [15:0]  kd,           // Q4.12
    input  wire signed [W-1:0] out_max,
    output reg  signed [W-1:0] out,
    output reg                 saturated,
    output reg  signed [W-1:0] error_dbg
);
    reg signed [W-1:0] err, prev_meas;
    reg signed [W+16:0] integ;               // wide: integrator must not wrap
    wire signed [W-1:0] dmeas = measured - prev_meas;

    // Q4.12 * Q12.4 -> Q16.8; shift back to Q12.4 (>> 12 with rounding).
    wire signed [W+16:0] p_term = err * kp;
    wire signed [W+16:0] i_term = integ * ki;
    wire signed [W+16:0] d_term = dmeas * kd;
    wire signed [W+16:0] unsat  = (p_term >>> 12) + (i_term >>> 12) - (d_term >>> 12);

    wire signed [W-1:0] out_lim = (unsat > out_max)  ? out_max  :
                                  (unsat < -out_max) ? -out_max : unsat[W-1:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            err <= {W{1'b0}}; prev_meas <= {W{1'b0}}; integ <= {(W+17){1'b0}};
            out <= {W{1'b0}}; saturated <= 1'b0; error_dbg <= {W{1'b0}};
        end else if (sample_en) begin
            err <= setpoint - measured;
            error_dbg <= setpoint - measured;
            prev_meas <= measured;
            // conditional integration: only accumulate while unsaturated
            if (!saturated) integ <= integ + {{(17){setpoint[W-1]}}, (setpoint - measured)};
            out <= out_lim;
            saturated <= (unsat > out_max) || (unsat < -out_max);
        end
    end
endmodule
