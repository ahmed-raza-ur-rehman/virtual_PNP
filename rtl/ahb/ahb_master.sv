// AHB-Lite Master
module ahb_master #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    req,
    input  logic                    write,
    input  logic [ADDR_WIDTH-1:0]   addr,
    input  logic [DATA_WIDTH-1:0]   wdata,
    input  logic [2:0]              size,
    output logic [DATA_WIDTH-1:0]   rdata,
    output logic                    ready,
    // AHB
    output logic [ADDR_WIDTH-1:0]   haddr,
    output logic [2:0]              hburst,
    output logic                    hmastlock,
    output logic [3:0]              hprot,
    output logic [2:0]              hsize,
    output logic [1:0]              htrans,
    output logic                    hwrite,
    output logic [DATA_WIDTH-1:0]   hwdata,
    input  logic [DATA_WIDTH-1:0]   hrdata,
    input  logic                    hready,
    input  logic                    hresp
);
    typedef enum logic [1:0] {IDLE, BUSY, NONSEQ, SEQ} trans_t;
    logic [1:0] state;
    logic [ADDR_WIDTH-1:0] addr_r;
    logic write_r;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= 0;
            haddr <= 0;
            htrans <= 0;
            hwrite <= 0;
            hwdata <= 0;
            hsize <= 0;
            hburst <= 0;
            hmastlock <= 0;
            hprot <= 0;
            ready <= 0;
            rdata <= 0;
        end else begin
            if (req && state == 0) begin
                addr_r <= addr;
                write_r <= write;
                state <= 2; // NONSEQ
                haddr <= addr;
                htrans <= 2;
                hwrite <= write;
                hwdata <= wdata;
                hsize <= size;
                hburst <= 3'b000; // SINGLE
                hprot <= 4'b0011;
            end else if (state == 2) begin
                if (hready) begin
                    if (hresp) begin
                        // error
                    end
                    if (!write_r) rdata <= hrdata;
                    ready <= 1;
                    state <= 0;
                    htrans <= 0;
                end
            end
        end
    end
endmodule
