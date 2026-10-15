module encoder (
    input wire clk,
    input wire a,
    input wire b,
    output reg [31:0] count
);
    reg a_prev;
    always @(posedge clk) begin
        a_prev <= a;
        if (a && !a_prev) begin
            if (b) count <= count + 1;
            else   count <= count - 1;
        end
    end
endmodule
