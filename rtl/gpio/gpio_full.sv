// Full GPIO with interrupt support
module gpio_full #(
    parameter WIDTH = 16
)(
    input  logic            clk,
    input  logic            rst_n,
    input  logic [WIDTH-1:0] pin_in,
    output logic [WIDTH-1:0] pin_out,
    output logic [WIDTH-1:0] pin_oe,
    // Register interface
    input  logic [WIDTH-1:0] moder,
    input  logic [WIDTH-1:0] otyper,
    input  logic [WIDTH-1:0] ospeedr,
    input  logic [WIDTH-1:0] pupdr,
    input  logic [WIDTH-1:0] odr_in,
    input  logic [WIDTH-1:0] bsrr,
    input  logic [WIDTH-1:0] lckr,
    output logic [WIDTH-1:0] idr,
    output logic [WIDTH-1:0] odr_out,
    // Interrupt
    input  logic [WIDTH-1:0] exti_rtsr, // rising trigger
    input  logic [WIDTH-1:0] exti_ftsr, // falling trigger
    input  logic [WIDTH-1:0] exti_imr,  // interrupt mask
    output logic [WIDTH-1:0] exti_pr,   // pending
    output logic            irq
);
    logic [WIDTH-1:0] pin_sync1, pin_sync2, pin_prev;
    logic [WIDTH-1:0] odr_reg;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pin_sync1 <= 0;
            pin_sync2 <= 0;
            pin_prev <= 0;
            odr_reg <= 0;
            exti_pr <= 0;
        end else begin
            pin_sync1 <= pin_in;
            pin_sync2 <= pin_sync1;
            pin_prev <= pin_sync2;
            // BSRR handling
            for (int i = 0; i < WIDTH; i++) begin
                if (bsrr[i]) odr_reg[i] <= 1;
                if (bsrr[WIDTH + i]) odr_reg[i] <= 0;
            end
            odr_reg <= odr_in | odr_reg;
            // EXTI pending
            for (int i = 0; i < WIDTH; i++) begin
                logic rising = pin_sync2[i] && !pin_prev[i];
                logic falling = !pin_sync2[i] && pin_prev[i];
                if ((rising && exti_rtsr[i]) || (falling && exti_ftsr[i])) begin
                    exti_pr[i] <= 1;
                end
            end
        end
    end

    // output driver
    always_comb begin
        for (int i = 0; i < WIDTH; i++) begin
            if (moder[2*i+1:2*i] == 2'b01) begin
                // output mode
                pin_oe[i] = 1;
                if (otyper[i]) begin
                    // open drain
                    pin_out[i] = odr_reg[i] ? 1'bz : 1'b0;
                end else begin
                    pin_out[i] = odr_reg[i];
                end
            end else begin
                pin_oe[i] = 0;
                pin_out[i] = 1'bz;
            end
        end
    end

    assign idr = pin_sync2;
    assign odr_out = odr_reg;
    assign irq = |(exti_pr & exti_imr);
endmodule
