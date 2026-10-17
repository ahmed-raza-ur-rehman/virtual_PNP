#include "stm32_hal.h"

#define ENC_TIMER TIM2
#define ENC_PPR 1000

typedef struct {
    int32_t count;
    int32_t prev_count;
    float position;
    float velocity;
    float acceleration;
    uint8_t direction;
    uint8_t index_found;
    uint32_t last_time;
    float filter_alpha;
} Encoder_t;

static Encoder_t encoders[4];

void encoder_init(uint8_t id) {
    if (id >= 4) return;
    encoders[id].count = 0;
    encoders[id].prev_count = 0;
    encoders[id].position = 0.0f;
    encoders[id].velocity = 0.0f;
    encoders[id].acceleration = 0.0f;
    encoders[id].direction = 0;
    encoders[id].index_found = 0;
    encoders[id].last_time = hal_get_tick();
    encoders[id].filter_alpha = 0.1f;
    // configure timer as encoder mode
    hal_timer_init(ENC_TIMER, 0, 0xFFFFFFFF);
}

void encoder_update(uint8_t id, uint32_t dt_us) {
    if (id >= 4) return;
    int32_t delta = encoders[id].count - encoders[id].prev_count;
    encoders[id].prev_count = encoders[id].count;
    encoders[id].direction = (delta >= 0) ? 1 : 0;
    float pos_delta = (float)delta / ENC_PPR;
    encoders[id].position += pos_delta;
    float vel = pos_delta / (dt_us / 1e6f + 1e-9f);
    encoders[id].velocity = encoders[id].filter_alpha * vel + (1 - encoders[id].filter_alpha) * encoders[id].velocity;
    encoders[id].acceleration = (encoders[id].velocity - (vel)) / (dt_us / 1e6f + 1e-9f);
}

int32_t encoder_get_count(uint8_t id) {
    if (id >= 4) return 0;
    return encoders[id].count;
}

float encoder_get_position(uint8_t id) {
    if (id >= 4) return 0.0f;
    return encoders[id].position;
}

float encoder_get_velocity(uint8_t id) {
    if (id >= 4) return 0.0f;
    return encoders[id].velocity;
}

void encoder_reset(uint8_t id) {
    if (id >= 4) return;
    encoders[id].count = 0;
    encoders[id].prev_count = 0;
    encoders[id].position = 0.0f;
    encoders[id].velocity = 0.0f;
    encoders[id].acceleration = 0.0f;
}

void encoder_set_count(uint8_t id, int32_t count) {
    if (id >= 4) return;
    encoders[id].count = count;
}

uint8_t encoder_get_direction(uint8_t id) {
    if (id >= 4) return 0;
    return encoders[id].direction;
}

void encoder_handle_interrupt(uint8_t id) {
    if (id >= 4) return;
    // read timer counter
    // encoders[id].count = TIM2->CNT;
}

float encoder_get_rpm(uint8_t id) {
    if (id >= 4) return 0.0f;
    return encoders[id].velocity * 60.0f;
}
