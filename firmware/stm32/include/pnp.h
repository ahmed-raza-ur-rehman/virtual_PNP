#ifndef PNP_H
#define PNP_H
#include <stdint.h>

typedef struct { float x, y, z, r; } Pose;

void pnp_init(void);
void pnp_home(void);
void pnp_move_to(Pose target);
void pnp_pick(void);
void pnp_place(void);
void pnp_set_vacuum(uint8_t on);
void pnp_update(void);  // call in main loop

#endif
