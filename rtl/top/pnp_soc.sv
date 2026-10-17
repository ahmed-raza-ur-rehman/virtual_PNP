// Complete PnP SoC: RISC-V core + bus + peripherals
module pnp_soc #(
    parameter N_AXES = 4
)(
    input  wire clk,
    input  wire rst_n,
    // external
    input  wire [7:0] gpio_in,
    output wire [7:0] gpio_out,
    output wire uart_tx,
    input  wire uart_rx,
    output wire can_tx,
    input  wire can_rx,
    inout  wire usb_dp,
    inout  wire usb_dm
);
    // CPU
    wire [31:0] pc;
    wire [31:0] instr;
    wire mem_we;
    wire [31:0] mem_addr, mem_wdata, mem_rdata;
    rv32i_core cpu (.clk(clk), .rst_n(rst_n), .pc(pc), .instr(instr),
        .mem_we(mem_we), .mem_addr(mem_addr), .mem_wdata(mem_wdata), .mem_rdata(mem_rdata));

    // instruction memory (ROM)
    reg [31:0] imem [0:1023];
    assign instr = imem[pc[11:2]];

    // data memory (SRAM)
    sram_ctrl #(.ADDR_W(14), .DATA_W(32)) dmem (
        .clk(clk), .rst_n(rst_n), .ce(1'b1), .we(mem_we),
        .addr(mem_addr[15:2]), .wdata(mem_wdata), .rdata(mem_rdata));

    // GPIO
    gpio #(.N(8)) gpio0 (.clk(clk), .rst_n(rst_n), .in(gpio_in), .out(gpio_out),
        .oe(), .wdata(mem_wdata[7:0]), .we_out(mem_we && mem_addr[31:28]==4'h1),
        .we_oe(1'b0));

    // UART
    uart_tx utx (.clk(clk), .rst_n(rst_n), .data(mem_wdata[7:0]),
        .send(mem_we && mem_addr[31:28]==4'h2), .tx(uart_tx), .busy());
    assign uart_rx = 1'b1;

    // CAN
    can_ctrl can0 (.clk(clk), .rst_n(rst_n), .tx_id(11'h123), .tx_data('{8{8'h00}}),
        .tx_len(4'd0), .tx_start(1'b0), .tx_done(), .tx_error(), .can_rx(can_rx), .can_tx(can_tx));

    // USB
    usb_dev usb0 (.clk(clk), .rst_n(rst_n), .usb_dp(usb_dp), .usb_dm(usb_dm),
        .usb_pullup(), .rx_data(), .rx_valid());

    // Timer
    wire tick;
    timer #(.W(32)) t0 (.clk(clk), .rst_n(rst_n), .period(32'd100000), .enable(1'b1), .tick(tick), .count());

    // initial program
    initial begin
        // simple: load NOPs
        for (int i = 0; i < 1024; i++) imem[i] = 32'h00000013; // NOP (addi x0,x0,0)
    end
endmodule
