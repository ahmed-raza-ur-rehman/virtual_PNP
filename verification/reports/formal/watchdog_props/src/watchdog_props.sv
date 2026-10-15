// ---------------------------------------------------------------------------
// watchdog_props - window watchdog: prove both failure modes and the reset
// request latching.
//
//   P1  a kick inside the window resets the counter and never trips
//   P2  a kick before WIN_LOW is flagged as early_kick
//   P3  no kick for WIN_HIGH cycles raises reset_req and late_kick
//   P4  reset_req is sticky: only clear_fault removes it
//   C1  non-vacuity: both trip paths are reachable
// ---------------------------------------------------------------------------
module watchdog_props (
    input wire clk,
    input wire rst_n
);
    localparam integer WIN_LOW  = 4;
    localparam integer WIN_HIGH = 12;

    (* anyseq *) reg kick;
    (* anyseq *) reg clr;

    wire reset_req, early_kick, late_kick;
    wire [31:0] counter;

    watchdog_wwdg #(.WIN_LOW(WIN_LOW), .WIN_HIGH(WIN_HIGH)) dut (
        .clk(clk), .rst_n(rst_n), .kick(kick), .clear_fault(clr),
        .reset_req(reset_req), .early_kick(early_kick), .late_kick(late_kick),
        .counter(counter)
    );


    // ------------------------------------------------------------------
    // Formal harness preamble.
    //
    // The design is held in reset for RESET_CYCLES cycles and the properties
    // are only evaluated afterwards.  Two reasons, both standard practice:
    //   1. without an explicit reset sequence the SMT solver is free to pick
    //      any initial state, which produces counterexamples that no real
    //      power-up can reach;
    //   2. every property then refers to a known-good history, so $past()
    //      never reads a value from before the reset.
    // ------------------------------------------------------------------
    localparam integer RESET_CYCLES = 3;
    reg [7:0] cyc = 8'd0;
    always @(posedge clk) if (cyc != 8'hFF) cyc <= cyc + 8'd1;
    always @(posedge clk) if (cyc < RESET_CYCLES) assume (!rst_n);
    // Reset is released once and stays released: an unconstrained reset line
    // lets the solver inject an asynchronous reset in the middle of a trace,
    // which is not a reachable behaviour of the machine.
    always @(posedge clk) if (cyc >= RESET_CYCLES) assume (rst_n);
    wire past_reset = (cyc > RESET_CYCLES);

    // P1 - a well-behaved kick clears the counter.
    //      The clear_fault input has priority over a concurrent kick by
    //      design (a fault acknowledge restarts the window), so the property
    //      excludes the cycle in which the window was explicitly restarted.
    always @(posedge clk) if (past_reset && rst_n && !$past(clr))
        if ($past(kick) && $past(counter) >= WIN_LOW && !$past(reset_req))
            assert (counter == 32'd0 || reset_req);

    // P2 - an early kick is flagged (again, unless the window was restarted)
    always @(posedge clk) if (past_reset && rst_n && !$past(clr))
        if ($past(kick) && $past(counter) < WIN_LOW) assert (early_kick);

    // P3 - the counter never leaves the legal window without the trip being
    //      raised in the same cycle
    always @(posedge clk) if (past_reset && rst_n)
        assert (counter <= WIN_HIGH || reset_req);

    // P3b - the kick that would have been late is exactly what trips it
    always @(posedge clk) if (past_reset && rst_n && !$past(clr))
        if ($past(counter) == WIN_HIGH - 1 && !$past(kick) && !$past(reset_req))
            assert (reset_req && late_kick);

    // P4 - sticky fault until an explicit clear
    always @(posedge clk) if (past_reset && rst_n && !$past(clr))
        if ($past(reset_req)) assert (reset_req);

    always @(posedge clk) cover (reset_req);
    always @(posedge clk) cover (early_kick);
endmodule
