"""QVL/1 handshake and record-layer tests."""
from __future__ import annotations

import struct

import pytest

from qoravul.protocol.handshake import GatewayHandshake, Identity, NodeHandshake
from qoravul.protocol.session import RECORD_OVERHEAD, ReplayWindow, Session
from qoravul.protocol.wire import (
    FrameType,
    ProtocolError,
    Suite,
    make_frame,
    pack_fields,
    parse_frame,
    unpack_fields,
)


@pytest.fixture(scope="module")
def ids():
    return {"node": Identity.generate(), "gw": Identity.generate(), "rogue": Identity.generate()}


def handshake(ids, suite=Suite.HYBRID, allowed=None, registry=None, gw_identity=None):
    node, gw = ids["node"], ids["gw"]
    reg = registry if registry is not None else {node.node_id: node.pk}
    gwh = GatewayHandshake(gw_identity or gw, reg, **({"allowed": allowed} if allowed else {}))
    nh = NodeHandshake(node, gw.pk, suite)
    res = gwh.respond(nh.hello())
    return nh, res


def connected(ids, **kw):
    nh, res = handshake(ids, **kw)
    assert res.session is not None, res.reason
    return nh.finish(res.frame), res.session


def test_hybrid_roundtrip_both_directions(ids):
    node_s, gw_s = connected(ids)
    assert node_s.session_id == gw_s.session_id and len(node_s.session_id) == 8
    for i in range(5):
        ft, pt = gw_s.open(node_s.seal(FrameType.DATA, b"up %d" % i))
        assert (ft, pt) == (FrameType.DATA, b"up %d" % i)
        ft, pt = node_s.open(gw_s.seal(FrameType.DATA, b"down %d" % i))
        assert (ft, pt) == (FrameType.DATA, b"down %d" % i)


def test_record_overhead_is_34_bytes(ids):
    node_s, _ = connected(ids)
    assert len(node_s.seal(FrameType.DATA, b"x" * 100)) - 100 == RECORD_OVERHEAD == 34


def test_pq_only_when_policy_allows(ids):
    node_s, gw_s = connected(ids, suite=Suite.PQ_ONLY, allowed={Suite.HYBRID, Suite.PQ_ONLY})
    assert gw_s.open(node_s.seal(FrameType.DATA, b"pq"))[1] == b"pq"


def test_pq_only_rejected_by_default_policy(ids):
    _, res = handshake(ids, suite=Suite.PQ_ONLY)
    assert res.session is None and res.reason == "suite below policy"


def test_classic_downgrade_rejected(ids):
    nh, res = handshake(ids, suite=Suite.CLASSIC)
    assert res.session is None and res.reason == "suite below policy"
    with pytest.raises(ProtocolError, match="suite below policy"):
        nh.finish(res.frame)


def test_suite_byte_tamper_is_bad_signature(ids):
    node, gw = ids["node"], ids["gw"]
    hello = NodeHandshake(node, gw.pk, Suite.HYBRID).hello()
    _, body = parse_frame(hello)
    f = unpack_fields(body, 6)
    f[0] = bytes([Suite.CLASSIC])  # MITM tries to downgrade in flight
    res = GatewayHandshake(gw, {node.node_id: node.pk}, allowed=set(Suite)).respond(
        make_frame(FrameType.HELLO, pack_fields(f))
    )
    assert res.session is None and res.reason == "bad signature"


def test_unknown_node_rejected(ids):
    _, res = handshake(ids, registry={})
    assert res.session is None and res.reason == "unknown node"


def test_rogue_gateway_detected(ids):
    nh, res = handshake(ids, gw_identity=ids["rogue"])
    assert res.session is not None  # rogue happily answers...
    with pytest.raises(ProtocolError, match="gateway signature invalid"):
        nh.finish(res.frame)  # ...but the node pinned the real gateway key


def test_replay_rejected(ids):
    node_s, gw_s = connected(ids)
    rec = node_s.seal(FrameType.DATA, b"once")
    gw_s.open(rec)
    with pytest.raises(ProtocolError, match="replay"):
        gw_s.open(rec)


