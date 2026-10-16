// ---------------------------------------------------------------------------
// centroid_accel - streaming moment accumulator for the vision head.
//
// For every pixel above the configured threshold the accelerator accumulates
// the five moments needed to place a part without a full frame buffer:
//
//     count  = sum(1)
//     sum_x  = sum(x)            sum_y  = sum(y)
//     sum_xx = sum(x*x)          sum_yy = sum(y*y)      sum_xy = sum(x*y)
//
// From these the host (or the next stage in the pipeline) obtains the centroid
// and the principal-axis orientation
//
//     theta = 0.5 * atan2(2*(sum_xy - sum_x*sum_y/n), (sum_xx - sum_x^2/n) - (sum_yy - sum_y^2/n))
//
// which is exactly the quantity the alignment step needs.  Doing it in the
// streaming path means the placement head does not have to wait for a full
// frame to be stored and re-read, and the accumulator width is bounded by the
// maximum sensor row/column count, so the hardware is not tied to a resolution.
//
// One pixel per clock; `frame_start` clears the accumulators and `frame_end`
// raises `done` for one cycle with the latched results.
// ---------------------------------------------------------------------------
module centroid_accel #(
    parameter integer COORD_W = 12,      // sensor rows/columns
    parameter integer ACC_W   = 32,      // moment accumulator width
    parameter integer PIX_W   = 8        // pixel intensity width
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    frame_start,
    input  wire                    frame_end,
    input  wire                    pix_valid,
    input  wire [COORD_W-1:0]      pix_x,
    input  wire [COORD_W-1:0]      pix_y,
    input  wire [PIX_W-1:0]        intensity,
    input  wire [PIX_W-1:0]        threshold,
    output reg  [ACC_W-1:0]        count,
    output reg  signed [ACC_W-1:0] sum_x,
    output reg  signed [ACC_W-1:0] sum_y,
    output reg  signed [ACC_W-1:0] sum_xx,
    output reg  signed [ACC_W-1:0] sum_yy,
    output reg  signed [ACC_W-1:0] sum_xy,
    output reg                     done,
    output reg                     overflow
);
    wire        hit  = pix_valid && (intensity >= threshold);
    wire [ACC_W-1:0] x = pix_x;
    wire [ACC_W-1:0] y = pix_y;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= {ACC_W{1'b0}}; sum_x <= {ACC_W{1'b0}}; sum_y <= {ACC_W{1'b0}};
            sum_xx <= {ACC_W{1'b0}}; sum_yy <= {ACC_W{1'b0}}; sum_xy <= {ACC_W{1'b0}};
            done <= 1'b0; overflow <= 1'b0;
        end else begin
            done <= 1'b0;
            if (frame_start) begin
                count <= {ACC_W{1'b0}}; sum_x <= {ACC_W{1'b0}}; sum_y <= {ACC_W{1'b0}};
                sum_xx <= {ACC_W{1'b0}}; sum_yy <= {ACC_W{1'b0}}; sum_xy <= {ACC_W{1'b0}};
                overflow <= 1'b0;
            end else if (hit) begin
                if (count == {ACC_W{1'b1}}) overflow <= 1'b1;   // saturate, never wrap
                else count <= count + 1'b1;
                sum_x  <= sum_x  + x;
                sum_y  <= sum_y  + y;
                sum_xx <= sum_xx + (x * x);
                sum_yy <= sum_yy + (y * y);
                sum_xy <= sum_xy + (x * y);
            end
            if (frame_end && !frame_start) done <= 1'b1;
        end
    end
endmodule
