#include "pnp.h"
// Camera trigger and frame capture
void vision_trigger(void) {}
uint8_t vision_frame_ready(void) { return 0; }
void vision_get_result(float *x, float *y, float *angle) { *x=0;*y=0;*angle=0; }
