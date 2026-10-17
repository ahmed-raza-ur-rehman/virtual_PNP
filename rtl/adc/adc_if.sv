module adc_if #(
    parameter CHANNELS = 8,
    parameter WIDTH = 12
)(
    input  wire clk,
    input  wire rst_n,
    input  wire [CHANNELS-1:0] analog_in,
    output reg  [WIDTH-1:0] digital_out [0:CHANNELS-1],
    input  wire [2:0] channel_sel,
    input  wire convert,
    output reg  eoc
);
    // simplified ADC interface
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin eoc <= 0; end
        else if (convert) begin
            digital_out[channel_sel] <= analog_in[channel_sel] ? {WIDTH{1'b1}} : 0;
            eoc <= 1;
        end else eoc <= 0;
    end
endmodule
