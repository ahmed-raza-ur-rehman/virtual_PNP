#include "pnp.h"
#include <stdio.h>

int main(void) {
    pnp_init();
    pnp_home();
    Pose t = {10.0f, 20.0f, 5.0f, 0.0f};
    pnp_move_to(t);
    pnp_pick();
    t.x = 50.0f; t.z = 1.0f;
    pnp_move_to(t);
    pnp_place();
    while (1) {
        pnp_update();
    }
    return 0;
}
