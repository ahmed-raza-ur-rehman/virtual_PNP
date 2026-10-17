/* STM32 HAL Header - comprehensive */
#ifndef STM32_HAL_H
#define STM32_HAL_H

#include <stdint.h>
#include <stdbool.h>

/* Base addresses */
#define PERIPH_BASE       0x40000000U
#define APB1_BASE         (PERIPH_BASE + 0x00000000U)
#define APB2_BASE         (PERIPH_BASE + 0x00010000U)
#define AHB1_BASE         (PERIPH_BASE + 0x00020000U)
#define AHB2_BASE         (PERIPH_BASE + 0x10000000U)

/* GPIO */
#define GPIOA_BASE        (AHB1_BASE + 0x0000U)
#define GPIOB_BASE        (AHB1_BASE + 0x0400U)
#define GPIOC_BASE        (AHB1_BASE + 0x0800U)
#define GPIOD_BASE        (AHB1_BASE + 0x0C00U)
#define GPIOE_BASE        (AHB1_BASE + 0x1000U)

typedef struct {
    volatile uint32_t MODER;
    volatile uint32_t OTYPER;
    volatile uint32_t OSPEEDR;
    volatile uint32_t PUPDR;
    volatile uint32_t IDR;
    volatile uint32_t ODR;
    volatile uint32_t BSRR;
    volatile uint32_t LCKR;
    volatile uint32_t AFR[2];
} GPIO_TypeDef;

#define GPIOA ((GPIO_TypeDef *) GPIOA_BASE)
#define GPIOB ((GPIO_TypeDef *) GPIOB_BASE)
#define GPIOC ((GPIO_TypeDef *) GPIOC_BASE)
#define GPIOD ((GPIO_TypeDef *) GPIOD_BASE)
#define GPIOE ((GPIO_TypeDef *) GPIOE_BASE)

/* RCC */
#define RCC_BASE          (AHB1_BASE + 0x3800U)
typedef struct {
    volatile uint32_t CR;
    volatile uint32_t PLLCFGR;
    volatile uint32_t CFGR;
    volatile uint32_t CIR;
    volatile uint32_t AHB1RSTR;
    volatile uint32_t AHB2RSTR;
    volatile uint32_t AHB3RSTR;
    volatile uint32_t APB1RSTR;
    volatile uint32_t APB2RSTR;
    volatile uint32_t AHB1ENR;
    volatile uint32_t AHB2ENR;
    volatile uint32_t AHB3ENR;
    volatile uint32_t APB1ENR;
    volatile uint32_t APB2ENR;
} RCC_TypeDef;
#define RCC ((RCC_TypeDef *) RCC_BASE)

/* TIM */
#define TIM1_BASE         (APB2_BASE + 0x0000U)
#define TIM2_BASE         (APB1_BASE + 0x0000U)
#define TIM3_BASE         (APB1_BASE + 0x0400U)
#define TIM4_BASE         (APB1_BASE + 0x0800U)
#define TIM5_BASE         (APB1_BASE + 0x0C00U)

typedef struct {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t SMCR;
    volatile uint32_t DIER;
    volatile uint32_t SR;
    volatile uint32_t EGR;
    volatile uint32_t CCMR1;
    volatile uint32_t CCMR2;
    volatile uint32_t CCER;
    volatile uint32_t CNT;
    volatile uint32_t PSC;
    volatile uint32_t ARR;
    volatile uint32_t RCR;
    volatile uint32_t CCR1;
    volatile uint32_t CCR2;
    volatile uint32_t CCR3;
    volatile uint32_t CCR4;
    volatile uint32_t BDTR;
    volatile uint32_t DCR;
    volatile uint32_t DMAR;
} TIM_TypeDef;

#define TIM1 ((TIM_TypeDef *) TIM1_BASE)
#define TIM2 ((TIM_TypeDef *) TIM2_BASE)
#define TIM3 ((TIM_TypeDef *) TIM3_BASE)
#define TIM4 ((TIM_TypeDef *) TIM4_BASE)
#define TIM5 ((TIM_TypeDef *) TIM5_BASE)

