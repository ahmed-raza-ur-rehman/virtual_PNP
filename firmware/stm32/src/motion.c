#include "pnp.h"
#include <math.h>

static Pose cur = {0,0,80,0};
static Pose tgt = {0,0,80,0};
static float v[4] = {0,0,0,0};

void pnp_init(void) { /* init timers, PWM, encoders */ }
void pnp_home(void) { cur.x=cur.y=cur.z=0; cur.z=80; cur.r=0; }
void pnp_move_to(Pose target) { tgt = target; }
void pnp_pick(void) { pnp_set_vacuum(1); }
void pnp_place(void) { pnp_set_vacuum(0); }
void pnp_set_vacuum(uint8_t on) { /* GPIO */ (void)on; }

void pnp_update(void) {
    const float dt = 0.001f;
    const float kp = 2.0f;
    // simple P control per axis
    float ex = tgt.x - cur.x;
    float ey = tgt.y - cur.y;
    float ez = tgt.z - cur.z;
    float er = tgt.r - cur.r;
    v[0] += ex * kp * dt;
    v[1] += ey * kp * dt;
    v[2] += ez * kp * dt;
    v[3] += er * kp * dt;
    // clamp
    for (int i=0;i<4;i++) if (v[i]>50) v[i]=50; if (v[i]<-50) v[i]=-50;
    cur.x += v[0]*dt; cur.y += v[1]*dt; cur.z += v[2]*dt; cur.r += v[3]*dt;
}
