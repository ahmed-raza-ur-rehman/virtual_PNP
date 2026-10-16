// ---------------------------------------------------------------------------
// pnp_core - top level of the PnP motion/vision control core.
//
// Block diagram (docs/architecture.md):
//
//   SPI slave ─┐
//              ├─> packet_if ─> cmd decoder ─┬─> csr_bank ─> axis_ctrl X/DATA
//   UART rx  ──┘                             ├─> watchdog kick
//                                            └─> telemetry framing -> UART tx
//
//   limit_monitor ─> motion_inhibit ─> every axis (hard-wired stop path)
//   centroid_accel <─ camera pixel stream (vision head)
//
// Design rules applied here:
//   * the stop path is combinational from the limit monitor to the step
//     generators; it never depends on a register that software can stall;
//   * every asynchronous input is synchronised at the pin;
//   * telemetry is rate-limited so that a fast host cannot starve the control
//     loop.
// ---------------------------------------------------------------------------
`include "pnp_defs.svh"
module pnp_core #(
    parameter integer CLK_HZ     = 100_000_000,
    parameter integer BAUD       = 921_600,
    parameter integer N_AXES     = 3,
    parameter integer TELEM_DIV  = 10_000,
    parameter integer WIN_LOW    = 64,
    parameter integer WIN_HIGH   = 200_000,
    parameter integer COORD_W    = 12
) (
    input  wire        clk,
    input  wire        rst_n,
    // SPI link
    input  wire        spi_sck,
    input  wire        spi_cs_n,
    input  wire        spi_mosi,
    output wire        spi_miso,
    // UART link
    input  wire        uart_rx_pin,
    output wire        uart_tx_pin,
    // per-axis encoder + drive
    input  wire [N_AXES-1:0] enc_a,
    input  wire [N_AXES-1:0] enc_b,
    input  wire [N_AXES-1:0] enc_idx,
    output wire [N_AXES-1:0] step,
    output wire [N_AXES-1:0] dir,
    // machine safety inputs (active low: 0 = asserted)
    input  wire [6:0]  limit_sw,
    input  wire        estop_n,
    // vision pixel stream
    input  wire        pix_valid,
    input  wire [COORD_W-1:0] pix_x,
    input  wire [COORD_W-1:0] pix_y,
    input  wire [7:0]  pix_intensity,
    input  wire        frame_start,
    input  wire        frame_end,
    // host-visible status
    output wire        led_heartbeat,
    output wire        led_fault,
    output wire        led_link
);
    // ------------------------------------------------------------------ links
    wire [7:0] spi_byte;
    wire       spi_byte_valid;
    wire [7:0] rx_byte;
    wire       rx_valid;
    wire [7:0] tx_byte;
    wire       tx_valid;
    wire       tx_ready;

    spi_slave #(.W(8), .CPOL(0)) u_spi (
        .clk(clk), .rst_n(rst_n), .sck(spi_sck), .cs_n(spi_cs_n), .mosi(spi_mosi),
        .tx_data(8'h5A), .rx_data(spi_byte), .rx_valid(spi_byte_valid),
        .miso(spi_miso), .tx_load()
    );

    uart_rx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_uart_rx (
        .clk(clk), .rst_n(rst_n), .rx(uart_rx_pin), .data(rx_byte),
        .valid(rx_valid), .frame_error()
    );

    uart_tx #(.CLK_HZ(CLK_HZ), .BAUD(BAUD)) u_uart_tx (
        .clk(clk), .rst_n(rst_n), .data(tx_byte), .valid(tx_valid),
        .ready(tx_ready), .tx(uart_tx_pin), .busy()
    );

    // the byte path is multiplexed: SPI wins when a chip-select is active,
    // because the SPI master is the deterministic real-time link
    wire [7:0] link_byte  = spi_cs_n ? rx_byte : spi_byte;
    wire       link_valid = spi_cs_n ? rx_valid : spi_byte_valid;

    // --------------------------------------------------------------- protocol
    wire        cmd_valid;
    wire [7:0]  cmd;
    wire [3:0]  payload_len;
    wire [63:0] payload;
    wire        err_bad_crc, err_bad_len, err_timeout;
    wire [7:0]  frames_ok, frames_err;

    packet_if #(.MAX_PAYLOAD(8), .LEN_W(4), .TIMEOUT(200_000)) u_packet (
        .clk(clk), .rst_n(rst_n), .rx_byte(link_byte), .rx_valid(link_valid),
        .cmd_valid(cmd_valid), .cmd(cmd), .payload_len(payload_len), .payload(payload),
        .err_bad_crc(err_bad_crc), .err_bad_len(err_bad_len), .err_timeout(err_timeout),
        .frames_ok(frames_ok), .frames_err(frames_err)
    );

    // --------------------------------------------------------------- registers
    wire                   csr_wr_en, csr_rd_en;
    wire [`PNP_ADDR_W-1:0] csr_addr;
    wire [31:0]            csr_wdata, csr_rdata;
    wire [3:0]             csr_strb;
    wire                   csr_rd_valid;
    wire                   ctrl_enable, ctrl_start, ctrl_stop, ctrl_clear_faults;
    wire                   wd_kick;
    wire signed [31:0]     axis_target, axis_position;
    wire signed [31:0]     v_max, a_max, j_max;
    wire signed [15:0]     pid_kp, pid_ki, pid_kd;

    // command decoder: cmd 0x01 = write register, 0x02 = read register,
    // 0x03 = start move, 0x04 = kick watchdog, 0x05 = clear faults
    reg  csr_wr_en_r, csr_rd_en_r;
    reg  [`PNP_ADDR_W-1:0] csr_addr_r;
    reg  [31:0] csr_wdata_r;
    reg  wd_kick_r;
    reg  cmd_decode_err;
    reg  [7:0] cmd_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            csr_wr_en_r <= 1'b0; csr_rd_en_r <= 1'b0; csr_addr_r <= 8'h00;
            csr_wdata_r <= 32'h0; wd_kick_r <= 1'b0; cmd_decode_err <= 1'b0;
            cmd_count <= 8'h00;
        end else begin
            csr_wr_en_r <= 1'b0;
            csr_rd_en_r <= 1'b0;
            wd_kick_r   <= 1'b0;
            if (cmd_valid) begin
                cmd_count <= cmd_count + 8'd1;
                case (cmd)
                    8'h01: if (payload_len >= 4'd5) begin
                               csr_wr_en_r <= 1'b1;
                               csr_addr_r  <= payload[7:0];
                               csr_wdata_r <= payload[39:8];
                           end else cmd_decode_err <= 1'b1;
                    8'h02: if (payload_len >= 4'd1) begin
                               csr_rd_en_r <= 1'b1;
                               csr_addr_r  <= payload[7:0];
                           end else cmd_decode_err <= 1'b1;
                    8'h03: begin csr_wr_en_r <= 1'b1; csr_addr_r <= 8'h00; csr_wdata_r <= 32'h2; end
                    8'h04: wd_kick_r <= 1'b1;
                    8'h05: begin csr_wr_en_r <= 1'b1; csr_addr_r <= 8'h00; csr_wdata_r <= 32'h8; end
                    default: cmd_decode_err <= 1'b1;
                endcase
            end
        end
    end

    assign csr_wr_en = csr_wr_en_r;
    assign csr_rd_en = csr_rd_en_r;
    assign csr_addr  = csr_addr_r;
    assign csr_wdata = csr_wdata_r;
    assign csr_strb  = 4'hF;

    // --------------------------------------------------------------- safety
    wire [6:0]  chan_filt;
    wire        fault, motion_inhibit;
    wire [6:0]  limit_in = {estop_n, limit_sw[5:0]};

    limit_monitor #(.FILTER_LEN(16), .N_CH(7)) u_limits (
        .clk(clk), .rst_n(rst_n), .chan_raw(limit_in), .clear_fault(ctrl_clear_faults),
        .enable(ctrl_enable), .fault(fault), .latched(), .chan_filt(chan_filt),
        .motion_inhibit(motion_inhibit)
    );

    wire wd_reset_req, wd_early, wd_late;
    watchdog_wwdg #(.WIN_LOW(WIN_LOW), .WIN_HIGH(WIN_HIGH)) u_wdg (
        .clk(clk), .rst_n(rst_n), .kick(wd_kick || wd_kick_r), .clear_fault(ctrl_clear_faults),
        .reset_req(wd_reset_req), .early_kick(wd_early), .late_kick(wd_late), .counter()
    );

    wire stat_fault = fault | wd_reset_req | cmd_decode_err | (|{err_bad_crc, err_bad_len, err_timeout});

    csr_bank u_csr (
        .clk(clk), .rst_n(rst_n),
        .wr_en(csr_wr_en), .wr_addr(csr_addr), .wr_data(csr_wdata), .wr_strb(csr_strb),
        .rd_en(csr_rd_en), .rd_addr(csr_addr), .rd_data(csr_rdata), .rd_valid(csr_rd_valid),
        .ctrl_enable(ctrl_enable), .ctrl_start(ctrl_start), .ctrl_stop(ctrl_stop),
        .ctrl_clear_faults(ctrl_clear_faults),
        .stat_busy(axis_busy[0]), .stat_at_target(axis_at_target[0]),
        .stat_fault(stat_fault), .stat_link_ok(link_valid | ctrl_enable),
        .axis_target(axis_target), .axis_position(axis_position),
        .v_max(v_max), .a_max(a_max), .j_max(j_max),
        .pid_kp(pid_kp), .pid_ki(pid_ki), .pid_kd(pid_kd),
        .wd_kick(wd_kick), .err_sticky()
    );

    // ------------------------------------------------------------------ axes
    reg  [15:0] sample_cnt;
    wire        sample_en = (sample_cnt == 16'd9);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) sample_cnt <= 16'd0;
        else sample_cnt <= (sample_cnt == 16'd9) ? 16'd0 : sample_cnt + 16'd1;
    end

    wire [N_AXES-1:0] axis_busy, axis_at_target, axis_sat;
    wire signed [31:0] axis_pos [0:N_AXES-1];
    wire signed [31:0] axis_err [0:N_AXES-1];

    genvar gi;
    generate
        for (gi = 0; gi < N_AXES; gi = gi + 1) begin : g_axis
            axis_ctrl #(.W(32)) u_axis (
                .clk(clk), .rst_n(rst_n), .sample_en(sample_en), .mode(2'd0),
                .enable(ctrl_enable), .start(ctrl_start),
                .target(axis_target), .v_max(v_max), .a_max(a_max), .j_max(j_max),
                .kp(pid_kp), .ki(pid_ki), .kd(pid_kd),
                .enc_a(enc_a[gi]), .enc_b(enc_b[gi]), .enc_idx(enc_idx[gi]),
                .motion_inhibit(motion_inhibit),
                .step(step[gi]), .dir(dir[gi]), .busy(axis_busy[gi]),
                .at_target(axis_at_target[gi]), .saturated(axis_sat[gi]),
                .position_out(axis_pos[gi]), .error_out(axis_err[gi])
            );
        end
    endgenerate

    // axis 0 (X) is the axis reported through the register file; the other
    // axes are gated by the same enable/start and share the profile limits
    assign axis_position = axis_pos[0];

    // ------------------------------------------------------------- telemetry
    // A compact status frame is pushed to the UART at TELEM_DIV, giving the
    // host a heartbeat that doubles as a link-quality indicator.
    reg [31:0] telem_div;
    reg [3:0]  telem_idx;
    reg        telem_active;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            telem_div <= 32'd0; telem_idx <= 4'd0; telem_active <= 1'b0;
        end else if (!telem_active) begin
            if (telem_div == TELEM_DIV[31:0] - 1) begin
                telem_div <= 32'd0; telem_active <= 1'b1; telem_idx <= 4'd0;
            end else telem_div <= telem_div + 32'd1;
        end else if (tx_ready) begin
            telem_idx <= telem_idx + 4'd1;
            if (telem_idx == 4'd7) telem_active <= 1'b0;
        end
    end
    assign tx_valid = telem_active && tx_ready;

    reg [7:0] telem_byte;
    always @(*) begin
        case (telem_idx)
            4'd0: telem_byte = 8'hAA;
            4'd1: telem_byte = 8'h55;
            4'd2: telem_byte = 8'h30;                       // status frame
            4'd3: telem_byte = {6'b0, cmd_decode_err, stat_fault};
            4'd4: telem_byte = axis_position[15:8];
            4'd5: telem_byte = axis_position[7:0];
            4'd6: telem_byte = frames_ok;
            4'd7: telem_byte = frames_err;
            default: telem_byte = 8'h00;
        endcase
    end
    assign tx_byte = telem_byte;

    // ------------------------------------------------------------------ LFOs
    reg [23:0] heartbeat;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) heartbeat <= 24'd0;
        else heartbeat <= heartbeat + 24'd1;
    end
    assign led_heartbeat = heartbeat[23];
    assign led_fault     = stat_fault;
    assign led_link      = frames_ok != 8'h00;
endmodule
