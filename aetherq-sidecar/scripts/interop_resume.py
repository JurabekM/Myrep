"""
Resumption va PoW uchun cross-implementation interop (Python referens ↔ Rust aq-sidecar).

  E. Python klient → Rust `serve`: 1-ulanish to'liq, ticket olinadi; 2-ulanish resumption bilan.
  F. Rust `connect` (sidecar) → Python server (PoW D=8 + ticket): har ikki ulanish echo;
     Python server 2-ulanishni resumed deb belgilaydi.

Ishga tushirish (release binary kerak):
    set PYTHONIOENCODING=utf-8
    python scripts/interop_resume.py
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
from aether_q_v51.dos import PuzzleAuthority  # noqa: E402
from aether_q_v51.handshake import TicketAuthority  # noqa: E402

ECHO, SERVE, PYSRV, CONNECT = 19300, 19301, 19302, 19303


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


def plain_echo(stop):
    ls = socket.socket()
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", ECHO))
    ls.listen(8)
    ls.settimeout(0.5)

    def serve(c):
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

    while not stop.is_set():
        try:
            c, _ = ls.accept()
        except socket.timeout:
            continue
        threading.Thread(target=serve, args=(c,), daemon=True).start()
    ls.close()


def py_server(sig_priv, stop, results, n_conn):
    """Python AETHER-Q server: PoW + tickets; har ulanishda resumed bayrog'ini yozadi."""
    ls = socket.socket()
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", PYSRV))
    ls.listen(4)
    ls.settimeout(0.5)
    puzzle = PuzzleAuthority(difficulty=8)
    tickets = TicketAuthority()
    done = 0
    while not stop.is_set() and done < n_conn:
        try:
            c, _ = ls.accept()
        except socket.timeout:
            continue
        try:
            sess = net.server_handshake(c, sig_priv=sig_priv, puzzle_authority=puzzle, ticket_authority=tickets)
            data = net.recv(c, sess)
            net.send(c, sess, data)
            results.append(bool(sess.resumed))
        except Exception as e:  # noqa: BLE001
            import traceback

            results.append(("error", repr(e), traceback.format_exc()[-900:]))
        finally:
            c.close()
            done += 1
    ls.close()


def main():
    if not os.path.exists(BIN):
        print("XATO: release binary topilmadi:", BIN)
        return 2
    tmp = tempfile.mkdtemp(prefix="aq-resume-")
    key = os.path.join(tmp, "server.key")
    r = subprocess.run([BIN, "keygen", "--out", key], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    pk = bytes.fromhex(open(key + ".pub", encoding="utf-8").read().strip())
    seed = bytes.fromhex([l for l in open(key, encoding="utf-8").read().splitlines() if l.startswith("seed=")][0][5:])
    priv = mldsa.MLDSA65PrivateKey.from_seed_bytes(seed)

    stop = threading.Event()
    threading.Thread(target=plain_echo, args=(stop,), daemon=True).start()
    assert wait_port(ECHO), "echo ishlamadi"
    results = {}
    procs = []
    try:
        # ── E: Python klient → Rust serve (resumption)
        serve = subprocess.Popen(
            [BIN, "serve", "--listen", f"127.0.0.1:{SERVE}", "--upstream", f"127.0.0.1:{ECHO}", "--identity", key],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        procs.append(serve)
        assert wait_port(SERVE), "serve ishlamadi"
        s1 = socket.create_connection(("127.0.0.1", SERVE), timeout=10)
        sess1 = net.client_handshake(s1, server_pub=pk, want_ticket=True)
        results["E1 python→rust: to'liq handshake"] = not sess1.resumed
        results["E2 python→rust: NST ticket olindi"] = getattr(sess1, "new_ticket", None) is not None
        net.send(s1, sess1, b"E1 echo")
        results["E3 python→rust: echo (1-ulanish)"] = net.recv(s1, sess1) == b"E1 echo"
        s1.close()
        t = sess1.new_ticket
        s2 = socket.create_connection(("127.0.0.1", SERVE), timeout=10)
        sess2 = net.client_handshake(s2, server_pub=pk, resume=t, want_ticket=True)
        results["E4 python→rust: resumption (2-ulanish)"] = bool(sess2.resumed)
        net.send(s2, sess2, b"E4 echo")
        results["E5 python→rust: echo (resumed)"] = net.recv(s2, sess2) == b"E4 echo"
        s2.close()
        serve.kill()
        serve.wait()

        # ── F: Rust connect → Python server (PoW D=8 + tickets)
        py_stop = threading.Event()
        py_results = []
        th = threading.Thread(target=py_server, args=(priv, py_stop, py_results, 2), daemon=True)
        th.start()
        time.sleep(0.5)  # port probe YO'Q — u Python server hisobini buzadi
        conn_err = open(os.path.join(tmp, "connect.err"), "w", encoding="utf-8")
        conn = subprocess.Popen(
            [BIN, "connect", "--listen", f"127.0.0.1:{CONNECT}", "--peer", f"127.0.0.1:{PYSRV}",
             "--server-pub", key + ".pub", "--resume"],
            stdout=subprocess.PIPE, stderr=conn_err)
        procs.append(conn)
        time.sleep(0.5)  # probe YO'Q: har probe sidecar'da tunnel ochadi (server hisobini buzadi)
        echoes = []
        for i in range(2):
            c = socket.create_connection(("127.0.0.1", CONNECT), timeout=15)
            msg = f"F{i} plain->rust connect->python(PoW)".encode()
            got = b""
            try:
                c.sendall(msg)
                while len(got) < len(msg):
                    chunk = c.recv(4096)
                    if not chunk:
                        break
                    got += chunk
            except OSError as e:
                print(f"F{i} plain klient xatosi: {e!r}")
            echoes.append(got == msg)
            c.close()
            time.sleep(0.3)
        th.join(timeout=30)
        conn_err.flush()
        print("connect stderr:", open(os.path.join(tmp, "connect.err"), encoding="utf-8").read()[-600:])
        print("python server natijasi:", py_results)
        results["F1 rust→python: PoW + echo (1-ulanish)"] = echoes[0]
        results["F2 rust→python: echo (2-ulanish, resumption)"] = echoes[1]
        results["F3 python server: 1-ulanish to'liq, 2-ulanish resumed"] = py_results == [False, True]
        if py_results and not all(isinstance(x, bool) for x in py_results):
            print("python server xatolari:", py_results)
        py_stop.set()
    finally:
        stop.set()
        for p in procs:
            try:
                p.kill()
                p.wait(timeout=5)
            except Exception:  # noqa: BLE001
                pass

    ok = True
    for name, passed in results.items():
        print(("PASS" if passed else "FAIL"), name)
        ok = ok and bool(passed)
    print("\nNATIJA:", "barchasi o'tdi" if ok else "ba'zi tekshiruvlar muvaffaqiyatsiz")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
