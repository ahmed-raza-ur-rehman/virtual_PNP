// ---------------------------------------------------------------------------
// axis_ctrl - one complete axis: profile generator, PID and step output.
//
// Modes (docs/architecture.md):
//   MODE_OPEN   the profile generator drives the step DDA directly; used for
//               commissioning and for machines without scale feedback.
//   MODE_CLOSED the encoder is the position source and the PID closes the loop
//               around it; the profile generator then supplies the setpoint.
//
// The mode is a run-time input because the same PCB serves both machine
// variants; selecting it in RTL rather than in firmware keeps the safety
// interlocks in one place.
// ---------------------------------------------------------------------------
`include "pnp_defs.svh"
module axis_ctrl #(
    parameter integer W  = `PNP_POS_W,
    parameter integer ACC_W = 24
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                sample_en,
    input  wire [1:0]          mode,           // 0 = open, 1 = closed
    input  wire                enable,
    input  wire                start,
    input  wire signed [W-1:0] target,
    input  wire signed [W-1:0] v_max,
    input  wire signed [W-1:0] a_max,
    input  wire signed [W-1:0] j_max,
    input  wire signed [15:0]  kp,
    input  wire signed [15:0]  ki,
    input  wire signed [15:0]  kd,
    input  wire                enc_a,
    input  wire                enc_b,
    input  wire                enc_idx,
    input  wire                motion_inhibit,
    output wire                step,
    output wire                dir,
    output wire                busy,
    output wire                at_target,
    output wire                saturated,
    output wire signed [W-1:0] position_out,
    output wire signed [W-1:0] error_out
);
    wire signed [W-1:0] profile_pos, profile_vel;
    wire signed [W-1:0] enc_count, pid_out;
    wire                pid_sat;

    profile_gen #(.W(W)) u_profile (
        .clk(clk), .rst_n(rst_n), .start(start), .target(target),
        .v_max(v_max), .a_max(a_max), .j_max(j_max), .hold(motion_inhibit),
        .position(profile_pos), .velocity(profile_vel), .accel(),
        .busy(busy), .at_target(at_target)
    );

    quad_decoder #(.CNT_W(W), .FILTER_LEN(4)) u_enc (
        .clk(clk), .rst_n(rst_n), .a_raw(enc_a), .b_raw(enc_b), .idx_raw(enc_idx),
        .count_en(enable), .count(enc_count), .index_pos(), .index_seen(),
        .dir(), .moving()
    );

    pid_axis #(.W(W)) u_pid (
        .clk(clk), .rst_n(rst_n), .sample_en(sample_en),
        .setpoint(profile_pos), .measured(enc_count),
        .kp(kp), .ki(ki), .kd(kd),
        .out_max(v_max),
        .out(pid_out), .saturated(pid_sat), .error_dbg(error_out)
    );

    wire signed [W-1:0] cmd_vel = (mode == 2'd1) ? pid_out : profile_vel;
    wire signed [W-1:0] open_pos;

    stepgen #(.W(W), .ACC_W(ACC_W)) u_step (
        .clk(clk), .rst_n(rst_n), .sample_en(sample_en), .velocity(cmd_vel),
        .enable(enable && !motion_inhibit), .step(step), .dir(dir),
        .position_um(open_pos)
    );

    // the position reported to the CSR bank is the encoder count in closed
    // loop mode and the DDA-integrated position in open loop mode
    assign position_out = (mode == 2'd1) ? enc_count : open_pos;
    assign saturated    = pid_sat;
endmodule
