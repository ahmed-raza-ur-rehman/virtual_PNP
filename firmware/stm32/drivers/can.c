#include "pnp.h"
void can_init(void) {}
void can_send(uint32_t id, const uint8_t *data, uint8_t len) { (void)id; (void)data; (void)len; }
uint8_t can_receive(uint32_t *id, uint8_t *data, uint8_t *len) { return 0; }
