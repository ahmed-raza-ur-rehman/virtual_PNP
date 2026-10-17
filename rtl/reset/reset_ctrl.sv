// Reset controller
module reset_ctrl #(
    parameter NUM_RESETS = 4
)(
    input  logic        clk,
    input  logic        ext_rst_n,
    input  logic        por_n,
    input  logic [NUM_RESETS-1:0] rst_req,
    output logic [NUM_RESETS-1:0] rst_out_n,
    output logic        rst_done
);
    logic [3:0] rst_counter [0:NUM_RESETS-1];
    logic [NUM_RESETS-1:0] rst_state;

    always_ff @(posedge clk or negedge por_n) begin
        if (!por_n) begin
            for (int i = 0; i < NUM_RESETS; i++) begin
                rst_counter[i] <= 15;
                rst_out_n[i] <= 0;
            end
            rst_state <= 0;
            rst_done <= 0;
        end else begin
            rst_done <= 1;
            for (int i = 0; i < NUM_RESETS; i++) begin
                if (rst_req[i] || !ext_rst_n) begin
                    rst_counter[i] <= 15;
                    rst_out_n[i] <= 0;
                end else if (rst_counter[i] > 0) begin
                    rst_counter[i] <= rst_counter[i] - 1;
                    rst_out_n[i] <= 0;
                end else begin
                    rst_out_n[i] <= 1;
                end
            end
        end
    end
endmodule
