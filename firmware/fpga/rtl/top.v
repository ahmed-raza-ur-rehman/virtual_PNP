module top (
    input wire clk,
    input wire rst,
    output wire pwm_out
);
    pwm #(.WIDTH(16)) pwm0 (.clk(clk), .rst(rst), .duty(16'h8000), .out(pwm_out));
endmodule
