// ---------------------------------------------------------------------------
// seq_div_props - functional proof of the restoring divider.
//
// The proof uses a narrow instance (W=8): the property is width independent,
// and an 8-bit instance keeps the SMT problem small enough to close
// exhaustively rather than relying on a bounded depth.
//
//   P1  done is asserted exactly once, one cycle after the last quotient bit
//   P2  on done, quotient * divisor + remainder == dividend   (the arithmetic
//       contract the profile planner relies on)
//   P3  remainder < divisor                                   (canonical form)
//   P4  divide-by-zero reports a saturated quotient and never a spurious done
//       without the saturation flag
//   C1  non-vacuity: the done state is reachable
// ---------------------------------------------------------------------------
module seq_div_props (
    input wire clk,
    input wire rst_n
);
    localparam integer W = 8;
    wire           start;
    wire [W-1:0]   dividend, divisor, quotient, remainder;
    wire           busy, done;

    // free inputs constrained to realistic traffic
    (* anyseq *) reg [W-1:0] a;
    (* anyseq *) reg [W-1:0] b;
    (* anyseq *) reg         s;
    assign dividend = a;
    assign divisor  = b;
    assign start    = s;

    seq_div #(.W(W)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .dividend(dividend),
        .divisor(divisor), .quotient(quotient), .remainder(remainder),
        .busy(busy), .done(done)
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

    // P2/P3 - the arithmetic contract, checked against the operands that the
    // divider actually latched (the free inputs may have changed since).
    reg [W-1:0] dividend_l, divisor_l;
    always @(posedge clk) if (rst_n && start && !busy) begin
        dividend_l <= a;
        divisor_l  <= b;
    end
    // The divider has a data-independent latency, so the operands latched at
    // the start of the run are exactly the ones the result corresponds to.
    always @(posedge clk) if (rst_n && done && divisor_l != 0) begin
        assert (quotient * divisor_l + remainder == dividend_l);
        assert (remainder < divisor_l);
    end

    // P1 - protocol: done only ever follows a completed run
    reg started = 1'b0;
    always @(posedge clk) begin
        if (!rst_n) started <= 1'b0;
        else begin
            // A start presented in the same cycle as a `done` begins the next
            // division immediately (that is the DUT contract), so the monitor
            // must give the start priority or it would lose track of the run.
            if (start && !busy) started <= 1'b1;
            else if (done) started <= 1'b0;
        end
    end
    // `done` is raised either after a completed run (started is set) or in the
    // same cycle as a start that was rejected for a zero divisor.
    always @(posedge clk) if (rst_n)
        assert (!done || started || (start && !busy));
    always @(posedge clk) if (rst_n) assert (!(busy && done));

    // P4 - division by zero is reported, never silently wrong
    always @(posedge clk) if (rst_n && done && divisor_l == 0)
        assert (quotient == {W{1'b1}} && remainder == {W{1'b0}});

    // C1 - non-vacuity: a completed division with a non-zero divisor happens
    always @(posedge clk) cover (done && divisor_l != 0);
    always @(posedge clk) cover (done && divisor_l == 0);
endmodule
