// Window Watchdog
module wdt #(
    parameter CLK_FREQ = 1000
)(
    input  logic        clk,
    input  logic        rst_n,
    input  logic        enable,
    input  logic [31:0] timeout,
    input  logic [31:0] window_min,
    input  logic [31:0] window_max,
    input  logic        feed,
    output logic        timeout_flag,
    output logic        early_warning,
    output logic        reset_out
);
    logic [31:0] counter;
    logic enabled_r;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            counter <= 0;
            enabled_r <= 0;
            timeout_flag <= 0;
            early_warning <= 0;
            reset_out <= 0;
        end else begin
            if (enable && !enabled_r) begin
                enabled_r <= 1;
                counter <= 0;
            end
            if (enabled_r) begin
                if (feed) begin
                    if (counter < window_min || counter > window_max) begin
                        timeout_flag <= 1;
                        reset_out <= 1;
                    end
                    counter <= 0;
                end else begin
                    counter <= counter + 1;
                    if (counter >= timeout * 8 / 10) early_warning <= 1;
                    if (counter >= timeout) begin
                        timeout_flag <= 1;
                        reset_out <= 1;
                    end
                end
            end
        end
    end
endmodule
