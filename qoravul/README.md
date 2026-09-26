# QORAVUL v0.1

Post-quantum secure TinyML edge device for smart electricity meters (230 V / 50 Hz).
Each one-minute measurement window is analysed on the device (8 features, int8
autoencoder + envelope stage). The server receives only 15-minute summaries and
ML-DSA-65-signed evidence, over QVL/1: a hybrid X25519 + ML-KEM-768 1-RTT
handshake followed by ChaCha20-Poly1305 records.

Architecture, threat model and measured results (in Uzbek): [ARCHITECTURE.md](ARCHITECTURE.md).

> **Security warning.** The default PQ backend is pure Python (`kyber-py`,
> `dilithium-py`). It is **not constant-time** and must not be used where an
> attacker can measure timing, power or EM. It is a reference for protocol
> development only. `liboqs` is available as an opt-in backend
> (`QORAVUL_PQ_BACKEND=liboqs`).
>
> **Data warning.** Every ML number comes from a **synthetic** load model and
> hand-written attack signatures. No real meter data was used.

## Quick start

```bash
pip install -r requirements.txt
python -m qoravul.tinyml.train                        # train, quantise, export models/ + firmware/*.h
make -C firmware test                                 # parity: 500/500 vectors bit-exact
pytest -q                                             # 55 tests
python -m qoravul.sim.run --nodes 30 --thieves 6 --hours 24
python -m qoravul.sim.run --reconnect-hours 4         # reconnect every 4 h with PSK resumption
python -m bench.bench --fleet-meters 2000             # handshake sizes/latency, overhead, false incidents
```

Optional, needs `arm-none-eabi-gcc` and `qemu-system-arm`:

```bash
make -C firmware size-m33        # Cortex-M33 code size
make -C firmware qemu-m33        # 500/500 parity on an emulated Cortex-M33 (mps2-an505)
make -C firmware qemu-bench-m33  # instruction count per window (QEMU icount proxy)
```

### liboqs backend (opt-in)

`import oqs` may try to download and build liboqs and hang, so it is never imported
unless requested. Install liboqs first (e.g. 0.16.0 with
`-DOQS_MINIMAL_BUILD="KEM_ml_kem_768;SIG_ml_dsa_65"`), then `pip install liboqs-python==0.16.0.1`:

```bash
QORAVUL_PQ_BACKEND=liboqs python -m bench.bench              # HYBRID handshake ~0.6 ms instead of ~90 ms
QORAVUL_TEST_LIBOQS=1 pytest -q tests/test_liboqs_interop.py # liboqs <-> pure-Python interop
```

## Measured results (x86_64 host, pure-Python PQ)

| Item | Result |
|---|---|
| Window FPR (100k unseen normal windows) | 0.064% |
| TPR bypass / magnet / sag / freq / night_load | 100 / 100 / 100 / 100 / 100% |
| C parity, host and Cortex-M33 (QEMU) | 500/500 bit-exact |
| Detector code + constants on Cortex-M33 | 1444 B |
| HYBRID handshake | 4592 B HELLO + 4475 B ACCEPT, ~90 ms total |
| PSK resumption | 126 B + 108 B = 234 B, single-use tickets |
| Record overhead | 34 B + 4 B length prefix |
| Fleet 30 nodes / 6 thieves / 24 h | 6/6 detected, 0 false alerts, ledger intact, 87.2% bandwidth saved |
| Honest fleet 2000 meters x 24 h | 0 false incidents |

## Layout

```
qoravul/crypto/backend.py      PQ abstraction (RLock-guarded; liboqs opt-in)
qoravul/protocol/wire.py       framing, TLV-lite, FrameType, Suite, ProtocolError
qoravul/protocol/handshake.py  Identity, NodeHandshake, GatewayHandshake
qoravul/protocol/session.py    ReplayWindow, Session (seal/open)
qoravul/protocol/resume.py     PSK resumption: Ticket, TicketStore, NodeResume, GatewayResume
qoravul/tinyml/meter.py        VirtualMeter, 8 features, 5 attacks
qoravul/tinyml/model.py        FloatAE (numpy Adam), QuantAE (int8), quantize_multiplier
qoravul/tinyml/export_c.py     qv_model.h + qv_vectors.h
qoravul/tinyml/train.py        training CLI
qoravul/edge/node.py           EdgeNode: detector + incident FSM + QVL/1 client
qoravul/gateway/server.py      asyncio Gateway + EvidenceLedger
qoravul/sim/run.py             fleet simulation CLI
firmware/                      C99 int8 inference, parity test, M33/QEMU targets
bench/bench.py                 benchmarks
tests/                         pytest suite
```
