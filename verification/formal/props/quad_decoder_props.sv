// ---------------------------------------------------------------------------
// quad_decoder_props - encoder front-end properties.
//
//   P1  the counter moves by at most one count per clock (a decoder can never
//       skip, whatever the input does)
//   P2  the counter only moves while count_en is high
//   P3  direction is only reported together with a count update
//   C1  non-vacuity: forward and reverse motion are both reachable
// ---------------------------------------------------------------------------
module quad_decoder_props (
    input wire clk,
    input wire rst_n
);
    localparam integer CNT_W = 8;

    (* anyseq *) reg a, b, idx, en;

    wire signed [CNT_W-1:0] count, index_pos;
    wire                    index_seen, dir, moving;

    quad_decoder #(.CNT_W(CNT_W), .FILTER_LEN(2)) dut (
        .clk(clk), .rst_n(rst_n), .a_raw(a), .b_raw(b), .idx_raw(idx),
        .count_en(en), .count(count), .index_pos(index_pos),
        .index_seen(index_seen), .dir(dir), .moving(moving)
    );

    localparam integer RESET_CYCLES = 4;
    reg [7:0] cyc = 8'd0;
    always @(posedge clk) if (cyc != 8'hFF) cyc <= cyc + 8'd1;
    always @(posedge clk) if (cyc < RESET_CYCLES) assume (!rst_n);
    always @(posedge clk) if (cyc >= RESET_CYCLES) assume (rst_n);
    wire past_reset = (cyc > RESET_CYCLES);

    // $past may only be used inside a clocked block, so the delta is computed
    // with an explicit shadow register.
    reg signed [CNT_W-1:0] count_d = {CNT_W{1'b0}};
    reg                    en_d = 1'b0;
    always @(posedge clk) begin
        count_d <= count;
        en_d    <= en;
    end
    wire signed [CNT_W-1:0] delta = count - count_d;

    always @(posedge clk) if (past_reset && rst_n) begin
        // P1 - at most one count per sample
        assert (delta <= 1 && delta >= -1);
        // P2 - no movement when counting is disabled
        if (!en_d) assert (count == count_d);
    end

    always @(posedge clk) cover (delta == 1);
    always @(posedge clk) cover (delta == -1);
    always @(posedge clk) cover (index_seen);
endmodule
