// ADC controller with sequencer
module adc_full #(
    parameter CHANNELS = 16,
    parameter RESOLUTION = 12
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    start,
    input  logic [3:0]              num_channels,
    input  logic [3:0]              channel_seq [0:15],
    output logic [RESOLUTION-1:0]    result [0:CHANNELS-1],
    output logic                    busy,
    output logic                    done,
    output logic                    overrun,
    // analog interface (digital model)
    input  logic [RESOLUTION-1:0]   analog_in [0:CHANNELS-1]
);
    logic [3:0] seq_idx;
    logic [3:0] current_ch;
    logic [31:0] conv_cnt;
    localparam CONV_TIME = 100;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 0;
            done <= 0;
            overrun <= 0;
            seq_idx <= 0;
            conv_cnt <= 0;
            for (int i = 0; i < CHANNELS; i++) result[i] <= 0;
        end else begin
            done <= 0;
            if (start && !busy) begin
                busy <= 1;
                seq_idx <= 0;
                conv_cnt <= 0;
                overrun <= 0;
            end else if (busy) begin
                if (conv_cnt < CONV_TIME - 1) begin
                    conv_cnt <= conv_cnt + 1;
                end else begin
                    conv_cnt <= 0;
                    current_ch = channel_seq[seq_idx];
                    result[current_ch] <= analog_in[current_ch];
                    if (seq_idx < num_channels - 1) begin
                        seq_idx <= seq_idx + 1;
                    end else begin
                        busy <= 0;
                        done <= 1;
                        seq_idx <= 0;
                    end
                end
            end
        end
    end
endmodule
