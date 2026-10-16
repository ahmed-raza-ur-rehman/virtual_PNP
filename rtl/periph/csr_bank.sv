// ---------------------------------------------------------------------------
// csr_bank - control/status register file shared by firmware and the FPGA.
//
// Register map (see docs/ICD.md; firmware uses the same offsets):
//   0x00 CTRL      RW  bit0 enable, bit1 start, bit2 stop, bit3 clear_faults
//   0x04 STATUS    RO  bit0 busy, bit1 at_target, bit2 fault, bit3 link_ok
//   0x08 AXIS_TGT  RW  target position, Q12.4 um
//   0x0C AXIS_POS  RO  measured position, Q12.4 um
//   0x10 V_MAX     RW  Q12.4 um/s
//   0x14 A_MAX     RW  Q12.4 um/s^2
//   0x18 J_MAX     RW  Q12.4 um/s^3
//   0x1C PID_KP    RW  Q4.12
//   0x20 PID_KI    RW  Q4.12
//   0x24 PID_KD    RW  Q4.12
//   0x28 WD_KICK   WO  any write feeds the window watchdog
//   0x2C ERR_STAT  RW1C sticky error flags
//   0x30 VERSION   RO  {major, minor, patch, build}
//
// Byte writes are supported because the host link is byte oriented; a
// read-modify-write from firmware would otherwise have to be atomic with
// respect to the control loop, which the link cannot guarantee.
// ---------------------------------------------------------------------------
`include "pnp_defs.svh"
module csr_bank #(
    parameter [31:0] VERSION = 32'h02_00_00_01
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   wr_en,
    input  wire [`PNP_ADDR_W-1:0] wr_addr,
    input  wire [`PNP_DATA_W-1:0] wr_data,
    input  wire [3:0]             wr_strb,
    input  wire                   rd_en,
    input  wire [`PNP_ADDR_W-1:0] rd_addr,
    output reg  [`PNP_DATA_W-1:0] rd_data,
    output reg                    rd_valid,
    // control/status contract with the rest of the core
    output reg                    ctrl_enable,
    output reg                    ctrl_start,
    output reg                    ctrl_stop,
    output reg                    ctrl_clear_faults,
    input  wire                   stat_busy,
    input  wire                   stat_at_target,
    input  wire                   stat_fault,
    input  wire                   stat_link_ok,
    output reg  signed [31:0]     axis_target,
    input  wire signed [31:0]     axis_position,
    output reg  signed [31:0]     v_max,
    output reg  signed [31:0]     a_max,
    output reg  signed [31:0]     j_max,
    output reg  signed [15:0]     pid_kp,
    output reg  signed [15:0]     pid_ki,
    output reg  signed [15:0]     pid_kd,
    output reg                    wd_kick,
    output reg  [31:0]            err_sticky
);
    reg [31:0] status_word;

    always @(*) begin
        status_word = {28'h0, stat_link_ok, stat_fault, stat_at_target, stat_busy};
    end

    // byte-enable merge: only the bytes selected by wr_strb are replaced
    function [31:0] merge;
        input [31:0] old;
        input [31:0] new;
        input [3:0]  strb;
        begin
            merge[7:0]   = strb[0] ? new[7:0]   : old[7:0];
            merge[15:8]  = strb[1] ? new[15:8]  : old[15:8];
            merge[23:16] = strb[2] ? new[23:16] : old[23:16];
            merge[31:24] = strb[3] ? new[31:24] : old[31:24];
        end
    endfunction

    // 16-bit registers only expose their low two bytes on the link
    function [15:0] merge16;
        input [15:0] old;
        input [31:0] new;
        input [3:0]  strb;
        begin
            merge16[7:0]  = strb[0] ? new[7:0]  : old[7:0];
            merge16[15:8] = strb[1] ? new[15:8] : old[15:8];
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ctrl_enable <= 1'b0; ctrl_start <= 1'b0; ctrl_stop <= 1'b0;
            ctrl_clear_faults <= 1'b0; wd_kick <= 1'b0;
            axis_target <= 32'sd0; v_max <= 32'sd400_000; a_max <= 32'sd200_000;
            j_max <= 32'sd1_000_000; pid_kp <= 16'sd2048; pid_ki <= 16'sd32;
            pid_kd <= 16'sd0; err_sticky <= 32'd0;
            rd_data <= 32'd0; rd_valid <= 1'b0;
        end else begin
            wd_kick           <= 1'b0;
            ctrl_start        <= 1'b0;
            ctrl_clear_faults <= 1'b0;
            ctrl_stop         <= 1'b0;
            rd_valid          <= 1'b0;

            if (wr_en) begin
                case (wr_addr)
                    8'h00: begin
                        ctrl_enable       <= wr_data[0];
                        ctrl_start        <= wr_data[1];
                        ctrl_stop         <= wr_data[2];
                        ctrl_clear_faults <= wr_data[3];
                    end
                    8'h08: axis_target <= signed'(merge(axis_target, wr_data, wr_strb));
                    8'h10: v_max       <= signed'(merge(v_max, wr_data, wr_strb));
                    8'h14: a_max       <= signed'(merge(a_max, wr_data, wr_strb));
                    8'h18: j_max       <= signed'(merge(j_max, wr_data, wr_strb));
                    8'h1C: pid_kp      <= merge16(pid_kp, wr_data, wr_strb);
                    8'h20: pid_ki      <= merge16(pid_ki, wr_data, wr_strb);
                    8'h24: pid_kd      <= merge16(pid_kd, wr_data, wr_strb);
                    8'h28: wd_kick     <= 1'b1;
                    // write-one-to-clear: only the bits written as 1 are cleared
                    8'h2C: err_sticky  <= err_sticky & ~wr_data;
                    default: ;
                endcase
            end

            if (stat_fault) err_sticky[0] <= 1'b1;   // latch any controller fault
            if (ctrl_clear_faults) err_sticky <= 32'd0;

            if (rd_en) begin
                rd_valid <= 1'b1;
                case (rd_addr)
                    8'h00: rd_data <= {28'h0, 1'b0, ctrl_stop, ctrl_start, ctrl_enable};
                    8'h04: rd_data <= status_word;
                    8'h08: rd_data <= axis_target;
                    8'h0C: rd_data <= axis_position;
                    8'h10: rd_data <= v_max;
                    8'h14: rd_data <= a_max;
                    8'h18: rd_data <= j_max;
                    8'h1C: rd_data <= {{16{pid_kp[15]}}, pid_kp};
                    8'h20: rd_data <= {{16{pid_ki[15]}}, pid_ki};
                    8'h24: rd_data <= {{16{pid_kd[15]}}, pid_kd};
                    8'h2C: rd_data <= err_sticky;
                    8'h30: rd_data <= VERSION;
                    default: rd_data <= 32'hDEAD_BEEF;
                endcase
            end
        end
    end
endmodule
