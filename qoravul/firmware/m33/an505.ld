/* Minimal linker script for QEMU mps2-an505 (Cortex-M33, secure alias of ZBT SRAM1).
 * Everything runs from RAM; QEMU loads the ELF segments directly. */
ENTRY(Reset_Handler)
MEMORY
{
    RAM (rwx) : ORIGIN = 0x10000000, LENGTH = 4M
}
SECTIONS
{
    .text : {
        KEEP(*(.vectors))
        *(.text*)
        KEEP(*(.init)) KEEP(*(.fini))
        *(.rodata*)
        . = ALIGN(4);
    } > RAM
    .ARM.exidx : { *(.ARM.exidx*) } > RAM
    .init_array : { PROVIDE_HIDDEN(__init_array_start = .); KEEP(*(.init_array*)); PROVIDE_HIDDEN(__init_array_end = .); } > RAM
    .fini_array : { PROVIDE_HIDDEN(__fini_array_start = .); KEEP(*(.fini_array*)); PROVIDE_HIDDEN(__fini_array_end = .); } > RAM
    .data : { *(.data*) . = ALIGN(4); } > RAM
    .bss (NOLOAD) : { __bss_start__ = .; *(.bss*) *(COMMON) . = ALIGN(4); __bss_end__ = .; } > RAM
    end = .;
    PROVIDE(_end = .);
    PROVIDE(__end__ = .);
    __stack_top = ORIGIN(RAM) + LENGTH(RAM);
    PROVIDE(__stack = __stack_top);
}
