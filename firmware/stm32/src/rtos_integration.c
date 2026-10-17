#include "pnp.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

static QueueHandle_t cmd_queue;
static SemaphoreHandle_t motion_mutex;

void rtos_init(void) {
    cmd_queue = xQueueCreate(16, sizeof(uint32_t));
    motion_mutex = xSemaphoreCreateMutex();
}

void vMotionTask(void *pv) {
    (void)pv;
    for (;;) {
        uint32_t cmd;
        if (xQueueReceive(cmd_queue, &cmd, pdMS_TO_TICKS(1)) == pdTRUE) {
            xSemaphoreTake(motion_mutex, portMAX_DELAY);
            pnp_update();
            xSemaphoreGive(motion_mutex);
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

void vSafetyTask(void *pv) {
    (void)pv;
    for (;;) {
        // watchdog, limits
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void vVisionTask(void *pv) {
    (void)pv;
    for (;;) {
        // process vision
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

void vCommsTask(void *pv) {
    (void)pv;
    for (;;) {
        // SPI/UART
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

void rtos_start(void) {
    rtos_init();
    xTaskCreate(vMotionTask, "motion", 512, NULL, 4, NULL);
    xTaskCreate(vSafetyTask, "safety", 256, NULL, 5, NULL);
    xTaskCreate(vVisionTask, "vision", 512, NULL, 3, NULL);
    xTaskCreate(vCommsTask, "comms", 256, NULL, 2, NULL);
    vTaskStartScheduler();
}
