# CLAUDE.md — QORAVUL v0.1

## Project goal
QORAVUL is a post-quantum-secure TinyML edge device for smart electricity meters
(230 V / 50 Hz). Every minute the meter analyses its measurement window on-device
(8 features -> int8 autoencoder + envelope stage), and sends the server only
summaries plus ML-DSA-65-signed evidence over the QVL/1 protocol
(hybrid X25519 + ML-KEM-768 handshake, ChaCha20-Poly1305 records).

## Commands (run from this directory)
```
pip install -r requirements.txt
python -m qoravul.tinyml.train          # train + quantize + export models/ and firmware/*.h
make -C firmware test                   # C int8 inference, 500/500 bit-exact parity
pytest -q                               # all tests
python -m qoravul.sim.run --nodes 30 --thieves 6 --hours 24
python -m bench.bench                   # handshake sizes / latency / record overhead
make -C firmware size-m33               # optional, needs arm-none-eabi-gcc
QORAVUL_PQ_BACKEND=liboqs ...           # opt-in liboqs backend (default pure-Python)
```

## Rules
- Code, commits, docstrings: English. `ARCHITECTURE.md` and reports: Uzbek.
- Every number in docs must be measured; an estimate is labelled "TAXMIN" with its formula.
- State the synthetic-data limitation openly in docs.
- Never tune a threshold or a test just to make it pass — fix the root cause.
- Pure-Python PQ is NOT constant-time — keep the README warning.
- Don't rewrite working parts; run `make -C firmware test` and `pytest -q` first.
- Small commit at the end of each stage once tests are green.

## Lessons learned (mandatory)
1. An AE alone is not enough: it passes independent noisy features (n_imb, f_dev)
   through the bottleneck, bypass TPR ~2%. The envelope stage is REQUIRED.
2. `s_in = 4/127` clips Gaussian tails, envelope sticks at ±127. Use `8/127`.
3. Few meters in the training set (64) -> overfit to households, false alerts
   in the morning hours. Use `dataset(meters=4096)`, `n_train = 120000`.
4. 99.5-percentile + 3/5 debounce gives a daily false incident at 1% of meters.
   Use 99.9-percentile + 4/6 debounce.
5. kyber-py / dilithium-py are not thread-safe. Wrap backend methods in an
   `RLock`; do not use `to_thread` in the gateway.
6. `import oqs` may hang trying to build liboqs from source -> opt-in only.
7. Do not ship the alert signature as hex inside JSON (2x size). Binary payload.
8. In bandwidth comparisons add the handshake size to the raw-stream baseline too.
