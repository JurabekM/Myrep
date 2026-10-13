"""
Python referens (aether_q_v3) ↔ Rust aq-sidecar cross-implementation interop testi.

Stsenariylar:
  A. Python klient  → Rust `serve` (sidecar) → plain upstream (echo)     [server auth]
  B. Rust `connect` (sidecar) → Python server (net.server_handshake)      [server auth]
  C. Python klient (identity) → Rust `serve --require-client-auth --allow` [mutual auth, OK]
  D. Python klient (identity, allowlist'da yo'q) → Rust `serve`           [mutual auth, RAD]

Ishga tushirish (repo ildizidan, avval `cargo build --release -p aq-sidecar`):
    set PYTHONIOENCODING=utf-8
    python scripts/interop_py.py
"""

import os
import socket
import subprocess
import sys
import tempfile
import threading
import time

REF = r"C:/Users/comp_2.1/Downloads/aether_q_v3"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "target", "release", "aq-sidecar.exe")
sys.path.insert(0, REF)

from cryptography.hazmat.primitives.asymmetric import mldsa  # noqa: E402

from aether_q_v51 import net  # noqa: E402

PORTS = {"echo": 19000, "serve": 19001, "py_srv": 19002, "connect": 19003, "serve_auth": 19004}


def free_port_ok(port):
    s = socket.socket()
    s.settimeout(0.2)
    try:
        s.connect(("127.0.0.1", port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def wait_port(port, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        s = socket.socket()
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except OSError:
            s.close()
            time.sleep(0.1)
    return False


def rust(args):
    """aq-sidecar buyrug'ini fon jarayon sifatida ishga tushiradi."""
    return subprocess.Popen([BIN] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def plain_echo_server(port, stop):
    """Monolit o'rnida: oddiy (shifrlanmagan) TCP echo."""
    ls = socket.socket()
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", port))
    ls.listen(8)
    ls.settimeout(0.5)
    while not stop.is_set():
        try:
            c, _ = ls.accept()
        except socket.timeout:
            continue
        threading.Thread(target=_echo_conn, args=(c,), daemon=True).start()
    ls.close()


def _echo_conn(c):
    try:
        while True:
            d = c.recv(65536)
            if not d:
                break
            c.sendall(d)
    except OSError:
        pass
    finally:
        c.close()


def aether_echo_server(port, sig_priv, stop, results):
    """Python AETHER-Q server (net.server_handshake) + record echo."""
    ls = socket.socket()
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", port))
    ls.listen(4)
    ls.settimeout(0.5)
    while not stop.is_set():
        try:
            c, _ = ls.accept()
        except socket.timeout:
            continue
        try:
            sess = net.server_handshake(c, sig_priv=sig_priv)
            data = net.recv(c, sess)
            results.append(("py-server got", data))
            net.send(c, sess, data)
        except Exception as e:  # noqa: BLE001
            results.append(("py-server error", repr(e)))
        finally:
            c.close()
    ls.close()


def main():
    if not os.path.exists(BIN):
        print("XATO: release binary topilmadi:", BIN)
        return 2
    tmp = tempfile.mkdtemp(prefix="aq-interop-")
    srv_key = os.path.join(tmp, "server.key")
    cli_key = os.path.join(tmp, "client.key")
    rogue_key = os.path.join(tmp, "rogue.key")
    allow = os.path.join(tmp, "allow.txt")

    # Rust bilan identity yaratish
    for path in (srv_key, cli_key, rogue_key):
        out = subprocess.run([BIN, "keygen", "--out", path], capture_output=True, text=True)
        assert out.returncode == 0, out.stderr

    def load(path):
        seed = None
        pk = None
        for line in open(path, encoding="utf-8").read().splitlines():
            if line.startswith("seed="):
                seed = bytes.fromhex(line[5:])
            if line.startswith("pk="):
                pk = bytes.fromhex(line[3:])
        return seed, pk

    srv_seed, srv_pk = load(srv_key)
    cli_seed, cli_pk = load(cli_key)
    _rog_seed, _rog_pk = load(rogue_key)
    srv_priv = mldsa.MLDSA65PrivateKey.from_seed_bytes(srv_seed)
    cli_priv = mldsa.MLDSA65PrivateKey.from_seed_bytes(cli_seed)
    rog_priv = mldsa.MLDSA65PrivateKey.from_seed_bytes(_rog_seed)
    # Python bilan ochiq kalit mosligi (FIPS 204 seed → pk)
    assert srv_priv.public_key().public_bytes_raw() == srv_pk, "ML-DSA seed→pk: Python ≠ Rust"
    assert cli_priv.public_key().public_bytes_raw() == cli_pk, "ML-DSA seed→pk: Python ≠ Rust"
    with open(allow, "w", encoding="utf-8") as f:
        f.write(cli_pk.hex() + "\n")

    stop = threading.Event()
    threading.Thread(target=plain_echo_server, args=(PORTS["echo"], stop), daemon=True).start()
    assert wait_port(PORTS["echo"]), "echo server ishlamadi"

    results = {}
    procs = []
    try:
        # ── A: Python klient → Rust serve → echo
        pa = rust(["serve", "--listen", f"127.0.0.1:{PORTS['serve']}",
                   "--upstream", f"127.0.0.1:{PORTS['echo']}", "--identity", srv_key])
        procs.append(pa)
        assert wait_port(PORTS["serve"]), "serve ishlamadi: " + pa.stderr.read(400).decode(errors="replace")
        s = socket.create_connection(("127.0.0.1", PORTS["serve"]), timeout=10)
        sess = net.client_handshake(s, server_pub=srv_pk)
        net.send(s, sess, b"A: Python -> Rust serve -> echo")
        results["A python->rust serve"] = net.recv(s, sess) == b"A: Python -> Rust serve -> echo"
        s.close()

        # ── B: Rust connect → Python server (AETHER-Q) ; plain klient Rust sidecar orqali
        py_stop = threading.Event()
        py_results = []
        threading.Thread(target=aether_echo_server,
                         args=(PORTS["py_srv"], srv_priv, py_stop, py_results), daemon=True).start()
        assert wait_port(PORTS["py_srv"]), "python server ishlamadi"
        pb = rust(["connect", "--listen", f"127.0.0.1:{PORTS['connect']}",
                   "--peer", f"127.0.0.1:{PORTS['py_srv']}", "--server-pub", srv_key + ".pub"])
        procs.append(pb)
        assert wait_port(PORTS["connect"]), "connect ishlamadi"
        c = socket.create_connection(("127.0.0.1", PORTS["connect"]), timeout=10)
        c.sendall(b"B: plain -> Rust connect -> Python server")
        got = b""
        while len(got) < len(b"B: plain -> Rust connect -> Python server"):
            chunk = c.recv(4096)
            if not chunk:
                break
            got += chunk
        results["B rust connect->python server"] = got == b"B: plain -> Rust connect -> Python server"
        c.close()
        py_stop.set()

        # ── C: Python klient (identity, allowlist'da) → Rust serve --require-client-auth
        pc = rust(["serve", "--listen", f"127.0.0.1:{PORTS['serve_auth']}",
                   "--upstream", f"127.0.0.1:{PORTS['echo']}", "--identity", srv_key,
                   "--require-client-auth", "--allow", allow])
        procs.append(pc)
        assert wait_port(PORTS["serve_auth"]), "serve_auth ishlamadi"
        s = socket.create_connection(("127.0.0.1", PORTS["serve_auth"]), timeout=10)
        sess = net.client_handshake(s, server_pub=srv_pk, identity=(cli_pk, cli_priv))
        net.send(s, sess, b"C: mutual auth OK")
        results["C mutual auth (allowlist)"] = net.recv(s, sess) == b"C: mutual auth OK"
        s.close()

        # ── D: Python klient (identity, allowlist'da YO'Q) → RAD
        s = socket.create_connection(("127.0.0.1", PORTS["serve_auth"]), timeout=10)
        rejected = False
        try:
            sess = net.client_handshake(s, server_pub=srv_pk, identity=(_rog_pk, rog_priv))
            net.send(s, sess, b"D")
            rejected = net.recv(s, sess) != b"D"
        except Exception:  # noqa: BLE001
            rejected = True
        s.close()
        results["D rogue client rejected"] = rejected
    finally:
        stop.set()
        for p in procs:
            p.kill()
            p.wait()

    ok = True
    for name, passed in results.items():
        print(("PASS" if passed else "FAIL"), name)
        ok = ok and bool(passed)
    print("\nNATIJA:", "barchasi o'tdi" if ok else "ba'zi stsenariylar muvaffaqiyatsiz")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
