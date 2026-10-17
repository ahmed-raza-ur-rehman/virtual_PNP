// Real-Time Clock
module rtc #(
    parameter CLK_FREQ = 32768
)(
    input  logic        clk,
    input  logic        rst_n,
    input  logic        set_en,
    input  logic [5:0]  set_sec,
    input  logic [5:0]  set_min,
    input  logic [4:0]  set_hour,
    input  logic [4:0]  set_day,
    input  logic [3:0]  set_month,
    input  logic [11:0] set_year,
    input  logic        alarm_en,
    input  logic [5:0]  alarm_sec,
    input  logic [5:0]  alarm_min,
    input  logic [4:0]  alarm_hour,
    output logic [5:0]  sec,
    output logic [5:0]  min,
    output logic [4:0]  hour,
    output logic [4:0]  day,
    output logic [3:0]  month,
    output logic [11:0] year,
    output logic        alarm_flag
);
    logic [15:0] prescaler;
    logic tick;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            prescaler <= 0;
            tick <= 0;
        end else begin
            if (prescaler >= CLK_FREQ - 1) begin
                prescaler <= 0;
                tick <= 1;
            end else begin
                prescaler <= prescaler + 1;
                tick <= 0;
            end
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sec <= 0; min <= 0; hour <= 0; day <= 1; month <= 1; year <= 2026;
        end else if (set_en) begin
            sec <= set_sec; min <= set_min; hour <= set_hour; day <= set_day; month <= set_month; year <= set_year;
        end else if (tick) begin
            if (sec == 59) begin
                sec <= 0;
                if (min == 59) begin
                    min <= 0;
                    if (hour == 23) begin
                        hour <= 0;
                        // day/month/year increment simplified
                        day <= day + 1;
                    end else hour <= hour + 1;
                end else min <= min + 1;
            end else sec <= sec + 1;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) alarm_flag <= 0;
        else if (alarm_en && tick && sec == alarm_sec && min == alarm_min && hour == alarm_hour)
            alarm_flag <= 1;
        else if (!alarm_en)
            alarm_flag <= 0;
    end
endmodule
