// AXI4-Lite master with burst support (single beat)
module axi_lite_master #(
    parameter ADDR_W = 32,
    parameter DATA_W = 32
)(
    input  wire clk,
    input  wire rst_n,
    // command interface
    input  wire        cmd_valid,
    input  wire        cmd_write,
    input  wire [ADDR_W-1:0] cmd_addr,
    input  wire [DATA_W-1:0] cmd_wdata,
    output reg         cmd_ready,
    output reg  [DATA_W-1:0] cmd_rdata,
    output reg         cmd_rvalid,
    // AXI4-Lite
    output reg  [ADDR_W-1:0] m_axi_awaddr,
    output reg         m_axi_awvalid,
    input  wire        m_axi_awready,
    output reg  [DATA_W-1:0] m_axi_wdata,
    output reg  [DATA_W/8-1:0] m_axi_wstrb,
    output reg         m_axi_wvalid,
    input  wire        m_axi_wready,
    input  wire [1:0]  m_axi_bresp,
    input  wire        m_axi_bvalid,
    output reg         m_axi_bready,
    output reg  [ADDR_W-1:0] m_axi_araddr,
    output reg         m_axi_arvalid,
    input  wire        m_axi_arready,
    input  wire [DATA_W-1:0] m_axi_rdata,
    input  wire [1:0]  m_axi_rresp,
    input  wire        m_axi_rvalid,
    output reg         m_axi_rready
);
    typedef enum logic [2:0] {IDLE, WRITE_ADDR, WRITE_DATA, WRITE_RESP, READ_ADDR, READ_DATA} state_t;
    state_t state;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; cmd_ready <= 0; cmd_rvalid <= 0;
            m_axi_awvalid <= 0; m_axi_wvalid <= 0; m_axi_bready <= 0;
            m_axi_arvalid <= 0; m_axi_rready <= 0;
        end else begin
            cmd_ready <= 0; cmd_rvalid <= 0;
            case (state)
                IDLE: begin
                    if (cmd_valid) begin
                        if (cmd_write) begin
                            m_axi_awaddr <= cmd_addr; m_axi_awvalid <= 1;
                            m_axi_wdata <= cmd_wdata; m_axi_wstrb <= '1; m_axi_wvalid <= 1;
                            state <= WRITE_ADDR;
                        end else begin
                            m_axi_araddr <= cmd_addr; m_axi_arvalid <= 1;
                            state <= READ_ADDR;
                        end
                    end
                end
                WRITE_ADDR: begin
                    if (m_axi_awready && m_axi_wready) begin
                        m_axi_awvalid <= 0; m_axi_wvalid <= 0; m_axi_bready <= 1;
                        state <= WRITE_RESP;
                    end
                end
                WRITE_RESP: begin
                    if (m_axi_bvalid) begin
                        m_axi_bready <= 0; cmd_ready <= 1; state <= IDLE;
                    end
                end
                READ_ADDR: begin
                    if (m_axi_arready) begin
                        m_axi_arvalid <= 0; m_axi_rready <= 1; state <= READ_DATA;
                    end
                end
                READ_DATA: begin
                    if (m_axi_rvalid) begin
                        m_axi_rready <= 0; cmd_rdata <= m_axi_rdata; cmd_rvalid <= 1; cmd_ready <= 1;
                        state <= IDLE;
                    end
                end
            endcase
        end
    end
endmodule
