// Wishbone Master (Classic)
module wb_master #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32
)(
    input  logic                    clk,
    input  logic                    rst,
    input  logic                    req,
    input  logic                    write,
    input  logic [ADDR_WIDTH-1:0]   addr,
    input  logic [DATA_WIDTH-1:0]   wdata,
    output logic [DATA_WIDTH-1:0]   rdata,
    output logic                    ack,
    output logic                    err,
    // Wishbone
    output logic                    cyc,
    output logic                    stb,
    output logic                    we,
    output logic [ADDR_WIDTH-1:0]   adr,
    output logic [DATA_WIDTH-1:0]   dat_o,
    input  logic [DATA_WIDTH-1:0]   dat_i,
    input  logic                    ack_i,
    input  logic                    err_i,
    output logic [DATA_WIDTH/8-1:0] sel
);
    typedef enum logic [1:0] {IDLE, TRANSFER, WAIT} state_t;
    state_t state;

    always_ff @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            cyc <= 0;
            stb <= 0;
            we <= 0;
            adr <= 0;
            dat_o <= 0;
            sel <= 0;
            ack <= 0;
            err <= 0;
            rdata <= 0;
        end else begin
            case (state)
                IDLE: begin
                    ack <= 0;
                    err <= 0;
                    if (req) begin
                        cyc <= 1;
                        stb <= 1;
                        we <= write;
                        adr <= addr;
                        dat_o <= wdata;
                        sel <= {DATA_WIDTH/8{1'b1}};
                        state <= TRANSFER;
                    end
                end
                TRANSFER: begin
                    if (ack_i) begin
                        cyc <= 0;
                        stb <= 0;
                        ack <= 1;
                        rdata <= dat_i;
                        state <= IDLE;
                    end else if (err_i) begin
                        cyc <= 0;
                        stb <= 0;
                        err <= 1;
                        state <= IDLE;
                    end
                end
            endcase
        end
    end
endmodule
