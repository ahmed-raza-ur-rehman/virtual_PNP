// ---------------------------------------------------------------------------
// limit_monitor - latching limit-switch and emergency-stop supervisor.
//
// Every channel is filtered with the same debounce used by the encoder front
// end so that a bouncing mechanical limit switch cannot chatter the stop line.
// A trip is latched: even if the switch re-opens, the machine stays stopped
// until software issues an explicit clear *while every channel reads safe*.
// That "clear requires safe" rule is what prevents an operator from jogging
// into a switch that is still active.
// ---------------------------------------------------------------------------
module limit_monitor #(
    parameter integer FILTER_LEN = 8,
    parameter integer N_CH       = 7   // 6 end-of-travel switches + e-stop
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire [N_CH-1:0]     chan_raw,     // 1 = switch idle, 0 = asserted
    input  wire                clear_fault,
    input  wire                enable,
    output reg                 fault,
    output reg  [N_CH-1:0]     latched,
    output reg  [N_CH-1:0]     chan_filt,
    output wire                motion_inhibit
);
    reg [15:0] cnt [0:N_CH-1];
    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < N_CH; i = i + 1) begin
                cnt[i] <= 16'd0;
                chan_filt[i] <= 1'b1;
            end
            latched <= {N_CH{1'b0}};
            fault <= 1'b0;
        end else begin
            for (i = 0; i < N_CH; i = i + 1) begin
                if (chan_raw[i] == chan_filt[i]) cnt[i] <= 16'd0;
                else if (cnt[i] == FILTER_LEN[15:0] - 16'd1) begin
                    chan_filt[i] <= chan_raw[i];
                    cnt[i] <= 16'd0;
                end else cnt[i] <= cnt[i] + 16'd1;
            end

            // any asserted (active-low) channel trips the latch
            if (enable && (|(~chan_filt))) begin
                latched <= latched | (~chan_filt);
                fault   <= 1'b1;
            end

            if (clear_fault && (&chan_filt)) begin
                latched <= {N_CH{1'b0}};
                fault   <= 1'b0;
            end

        end
    end

    // The inhibit is combinational on purpose: registering it would add a
    // clock of latency to the emergency-stop path for no benefit, and the
    // debounce filter ahead of it already provides the noise immunity.
    // Property limit_monitor_props P3 states exactly this contract.
    assign motion_inhibit = fault | (|(~chan_filt));
endmodule
