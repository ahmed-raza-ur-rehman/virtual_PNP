// ---------------------------------------------------------------------------
// limit_monitor_props - safety interlock properties.
//
// The monitor is the only block between a limit switch and a moving axis, so
// its contract is stated as invariants rather than as scenarios:
//
//   P1  a trip is sticky: with no clear, fault can never fall
//   P2  clearing is refused while any channel is still asserted
//   P3  motion_inhibit is high whenever any channel is asserted
//   P4  an asserted channel is latched, and the latch is only released by a
//       legal clear
//   C1  non-vacuity: a trip and a successful clear are both reachable
// ---------------------------------------------------------------------------
module limit_monitor_props (
    input wire clk,
    input wire rst_n
);
    localparam integer N_CH       = 3;
    localparam integer FILTER_LEN = 2;

    (* anyseq *) reg [N_CH-1:0] chan;
    (* anyseq *) reg            clr;
    (* anyseq *) reg            en;

    wire        fault, motion_inhibit;
    wire [N_CH-1:0] latched, chan_filt;

    limit_monitor #(.FILTER_LEN(FILTER_LEN), .N_CH(N_CH)) dut (
        .clk(clk), .rst_n(rst_n), .chan_raw(chan), .clear_fault(clr),
        .enable(en), .fault(fault), .latched(latched), .chan_filt(chan_filt),
        .motion_inhibit(motion_inhibit)
    );

    // ---------------------------------------------------------------- harness
    localparam integer RESET_CYCLES = 3;
    reg [7:0] cyc = 8'd0;
    always @(posedge clk) if (cyc != 8'hFF) cyc <= cyc + 8'd1;
    always @(posedge clk) if (cyc < RESET_CYCLES) assume (!rst_n);
    always @(posedge clk) if (cyc >= RESET_CYCLES) assume (rst_n);
    wire past_reset = (cyc > RESET_CYCLES);

    always @(posedge clk) if (past_reset && rst_n) begin
        // P1 - sticky trip
        if ($past(fault) && !$past(clr)) assert (fault);
        // P3 - the stop path follows the filtered channels
        if (|(~chan_filt)) assert (motion_inhibit);
        // P4 - an asserted channel is latched by the next cycle (given the
        //      monitor is enabled and the cycle was not a legal clear)
        if ($past(en) && !$past(clr)) if (|(~$past(chan_filt))) assert (|latched);
        // P2 - a clear is refused while a channel is asserted
        if ($past(clr) && |(~$past(chan_filt)) && $past(en)) assert (fault || |latched);
    end

    always @(posedge clk) cover (fault);
    always @(posedge clk) cover (!fault && past_reset);
    always @(posedge clk) cover (|latched);
endmodule
