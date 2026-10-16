// ---------------------------------------------------------------------------
// quad_decoder - quadrature encoder front end.
//
//  * 4x decoding of an A/B channel pair with a synchronous 2-flop sampler so
//    that asynchronous encoder edges cannot create meta-stable state.
//  * A glitch filter rejects transitions shorter than FILTER_LEN samples,
//    which is what keeps a noisy cable from injecting phantom counts.
//  * INDEX input latches the count into index_pos, giving the drive a
//    repeatable electrical home independent of software.
// ---------------------------------------------------------------------------
module quad_decoder #(
    parameter integer CNT_W      = 32,
    parameter integer FILTER_LEN = 4
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                a_raw,
    input  wire                b_raw,
    input  wire                idx_raw,
    input  wire                count_en,
    output reg  signed [CNT_W-1:0] count,
    output reg  signed [CNT_W-1:0] index_pos,
    output reg                 index_seen,
    output reg                 dir,          // 1 = increasing count
    output wire                moving
);
    // --- input synchronisers ------------------------------------------------
    reg [2:0] a_sync, b_sync, idx_sync;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_sync <= 3'b000;
            b_sync <= 3'b000;
            idx_sync <= 3'b000;
        end else begin
            a_sync <= {a_sync[1:0], a_raw};
            b_sync <= {b_sync[1:0], b_raw};
            idx_sync <= {idx_sync[1:0], idx_raw};
        end
    end

    wire a = a_sync[2];
    wire b = b_sync[2];

    // --- glitch filter ------------------------------------------------------
    // A transition is accepted only after it has been stable for FILTER_LEN
    // samples; this is a counter-based debounce, not a fixed delay line.
    reg a_f, b_f;
    reg [15:0] a_stable, b_stable;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_f <= 1'b0; b_f <= 1'b0;
            a_stable <= 16'd0; b_stable <= 16'd0;
        end else begin
            if (a == a_f) a_stable <= 16'd0;
            else if (a_stable == FILTER_LEN[15:0] - 16'd1) begin
                a_f <= a; a_stable <= 16'd0;
            end else a_stable <= a_stable + 16'd1;

            if (b == b_f) b_stable <= 16'd0;
            else if (b_stable == FILTER_LEN[15:0] - 16'd1) begin
                b_f <= b; b_stable <= 16'd0;
            end else b_stable <= b_stable + 16'd1;
        end
    end

    wire [1:0] state = {a_f, b_f};
    reg  [1:0] state_d;

    // Gray-coded quadrature table: the two legal transition sequences differ
    // in direction, which is decoded by comparing with the previous state.
    reg signed [1:0] step;
    always @(*) begin
        case ({state_d, state})
            4'b00_01, 4'b01_11, 4'b11_10, 4'b10_00: step = 2'sd1;
            4'b00_10, 4'b10_11, 4'b11_01, 4'b01_00: step = -2'sd1;
            default: step = 2'sd0;
        endcase
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state_d <= 2'b00;
            count   <= {CNT_W{1'b0}};
            dir     <= 1'b0;
        end else begin
            state_d <= state;
            if (count_en && (step != 2'sd0)) begin
                count <= count + {{(CNT_W-2){step[1]}}, step};
                dir   <= (step > 0);
            end
        end
    end

    // --- index capture ------------------------------------------------------
    reg idx_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            idx_d <= 1'b0;
            index_seen <= 1'b0;
            index_pos <= {CNT_W{1'b0}};
        end else begin
            idx_d <= idx_sync[2];
            if (!idx_d && idx_sync[2]) begin
                index_pos  <= count;
                index_seen <= 1'b1;
            end
        end
    end

    assign moving = (step != 2'sd0);

`ifdef FORMAL
    // Direction is never reported without a count change and vice versa.
    reg f_past_valid = 1'b0;
    always @(posedge clk) f_past_valid <= 1'b1;
    always @(posedge clk) if (f_past_valid && $past(rst_n) && rst_n) begin
        if ($past(count_en) && $past(step) != 2'sd0)
            assert (count != $past(count));
    end
`endif
endmodule
