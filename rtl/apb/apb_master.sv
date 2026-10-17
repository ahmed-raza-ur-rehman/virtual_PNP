// APB Master
module apb_master #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32
)(
    input  logic                    clk,
    input  logic                    rst_n,
    // Control interface
    input  logic                    req,
    input  logic                    write,
    input  logic [ADDR_WIDTH-1:0]   addr,
    input  logic [DATA_WIDTH-1:0]   wdata,
    output logic [DATA_WIDTH-1:0]   rdata,
    output logic                    ready,
    output logic                    error,
    // APB interface
    output logic                    psel,
    output logic                    penable,
    output logic                    pwrite,
    output logic [ADDR_WIDTH-1:0]   paddr,
    output logic [DATA_WIDTH-1:0]   pwdata,
    input  logic [DATA_WIDTH-1:0]   prdata,
    input  logic                    pready,
    input  logic                    pslverr
);
    typedef enum logic [1:0] {IDLE, SETUP, ACCESS} state_t;
    state_t state;
    logic [ADDR_WIDTH-1:0] addr_r;
    logic [DATA_WIDTH-1:0] wdata_r;
    logic write_r;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            psel <= 0;
            penable <= 0;
            pwrite <= 0;
            paddr <= 0;
            pwdata <= 0;
            ready <= 0;
            error <= 0;
            rdata <= 0;
        end else begin
            case (state)
                IDLE: begin
                    ready <= 0;
                    if (req) begin
                        addr_r <= addr;
                        wdata_r <= wdata;
                        write_r <= write;
                        state <= SETUP;
                    end
                end
                SETUP: begin
                    psel <= 1;
                    penable <= 0;
                    paddr <= addr_r;
                    pwrite <= write_r;
                    pwdata <= wdata_r;
                    state <= ACCESS;
                end
                ACCESS: begin
                    penable <= 1;
                    if (pready) begin
                        psel <= 0;
                        penable <= 0;
                        ready <= 1;
                        error <= pslverr;
                        if (!write_r) rdata <= prdata;
                        state <= IDLE;
                    end
                end
            endcase
        end
    end
endmodule