/* USART */
#define USART1_BASE       (APB2_BASE + 0x1000U)
#define USART2_BASE       (APB1_BASE + 0x4400U)
#define USART3_BASE       (APB1_BASE + 0x4800U)

typedef struct {
    volatile uint32_t SR;
    volatile uint32_t DR;
    volatile uint32_t BRR;
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t CR3;
    volatile uint32_t GTPR;
} USART_TypeDef;

#define USART1 ((USART_TypeDef *) USART1_BASE)
#define USART2 ((USART_TypeDef *) USART2_BASE)
#define USART3 ((USART_TypeDef *) USART3_BASE)

/* SPI */
#define SPI1_BASE         (APB2_BASE + 0x3000U)
#define SPI2_BASE         (APB1_BASE + 0x3800U)
#define SPI3_BASE         (APB1_BASE + 0x3C00U)

typedef struct {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t SR;
    volatile uint32_t DR;
    volatile uint32_t CRCPR;
    volatile uint32_t RXCRCR;
    volatile uint32_t TXCRCR;
    volatile uint32_t I2SCFGR;
    volatile uint32_t I2SPR;
} SPI_TypeDef;

#define SPI1 ((SPI_TypeDef *) SPI1_BASE)
#define SPI2 ((SPI_TypeDef *) SPI2_BASE)
#define SPI3 ((SPI_TypeDef *) SPI3_BASE)

/* I2C */
#define I2C1_BASE         (APB1_BASE + 0x5400U)
#define I2C2_BASE         (APB1_BASE + 0x5800U)

typedef struct {
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t OAR1;
    volatile uint32_t OAR2;
    volatile uint32_t DR;
    volatile uint32_t SR1;
    volatile uint32_t SR2;
    volatile uint32_t CCR;
    volatile uint32_t TRISE;
    volatile uint32_t FLTR;
} I2C_TypeDef;

#define I2C1 ((I2C_TypeDef *) I2C1_BASE)
#define I2C2 ((I2C_TypeDef *) I2C2_BASE)

/* ADC */
#define ADC1_BASE         (APB2_BASE + 0x2000U)
#define ADC2_BASE         (APB2_BASE + 0x2100U)
#define ADC3_BASE         (APB2_BASE + 0x2200U)

typedef struct {
    volatile uint32_t SR;
    volatile uint32_t CR1;
    volatile uint32_t CR2;
    volatile uint32_t SMPR1;
    volatile uint32_t SMPR2;
    volatile uint32_t JOFR1;
    volatile uint32_t JOFR2;
    volatile uint32_t JOFR3;
    volatile uint32_t JOFR4;
    volatile uint32_t HTR;
    volatile uint32_t LTR;
    volatile uint32_t SQR1;
    volatile uint32_t SQR2;
    volatile uint32_t SQR3;
    volatile uint32_t JSQR;
    volatile uint32_t JDR1;
    volatile uint32_t JDR2;
    volatile uint32_t JDR3;
    volatile uint32_t JDR4;
    volatile uint32_t DR;
} ADC_TypeDef;

#define ADC1 ((ADC_TypeDef *) ADC1_BASE)
#define ADC2 ((ADC_TypeDef *) ADC2_BASE)
#define ADC3 ((ADC_TypeDef *) ADC3_BASE)

/* DAC */
#define DAC_BASE          (APB1_BASE + 0x7400U)
typedef struct {
    volatile uint32_t CR;
    volatile uint32_t SWTRIGR;
    volatile uint32_t DHR12R1;
    volatile uint32_t DHR12L1;
    volatile uint32_t DHR8R1;
    volatile uint32_t DHR12R2;
    volatile uint32_t DHR12L2;
    volatile uint32_t DHR8R2;
    volatile uint32_t DHR12RD;
    volatile uint32_t DHR12LD;
    volatile uint32_t DHR8RD;
    volatile uint32_t DOR1;
    volatile uint32_t DOR2;
    volatile uint32_t SR;
} DAC_TypeDef;
#define DAC ((DAC_TypeDef *) DAC_BASE)

