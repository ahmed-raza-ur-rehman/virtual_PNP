// Full I2C master
module i2c_full #(
    parameter CLK_FREQ = 50000000,
    parameter I2C_FREQ = 100000
)(
    input  logic        clk,
    input  logic        rst_n,
    input  logic        start,
    input  logic        rw, // 0 write, 1 read
    input  logic [6:0]  addr,
    input  logic [7:0]  tx_data,
    output logic [7:0]  rx_data,
    output logic        busy,
    output logic        done,
    output logic        ack_error,
    inout  wire         sda,
    output logic        scl
);
    localparam CLKS_PER_BIT = CLK_FREQ / I2C_FREQ;
    logic sda_out, sda_oe;
    assign sda = sda_oe ? sda_out : 1'bz;

    typedef enum logic [3:0] {IDLE, START, ADDR, ADDR_ACK, DATA, DATA_ACK, STOP, DONE_ST} state_t;
    state_t state;
    logic [7:0] shift;
    logic [2:0] bit_idx;
    logic [31:0] clk_cnt;
    logic [7:0] rx_shift;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            scl <= 1;
            sda_out <= 1;
            sda_oe <= 0;
            busy <= 0;
            done <= 0;
            ack_error <= 0;
            bit_idx <= 0;
            clk_cnt <= 0;
        end else begin
            done <= 0;
            case (state)
                IDLE: begin
                    scl <= 1;
                    sda_out <= 1;
                    sda_oe <= 0;
                    busy <= 0;
                    if (start) begin
                        busy <= 1;
                        state <= START;
                        clk_cnt <= 0;
                    end
                end
                START: begin
                    sda_out <= 0;
                    sda_oe <= 1;
                    if (clk_cnt < CLKS_PER_BIT - 1) begin
                        clk_cnt <= clk_cnt + 1;
                    end else begin
                        clk_cnt <= 0;
                        scl <= 0;
                        shift <= {addr, rw};
                        bit_idx <= 0;
                        state <= ADDR;
                    end
                end
                ADDR: begin
                    sda_out <= shift[7];
                    sda_oe <= 1;
                    if (clk_cnt < CLKS_PER_BIT/2 - 1) begin
                        clk_cnt <= clk_cnt + 1;
                    end else begin
                        scl <= 1;
                        if (clk_cnt < CLKS_PER_BIT - 1) begin
                            clk_cnt <= clk_cnt + 1;
                        end else begin
                            clk_cnt <= 0;
                            scl <= 0;
                            shift <= {shift[6:0], 1'b0};
                            if (bit_idx < 7) begin
                                bit_idx <= bit_idx + 1;
                            end else begin
                                state <= ADDR_ACK;
                                sda_oe <= 0;
                            end
                        end
                    end
                end
                ADDR_ACK: begin
                    sda_oe <= 0;
                    if (clk_cnt < CLKS_PER_BIT/2 - 1) begin
                        clk_cnt <= clk_cnt + 1;
                    end else begin
                        scl <= 1;
                        if (clk_cnt < CLKS_PER_BIT - 1) begin
                            clk_cnt <= clk_cnt + 1;
                        end else begin
                            clk_cnt <= 0;
                            scl <= 0;
                            if (sda == 1) ack_error <= 1;
                            if (rw) begin
                                bit_idx <= 0;
                                rx_shift <= 0;
                                state <= DATA;
                            end else begin
                                shift <= tx_data;
                                bit_idx <= 0;
                                state <= DATA;
                            end
                        end
                    end
                end
                DATA: begin
                    if (!rw) begin
                        sda_out <= shift[7];
                        sda_oe <= 1;
                    end else begin
                        sda_oe <= 0;
                    end
                    if (clk_cnt < CLKS_PER_BIT/2 - 1) begin
                        clk_cnt <= clk_cnt + 1;
                    end else begin
                        scl <= 1;
                        if (clk_cnt < CLKS_PER_BIT - 1) begin
                            clk_cnt <= clk_cnt + 1;
                        end else begin
                            clk_cnt <= 0;
                            scl <= 0;
                            if (rw) begin
                                rx_shift <= {rx_shift[6:0], sda};
                            end else begin
                                shift <= {shift[6:0], 1'b0};
                            end
                            if (bit_idx < 7) begin
                                bit_idx <= bit_idx + 1;
                            end else begin
                                if (rw) rx_data <= rx_shift;
                                state <= DATA_ACK;
                                if (!rw) sda_oe <= 0;
                            end
                        end
                    end
                end
                DATA_ACK: begin
                    if (!rw) begin
                        sda_oe <= 0;
                    end else begin
                        sda_out <= 0; // NACK for last byte (simplified)
                        sda_oe <= 1;
                    end
                    if (clk_cnt < CLKS_PER_BIT/2 - 1) begin
                        clk_cnt <= clk_cnt + 1;
                    end else begin
                        scl <= 1;
                        if (clk_cnt < CLKS_PER_BIT - 1) begin
                            clk_cnt <= clk_cnt + 1;
                        end else begin
                            clk_cnt <= 0;
                            scl <= 0;
                            state <= STOP;
                        end
                    end
                end
                STOP: begin
                    sda_out <= 0;
                    sda_oe <= 1;
                    scl <= 1;
                    if (clk_cnt < CLKS_PER_BIT - 1) begin
                        clk_cnt <= clk_cnt + 1;
                    end else begin
                        clk_cnt <= 0;
                        sda_out <= 1;
                        state <= DONE_ST;
                    end
                end
                DONE_ST: begin
                    busy <= 0;
                    done <= 1;
                    state <= IDLE;
                end
            endcase
        end
    end
endmodule
