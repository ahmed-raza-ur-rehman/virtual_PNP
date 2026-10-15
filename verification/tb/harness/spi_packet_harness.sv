// ---------------------------------------------------------------------------
// spi_packet_harness - integration harness for the host link.
//
// Wires the SPI slave to the packet framer exactly as pnp_core does, so the
// netlist simulation exercises the real byte path (bit ordering, chip-select
// gating, CRC check) rather than two blocks in isolation.  It lives in the
// verification tree because it is not part of the product netlist.
// ---------------------------------------------------------------------------
module spi_packet_harness #(
    parameter integer MAX_PAYLOAD = 8,
    parameter integer LEN_W       = 4,
    parameter integer TIMEOUT     = 1000
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         sck,
    input  wire         cs_n,
    input  wire         mosi,
    output wire         miso,
    output wire         cmd_valid,
    output wire [7:0]   cmd,
    output wire [LEN_W-1:0] payload_len,
    output wire [MAX_PAYLOAD*8-1:0] payload,
    output wire         err_bad_crc,
    output wire         err_bad_len,
    output wire         err_timeout,
    output wire [7:0]   frames_ok,
    output wire [7:0]   frames_err
);
    wire [7:0] rx_byte;
    wire       rx_valid;

    spi_slave #(.W(8), .CPOL(0)) u_spi (
        .clk(clk), .rst_n(rst_n), .sck(sck), .cs_n(cs_n), .mosi(mosi),
        .tx_data(8'h5A), .rx_data(rx_byte), .rx_valid(rx_valid),
        .miso(miso), .tx_load()
    );

    packet_if #(.MAX_PAYLOAD(MAX_PAYLOAD), .LEN_W(LEN_W), .TIMEOUT(TIMEOUT)) u_packet (
        .clk(clk), .rst_n(rst_n), .rx_byte(rx_byte), .rx_valid(rx_valid),
        .cmd_valid(cmd_valid), .cmd(cmd), .payload_len(payload_len), .payload(payload),
        .err_bad_crc(err_bad_crc), .err_bad_len(err_bad_len), .err_timeout(err_timeout),
        .frames_ok(frames_ok), .frames_err(frames_err)
    );
endmodule
