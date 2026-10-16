`timescale 1ns/1ps
module tb_pwm;
    reg clk=0, rst=1;
    reg [15:0] duty=16'h4000;
    wire out;
    pwm #(.WIDTH(16)) dut(.clk(clk), .rst(rst), .duty(duty), .out(out));
    always #5 clk = ~clk;
    initial begin
        #20 rst=0;
        #1000 $finish;
    end
endmodule