def test_out_of_order_within_window_ok(ids):
    node_s, gw_s = connected(ids)
    recs = [node_s.seal(FrameType.DATA, bytes([i])) for i in range(10)]
    for i in [9, 3, 0, 7, 1, 2, 8, 4, 6, 5]:
        assert gw_s.open(recs[i])[1] == bytes([i])
    old = [node_s.seal(FrameType.DATA, b"old")]
    for _ in range(70):
        gw_s.open(node_s.seal(FrameType.DATA, b"new"))
    with pytest.raises(ProtocolError, match="replay"):
        gw_s.open(old[0])  # fell out of the 64-wide window


def test_tamper_rejected(ids):
    node_s, gw_s = connected(ids)
    rec = bytearray(node_s.seal(FrameType.DATA, b"kwh=1.23"))
    rec[-20] ^= 0x01
    with pytest.raises(ProtocolError, match="bad record MAC"):
        gw_s.open(bytes(rec))
    # A forged record must not advance the replay window: the genuine one still opens.
    rec[-20] ^= 0x01
    assert gw_s.open(bytes(rec))[1] == b"kwh=1.23"


def test_type_confusion_data_to_alert(ids):
    node_s, gw_s = connected(ids)
    rec = bytearray(node_s.seal(FrameType.DATA, b"summary"))
    rec[1] = FrameType.ALERT
    with pytest.raises(ProtocolError, match="bad record MAC"):
        gw_s.open(bytes(rec))


def test_reflection_rejected(ids):
    node_s, gw_s = connected(ids)
    rec = node_s.seal(FrameType.DATA, b"mine")
    with pytest.raises(ProtocolError):
        node_s.open(rec)  # node's own UP record bounced back as DN
    rec2 = gw_s.seal(FrameType.DATA, b"gw")
    with pytest.raises(ProtocolError):
        gw_s.open(rec2)


def test_wrong_session_id_rejected(ids):
    a_node, _ = connected(ids)
    _, b_gw = connected(ids)
    with pytest.raises(ProtocolError, match="wrong session"):
        b_gw.open(a_node.seal(FrameType.DATA, b"x"))


def test_replay_window_unit():
    w = ReplayWindow()
    assert not w.check(0)  # seq 0 never valid
    for s in (1, 2, 5):
        w.update(s)
    assert not w.check(5) and not w.check(1)
    assert w.check(3) and w.check(4)
    w.update(4)
    assert not w.check(4)
    w.update(100)
    assert w.top == 100 and not w.check(36) and w.check(37)
    w.update(37)
    assert not w.check(37)
    with pytest.raises(ProtocolError):
        w.update(37)
    w.update(100 + 64)  # shift by exactly the window size
    assert w.bitmap == 1 and not w.check(100)


def test_rekey_limit(ids):
    node_s, _ = connected(ids)
    node_s.send_seq = 2**20
    with pytest.raises(ProtocolError, match="rekey"):
        node_s.seal(FrameType.DATA, b"x")


def test_malformed_frames():
    with pytest.raises(ProtocolError):
        parse_frame(b"\x02\x01")  # bad version
    with pytest.raises(ProtocolError):
        parse_frame(b"\x01\x63")  # unknown type
    with pytest.raises(ProtocolError):
        unpack_fields(struct.pack(">H", 10) + b"abc")
    with pytest.raises(ProtocolError):
        make_frame(FrameType.DATA, b"x" * 70000)


def test_garbage_hello_is_reject_not_crash(ids):
    gwh = GatewayHandshake(ids["gw"], {})
    for junk in (b"", b"\x01\x01", b"\x01\x02abc", make_frame(FrameType.HELLO, b"\x00\x05ab")):
        res = gwh.respond(junk)
        assert res.session is None and parse_frame(res.frame)[0] == FrameType.REJECT


def test_session_rejects_non_record_type(ids):
    node_s, gw_s = connected(ids)
    with pytest.raises(ProtocolError):
        node_s.seal(FrameType.HELLO, b"x")
    with pytest.raises(ProtocolError):
        gw_s.open(make_frame(FrameType.ACCEPT, b"\x00" * 40))


# ------------------------------------------------------------- PSK resumption
from qoravul.protocol.resume import GatewayResume, NodeResume, Ticket, TicketStore  # noqa: E402
from qoravul.protocol.wire import encode_stream  # noqa: E402


def full_then_store(ids, suite=Suite.HYBRID, allowed=None):
    store = TicketStore()
    node, gw = ids["node"], ids["gw"]
    gwh = GatewayHandshake(gw, {node.node_id: node.pk}, allowed=allowed or {Suite.HYBRID}, tickets=store)
    nh = NodeHandshake(node, gw.pk, suite)
    res = gwh.respond(nh.hello())
    return nh.finish(res.frame), res.session, store


