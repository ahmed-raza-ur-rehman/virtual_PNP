module dma_ctrl #(
    parameter ADDR_W = 32,
    parameter DATA_W = 32
)(
    input  wire clk,
    input  wire rst_n,
    input  wire start,
    input  wire [ADDR_W-1:0] src_addr,
    input  wire [ADDR_W-1:0] dst_addr,
    input  wire [15:0]       length,
    output reg  busy,
    output reg  done,
    // memory interface
    output reg  [ADDR_W-1:0] mem_addr,
    output reg         mem_we,
    output reg  [DATA_W-1:0] mem_wdata,
    input  wire [DATA_W-1:0] mem_rdata
);
    reg [15:0] count;
    reg [ADDR_W-1:0] src, dst;
    typedef enum logic [1:0] {IDLE, READ, WRITE} st_t;
    st_t state;
    reg [DATA_W-1:0] buf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin state <= IDLE; busy <= 0; done <= 0; count <= 0; end
        else begin
            done <= 0;
            case (state)
                IDLE: begin
                    if (start) begin src <= src_addr; dst <= dst_addr; count <= length; busy <= 1; state <= READ; end
                end
                READ: begin
                    mem_addr <= src; mem_we <= 0; state <= WRITE;
                end
                WRITE: begin
                    buf <= mem_rdata; mem_addr <= dst; mem_we <= 1; mem_wdata <= buf;
                    src <= src + 4; dst <= dst + 4; count <= count - 1;
                    if (count == 1) begin busy <= 0; done <= 1; state <= IDLE; end
                    else state <= READ;
                end
            endcase
        end
    end
endmodule
