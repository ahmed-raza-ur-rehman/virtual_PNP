// Axis motion controller with trapezoidal profile
module motion_controller #(
    parameter DATA_W = 32
)(
    input  wire clk,
    input  wire rst,
    input  wire [DATA_W-1:0] target,
    input  wire [DATA_W-1:0] v_max,
    input  wire [DATA_W-1:0] a_max,
    output reg  [DATA_W-1:0] position,
    output reg  [DATA_W-1:0] velocity
);
    reg [DATA_W-1:0] err;
    always @(posedge clk or posedge rst) begin
        if (rst) begin position <= 0; velocity <= 0; end
        else begin
            err = (target > position) ? (target - position) : (position - target);
            if (err > 0) begin
                if (velocity < v_max) velocity <= velocity + a_max;
                position <= position + (target > position ? velocity : -velocity);
            end else begin
                velocity <= 0;
            end
        end
    end
endmodule
