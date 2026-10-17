module axi_lite_slave #(
    parameter ADDR_W = 32,
    parameter DATA_W = 32
)(
    input  wire clk,
    input  wire rst_n,
    // AXI
    input  wire [ADDR_W-1:0] s_axi_awaddr,
    input  wire        s_axi_awvalid,
    output reg         s_axi_awready,
    input  wire [DATA_W-1:0] s_axi_wdata,
    input  wire [DATA_W/8-1:0] s_axi_wstrb,
    input  wire        s_axi_wvalid,
    output reg         s_axi_wready,
    output reg  [1:0]  s_axi_bresp,
    output reg         s_axi_bvalid,
    input  wire        s_axi_bready,
    input  wire [ADDR_W-1:0] s_axi_araddr,
    input  wire        s_axi_arvalid,
    output reg         s_axi_arready,
    output reg  [DATA_W-1:0] s_axi_rdata,
    output reg  [1:0]  s_axi_rresp,
    output reg         s_axi_rvalid,
    input  wire        s_axi_rready,
    // register interface
    output reg  [ADDR_W-1:0] reg_addr,
    output reg  [DATA_W-1:0] reg_wdata,
    output reg         reg_we,
    input  wire [DATA_W-1:0] reg_rdata
);
    typedef enum logic [1:0] {IDLE, WRITE, READ} st_t;
    st_t state;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; s_axi_awready <= 0; s_axi_wready <= 0;
            s_axi_bvalid <= 0; s_axi_arready <= 0; s_axi_rvalid <= 0;
            reg_we <= 0;
        end else begin
            reg_we <= 0;
            case (state)
                IDLE: begin
                    if (s_axi_awvalid && s_axi_wvalid) begin
                        s_axi_awready <= 1; s_axi_wready <= 1;
                        reg_addr <= s_axi_awaddr; reg_wdata <= s_axi_wdata; reg_we <= 1;
                        state <= WRITE;
                    end else if (s_axi_arvalid) begin
                        s_axi_arready <= 1; reg_addr <= s_axi_araddr; state <= READ;
                    end
                end
                WRITE: begin
                    s_axi_awready <= 0; s_axi_wready <= 0;
                    s_axi_bresp <= 0; s_axi_bvalid <= 1;
                    if (s_axi_bready) begin s_axi_bvalid <= 0; state <= IDLE; end
                end
                READ: begin
                    s_axi_arready <= 0;
                    s_axi_rdata <= reg_rdata; s_axi_rresp <= 0; s_axi_rvalid <= 1;
                    if (s_axi_rready) begin s_axi_rvalid <= 0; state <= IDLE; end
                end
            endcase
        end
    end
endmodule
