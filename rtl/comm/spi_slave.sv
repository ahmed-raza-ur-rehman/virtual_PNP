// ---------------------------------------------------------------------------
// spi_slave - byte-level SPI slave, mode 0 (CPOL=0/CPHA=0) or mode 3.
//
// MOSI is sampled on the leading edge and MISO is updated on the trailing
// edge, which is the definition of both modes; CPOL only changes the idle
// level.  One `rx_valid` pulse is produced per accepted byte and the transmit
// byte must be presented before the next `tx_load`.  There is no internal FIFO
// by design: the stream is consumed by the packet framer at line rate, and a
// FIFO here would only add latency to the safety kick path.
// ---------------------------------------------------------------------------
module spi_slave #(
    parameter integer W = 8,
    parameter integer CPOL = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          sck,
    input  wire          cs_n,
    input  wire          mosi,
    input  wire [W-1:0]  tx_data,
    output reg  [W-1:0]  rx_data,
    output reg           rx_valid,
    output wire          miso,
    output reg           tx_load
);
    reg [2:0]  sck_sync, cs_sync, mosi_sync;
    reg [2:0]  bit_idx;
    reg [W-1:0] shifter_rx, shifter_tx;
    reg        sck_d, cs_d;

    wire sck_i  = sck_sync[2];
    wire cs_i   = cs_sync[2];
    wire mosi_i = mosi_sync[2];
    wire lead_edge  = (sck_i != sck_d) && (sck_i == (CPOL[0] ? 1'b1 : 1'b0));
    wire trail_edge = (sck_i != sck_d) && (sck_i == (CPOL[0] ? 1'b0 : 1'b1));
    wire cs_fall    = cs_d && !cs_i;

    assign miso = cs_i ? 1'bz : shifter_tx[W-1];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sck_sync <= 3'b000; cs_sync <= 3'b111; mosi_sync <= 3'b000;
            rx_data <= {W{1'b0}}; rx_valid <= 1'b0; tx_load <= 1'b0;
            bit_idx <= 3'd0; shifter_rx <= {W{1'b0}}; shifter_tx <= {W{1'b0}};
            sck_d <= CPOL[0]; cs_d <= 1'b1;
        end else begin
            sck_sync  <= {sck_sync[1:0], sck};
            cs_sync   <= {cs_sync[1:0], cs_n};
            mosi_sync <= {mosi_sync[1:0], mosi};
            sck_d <= sck_i;
            cs_d  <= cs_i;
            rx_valid <= 1'b0;
            tx_load  <= 1'b0;

            if (cs_fall) begin
                shifter_tx <= tx_data;      // load on chip select, before edges
                tx_load    <= 1'b1;
                bit_idx    <= 3'd0;
            end

            if (!cs_i) begin
                if (lead_edge) begin
                    shifter_rx <= {shifter_rx[W-2:0], mosi_i};
                    if (bit_idx == W[2:0] - 3'd1) begin
                        rx_data  <= {shifter_rx[W-2:0], mosi_i};
                        rx_valid <= 1'b1;
                        bit_idx  <= 3'd0;
                    end else bit_idx <= bit_idx + 3'd1;
                end
                if (trail_edge) shifter_tx <= {shifter_tx[W-2:0], 1'b0};
            end
        end
    end
endmodule
