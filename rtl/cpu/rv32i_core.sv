// Minimal RV32I single-cycle core (educational)
module rv32i_core (
    input  wire        clk,
    input  wire        rst_n,
    output wire [31:0] pc,
    input  wire [31:0] instr,
    output wire        mem_we,
    output wire [31:0] mem_addr,
    output wire [31:0] mem_wdata,
    input  wire [31:0] mem_rdata
);
    reg [31:0] pc_r;
    assign pc = pc_r;
    // decode
    wire [6:0] opcode = instr[6:0];
    wire [4:0] rd = instr[11:7];
    wire [4:0] rs1 = instr[19:15];
    wire [4:0] rs2 = instr[24:20];
    // register file
    reg [31:0] rf [0:31];
    // immediate
    wire [31:0] imm_i = {{20{instr[31]}}, instr[31:20]};
    // ALU
    reg [31:0] alu_out;
    always @(*) begin
        case (opcode)
            7'b0010011: alu_out = rf[rs1] + imm_i; // ADDI
            7'b0110011: alu_out = rf[rs1] + rf[rs2]; // ADD
            default: alu_out = rf[rs1] + imm_i;
        endcase
    end
    assign mem_we = (opcode == 7'b0100011);
    assign mem_addr = rf[rs1] + imm_i;
    assign mem_wdata = rf[rs2];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) pc_r <= 0;
        else begin
            if (rd != 0 && opcode != 7'b0100011 && opcode != 7'b1100011)
                rf[rd] <= (opcode == 7'b0000011) ? mem_rdata : alu_out;
            pc_r <= pc_r + 4;
        end
    end
endmodule
