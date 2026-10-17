#include "stm32_hal.h"
#include <math.h>

#define VISION_UART USART1
#define VISION_CAM_WIDTH 640
#define VISION_CAM_HEIGHT 480

typedef struct {
    int16_t x;
    int16_t y;
    uint16_t w;
    uint16_t h;
    float angle;
    float confidence;
    uint8_t valid;
} VisionObject_t;

typedef struct {
    uint8_t initialized;
    uint8_t frame_ready;
    uint32_t frame_count;
    VisionObject_t objects[16];
    uint8_t num_objects;
    uint8_t processing;
    float exposure;
    float gain;
} Vision_t;

static Vision_t vision;

void vision_init(void) {
    vision.initialized = 0;
    vision.frame_ready = 0;
    vision.frame_count = 0;
    vision.num_objects = 0;
    vision.processing = 0;
    vision.exposure = 50.0f;
    vision.gain = 1.0f;
    hal_uart_init(VISION_UART, 115200);
    vision.initialized = 1;
}

void vision_capture_frame(void) {
    vision.frame_ready = 0;
    vision.processing = 1;
    // trigger camera capture via UART command
    hal_uart_send(VISION_UART, 0x01);
    vision.frame_count++;
}

uint8_t vision_is_frame_ready(void) {
    return vision.frame_ready;
}

void vision_process_frame(void) {
    if (!vision.frame_ready) return;
    vision.processing = 1;
    // parse UART response for detected objects
    // simplified: read 16 objects
    vision.num_objects = 0;
    // ...
    vision.processing = 0;
}

uint8_t vision_get_objects(VisionObject_t *out, uint8_t max_count) {
    uint8_t n = vision.num_objects;
    if (n > max_count) n = max_count;
    for (uint8_t i = 0; i < n; i++) {
        out[i] = vision.objects[i];
    }
    return n;
}

void vision_set_exposure(float exp) {
    vision.exposure = exp;
    // send to camera
    uint8_t cmd[4] = {0x02, (uint8_t)(exp), 0, 0};
    hal_uart_send(VISION_UART, cmd[0]);
}

void vision_set_gain(float gain) {
    vision.gain = gain;
    hal_uart_send(VISION_UART, 0x03);
}

float vision_compute_orientation(uint8_t *image, uint16_t w, uint16_t h) {
    // simplified: compute angle via moments
    float m00 = 0, m10 = 0, m01 = 0;
    for (uint16_t y = 0; y < h; y++) {
        for (uint16_t x = 0; x < w; x++) {
            if (image[y*w + x] > 128) {
                m00 += 1;
                m10 += x;
                m01 += y;
            }
        }
    }
    if (m00 == 0) return 0.0f;
    float cx = m10 / m00;
    float cy = m01 / m00;
    // compute orientation via central moments
    float mu11 = 0, mu20 = 0, mu02 = 0;
    for (uint16_t y = 0; y < h; y++) {
        for (uint16_t x = 0; x < w; x++) {
            if (image[y*w + x] > 128) {
                float dx = x - cx;
                float dy = y - cy;
                mu20 += dx*dx;
                mu02 += dy*dy;
                mu11 += dx*dy;
            }
        }
    }
    float angle = 0.5f * atan2f(2*mu11, mu20 - mu02);
    return angle * 180.0f / 3.14159265f;
}

uint8_t vision_detect_component(uint8_t *image, uint16_t w, uint16_t h, VisionObject_t *out) {
    // simple bounding box detection
    int16_t minx = w, maxx = 0, miny = h, maxy = 0;
    uint32_t count = 0;
    for (uint16_t y = 0; y < h; y++) {
        for (uint16_t x = 0; x < w; x++) {
            if (image[y*w + x] > 128) {
                count++;
                if (x < minx) minx = x;
                if (x > maxx) maxx = x;
                if (y < miny) miny = y;
                if (y > maxy) maxy = y;
            }
        }
    }
    if (count < 10) return 0;
    out->x = minx;
    out->y = miny;
    out->w = maxx - minx;
    out->h = maxy - miny;
    out->angle = 0.0f;
    out->confidence = 0.9f;
    out->valid = 1;
    return 1;
}

void vision_calibrate(void) {
    // send calibration command
    hal_uart_send(VISION_UART, 0x10);
}

uint8_t vision_is_initialized(void) {
    return vision.initialized;
}
