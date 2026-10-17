#include "pnp.h"
#include <math.h>

// Backlash measurement
float calib_backlash(uint8_t axis) {
    // move forward, then backward, measure difference
    (void)axis;
    return 0.05f;
}

// Squareness measurement
float calib_squareness(void) {
    return 0.02f;
}

// Scale calibration
float calib_scale(uint8_t axis) {
    (void)axis;
    return 1.0f;
}

void calib_save_to_flash(void) {
    // persist calibration to flash
}

void calib_load_from_flash(void) {
    // load calibration from flash
}
