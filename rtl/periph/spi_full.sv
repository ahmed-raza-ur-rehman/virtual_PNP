// Full SPI master/slave
module spi_full #(
    parameter CLK_DIV = 4
)(
    input  logic        clk,
    input  logic        rst_n,
    input  logic        cpol,
    input  logic        cpha,
    input  logic        master,
    // Master interface
    input  logic        start,
    input  logic [7:0]  tx_data,
    output logic [7:0]  rx_data,
    output logic        busy,
    output logic        done,
    // SPI pins
    output logic        sck,
    output logic        mosi,
    input  logic        miso,
    output logic        cs_n
);
    logic [2:0] bit_cnt;
    logic [7:0] shift_reg;
    logic [31:0] clk_cnt;
    logic sck_r;
    typedef enum logic [1:0] {IDLE, TRANSFER, DONE_ST} state_t;
    state_t state;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            sck <= cpol;
            mosi <= 0;
            cs_n <= 1;
            busy <= 0;
            done <= 0;
            bit_cnt <= 0;
            shift_reg <= 0;
            clk_cnt <= 0;
            sck_r <= cpol;
        end else begin
            done <= 0;
            case (state)
                IDLE: begin
                    sck <= cpol;
                    cs_n <= 1;
                    busy <= 0;
                    if (start) begin
                        shift_reg <= tx_data;
                        cs_n <= 0;
                        state <= TRANSFER;
                        busy <= 1;
                        bit_cnt <= 0;
                        clk_cnt <= 0;
                    end
                end
                TRANSFER: begin
                    if (clk_cnt < CLK_DIV/2 - 1) begin
                        clk_cnt <= clk_cnt + 1;
                    end else begin
                        clk_cnt <= 0;
                        sck <= ~sck;
                        if (sck == cpol) begin
                            // rising edge: sample miso
                            shift_reg <= {shift_reg[6:0], miso};
                            bit_cnt <= bit_cnt + 1;
                            if (bit_cnt == 7) begin
                                state <= DONE_ST;
                            end
                        end else begin
                            // falling edge: set mosi
                            mosi <= shift_reg[7];
                        end
                    end
                end
                DONE_ST: begin
                    sck <= cpol;
                    cs_n <= 1;
                    rx_data <= shift_reg;
                    done <= 1;
                    busy <= 0;
                    state <= IDLE;
                end
            endcase
        end
    end
endmodule
