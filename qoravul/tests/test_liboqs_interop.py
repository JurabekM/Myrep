"""Interop between the liboqs backend and the pure-Python backend (extension 9.3).

Opt-in: ``import oqs`` can try to download and build liboqs and hang (lesson 6),
so these tests only run with QORAVUL_TEST_LIBOQS=1 and a pre-installed liboqs.
"""
from __future__ import annotations

import contextlib
import os

import pytest

from qoravul.crypto import backend as pq

pytestmark = pytest.mark.skipif(os.environ.get("QORAVUL_TEST_LIBOQS") != "1",
                                reason="set QORAVUL_TEST_LIBOQS=1 with liboqs + liboqs-python installed")


@pytest.fixture(scope="module")
def backends():
    return {"oqs": pq.LiboqsBackend(), "pure": pq.PurePythonBackend()}


@contextlib.contextmanager
def use(b):
    old = pq._backend
    pq._backend = b
    try:
        yield
    finally:
        pq._backend = old


@pytest.mark.parametrize("gen,enc", [("oqs", "pure"), ("pure", "oqs")])
def test_mlkem_interop(backends, gen, enc):
    ek, dk = backends[gen].kem_keygen()
    assert (len(ek), len(dk)) == (1184, 2400)
    ss, ct = backends[enc].kem_encaps(ek)
    assert len(ct) == 1088 and backends[gen].kem_decaps(dk, ct) == ss


@pytest.mark.parametrize("signer,verifier", [("oqs", "pure"), ("pure", "oqs")])
def test_mldsa_interop_with_context(backends, signer, verifier):
    pk, sk = backends[signer].sig_keygen()
    assert (len(pk), len(sk)) == (1952, 4032)
    sig = backends[signer].sign(sk, b"evidence", b"QVL1-EVIDENCE")
    assert len(sig) == 3309
    assert backends[verifier].verify(pk, b"evidence", sig, b"QVL1-EVIDENCE")
    assert not backends[verifier].verify(pk, b"evidence", sig, b"other-ctx")
    assert not backends[verifier].verify(pk, b"evidencE", sig, b"QVL1-EVIDENCE")


@pytest.mark.parametrize("node_b,gw_b", [("oqs", "pure"), ("pure", "oqs")])
def test_hybrid_handshake_across_backends(backends, node_b, gw_b):
    from qoravul.protocol.handshake import GatewayHandshake, Identity, NodeHandshake
    from qoravul.protocol.wire import FrameType

    with use(backends[node_b]):
        node = Identity.generate()
    with use(backends[gw_b]):
        gw = Identity.generate()
        gwh = GatewayHandshake(gw, {node.node_id: node.pk})
    with use(backends[node_b]):
        nh = NodeHandshake(node, gw.pk)
        hello = nh.hello()
    with use(backends[gw_b]):
        res = gwh.respond(hello)
    assert res.session is not None, res.reason
    with use(backends[node_b]):
        ns = nh.finish(res.frame)
    assert res.session.open(ns.seal(FrameType.DATA, b"interop"))[1] == b"interop"