def test_resumption_roundtrip_and_size(ids):
    node_s, gw_s, store = full_then_store(ids)
    assert node_s.ticket.ticket_id == gw_s.ticket.ticket_id and len(store) == 1
    nr = NodeResume(node_s.ticket)
    first = nr.hello()
    res = GatewayResume(store, {Suite.HYBRID}).respond(first)
    assert res.session is not None, res.reason
    n2 = nr.finish(res.frame)
    g2 = res.session
    assert g2.peer_id == ids["node"].node_id
    assert n2.session_id == g2.session_id != node_s.session_id
    assert g2.open(n2.seal(FrameType.DATA, b"up"))[1] == b"up"
    assert n2.open(g2.seal(FrameType.DATA, b"dn"))[1] == b"dn"
    size = len(encode_stream(first)) + len(encode_stream(res.frame))
    assert size < 300, size  # vs ~9 KB for the full HYBRID handshake
    # the resumed session minted the next ticket; the old one is gone
    assert n2.ticket.ticket_id == g2.ticket.ticket_id != node_s.ticket.ticket_id
    assert store.peek(node_s.ticket.ticket_id) is None and len(store) == 1


def test_resumption_chain(ids):
    node_s, _, store = full_then_store(ids)
    ticket = node_s.ticket
    gr = GatewayResume(store, {Suite.HYBRID})
    for _ in range(3):
        nr = NodeResume(ticket)
        res = gr.respond(nr.hello())
        ticket = nr.finish(res.frame).ticket
    assert len(store) == 1


def test_resume_replay_rejected(ids):
    node_s, _, store = full_then_store(ids)
    first = NodeResume(node_s.ticket).hello()
    gr = GatewayResume(store, {Suite.HYBRID})
    assert gr.respond(first).session is not None
    res = gr.respond(first)  # captured RESUME replayed
    assert res.session is None and res.reason == "unknown ticket"


def test_resume_tamper_rejected(ids):
    node_s, _, store = full_then_store(ids)
    first = bytearray(NodeResume(node_s.ticket).hello())
    first[30] ^= 1  # inside Nn
    res = GatewayResume(store, {Suite.HYBRID}).respond(bytes(first))
    assert res.session is None and res.reason == "bad resume mac"
    assert len(store) == 1  # a forged RESUME must not burn the genuine ticket


def test_resume_cannot_downgrade_policy(ids):
    # ticket minted while CLASSIC was still allowed ...
    node_s, _, store = full_then_store(ids, suite=Suite.CLASSIC, allowed={Suite.CLASSIC, Suite.HYBRID})
    assert node_s.ticket.suite == Suite.CLASSIC
    # ... is useless once policy is HYBRID-only
    res = GatewayResume(store, {Suite.HYBRID}).respond(NodeResume(node_s.ticket).hello())
    assert res.session is None and res.reason == "suite below policy"


def test_resume_expired_ticket(ids):
    node_s, _, store = full_then_store(ids)
    res = GatewayResume(store, {Suite.HYBRID}).respond(NodeResume(node_s.ticket).hello(),
                                                        now=node_s.ticket.issued + 8 * 24 * 3600)
    assert res.session is None and res.reason == "ticket expired"


def test_resume_rogue_gateway(ids):
    node_s, _, _ = full_then_store(ids)
    nr = NodeResume(node_s.ticket)
    first = nr.hello()
    fake = Ticket(node_s.ticket.ticket_id, b"\x00" * 32, Suite.HYBRID, node_s.ticket.node_id, node_s.ticket.issued)
    rogue_store = TicketStore()
    rogue_store.put(fake)
    # the rogue cannot even validate the RESUME, and cannot forge RESUMED
    assert GatewayResume(rogue_store, {Suite.HYBRID}).respond(first).reason == "bad resume mac"
    other = Ticket.derive(b"x" * 32, b"y" * 48, Suite.HYBRID, node_s.ticket.node_id)
    other.ticket_id = node_s.ticket.ticket_id
    store2 = TicketStore()
    store2.put(other)
    nr2 = NodeResume(other)
    res = GatewayResume(store2, {Suite.HYBRID}).respond(nr2.hello())
    with pytest.raises(ProtocolError, match="gateway resume mac invalid"):
        nr.finish(res.frame)  # RESUMED keyed with a different secret
