// DMA controller
module dma_full #(
    parameter CHANNELS = 8,
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    ch_req [0:CHANNELS-1],
    output logic                    ch_ack [0:CHANNELS-1],
    input  logic [ADDR_WIDTH-1:0]   src_addr [0:CHANNELS-1],
    input  logic [ADDR_WIDTH-1:0]   dst_addr [0:CHANNELS-1],
    input  logic [15:0]             transfer_count [0:CHANNELS-1],
    input  logic                    ch_enable [0:CHANNELS-1],
    output logic                    ch_tc [0:CHANNELS-1], // terminal count
    output logic                    ch_ht [0:CHANNELS-1], // half transfer
    // memory interface
    output logic [ADDR_WIDTH-1:0]   mem_addr,
    output logic [DATA_WIDTH-1:0]   mem_wdata,
    input  logic [DATA_WIDTH-1:0]   mem_rdata,
    output logic                    mem_we,
    output logic                    mem_re,
    input  logic                    mem_ready
);
    logic [3:0] active_ch;
    logic [15:0] remaining [0:CHANNELS-1];
    logic [ADDR_WIDTH-1:0] cur_src [0:CHANNELS-1];
    logic [ADDR_WIDTH-1:0] cur_dst [0:CHANNELS-1];
    logic [2:0] state;
    logic [15:0] half_count [0:CHANNELS-1];

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active_ch <= 0;
            state <= 0;
            mem_we <= 0;
            mem_re <= 0;
            mem_addr <= 0;
            for (int i = 0; i < CHANNELS; i++) begin
                remaining[i] <= 0;
                cur_src[i] <= 0;
                cur_dst[i] <= 0;
                ch_ack[i] <= 0;
                ch_tc[i] <= 0;
                ch_ht[i] <= 0;
                half_count[i] <= 0;
            end
        end else begin
            // default
            mem_we <= 0;
            mem_re <= 0;
            for (int i = 0; i < CHANNELS; i++) ch_ack[i] <= 0;

            // find active channel
            if (state == 0) begin
                for (int i = 0; i < CHANNELS; i++) begin
                    if (ch_enable[i] && ch_req[i] && remaining[i] == 0) begin
                        remaining[i] <= transfer_count[i];
                        cur_src[i] <= src_addr[i];
                        cur_dst[i] <= dst_addr[i];
                        half_count[i] <= transfer_count[i] / 2;
                        active_ch <= i;
                        state <= 1;
                    end
                end
            end else if (state == 1) begin
                // read phase
                mem_addr <= cur_src[active_ch];
                mem_re <= 1;
                state <= 2;
            end else if (state == 2) begin
                // write phase
                mem_addr <= cur_dst[active_ch];
                mem_wdata <= mem_rdata;
                mem_we <= 1;
                cur_src[active_ch] <= cur_src[active_ch] + 4;
                cur_dst[active_ch] <= cur_dst[active_ch] + 4;
                remaining[active_ch] <= remaining[active_ch] - 1;
                if (remaining[active_ch] == half_count[active_ch]) begin
                    ch_ht[active_ch] <= 1;
                end
                if (remaining[active_ch] <= 1) begin
                    ch_tc[active_ch] <= 1;
                    ch_ack[active_ch] <= 1;
                    state <= 0;
                end else begin
                    state <= 1;
                end
            end
        end
    end
endmodule
