// Full UART with FIFO
module uart_full #(
    parameter CLK_FREQ = 50000000,
    parameter BAUD = 115200,
    parameter FIFO_DEPTH = 16
)(
    input  logic        clk,
    input  logic        rst_n,
    input  logic        tx_start,
    input  logic [7:0]  tx_data,
    output logic        tx_busy,
    output logic        tx_done,
    output logic        rx_data_valid,
    output logic [7:0]  rx_data,
    input  logic        rx,
    output logic        tx,
    output logic        rx_overflow,
    output logic        rx_frame_error,
    output logic        rx_parity_error
);
    localparam CLKS_PER_BIT = CLK_FREQ / BAUD;
    // TX state
    typedef enum logic [2:0] {TX_IDLE, TX_START, TX_DATA, TX_STOP} tx_state_t;
    tx_state_t tx_state;
    logic [31:0] tx_clk_count;
    logic [2:0]  tx_bit_idx;
    logic [7:0]  tx_shift;
    // RX state
    typedef enum logic [2:0] {RX_IDLE, RX_START, RX_DATA, RX_STOP} rx_state_t;
    rx_state_t rx_state;
    logic [31:0] rx_clk_count;
    logic [2:0]  rx_bit_idx;
    logic [7:0]  rx_shift;
    logic        rx_sync;
    // FIFO
    logic [7:0]  tx_fifo [0:FIFO_DEPTH-1];
    logic [4:0]  tx_fifo_wptr, tx_fifo_rptr, tx_fifo_count;
    logic [7:0]  rx_fifo [0:FIFO_DEPTH-1];
    logic [4:0]  rx_fifo_wptr, rx_fifo_rptr, rx_fifo_count;

    // sync rx
    always_ff @(posedge clk) begin
        rx_sync <= rx;
    end

    // TX logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_state <= TX_IDLE;
            tx <= 1;
            tx_busy <= 0;
            tx_done <= 0;
            tx_clk_count <= 0;
            tx_bit_idx <= 0;
            tx_fifo_wptr <= 0;
            tx_fifo_rptr <= 0;
            tx_fifo_count <= 0;
        end else begin
            tx_done <= 0;
            case (tx_state)
                TX_IDLE: begin
                    if (tx_fifo_count > 0) begin
                        tx_shift <= tx_fifo[tx_fifo_rptr];
                        tx_fifo_rptr <= (tx_fifo_rptr + 1) % FIFO_DEPTH;
                        tx_fifo_count <= tx_fifo_count - 1;
                        tx_state <= TX_START;
                        tx_clk_count <= 0;
                        tx_busy <= 1;
                    end else if (tx_start) begin
                        tx_shift <= tx_data;
                        tx_state <= TX_START;
                        tx_clk_count <= 0;
                        tx_busy <= 1;
                    end else begin
                        tx <= 1;
                        tx_busy <= 0;
                    end
                end
                TX_START: begin
                    tx <= 0;
                    if (tx_clk_count < CLKS_PER_BIT - 1) begin
                        tx_clk_count <= tx_clk_count + 1;
                    end else begin
                        tx_clk_count <= 0;
                        tx_state <= TX_DATA;
                        tx_bit_idx <= 0;
                    end
                end
                TX_DATA: begin
                    tx <= tx_shift[tx_bit_idx];
                    if (tx_clk_count < CLKS_PER_BIT - 1) begin
                        tx_clk_count <= tx_clk_count + 1;
                    end else begin
                        tx_clk_count <= 0;
                        if (tx_bit_idx < 7) begin
                            tx_bit_idx <= tx_bit_idx + 1;
                        end else begin
                            tx_state <= TX_STOP;
                        end
                    end
                end
                TX_STOP: begin
                    tx <= 1;
                    if (tx_clk_count < CLKS_PER_BIT - 1) begin
                        tx_clk_count <= tx_clk_count + 1;
                    end else begin
                        tx_clk_count <= 0;
                        tx_state <= TX_IDLE;
                        tx_done <= 1;
                        tx_busy <= 0;
                    end
                end
            endcase
        end
    end

    // RX logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_state <= RX_IDLE;
            rx_clk_count <= 0;
            rx_bit_idx <= 0;
            rx_shift <= 0;
            rx_data_valid <= 0;
            rx_fifo_wptr <= 0;
            rx_fifo_rptr <= 0;
            rx_fifo_count <= 0;
            rx_overflow <= 0;
            rx_frame_error <= 0;
        end else begin
            rx_data_valid <= 0;
            case (rx_state)
                RX_IDLE: begin
                    if (rx_sync == 0) begin
                        rx_state <= RX_START;
                        rx_clk_count <= 0;
                    end
                end
                RX_START: begin
                    if (rx_clk_count == CLKS_PER_BIT/2) begin
                        if (rx_sync == 0) begin
                            rx_clk_count <= 0;
                            rx_state <= RX_DATA;
                            rx_bit_idx <= 0;
                        end else begin
                            rx_state <= RX_IDLE;
                        end
                    end else begin
                        rx_clk_count <= rx_clk_count + 1;
                    end
                end
                RX_DATA: begin
                    if (rx_clk_count < CLKS_PER_BIT - 1) begin
                        rx_clk_count <= rx_clk_count + 1;
                    end else begin
                        rx_clk_count <= 0;
                        rx_shift[rx_bit_idx] <= rx_sync;
                        if (rx_bit_idx < 7) begin
                            rx_bit_idx <= rx_bit_idx + 1;
                        end else begin
                            rx_state <= RX_STOP;
                        end
                    end
                end
                RX_STOP: begin
                    if (rx_clk_count < CLKS_PER_BIT - 1) begin
                        rx_clk_count <= rx_clk_count + 1;
                    end else begin
                        rx_clk_count <= 0;
                        if (rx_sync == 1) begin
                            // valid byte
                            if (rx_fifo_count < FIFO_DEPTH) begin
                                rx_fifo[rx_fifo_wptr] <= rx_shift;
                                rx_fifo_wptr <= (rx_fifo_wptr + 1) % FIFO_DEPTH;
                                rx_fifo_count <= rx_fifo_count + 1;
                                rx_data_valid <= 1;
                                rx_data <= rx_shift;
                            end else begin
                                rx_overflow <= 1;
                            end
                        end else begin
                            rx_frame_error <= 1;
                        end
                        rx_state <= RX_IDLE;
                    end
                end
            endcase
        end
    end
endmodule
