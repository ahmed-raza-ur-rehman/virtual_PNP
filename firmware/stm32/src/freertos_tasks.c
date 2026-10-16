#include "pnp.h"
#include "FreeRTOS.h"
#include "task.h"

static void vMotionTask(void *pv) {
    (void)pv;
    for (;;) {
        pnp_update();
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

static void vSafetyTask(void *pv) {
    (void)pv;
    for (;;) {
        // watchdog, limit switches, current sensing
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

static void vCommsTask(void *pv) {
    (void)pv;
    for (;;) {
        // SPI to FPGA, UART to host
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

void pnp_start_rtos(void) {
    xTaskCreate(vMotionTask, "motion", 256, NULL, 3, NULL);
    xTaskCreate(vSafetyTask, "safety", 256, NULL, 4, NULL);
    xTaskCreate(vCommsTask, "comms", 256, NULL, 2, NULL);
    vTaskStartScheduler();
}
