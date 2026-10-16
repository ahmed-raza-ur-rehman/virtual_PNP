// ---------------------------------------------------------------------------
// watchdog_wwdg - window watchdog with two independent failure modes.
//
//   * too late  : the kick did not arrive inside the window      -> reset_req
//   * too early : the kick arrived before the lower window bound -> early_kick
//
// The second half is what makes a window watchdog worth its area: a control
// loop that has started spinning (a classic fault mode after a stack overflow)
// kicks far too often, and a plain watchdog will happily accept it.  Both
// conditions are latched and reported to the CSR bank, and the hardware reset
// request is only cleared by a power-on reset or an explicit clear.
// ---------------------------------------------------------------------------
module watchdog_wwdg #(
    parameter integer WIN_LOW  = 100,      // earliest legal kick, in clocks
    parameter integer WIN_HIGH = 100_000   // latest legal kick, in clocks
) (
    input  wire clk,
    input  wire rst_n,
    input  wire kick,
    input  wire clear_fault,
    output reg  reset_req,
    output reg  early_kick,
    output reg  late_kick,
    output reg  [31:0] counter
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            counter <= 32'd0; reset_req <= 1'b0; early_kick <= 1'b0; late_kick <= 1'b0;
        end else begin
            if (clear_fault) begin
                // Acknowledging the fault must also restart the window.  If
                // the counter kept its value the next kick would be judged
                // against a stale window: formal proof watchdog_props found
                // exactly this (counter >= WIN_HIGH with reset_req clear),
                // which would have re-tripped or, worse, masked the fault.
                reset_req  <= 1'b0;
                early_kick <= 1'b0;
                late_kick  <= 1'b0;
                counter    <= 32'd0;
            end else if (kick) begin
                if (counter < WIN_LOW[31:0]) early_kick <= 1'b1;
                else counter <= 32'd0;
            end else if (!reset_req) begin
                // The trip is raised one cycle *after* the counter would pass
                // WIN_HIGH.  Comparing against WIN_HIGH - 1 (as the property
                // watchdog_props._witness_ requires) keeps the effective window
                // exactly WIN_HIGH cycles wide; the earlier formulation let the
                // counter run to WIN_HIGH before reacting, i.e. the machine
                // observed a window one cycle longer than the specification.
                counter <= counter + 32'd1;
                if (counter >= WIN_HIGH[31:0] - 32'd1) begin
                    late_kick <= 1'b1;
                    reset_req <= 1'b1;
                end
            end
        end
    end
endmodule
