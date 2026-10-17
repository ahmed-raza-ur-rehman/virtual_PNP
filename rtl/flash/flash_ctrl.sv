// Flash memory controller
module flash_ctrl #(
    parameter ADDR_WIDTH = 24,
    parameter DATA_WIDTH = 32
)(
    input  logic                    clk,
    input  logic                    rst_n,
    // Host interface
    input  logic                    req,
    input  logic                    write,
    input  logic                    erase,
    input  logic [ADDR_WIDTH-1:0]   addr,
    input  logic [DATA_WIDTH-1:0]   wdata,
    output logic [DATA_WIDTH-1:0]   rdata,
    output logic                    ready,
    output logic                    busy,
    // Flash interface
    output logic                    flash_cs_n,
    output logic                    flash_sck,
    output logic                    flash_mosi,
    input  logic                    flash_miso
);
    typedef enum logic [2:0] {IDLE, CMD, ADDR, DUMMY, DATA, DONE} state_t;
    state_t state;
    logic [7:0] cmd_reg;
    logic [23:0] addr_reg;
    logic [31:0] data_reg;
    logic [5:0] bit_cnt;
    logic [7:0] byte_cnt;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            ready <= 0;
            busy <= 0;
            flash_cs_n <= 1;
            flash_sck <= 0;
            flash_mosi <= 0;
            bit_cnt <= 0;
        end else begin
            case (state)
                IDLE: begin
                    ready <= 0;
                    if (req) begin
                        busy <= 1;
                        flash_cs_n <= 0;
                        if (erase) cmd_reg <= 8'h20; // sector erase
                        else if (write) cmd_reg <= 8'h02; // page program
                        else cmd_reg <= 8'h03; // read
                        addr_reg <= addr;
                        data_reg <= wdata;
                        state <= CMD;
                        bit_cnt <= 0;
                    end
                end
                CMD: begin
                    flash_sck <= ~flash_sck;
                    if (flash_sck == 0) begin
                        flash_mosi <= cmd_reg[7];
                        cmd_reg <= {cmd_reg[6:0], 1'b0};
                        bit_cnt <= bit_cnt + 1;
                        if (bit_cnt == 7) begin
                            bit_cnt <= 0;
                            state <= ADDR;
                        end
                    end
                end
                ADDR: begin
                    flash_sck <= ~flash_sck;
                    if (flash_sck == 0) begin
                        flash_mosi <= addr_reg[23];
                        addr_reg <= {addr_reg[22:0], 1'b0};
                        bit_cnt <= bit_cnt + 1;
                        if (bit_cnt == 23) begin
                            bit_cnt <= 0;
                            if (cmd_reg == 8'h03) state <= DUMMY; // read has dummy
                            else state <= DATA;
                        end
                    end
                end
                DUMMY: begin
                    flash_sck <= ~flash_sck;
                    bit_cnt <= bit_cnt + 1;
                    if (bit_cnt == 7) begin
                        bit_cnt <= 0;
                        state <= DATA;
                    end
                end
                DATA: begin
                    flash_sck <= ~flash_sck;
                    if (flash_sck == 0) begin
                        if (write || erase) begin
                            flash_mosi <= data_reg[31];
                            data_reg <= {data_reg[30:0], 1'b0};
                        end else begin
                            data_reg <= {data_reg[30:0], flash_miso};
                        end
                        bit_cnt <= bit_cnt + 1;
                        if (bit_cnt == 31) begin
                            bit_cnt <= 0;
                            state <= DONE;
                        end
                    end
                end
                DONE: begin
                    flash_cs_n <= 1;
                    flash_sck <= 0;
                    rdata <= data_reg;
                    ready <= 1;
                    busy <= 0;
                    state <= IDLE;
                end
            endcase
        end
    end
endmodule