/* DMA */
#define DMA1_BASE         (AHB1_BASE + 0x6000U)
#define DMA2_BASE         (AHB1_BASE + 0x6400U)

/* NVIC */
#define NVIC_BASE         0xE000E100U

/* Flash */
#define FLASH_BASE        0x08000000U
#define FLASH_R_BASE      (AHB1_BASE + 0x3C00U)
typedef struct {
    volatile uint32_t ACR;
    volatile uint32_t KEYR;
    volatile uint32_t OPTKEYR;
    volatile uint32_t SR;
    volatile uint32_t CR;
    volatile uint32_t OPTCR;
} FLASH_TypeDef;
#define FLASH ((FLASH_TypeDef *) FLASH_R_BASE)

/* SYSCFG */
#define SYSCFG_BASE       (APB2_BASE + 0x3800U)

/* EXTI */
#define EXTI_BASE         (APB2_BASE + 0x3C00U)

/* Pin modes */
#define GPIO_MODE_INPUT   0
#define GPIO_MODE_OUTPUT  1
#define GPIO_MODE_AF      2
#define GPIO_MODE_ANALOG  3

#define GPIO_SPEED_LOW    0
#define GPIO_SPEED_MED    1
#define GPIO_SPEED_HIGH   2
#define GPIO_SPEED_VHIGH  3

#define GPIO_PULL_NONE    0
#define GPIO_PULL_UP      1
#define GPIO_PULL_DOWN    2

/* Function prototypes */
void hal_init(void);
void hal_clock_init(uint32_t freq);
void hal_gpio_init(GPIO_TypeDef *port, uint8_t pin, uint8_t mode, uint8_t speed, uint8_t pull, uint8_t af);
void hal_gpio_write(GPIO_TypeDef *port, uint8_t pin, uint8_t state);
uint8_t hal_gpio_read(GPIO_TypeDef *port, uint8_t pin);
void hal_gpio_toggle(GPIO_TypeDef *port, uint8_t pin);

void hal_uart_init(USART_TypeDef *uart, uint32_t baud);
void hal_uart_send(USART_TypeDef *uart, uint8_t data);
uint8_t hal_uart_recv(USART_TypeDef *uart);
void hal_uart_send_string(USART_TypeDef *uart, const char *str);

void hal_spi_init(SPI_TypeDef *spi, uint8_t mode, uint32_t speed);
uint8_t hal_spi_transfer(SPI_TypeDef *spi, uint8_t data);

void hal_i2c_init(I2C_TypeDef *i2c, uint32_t speed);
bool hal_i2c_write(I2C_TypeDef *i2c, uint8_t addr, const uint8_t *data, uint16_t len);
bool hal_i2c_read(I2C_TypeDef *i2c, uint8_t addr, uint8_t *data, uint16_t len);

void hal_adc_init(ADC_TypeDef *adc, uint8_t channel);
uint16_t hal_adc_read(ADC_TypeDef *adc, uint8_t channel);

void hal_dac_write(DAC_TypeDef *dac, uint8_t channel, uint16_t value);

void hal_timer_init(TIM_TypeDef *tim, uint32_t prescaler, uint32_t period);
void hal_timer_start(TIM_TypeDef *tim);
void hal_timer_stop(TIM_TypeDef *tim);
void hal_pwm_set(TIM_TypeDef *tim, uint8_t channel, uint16_t duty);

void hal_delay_ms(uint32_t ms);
void hal_delay_us(uint32_t us);

uint32_t hal_get_tick(void);
void hal_increment_tick(void);

void hal_flash_unlock(void);
void hal_flash_lock(void);
bool hal_flash_erase_sector(uint32_t sector);
bool hal_flash_program(uint32_t addr, const uint8_t *data, uint32_t len);

void hal_watchdog_init(uint32_t timeout_ms);
void hal_watchdog_feed(void);

void hal_nvic_enable_irq(uint8_t irq);
void hal_nvic_disable_irq(uint8_t irq);
void hal_nvic_set_priority(uint8_t irq, uint8_t priority);

#endif /* STM32_HAL_H */
