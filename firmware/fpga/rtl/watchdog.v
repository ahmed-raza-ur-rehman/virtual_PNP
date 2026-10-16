module watchdog #(
    parameter TIMEOUT = 1000000
)(
    input wire clk,
    input wire rst,
    input wire kick,
    output reg timeout
);
    reg [31:0] counter;
    always @(posedge clk or posedge rst) begin
        if (rst) begin counter <= 0; timeout <= 0; end
        else if (kick) counter <= 0;
        else if (counter < TIMEOUT) counter <= counter + 1;
        else timeout <= 1;
    end
endmodule
