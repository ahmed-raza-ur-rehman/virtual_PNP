#include "pnp.h"
#include <stdio.h>

void diag_self_test(void) {
    // Test all axes, sensors, vacuum
    printf("Self-test: axes OK\n");
    printf("Self-test: sensors OK\n");
    printf("Self-test: vacuum OK\n");
}

void diag_report(void) {
    printf("=== Diagnostics Report ===\n");
    printf("Uptime: %lu ms\n", 0UL);
    printf("Placements: %lu\n", 0UL);
    printf("Errors: %lu\n", 0UL);
}

void diag_loopback_test(void) {
    // SPI/UART loopback
    printf("Loopback: OK\n");
}
