// USB Endpoint
module usb_ep #(
    parameter EP_NUM = 0,
    parameter EP_TYPE = 0, // 0 control, 1 iso, 2 bulk, 3 interrupt
    parameter MAX_PACKET = 64
)(
    input  logic        clk,
    input  logic        rst_n,
    input  logic        setup,
    input  logic        in_token,
    input  logic        out_token,
    input  logic [7:0]  data_in,
    input  logic        data_valid,
    output logic [7:0]  data_out,
    output logic        data_ready,
    output logic        stall,
    // buffer interface
    input  logic [7:0]  buf_data_in,
    input  logic        buf_wr,
    output logic [7:0]  buf_data_out,
    output logic        buf_rd,
    output logic [7:0]  buf_count
);
    logic [7:0] buffer [0:MAX_PACKET-1];
    logic [7:0] wr_ptr, rd_ptr, count;
    logic [1:0] state;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= 0; rd_ptr <= 0; count <= 0; state <= 0; stall <= 0; data_ready <= 0;
        end else begin
            if (buf_wr && count < MAX_PACKET) begin
                buffer[wr_ptr] <= buf_data_in;
                wr_ptr <= wr_ptr + 1;
                count <= count + 1;
            end
            if (in_token && count > 0) begin
                data_out <= buffer[rd_ptr];
                rd_ptr <= rd_ptr + 1;
                count <= count - 1;
                data_ready <= 1;
            end else begin
                data_ready <= 0;
            end
            if (setup) begin
                // reset endpoint
                wr_ptr <= 0; rd_ptr <= 0; count <= 0;
            end
        end
    end

    assign buf_data_out = (rd_ptr < MAX_PACKET) ? buffer[rd_ptr] : 8'h00;
    assign buf_rd = (count > 0);
    assign buf_count = count;
endmodule
