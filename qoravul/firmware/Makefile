CC      ?= gcc
CFLAGS  ?= -std=c99 -O2 -Wall -Wextra -Werror -pedantic -ffp-contract=off -fno-fast-math
LDLIBS  = -lm

ARM_CC     ?= arm-none-eabi-gcc
ARM_SIZE   ?= arm-none-eabi-size
ARM_CFLAGS = -std=c99 -Os -Wall -Wextra -Werror -mcpu=cortex-m33 -mthumb -mfloat-abi=hard \
             -mfpu=fpv5-sp-d16 -ffp-contract=off -ffunction-sections -fdata-sections

.PHONY: test size-m33 clean

test: test_parity
	./test_parity

test_parity: test_parity.c qv_infer.c qv_infer.h qv_model.h qv_vectors.h
	$(CC) $(CFLAGS) -o $@ test_parity.c qv_infer.c $(LDLIBS)

size-m33: qv_infer.c qv_infer.h qv_model.h
	@command -v $(ARM_CC) >/dev/null || { echo "$(ARM_CC) not found"; exit 1; }
	$(ARM_CC) $(ARM_CFLAGS) -c qv_infer.c -o qv_infer_m33.o
	$(ARM_SIZE) qv_infer_m33.o

clean:
	rm -f test_parity *.o
