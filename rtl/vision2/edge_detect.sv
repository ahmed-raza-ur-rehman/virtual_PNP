// Edge detection accelerator (Sobel)
module edge_detect #(
    parameter IMG_WIDTH = 640,
    parameter DATA_WIDTH = 8
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    in_valid,
    input  logic [DATA_WIDTH-1:0]   in_pixel,
    output logic                    out_valid,
    output logic [DATA_WIDTH-1:0]   out_magnitude,
    output logic [2:0]              out_direction
);
    // 3x3 line buffer
    logic [DATA_WIDTH-1:0] line1 [0:IMG_WIDTH-1];
    logic [DATA_WIDTH-1:0] line2 [0:IMG_WIDTH-1];
    logic [DATA_WIDTH-1:0] cur [0:2];
    logic [9:0] col_cnt;
    logic [1:0] row_state;

    // Sobel kernels
    // Gx: [-1 0 1; -2 0 2; -1 0 1]
    // Gy: [-1 -2 -1; 0 0 0; 1 2 1]

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            col_cnt <= 0;
            out_valid <= 0;
            out_magnitude <= 0;
            out_direction <= 0;
        end else if (in_valid) begin
            // shift line buffers
            line2[col_cnt] <= line1[col_cnt];
            line1[col_cnt] <= in_pixel;
            // compute when we have 3 rows
            if (row_state == 2 && col_cnt >= 2) begin
                // simplified: use current and buffered pixels
                int gx, gy;
                // placeholder computation
                gx = 0; gy = 0;
                out_magnitude <= (gx > gy) ? gx[7:0] : gy[7:0];
                out_valid <= 1;
            end else begin
                out_valid <= 0;
            end
            if (col_cnt == IMG_WIDTH - 1) begin
                col_cnt <= 0;
                if (row_state < 2) row_state <= row_state + 1;
            end else begin
                col_cnt <= col_cnt + 1;
            end
        end else begin
            out_valid <= 0;
        end
    end
endmodule
