#include "pnp.h"
// Quadrature encoder with index
int32_t encoder_read(uint8_t axis) { (void)axis; return 0; }
void encoder_reset(uint8_t axis) { (void)axis; }
uint8_t encoder_index_seen(uint8_t axis) { (void)axis; return 0; }
