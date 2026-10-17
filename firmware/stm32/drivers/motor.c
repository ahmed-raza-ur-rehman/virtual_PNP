#include "stm32_hal.h"
#include <math.h>

#define MOTOR_PWM_TIMER TIM1
#define MOTOR_DIR_PORT GPIOA
#define MOTOR_DIR_PIN  4
#define MOTOR_EN_PORT  GPIOA
#define MOTOR_EN_PIN   5

typedef struct {
    float kp;
    float ki;
    float kd;
    float integral;
    float prev_error;
    float output_limit;
    float integral_limit;
} PID_t;

typedef struct {
    float position;
    float velocity;
    float target_position;
    float target_velocity;
    float max_velocity;
    float max_acceleration;
    float max_jerk;
    uint8_t homed;
    uint8_t enabled;
    uint8_t fault;
    PID_t pos_pid;
    PID_t vel_pid;
    uint32_t encoder_count;
    float encoder_resolution;
} Motor_t;

static Motor_t motors[8];

void motor_init(uint8_t id, float encoder_res) {
    if (id >= 8) return;
    motors[id].position = 0.0f;
    motors[id].velocity = 0.0f;
    motors[id].target_position = 0.0f;
    motors[id].target_velocity = 0.0f;
    motors[id].max_velocity = 1000.0f;
    motors[id].max_acceleration = 5000.0f;
    motors[id].max_jerk = 50000.0f;
    motors[id].homed = 0;
    motors[id].enabled = 0;
    motors[id].fault = 0;
    motors[id].encoder_count = 0;
    motors[id].encoder_resolution = encoder_res;
    motors[id].pos_pid.kp = 10.0f;
    motors[id].pos_pid.ki = 0.5f;
    motors[id].pos_pid.kd = 1.0f;
    motors[id].pos_pid.integral = 0.0f;
    motors[id].pos_pid.prev_error = 0.0f;
    motors[id].pos_pid.output_limit = 1000.0f;
    motors[id].pos_pid.integral_limit = 100.0f;
    motors[id].vel_pid.kp = 5.0f;
    motors[id].vel_pid.ki = 0.1f;
    motors[id].vel_pid.kd = 0.5f;
    motors[id].vel_pid.integral = 0.0f;
    motors[id].vel_pid.prev_error = 0.0f;
    motors[id].vel_pid.output_limit = 500.0f;
    motors[id].vel_pid.integral_limit = 50.0f;
}

void motor_enable(uint8_t id) {
    if (id >= 8) return;
    motors[id].enabled = 1;
    hal_gpio_write(MOTOR_EN_PORT, MOTOR_EN_PIN, 1);
}

void motor_disable(uint8_t id) {
    if (id >= 8) return;
    motors[id].enabled = 0;
    hal_gpio_write(MOTOR_EN_PORT, MOTOR_EN_PIN, 0);
    hal_pwm_set(MOTOR_PWM_TIMER, id, 0);
}

void motor_set_target_position(uint8_t id, float pos) {
    if (id >= 8) return;
    motors[id].target_position = pos;
}

void motor_set_target_velocity(uint8_t id, float vel) {
    if (id >= 8) return;
    if (vel > motors[id].max_velocity) vel = motors[id].max_velocity;
    if (vel < -motors[id].max_velocity) vel = -motors[id].max_velocity;
    motors[id].target_velocity = vel;
}

float motor_pid_update(PID_t *pid, float setpoint, float measurement, float dt) {
    float error = setpoint - measurement;
    pid->integral += error * dt;
    if (pid->integral > pid->integral_limit) pid->integral = pid->integral_limit;
    if (pid->integral < -pid->integral_limit) pid->integral = -pid->integral_limit;
    float derivative = (error - pid->prev_error) / dt;
    pid->prev_error = error;
    float output = pid->kp * error + pid->ki * pid->integral + pid->kd * derivative;
    if (output > pid->output_limit) output = pid->output_limit;
    if (output < -pid->output_limit) output = -pid->output_limit;
    return output;
}

void motor_update(uint8_t id, float dt) {
    if (id >= 8 || !motors[id].enabled) return;
    // position control
    float pos_output = motor_pid_update(&motors[id].pos_pid, motors[id].target_position, motors[id].position, dt);
    // velocity control
    float vel_target = pos_output;
    if (vel_target > motors[id].max_velocity) vel_target = motors[id].max_velocity;
    if (vel_target < -motors[id].max_velocity) vel_target = -motors[id].max_velocity;
    float vel_output = motor_pid_update(&motors[id].vel_pid, vel_target, motors[id].velocity, dt);
    // apply to PWM
    uint16_t duty = (uint16_t)((vel_output / motors[id].max_velocity) * 1000.0f);
    if (duty > 1000) duty = 1000;
    hal_pwm_set(MOTOR_PWM_TIMER, id, duty);
    // direction
    if (vel_output >= 0) {
        hal_gpio_write(MOTOR_DIR_PORT, MOTOR_DIR_PIN, 1);
    } else {
        hal_gpio_write(MOTOR_DIR_PORT, MOTOR_DIR_PIN, 0);
    }
}

void motor_home(uint8_t id) {
    if (id >= 8) return;
    // move to home switch
    motor_set_target_velocity(id, -100.0f);
    motor_enable(id);
    // wait for home switch (simplified)
    // ...
    motors[id].position = 0.0f;
    motors[id].homed = 1;
    motor_disable(id);
}

float motor_get_position(uint8_t id) {
    if (id >= 8) return 0.0f;
    return motors[id].position;
}

float motor_get_velocity(uint8_t id) {
    if (id >= 8) return 0.0f;
    return motors[id].velocity;
}

void motor_set_max_velocity(uint8_t id, float v) {
    if (id >= 8) return;
    motors[id].max_velocity = v;
}

void motor_set_max_acceleration(uint8_t id, float a) {
    if (id >= 8) return;
    motors[id].max_acceleration = a;
}

void motor_reset(uint8_t id) {
    if (id >= 8) return;
    motors[id].pos_pid.integral = 0.0f;
    motors[id].pos_pid.prev_error = 0.0f;
    motors[id].vel_pid.integral = 0.0f;
    motors[id].vel_pid.prev_error = 0.0f;
    motors[id].position = 0.0f;
    motors[id].velocity = 0.0f;
}

uint8_t motor_is_homed(uint8_t id) {
    if (id >= 8) return 0;
    return motors[id].homed;
}

uint8_t motor_has_fault(uint8_t id) {
    if (id >= 8) return 0;
    return motors[id].fault;
}

void motor_clear_fault(uint8_t id) {
    if (id >= 8) return;
    motors[id].fault = 0;
}

void motor_emergency_stop(uint8_t id) {
    if (id >= 8) return;
    motor_disable(id);
    motors[id].target_velocity = 0.0f;
    motors[id].target_position = motors[id].position;
    motors[id].fault = 1;
}

void motor_update_encoder(uint8_t id, int32_t count) {
    if (id >= 8) return;
    motors[id].encoder_count = count;
    motors[id].position = count / motors[id].encoder_resolution;
}
