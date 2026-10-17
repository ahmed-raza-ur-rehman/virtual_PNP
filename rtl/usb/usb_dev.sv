module usb_dev (
    input  wire clk,
    input  wire rst_n,
    input  wire usb_dp,
    input  wire usb_dm,
    output reg  usb_pullup,
    output reg  [7:0] rx_data,
    output reg        rx_valid
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin usb_pullup <= 0; rx_valid <= 0; end
        else begin usb_pullup <= 1; rx_valid <= usb_dp; rx_data <= 8'h00; end
    end
endmodule
