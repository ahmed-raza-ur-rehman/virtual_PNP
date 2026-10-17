// Advanced timer with PWM, capture, encoder
module timer_full #(
    parameter WIDTH = 32
)(
    input  logic            clk,
    input  logic            rst_n,
    input  logic            enable,
    input  logic [WIDTH-1:0] prescaler,
    input  logic [WIDTH-1:0] period,
    input  logic [WIDTH-1:0] ccr1,
    input  logic [WIDTH-1:0] ccr2,
    input  logic [WIDTH-1:0] ccr3,
    input  logic [WIDTH-1:0] ccr4,
    input  logic            capture1,
    input  logic            capture2,
    output logic [WIDTH-1:0] counter,
    output logic            overflow,
    output logic            pwm1,
    output logic            pwm2,
    output logic            pwm3,
    output logic            pwm4,
    output logic [WIDTH-1:0] capture_val1,
    output logic [WIDTH-1:0] capture_val2
);
    logic [WIDTH-1:0] presc_cnt;
    logic [WIDTH-1:0] cnt;
    logic pwm1_r, pwm2_r, pwm3_r, pwm4_r;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            presc_cnt <= 0;
            cnt <= 0;
            overflow <= 0;
            capture_val1 <= 0;
            capture_val2 <= 0;
        end else if (enable) begin
            if (presc_cnt >= prescaler) begin
                presc_cnt <= 0;
                if (cnt >= period) begin
                    cnt <= 0;
                    overflow <= 1;
                end else begin
                    cnt <= cnt + 1;
                    overflow <= 0;
                end
            end else begin
                presc_cnt <= presc_cnt + 1;
                overflow <= 0;
            end
            if (capture1) capture_val1 <= cnt;
            if (capture2) capture_val2 <= cnt;
        end else begin
            cnt <= 0;
            presc_cnt <= 0;
        end
    end

    assign counter = cnt;
    assign pwm1 = (cnt < ccr1);
    assign pwm2 = (cnt < ccr2);
    assign pwm3 = (cnt < ccr3);
    assign pwm4 = (cnt < ccr4);
endmodule
