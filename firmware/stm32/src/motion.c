#include "stm32_hal.h"
#include <math.h>

#define MAX_AXES 8
#define TRAJECTORY_BUFFER_SIZE 256

typedef struct {
    float position;
    float velocity;
    float acceleration;
    float target;
    float max_vel;
    float max_acc;
    float max_jerk;
    uint8_t state; // 0 idle, 1 moving, 2 homing, 3 error
} Axis_t;

typedef struct {
    float positions[MAX_AXES];
    float velocities[MAX_AXES];
    uint32_t timestamp;
    uint8_t valid;
} TrajectoryPoint_t;

static Axis_t axes[MAX_AXES];
static TrajectoryPoint_t traj_buffer[TRAJECTORY_BUFFER_SIZE];
static uint16_t traj_head = 0;
static uint16_t traj_tail = 0;
static uint8_t traj_count = 0;

void motion_init(void) {
    for (int i = 0; i < MAX_AXES; i++) {
        axes[i].position = 0.0f;
        axes[i].velocity = 0.0f;
        axes[i].acceleration = 0.0f;
        axes[i].target = 0.0f;
        axes[i].max_vel = 100.0f;
        axes[i].max_acc = 500.0f;
        axes[i].max_jerk = 5000.0f;
        axes[i].state = 0;
    }
    traj_head = 0;
    traj_tail = 0;
    traj_count = 0;
}

void motion_set_target(uint8_t axis, float target) {
    if (axis >= MAX_AXES) return;
    axes[axis].target = target;
    axes[axis].state = 1;
}

void motion_update(float dt) {
    for (int i = 0; i < MAX_AXES; i++) {
        if (axes[i].state != 1) continue;
        float error = axes[i].target - axes[i].position;
        float dir = (error > 0) ? 1.0f : -1.0f;
        float dist = fabsf(error);
        // trapezoidal velocity profile
        float v_max = axes[i].max_vel;
        float a_max = axes[i].max_acc;
        float t_acc = v_max / a_max;
        float d_acc = 0.5f * a_max * t_acc * t_acc;
        float vel;
        if (dist < 2 * d_acc) {
            // triangular
            float v_peak = sqrtf(a_max * dist);
            if (axes[i].velocity < v_peak) {
                axes[i].velocity += a_max * dt;
                if (axes[i].velocity > v_peak) axes[i].velocity = v_peak;
            } else {
                axes[i].velocity -= a_max * dt;
                if (axes[i].velocity < 0) axes[i].velocity = 0;
            }
        } else {
            if (axes[i].velocity < v_max) {
                axes[i].velocity += a_max * dt;
                if (axes[i].velocity > v_max) axes[i].velocity = v_max;
            }
            // check deceleration
            float remaining = dist - (axes[i].velocity * dt);
            float dec_dist = axes[i].velocity * axes[i].velocity / (2 * a_max);
            if (remaining <= dec_dist) {
                axes[i].velocity -= a_max * dt;
                if (axes[i].velocity < 0) axes[i].velocity = 0;
            }
        }
        axes[i].velocity *= dir;
        axes[i].position += axes[i].velocity * dt;
        // check arrival
        if (fabsf(axes[i].position - axes[i].target) < 0.01f && fabsf(axes[i].velocity) < 0.1f) {
            axes[i].position = axes[i].target;
            axes[i].velocity = 0.0f;
            axes[i].state = 0;
        }
    }
}

uint8_t motion_is_moving(uint8_t axis) {
    if (axis >= MAX_AXES) return 0;
    return axes[axis].state == 1;
}

float motion_get_position(uint8_t axis) {
    if (axis >= MAX_AXES) return 0.0f;
    return axes[axis].position;
}

void motion_home(uint8_t axis) {
    if (axis >= MAX_AXES) return;
    axes[axis].state = 2; // homing
    // move to home switch
    axes[axis].target = -1000.0f;
    axes[axis].state = 1;
}

void motion_stop(uint8_t axis) {
    if (axis >= MAX_AXES) return;
    axes[axis].velocity = 0.0f;
    axes[axis].target = axes[axis].position;
    axes[axis].state = 0;
}

void motion_emergency_stop(void) {
    for (int i = 0; i < MAX_AXES; i++) {
        axes[i].velocity = 0.0f;
        axes[i].target = axes[i].position;
        axes[i].state = 3; // error
    }
}

void motion_reset(void) {
    for (int i = 0; i < MAX_AXES; i++) {
        axes[i].position = 0.0f;
        axes[i].velocity = 0.0f;
        axes[i].acceleration = 0.0f;
        axes[i].state = 0;
    }
}

uint8_t motion_add_trajectory_point(TrajectoryPoint_t *pt) {
    if (traj_count >= TRAJECTORY_BUFFER_SIZE) return 0;
    traj_buffer[traj_head] = *pt;
    traj_head = (traj_head + 1) % TRAJECTORY_BUFFER_SIZE;
    traj_count++;
    return 1;
}

uint8_t motion_get_trajectory_point(TrajectoryPoint_t *pt) {
    if (traj_count == 0) return 0;
    *pt = traj_buffer[traj_tail];
    traj_tail = (traj_tail + 1) % TRAJECTORY_BUFFER_SIZE;
    traj_count--;
    return 1;
}
