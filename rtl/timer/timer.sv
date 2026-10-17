module timer #(
    parameter W = 32
)(
    input  wire clk,
    input  wire rst_n,
    input  wire [W-1:0] period,
    input  wire enable,
    output reg  tick,
    output reg  [W-1:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin count <= 0; tick <= 0; end
        else if (enable) begin
            if (count >= period - 1) begin count <= 0; tick <= 1; end
            else begin count <= count + 1; tick <= 0; end
        end else begin tick <= 0; end
    end
endmodule
