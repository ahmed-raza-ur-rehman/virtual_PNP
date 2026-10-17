// Histogram accelerator
module hist_accel #(
    parameter BINS = 256,
    parameter DATA_WIDTH = 8
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    in_valid,
    input  logic [DATA_WIDTH-1:0]   in_pixel,
    input  logic                    clear,
    output logic                    out_valid,
    output logic [31:0]             hist_out,
    output logic [7:0]              hist_addr,
    output logic                    hist_we
);
    logic [31:0] hist_mem [0:BINS-1];
    logic [9:0] pixel_count;
    logic processing;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0; i < BINS; i++) hist_mem[i] <= 0;
            pixel_count <= 0;
            processing <= 0;
            out_valid <= 0;
        end else begin
            if (clear) begin
                for (int i = 0; i < BINS; i++) hist_mem[i] <= 0;
                pixel_count <= 0;
            end else if (in_valid) begin
                hist_mem[in_pixel] <= hist_mem[in_pixel] + 1;
                pixel_count <= pixel_count + 1;
            end
            if (pixel_count == 1023) begin
                processing <= 1;
            end
            if (processing) begin
                // output histogram
                out_valid <= 1;
            end
        end
    end

    assign hist_out = hist_mem[hist_addr];
    assign hist_we = 0;
endmodule
