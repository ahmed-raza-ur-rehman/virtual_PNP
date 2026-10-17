// AXI-Lite to APB bridge
module axi_to_apb #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32
)(
    input  logic                    clk,
    input  logic                    rst_n,
    // AXI-Lite slave
    input  logic [ADDR_WIDTH-1:0]   s_axi_awaddr,
    input  logic                    s_axi_awvalid,
    output logic                    s_axi_awready,
    input  logic [DATA_WIDTH-1:0]   s_axi_wdata,
    input  logic [DATA_WIDTH/8-1:0] s_axi_wstrb,
    input  logic                    s_axi_wvalid,
    output logic                    s_axi_wready,
    output logic [1:0]              s_axi_bresp,
    output logic                    s_axi_bvalid,
    input  logic                    s_axi_bready,
    input  logic [ADDR_WIDTH-1:0]   s_axi_araddr,
    input  logic                    s_axi_arvalid,
    output logic                    s_axi_arready,
    output logic [DATA_WIDTH-1:0]   s_axi_rdata,
    output logic [1:0]              s_axi_rresp,
    output logic                    s_axi_rvalid,
    input  logic                    s_axi_rready,
    // APB master
    output logic                    m_apb_psel,
    output logic                    m_apb_penable,
    output logic                    m_apb_pwrite,
    output logic [ADDR_WIDTH-1:0]   m_apb_paddr,
    output logic [DATA_WIDTH-1:0]   m_apb_pwdata,
    input  logic [DATA_WIDTH-1:0]   m_apb_prdata,
    input  logic                    m_apb_pready,
    input  logic                    m_apb_pslverr
);
    typedef enum logic [2:0] {IDLE, WRITE_SETUP, WRITE_ACCESS, READ_SETUP, READ_ACCESS, RESP} state_t;
    state_t state;
    logic [ADDR_WIDTH-1:0] addr_r;
    logic [DATA_WIDTH-1:0] wdata_r;
    logic write_r;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            s_axi_awready <= 0;
            s_axi_wready <= 0;
            s_axi_bvalid <= 0;
            s_axi_arready <= 0;
            s_axi_rvalid <= 0;
            m_apb_psel <= 0;
            m_apb_penable <= 0;
            m_apb_pwrite <= 0;
            m_apb_paddr <= 0;
            m_apb_pwdata <= 0;
            s_axi_bresp <= 0;
            s_axi_rresp <= 0;
            s_axi_rdata <= 0;
        end else begin
            case (state)
                IDLE: begin
                    s_axi_bvalid <= 0;
                    s_axi_rvalid <= 0;
                    if (s_axi_awvalid && s_axi_wvalid) begin
                        addr_r <= s_axi_awaddr;
                        wdata_r <= s_axi_wdata;
                        write_r <= 1;
                        s_axi_awready <= 1;
                        s_axi_wready <= 1;
                        state <= WRITE_SETUP;
                    end else if (s_axi_arvalid) begin
                        addr_r <= s_axi_araddr;
                        write_r <= 0;
                        s_axi_arready <= 1;
                        state <= READ_SETUP;
                    end
                end
                WRITE_SETUP: begin
                    s_axi_awready <= 0;
                    s_axi_wready <= 0;
                    m_apb_psel <= 1;
                    m_apb_penable <= 0;
                    m_apb_pwrite <= 1;
                    m_apb_paddr <= addr_r;
                    m_apb_pwdata <= wdata_r;
                    state <= WRITE_ACCESS;
                end
                WRITE_ACCESS: begin
                    m_apb_penable <= 1;
                    if (m_apb_pready) begin
                        m_apb_psel <= 0;
                        m_apb_penable <= 0;
                        s_axi_bvalid <= 1;
                        s_axi_bresp <= m_apb_pslverr ? 2'b10 : 2'b00;
                        state <= RESP;
                    end
                end
                READ_SETUP: begin
                    s_axi_arready <= 0;
                    m_apb_psel <= 1;
                    m_apb_penable <= 0;
                    m_apb_pwrite <= 0;
                    m_apb_paddr <= addr_r;
                    state <= READ_ACCESS;
                end
                READ_ACCESS: begin
                    m_apb_penable <= 1;
                    if (m_apb_pready) begin
                        m_apb_psel <= 0;
                        m_apb_penable <= 0;
                        s_axi_rdata <= m_apb_prdata;
                        s_axi_rvalid <= 1;
                        s_axi_rresp <= m_apb_pslverr ? 2'b10 : 2'b00;
                        state <= RESP;
                    end
                end
                RESP: begin
                    if ((write_r && s_axi_bready) || (!write_r && s_axi_rready)) begin
                        s_axi_bvalid <= 0;
                        s_axi_rvalid <= 0;
                        state <= IDLE;
                    end
                end
            endcase
        end
    end
endmodule
