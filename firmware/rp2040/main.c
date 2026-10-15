#include <stdio.h>
#include "pico/stdlib.h"
int main() {
    stdio_init_all();
    printf("RP2040 PnP controller\n");
    while (1) { sleep_ms(100); }
}
