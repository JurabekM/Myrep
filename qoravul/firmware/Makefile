CC      ?= gcc
CFLAGS  ?= -std=c99 -O2 -Wall -Wextra -Werror -pedantic -ffp-contract=off -fno-fast-math
LDLIBS  = -lm

ARM_CC     ?= arm-none-eabi-gcc
ARM_SIZE   ?= arm-none-eabi-size
ARM_CFLAGS = -std=c99 -Os -Wall -Wextra -Werror -mcpu=cortex-m33 -mthumb -mfloat-abi=hard \
             -mfpu=fpv5-sp-d16 -ffp-contract=off -ffunction-sections -fdata-sections

.PHONY: test bench size-m33 qemu-m33 qemu-bench-m33 pq-fetch pq-m33 clean

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

# ML-KEM-768 / ML-DSA-65 on Cortex-M33 (QEMU): KAT output, instruction proxy, stack peak.
# Third-party sources are fetched at pinned commits, never vendored.
PQ_DIR    ?= third_party
MLKEM_REV ?= b87425bd27105506e5f4675d2edd76468b1a8f6f
MLDSA_REV ?= 14d195a82dd27ed6bac35b403f5386bf43a893d3
MLKEM_SRC  = $(PQ_DIR)/mlkem-native/mlkem
MLDSA_SRC  = $(PQ_DIR)/mldsa-native/mldsa
PQ_DEFS    = -DMLK_CONFIG_PARAMETER_SET=768 -DMLK_CONFIG_NO_RANDOMIZED_API -DMLK_CONFIG_NAMESPACE_PREFIX=mlkem \
             -DMLD_CONFIG_PARAMETER_SET=65 -DMLD_CONFIG_NO_RANDOMIZED_API -DMLD_CONFIG_NAMESPACE_PREFIX=mldsa
PQ_CFLAGS  = -std=c99 -O2 -mcpu=cortex-m33 -mthumb -mfloat-abi=hard -mfpu=fpv5-sp-d16 \
             -ffunction-sections -fdata-sections $(PQ_DEFS) -I$(MLKEM_SRC) -I$(MLDSA_SRC)

define pq_clone
	@if [ ! -d $(PQ_DIR)/$(1) ]; then \
	    mkdir -p $(PQ_DIR)/$(1) && cd $(PQ_DIR)/$(1) && git init -q && \
	    git remote add origin https://github.com/pq-code-package/$(1).git && \
	    git fetch -q --depth 1 origin $(2) && git checkout -q FETCH_HEAD; fi
endef

pq-fetch:
	$(call pq_clone,mlkem-native,$(MLKEM_REV))
	$(call pq_clone,mldsa-native,$(MLDSA_REV))

pq_m33/pq_bench.elf: pq_m33/pq_bench.c m33/startup.c m33/an505.ld | pq-fetch
	$(ARM_CC) $(PQ_CFLAGS) --specs=rdimon.specs -T m33/an505.ld -Wl,--gc-sections -o $@ \
	    m33/startup.c pq_m33/pq_bench.c $(MLKEM_SRC)/mlkem_native.c $(MLDSA_SRC)/mldsa_native.c
	$(ARM_SIZE) $@

pq-m33: pq_m33/pq_bench.elf
	timeout 600 qemu-system-arm -M mps2-an505 -nographic -icount shift=0 \
	    -semihosting-config enable=on,target=native -kernel pq_m33/pq_bench.elf

clean:
	rm -f test_parity bench_host *.o m33/*.elf pq_m33/*.elf
