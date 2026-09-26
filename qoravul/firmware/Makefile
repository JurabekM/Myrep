CC      ?= gcc
CFLAGS  ?= -std=c99 -O2 -Wall -Wextra -Werror -pedantic -ffp-contract=off -fno-fast-math
LDLIBS  = -lm

ARM_CC     ?= arm-none-eabi-gcc
ARM_SIZE   ?= arm-none-eabi-size
ARM_CFLAGS = -std=c99 -Os -Wall -Wextra -Werror -mcpu=cortex-m33 -mthumb -mfloat-abi=hard \
             -mfpu=fpv5-sp-d16 -ffp-contract=off -ffunction-sections -fdata-sections

.PHONY: test bench size-m33 qemu-m33 qemu-bench-m33 clean

test: test_parity
	./test_parity

test_parity: test_parity.c qv_infer.c qv_infer.h qv_model.h qv_vectors.h
	$(CC) $(CFLAGS) -o $@ test_parity.c qv_infer.c $(LDLIBS)

bench: bench_host
	./bench_host

bench_host: bench_host.c qv_infer.c qv_infer.h qv_model.h qv_vectors.h
	$(CC) $(CFLAGS) -o $@ bench_host.c qv_infer.c $(LDLIBS)

size-m33: qv_infer.c qv_infer.h qv_model.h
	@command -v $(ARM_CC) >/dev/null || { echo "$(ARM_CC) not found"; exit 1; }
	$(ARM_CC) $(ARM_CFLAGS) -c qv_infer.c -o qv_infer_m33.o
	$(ARM_SIZE) qv_infer_m33.o

# Cortex-M33 parity run under QEMU (mps2-an505), output via semihosting.
M33_ELF = m33/test_parity_m33.elf
$(M33_ELF): test_parity.c qv_infer.c qv_infer.h qv_model.h qv_vectors.h m33/startup.c m33/an505.ld
	$(ARM_CC) $(ARM_CFLAGS) -O2 --specs=rdimon.specs -T m33/an505.ld -Wl,--gc-sections \
	    -o $@ m33/startup.c test_parity.c qv_infer.c -lm
	$(ARM_SIZE) $@

qemu-m33: $(M33_ELF)
	timeout 120 qemu-system-arm -M mps2-an505 -nographic -semihosting-config enable=on,target=native \
	    -kernel $(M33_ELF)

m33/bench_m33.elf: m33/bench_m33.c qv_infer.c qv_infer.h qv_model.h qv_vectors.h m33/startup.c m33/an505.ld
	$(ARM_CC) $(ARM_CFLAGS) -O2 --specs=rdimon.specs -T m33/an505.ld -Wl,--gc-sections \
	    -o $@ m33/startup.c m33/bench_m33.c qv_infer.c -lm

qemu-bench-m33: m33/bench_m33.elf
	timeout 120 qemu-system-arm -M mps2-an505 -nographic -icount shift=0 \
	    -semihosting-config enable=on,target=native -kernel m33/bench_m33.elf

clean:
	rm -f test_parity bench_host *.o m33/*.elf
