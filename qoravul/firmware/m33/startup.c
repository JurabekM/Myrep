/* Reset vector for QEMU mps2-an505: enable the FPU, then hand over to newlib's
 * crt0 (_start), which clears .bss, opens semihosting and calls main(). */
#include <stdint.h>

extern uint32_t __stack_top;
extern void _start(void);
void Reset_Handler(void);
void Default_Handler(void);

__attribute__((section(".vectors"), used)) static void (*const vectors[16])(void) = {
    (void (*)(void))(&__stack_top), Reset_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, 0, 0, 0, 0,
    Default_Handler, Default_Handler, 0, Default_Handler, Default_Handler,
};

void Reset_Handler(void)
{
    volatile uint32_t *cpacr = (volatile uint32_t *)0xE000ED88u;
    *cpacr |= (0xFu << 20); /* CP10 + CP11 full access */
    __asm volatile("dsb\n isb");
    _start();
    for (;;) {
    }
}

void Default_Handler(void)
{
    for (;;) {
    }
}
