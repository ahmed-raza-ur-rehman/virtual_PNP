// Clock generator with PLL
module clock_gen #(
    parameter INPUT_FREQ = 8000000,
    parameter OUTPUT_FREQ = 168000000
)(
    input  logic        clk_in,
    input  logic        rst_n,
    output logic        clk_out,
    output logic        clk_out_div2,
    output logic        locked,
    output logic        clk_48m
);
    localparam MUL = OUTPUT_FREQ / INPUT_FREQ;
    logic [31:0] counter;
    logic pll_locked;

    always_ff @(posedge clk_in or negedge rst_n) begin
        if (!rst_n) begin
            counter <= 0;
            pll_locked <= 0;
        end else begin
            if (counter < MUL - 1)
                counter <= counter + 1;
            else begin
                counter <= 0;
                pll_locked <= 1;
            end
        end
    end

    assign locked = pll_locked;
    assign clk_out = (counter < MUL/2) ? 1'b1 : 1'b0;
    assign clk_out_div2 = (counter < MUL/4) ? 1'b1 : 1'b0;
    assign clk_48m = (counter % (OUTPUT_FREQ/48000000)) < (OUTPUT_FREQ/48000000)/2;
endmodule
