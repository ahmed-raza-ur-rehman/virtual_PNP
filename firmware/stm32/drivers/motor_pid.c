#include "pnp.h"
#include <math.h>

typedef struct { float kp, ki, kd; float integral, prev_err; } PID;

float pid_update(PID *p, float setpoint, float measured, float dt) {
    float err = setpoint - measured;
    p->integral += err * dt;
    if (p->integral > 100) p->integral = 100;
    if (p->integral < -100) p->integral = -100;
    float deriv = (err - p->prev_err) / dt;
    p->prev_err = err;
    return p->kp * err + p->ki * p->integral + p->kd * deriv;
}

void motor_pid_control(uint8_t axis, float target, float measured) {
    static PID pid[4] = {{1.0f,0.1f,0.05f,0,0}};
    float out = pid_update(&pid[axis], target, measured, 0.001f);
    motor_set_velocity(axis, out);
}
