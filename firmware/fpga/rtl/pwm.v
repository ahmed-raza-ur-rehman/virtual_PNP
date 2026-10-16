module pwm #(
    parameter WIDTH = 16
)(
    input  wire clk,
    input  wire rst,
    input  wire [WIDTH-1:0] duty,
    output reg  out
);
    reg [WIDTH-1:0] counter;
    always @(posedge clk or posedge rst) begin
        if (rst) begin counter <= 0; out <= 0; end
        else begin
            counter <= counter + 1;
            out <= (counter < duty);
        end
    end
endmodule
