#include "stm32_hal.h"

#define CAN_MAX_FILTERS 14
#define CAN_TX_MAILBOXES 3
#define CAN_RX_FIFOS 2

typedef struct {
    uint32_t id;
    uint8_t dlc;
    uint8_t data[8];
    uint8_t extended;
    uint8_t rtr;
    uint32_t timestamp;
} CAN_Frame_t;

typedef struct {
    CAN_Frame_t tx_mailbox[CAN_TX_MAILBOXES];
    uint8_t tx_head;
    uint8_t tx_tail;
    CAN_Frame_t rx_fifo[CAN_RX_FIFOS][8];
    uint8_t rx_head[CAN_RX_FIFOS];
    uint8_t rx_tail[CAN_RX_FIFOS];
    uint32_t filters[CAN_MAX_FILTERS][2];
    uint8_t num_filters;
    uint8_t mode; // 0 normal, 1 loopback, 2 silent
    uint32_t error_count;
    uint8_t state; // 0 active, 1 passive, 2 bus_off
    uint32_t bitrate;
} CAN_t;

static CAN_t can;

void can_init(uint32_t bitrate) {
    can.bitrate = bitrate;
    can.tx_head = 0;
    can.tx_tail = 0;
    can.num_filters = 0;
    can.mode = 0;
    can.error_count = 0;
    can.state = 0;
    for (int i = 0; i < CAN_RX_FIFOS; i++) {
        can.rx_head[i] = 0;
        can.rx_tail[i] = 0;
    }
}

uint8_t can_add_filter(uint32_t mask, uint32_t id) {
    if (can.num_filters >= CAN_MAX_FILTERS) return 0;
    can.filters[can.num_filters][0] = mask;
    can.filters[can.num_filters][1] = id;
    can.num_filters++;
    return 1;
}

uint8_t can_transmit(CAN_Frame_t *frame) {
    if (can.state == 2) return 0; // bus off
    uint8_t mb = can.tx_head;
    can.tx_mailbox[mb] = *frame;
    can.tx_head = (can.tx_head + 1) % CAN_TX_MAILBOXES;
    if (can.mode == 1) {
        // loopback: inject into rx fifo 0
        can.rx_fifo[0][can.rx_head[0]] = *frame;
        can.rx_head[0] = (can.rx_head[0] + 1) % 8;
    }
    return 1;
}

uint8_t can_receive(uint8_t fifo, CAN_Frame_t *frame) {
    if (fifo >= CAN_RX_FIFOS) return 0;
    if (can.rx_head[fifo] == can.rx_tail[fifo]) return 0; // empty
    *frame = can.rx_fifo[fifo][can.rx_tail[fifo]];
    can.rx_tail[fifo] = (can.rx_tail[fifo] + 1) % 8;
    return 1;
}

uint8_t can_rx_available(uint8_t fifo) {
    if (fifo >= CAN_RX_FIFOS) return 0;
    return can.rx_head[fifo] != can.rx_tail[fifo];
}

void can_set_mode(uint8_t mode) {
    can.mode = mode;
}

void can_handle_rx_interrupt(uint8_t fifo) {
    // called from ISR
}

void can_error_handler(void) {
    can.error_count++;
    if (can.error_count > 255) {
        can.state = 2; // bus off
    } else if (can.error_count > 127) {
        can.state = 1; // error passive
    }
}

void can_recover(void) {
    can.error_count = 0;
    can.state = 0;
}

uint8_t can_get_state(void) {
    return can.state;
}

uint32_t can_get_error_count(void) {
    return can.error_count;
}

void can_set_bitrate(uint32_t bitrate) {
    can.bitrate = bitrate;
}
