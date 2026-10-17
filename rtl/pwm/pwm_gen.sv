// PWM generator with dead-time
module pwm_gen #(
    parameter RESOLUTION = 10
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    enable,
    input  logic [RESOLUTION-1:0]   duty,
    input  logic [31:0]             period,
    input  logic [15:0]             dead_time,
    output logic                    pwm_out,
    output logic                    pwm_out_n
);
    logic [31:0] counter;
    logic [RESOLUTION-1:0] duty_reg;
    logic pwm_high;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            counter <= 0;
            duty_reg <= 0;
            pwm_high <= 0;
        end else if (enable) begin
            if (counter >= period - 1)
                counter <= 0;
            else
                counter <= counter + 1;
            duty_reg <= duty;
            pwm_high <= (counter < (period * duty_reg >> RESOLUTION));
        end else begin
            counter <= 0;
            pwm_high <= 0;
        end
    end

    assign pwm_out = enable ? pwm_high : 1'b0;
    // dead-time on complementary
    logic [15:0] dt_counter;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dt_counter <= 0;
            pwm_out_n <= 1;
        end else begin
            if (pwm_high) begin
                dt_counter <= dead_time;
                pwm_out_n <= 0;
            end else if (dt_counter > 0) begin
                dt_counter <= dt_counter - 1;
                pwm_out_n <= 0;
            end else begin
                pwm_out_n <= 1;
            end
        end
    end
endmodule
