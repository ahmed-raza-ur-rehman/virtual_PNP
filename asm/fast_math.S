# x86-64 fast math routines
.text
.globl fast_hypot
.type fast_hypot, @function
fast_hypot:
    # args: xmm0 = dx, xmm1 = dy
    mulsd %xmm0, %xmm0
    mulsd %xmm1, %xmm1
    addsd %xmm1, %xmm0
    sqrtsd %xmm0, %xmm0
    ret

.globl fast_dot
.type fast_dot, @function
fast_dot:
    # rdi = n, rsi = a, rdx = b -> xmm0
    xorpd %xmm0, %xmm0
    testq %rdi, %rdi
    jz .Ldone
.Lloop:
    movsd (%rsi), %xmm1
    mulsd (%rdx), %xmm1
    addsd %xmm1, %xmm0
    addq $8, %rsi
    addq $8, %rdx
    decq %rdi
    jnz .Lloop
.Ldone:
    ret

.section .note.GNU-stack,"",@progbits
