`timescale 1ns/1ps
module soc_tb;
    reg clk = 0;
    reg rst_n = 0;
    wire [7:0] gpio_out;
    wire uart_tx, can_tx;
    wire usb_dp, usb_dm;
    always #5 clk = ~clk;
    pnp_soc #(.N_AXES(4)) dut (
        .clk(clk), .rst_n(rst_n),
        .gpio_in(8'h00), .gpio_out(gpio_out),
        .uart_tx(uart_tx), .uart_rx(1'b1),
        .can_tx(can_tx), .can_rx(1'b1),
        .usb_dp(usb_dp), .usb_dm(usb_dm)
    );
    initial begin
        #20 rst_n = 1;
        #1000;
        $display("SOC TB: gpio_out=%02h", gpio_out);
        $display("SOC TB PASSED");
        $finish;
    end
endmodule
