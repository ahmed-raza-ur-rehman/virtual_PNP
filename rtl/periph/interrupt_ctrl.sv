// Interrupt controller (NVIC-like)
module interrupt_ctrl #(
    parameter NUM_IRQS = 32
)(
    input  logic            clk,
    input  logic            rst_n,
    input  logic [NUM_IRQS-1:0] irq_in,
    input  logic [7:0]      priority [0:NUM_IRQS-1],
    input  logic [NUM_IRQS-1:0] enable,
    input  logic            ack,
    output logic [NUM_IRQS-1:0] pending,
    output logic [5:0]      active_irq,
    output logic            irq_out,
    output logic            irq_valid
);
    logic [NUM_IRQS-1:0] pending_r;
    logic [5:0] best_irq;
    logic found;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pending_r <= 0;
            best_irq <= 0;
            irq_valid <= 0;
        end else begin
            // set pending
            pending_r <= pending_r | (irq_in & enable);
            // acknowledge
            if (ack && irq_valid) begin
                pending_r[best_irq] <= 0;
            end
            // find highest priority pending
            found = 0;
            best_irq = 0;
            for (int i = 0; i < NUM_IRQS; i++) begin
                if (pending_r[i] && enable[i]) begin
                    if (!found || priority[i] < priority[best_irq]) begin
                        best_irq = i;
                        found = 1;
                    end
                end
            end
            if (found) begin
                active_irq <= best_irq;
                irq_valid <= 1;
                irq_out <= 1;
            end else begin
                irq_valid <= 0;
                irq_out <= 0;
            end
        end
    end

    assign pending = pending_r;
endmodule
