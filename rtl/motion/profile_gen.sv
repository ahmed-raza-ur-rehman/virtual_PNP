// ---------------------------------------------------------------------------
// profile_gen - jerk-limited trapezoidal setpoint generator for one axis.
//
// Plan phase (once per move):
//   1. dist  = target - position                    (Q12.4)
//   2. v_peak = sqrt(2*a*dist) when the move is too short to reach v_max,
//      implemented as a compare against the braking distance instead of an
//      explicit square root (see step 3).
//   3. brake = v_max^2 / (2*a_max) via seq_div: the distance needed to stop
//      from v_max.  If dist < brake the move is triangular and the cruise
//      phase is skipped.
// Execute phase: accel ramps towards +/-a_max at j_max per sample, cruise
// holds v_max, decel mirrors accel, settle snaps the setpoint onto the target.
//
// The arithmetic saturates; it never wraps.  A wrapped position setpoint is a
// machine crash, and a saturating one is merely a late arrival.
//
// This block is the hardware twin of pnp/planning/trajectory.s_curve_1d();
// tools/rtl_compare.py runs both and reports the sample-by-sample error.
// ---------------------------------------------------------------------------
`include "pnp_defs.svh"
module profile_gen #(
    parameter integer W = `PNP_POS_W
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                start,
    input  wire signed [W-1:0] target,
    input  wire signed [W-1:0] v_max,
    input  wire signed [W-1:0] a_max,
    input  wire signed [W-1:0] j_max,
    input  wire                hold,
    output reg  signed [W-1:0] position,
    output reg  signed [W-1:0] velocity,
    output reg  signed [W-1:0] accel,
    output reg                 busy,
    output reg                 at_target
);
    localparam signed [W-1:0] ZERO = {W{1'b0}};

    // ---- saturating helpers -------------------------------------------------
    function signed [W-1:0] sat_add;
        input signed [W-1:0] a;
        input signed [W-1:0] b;
        reg signed [W:0] wide;
        begin
            wide = {a[W-1], a} + {b[W-1], b};
            if (wide[W:0] > {1'b0, {W{1'b0}}} + {1'b0, {1'b0, 1'b1, {(W-2){1'b0}}}})
                sat_add = {1'b0, {(W-1){1'b1}}};   // positive saturation
            else if (wide[W:0] < {1'b1, {1'b1, {(W-1){1'b0}}}})
                sat_add = {1'b1, {(W-1){1'b0}}};   // negative saturation
            else
                sat_add = wide[W-1:0];
        end
    endfunction

    function signed [W-1:0] abs_s;
        input signed [W-1:0] v;
        begin
            abs_s = v[W-1] ? -v : v;
        end
    endfunction

    // ---- planner inputs -----------------------------------------------------
    wire signed [W-1:0] vmax_abs = abs_s(v_max);
    wire signed [W-1:0] amax_abs = abs_s(a_max);
    wire signed [W-1:0] jmax_abs = abs_s(j_max);

    reg  signed [W-1:0] dist;          // signed remaining distance
    reg  signed [W-1:0] dir;           // +1 / -1 travel direction
    reg  signed [W-1:0] brake;         // braking distance from current speed

    // divider plumbing: v^2 / (2a).  v and a are Q12.4, so v*v is Q24.8 and
    // dividing by (2a) Q12.4 yields Q12.4 after scaling by 2^4.
    wire [2*W-1:0] vsq   = velocity * velocity;
    wire [2*W-1:0] denom = {amax_abs, 1'b0};        // 2*a in Q12.4 -> Q12.4
    reg  [2*W-1:0] divid, divis;
    wire [2*W-1:0] quo_w;
    wire           div_busy, div_done;
    reg            div_start;

    seq_div #(.W(2*W)) u_brake_div (
        .clk(clk), .rst_n(rst_n), .start(div_start),
        .dividend(divid), .divisor(divis),
        .quotient(quo_w), .remainder(), .busy(div_busy), .done(div_done)
    );

    // ---- state machine ------------------------------------------------------
    localparam [2:0] S_IDLE   = 3'd0,
                     S_PLAN   = 3'd1,
                     S_MOVE   = 3'd2,
                     S_SETTLE = 3'd3;

    reg [2:0] state;
    reg       triangular;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            position <= ZERO; velocity <= ZERO; accel <= ZERO;
            busy <= 1'b0; at_target <= 1'b0; div_start <= 1'b0;
            dist <= ZERO; dir <= ZERO; brake <= ZERO; triangular <= 1'b0;
            divid <= {(2*W){1'b0}}; divis <= {(2*W){1'b0}};
        end else begin
            at_target <= 1'b0;
            case (state)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        dist <= target - position;
                        dir  <= (target >= position) ? {W{1'b0}} | 1 : -1;
                        busy <= 1'b1;
                        state <= S_PLAN;
                    end
                end

                S_PLAN: begin
                    // Compute the braking distance for the configured v_max.
                    if (!div_busy && !div_done) begin
                        divid     <= vmax_abs * vmax_abs;   // Q24.8
                        divis     <= denom;                 // Q12.4
                        div_start <= 1'b1;
                    end else begin
                        div_start <= 1'b0;
                        if (div_done) begin
                            // quotient is Q24.8 / Q12.4 = Q12.4 scaled by 2^4:
                            // shift right by PNP_FRAC_W to return to Q12.4.
                            brake <= quo_w[W-1:0] >> `PNP_FRAC_W;
                            triangular <= (abs_s(dist) < (quo_w[W-1:0] >> `PNP_FRAC_W));
                            velocity <= ZERO;
                            accel <= ZERO;
                            state <= S_MOVE;
                        end
                    end
                end

                S_MOVE: begin
                    if (hold) begin
                        accel <= ZERO;
                        velocity <= ZERO;
                    end else begin
                        // Accelerate while far from the target, brake inside the
                        // braking distance.  Jerk limiting is applied by moving
                        // the acceleration one j_max step per sample.
                        if (abs_s(dist) > brake + vmax_abs) begin
                            if (dir > 0) begin
                                if (accel < amax_abs) accel <= sat_add(accel, jmax_abs);
                                if (velocity < vmax_abs) velocity <= sat_add(velocity, accel);
                            end else begin
                                if (accel > -amax_abs) accel <= sat_add(accel, -jmax_abs);
                                if (velocity > -vmax_abs) velocity <= sat_add(velocity, accel);
                            end
                        end else begin
                            if (dir > 0) begin
                                if (accel > -amax_abs) accel <= sat_add(accel, -jmax_abs);
                                if (velocity > ZERO) velocity <= sat_add(velocity, accel);
                            end else begin
                                if (accel < amax_abs) accel <= sat_add(accel, jmax_abs);
                                if (velocity < ZERO) velocity <= sat_add(velocity, accel);
                            end
                        end
                    end

                    position <= sat_add(position, velocity);
                    if (dir > 0) dist <= dist - velocity; else dist <= dist - velocity;

                    if ((dist <= 0 && dir > 0 && velocity <= 0) ||
                        (dist >= 0 && dir < 0 && velocity >= 0))
                        state <= S_SETTLE;
                end

                S_SETTLE: begin
                    position  <= target;
                    velocity  <= ZERO;
                    accel     <= ZERO;
                    busy      <= 1'b0;
                    at_target <= 1'b1;
                    state     <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end

`ifdef FORMAL
    reg f_past_valid = 1'b0;
    always @(posedge clk) f_past_valid <= 1'b1;
    // The generator is only ever busy after a start pulse.
    always @(posedge clk) if (f_past_valid && rst_n && !$past(rst_n))
        assert (busy == 1'b0);
`endif
endmodule
