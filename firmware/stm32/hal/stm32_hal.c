#include "stm32_hal.h"

// GPIO
void HAL_GPIO_Init(uint32_t port, uint32_t pin, uint32_t mode) { (void)port; (void)pin; (void)mode; }
void HAL_GPIO_WritePin(uint32_t port, uint32_t pin, uint32_t state) { (void)port; (void)pin; (void)state; }
uint32_t HAL_GPIO_ReadPin(uint32_t port, uint32_t pin) { (void)port; (void)pin; return 0; }
void HAL_GPIO_TogglePin(uint32_t port, uint32_t pin) { (void)port; (void)pin; }

// Timer
void HAL_TIM_Init(uint32_t timer, uint32_t prescaler, uint32_t period) { (void)timer; (void)prescaler; (void)period; }
void HAL_TIM_Start(uint32_t timer) { (void)timer; }
void HAL_TIM_Stop(uint32_t timer) { (void)timer; }
uint32_t HAL_TIM_GetCounter(uint32_t timer) { (void)timer; return 0; }

// UART
void HAL_UART_Init(uint32_t uart, uint32_t baudrate) { (void)uart; (void)baudrate; }
void HAL_UART_Transmit(uint32_t uart, const uint8_t *data, uint16_t len) { (void)uart; (void)data; (void)len; }
uint16_t HAL_UART_Receive(uint32_t uart, uint8_t *data, uint16_t maxlen, uint32_t timeout) { (void)uart; (void)data; (void)maxlen; (void)timeout; return 0; }

// SPI
void HAL_SPI_Init(uint32_t spi, uint32_t mode) { (void)spi; (void)mode; }
uint8_t HAL_SPI_TransmitReceive(uint32_t spi, uint8_t data) { (void)spi; (void)data; return 0; }

// I2C
void HAL_I2C_Init(uint32_t i2c, uint32_t speed) { (void)i2c; (void)speed; }
HAL_StatusTypeDef HAL_I2C_Master_Transmit(uint32_t i2c, uint16_t addr, const uint8_t *data, uint16_t len, uint32_t timeout) { (void)i2c; (void)addr; (void)data; (void)len; (void)timeout; return HAL_OK; }
HAL_StatusTypeDef HAL_I2C_Master_Receive(uint32_t i2c, uint16_t addr, uint8_t *data, uint16_t len, uint32_t timeout) { (void)i2c; (void)addr; (void)data; (void)len; (void)timeout; return HAL_OK; }

// ADC
void HAL_ADC_Init(uint32_t adc) { (void)adc; }
uint16_t HAL_ADC_Read(uint32_t adc, uint8_t channel) { (void)adc; (void)channel; return 0; }

// DAC
void HAL_DAC_Init(uint32_t dac) { (void)dac; }
void HAL_DAC_Write(uint32_t dac, uint8_t channel, uint16_t value) { (void)dac; (void)channel; (void)value; }

// DMA
void HAL_DMA_Init(uint32_t dma, uint32_t channel, uint32_t src, uint32_t dst, uint32_t len) { (void)dma; (void)channel; (void)src; (void)dst; (void)len; }
void HAL_DMA_Start(uint32_t dma, uint32_t channel) { (void)dma; (void)channel; }
uint8_t HAL_DMA_Complete(uint32_t dma, uint32_t channel) { (void)dma; (void)channel; return 1; }

// NVIC
void HAL_NVIC_SetPriority(uint32_t irq, uint32_t priority) { (void)irq; (void)priority; }
void HAL_NVIC_EnableIRQ(uint32_t irq) { (void)irq; }
void HAL_NVIC_DisableIRQ(uint32_t irq) { (void)irq; }

// System
void HAL_Init(void) {}
void HAL_Delay(uint32_t ms) { (void)ms; }
uint32_t HAL_GetTick(void) { return 0; }
