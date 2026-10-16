#include "pnp.h"
// Stepper/servo motor driver with microstepping
void motor_init(uint8_t axis) { (void)axis; }
void motor_set_velocity(uint8_t axis, float v) { (void)axis; (void)v; }
void motor_enable(uint8_t axis, uint8_t en) { (void)axis; (void)en; }
void motor_emergency_stop(void) { /* disable all drivers */ }
