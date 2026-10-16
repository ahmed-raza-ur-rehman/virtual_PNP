#include "pnp.h"
void eth_init(void) {}
void eth_send(const uint8_t *data, uint16_t len) { (void)data; (void)len; }
uint16_t eth_receive(uint8_t *buf, uint16_t maxlen) { return 0; }
