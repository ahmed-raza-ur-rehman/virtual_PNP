module pid #(
    parameter W = 16
)(
    input wire clk,
    input wire rst,
    input wire signed [W-1:0] setpoint,
    input wire signed [W-1:0] measured,
    input wire signed [W-1:0] kp, ki, kd,
    output reg signed [W-1:0] out
);
    reg signed [W-1:0] err, prev_err, integral;
    always @(posedge clk or posedge rst) begin
        if (rst) begin err <= 0; prev_err <= 0; integral <= 0; out <= 0; end
        else begin
            err <= setpoint - measured;
            integral <= integral + err;
            if (integral > (1<<(W-2))) integral <= (1<<(W-2));
            if (integral < -(1<<(W-2))) integral <= -(1<<(W-2));
            out <= (kp * err + ki * integral + kd * (err - prev_err)) >>> 8;
            prev_err <= err;
        end
    end
endmodule
