// Memory controller (SRAM/SDRAM)
module mem_ctrl #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32,
    parameter BURST_LEN = 8
)(
    input  logic                    clk,
    input  logic                    rst_n,
    // Host interface
    input  logic                    req,
    input  logic                    write,
    input  logic [ADDR_WIDTH-1:0]   addr,
    input  logic [DATA_WIDTH-1:0]   wdata,
    input  logic [DATA_WIDTH/8-1:0] wstrb,
    output logic [DATA_WIDTH-1:0]   rdata,
    output logic                    ready,
    output logic                    error,
    // Memory interface
    output logic [ADDR_WIDTH-1:0]   mem_addr,
    output logic [DATA_WIDTH-1:0]   mem_wdata,
    input  logic [DATA_WIDTH-1:0]   mem_rdata,
    output logic                    mem_we,
    output logic                    mem_re,
    output logic [DATA_WIDTH/8-1:0] mem_be,
    input  logic                    mem_ready,
    output logic                    mem_valid
);
    typedef enum logic [2:0] {IDLE, READ, WRITE, WAIT} state_t;
    state_t state;
    logic [ADDR_WIDTH-1:0] addr_r;
    logic [DATA_WIDTH-1:0] wdata_r;
    logic [DATA_WIDTH/8-1:0] wstrb_r;
    logic write_r;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            ready <= 0;
            error <= 0;
            rdata <= 0;
            mem_we <= 0;
            mem_re <= 0;
            mem_valid <= 0;
            mem_addr <= 0;
            mem_wdata <= 0;
            mem_be <= 0;
        end else begin
            ready <= 0;
            mem_we <= 0;
            mem_re <= 0;
            mem_valid <= 0;
            case (state)
                IDLE: begin
                    if (req) begin
                        addr_r <= addr;
                        wdata_r <= wdata;
                        wstrb_r <= wstrb;
                        write_r <= write;
                        if (write) begin
                            state <= WRITE;
                        end else begin
                            state <= READ;
                        end
                    end
                end
                READ: begin
                    mem_addr <= addr_r;
                    mem_re <= 1;
                    mem_valid <= 1;
                    state <= WAIT;
                end
                WRITE: begin
                    mem_addr <= addr_r;
                    mem_wdata <= wdata_r;
                    mem_we <= 1;
                    mem_be <= wstrb_r;
                    mem_valid <= 1;
                    state <= WAIT;
                end
                WAIT: begin
                    if (mem_ready) begin
                        if (!write_r) rdata <= mem_rdata;
                        ready <= 1;
                        state <= IDLE;
                    end
                end
            endcase
        end
    end
endmodule
