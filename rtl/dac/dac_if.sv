module dac_if #(
    parameter CHANNELS = 4,
    parameter WIDTH = 12
)(
    input  wire clk,
    input  wire rst_n,
    input  wire [WIDTH-1:0] digital_in [0:CHANNELS-1],
    output reg  [CHANNELS-1:0] analog_out,
    input  wire [1:0] channel_sel,
    input  wire update
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) analog_out <= 0;
        else if (update) analog_out[channel_sel] <= digital_in[channel_sel][WIDTH-1];
    end
endmodule
