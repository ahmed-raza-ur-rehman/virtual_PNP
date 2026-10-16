module quadrature (
    input wire clk,
    input wire a,
    input wire b,
    input wire index,
    output reg [31:0] count,
    output reg idx_pulse
);
    reg a_d, b_d, i_d;
    always @(posedge clk) begin
        a_d <= a; b_d <= b; i_d <= index;
        if (a && !a_d) begin
            if (b) count <= count + 1; else count <= count - 1;
        end
        if (index && !i_d) idx_pulse <= 1; else idx_pulse <= 0;
    end
endmodule
