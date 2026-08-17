"""Panel 5 — S-FILE: bo'laklash, Merkle daraxti va yaxlitlik hujumlari (spec §7)."""
from __future__ import annotations

import os
from dataclasses import replace

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...crypto.primitives import random_bytes
from ...protocol.sfile import decrypt_metadata
from ...sim.world import World
from .. import theme as T
from ..widgets import Badge, Card, KeyValue, Table, fmt_hex, page_header, scroll_page


class SFilePanel(QWidget):
    def __init__(self, state, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        self.world: World | None = None
        self.enc = None

        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)
        root.addWidget(
            page_header(
                "S-FILE — fayl shifrlash va yaxlitlik",
                "Spec §7: har bo'lak alohida kalit bilan shifrlanadi, "
                "AAD_i ichida indeks va total_chunks bo'ladi, ildiz Merkle "
                "daraxtidan quriladi va yig'ishdan OLDIN tekshiriladi.",
            )
        )

        # ---------------- manba ----------------
        src = Card("Manba fayl")
        row = QHBoxLayout()
        row.setSpacing(8)
        self.size_box = QComboBox()
        for label, n in [
            ("64 KiB (tasodifiy)", 64 * 1024),
            ("512 KiB (tasodifiy)", 512 * 1024),
            ("2 MiB (tasodifiy)", 2 * 1024 * 1024),
        ]:
            self.size_box.addItem(label, n)
        self.chunk_box = QSpinBox()
        self.chunk_box.setRange(1, 4096)
        self.chunk_box.setValue(64)
        self.chunk_box.setSuffix(" KiB bo'lak")
        btn_gen = QPushButton("Shifrlash va yuklash")
        btn_gen.setObjectName("Primary")
        btn_gen.clicked.connect(self.encrypt_random)
        btn_pick = QPushButton("Diskdan tanlash…")
        btn_pick.setObjectName("Ghost")
        btn_pick.clicked.connect(self.encrypt_from_disk)
        row.addWidget(self.size_box)
        row.addWidget(self.chunk_box)
        row.addWidget(btn_gen)
        row.addWidget(btn_pick)
        row.addStretch(1)
        src.add(row)
        root.addWidget(src)

        # ---------------- manifest ----------------
        man = Card("Manifest")
        self.kv = KeyValue()
        for k in ("file_id", "plaintext_size", "chunk_size", "total_chunks",
                  "file_salt", "root_hash", "name (deshifrlangan)",
                  "mime (deshifrlangan)", "ciphertext hajmi"):
            self.kv.add_row(k)
        man.add(self.kv)
        root.addWidget(man)

        # ---------------- hujumlar ----------------
        atk = Card("Yaxlitlik hujumlari",
                   "Har bir tugma serverdagi saqlangan ciphertextni buzadi, "
                   "so'ng qabul qilish jarayoni qayta ishga tushiriladi.")
        arow = QHBoxLayout()
        arow.setSpacing(8)
        for label, slot in [
            ("Bo'lakni o'zgartirish", self.tamper),
            ("Faylni qisqartirish", self.truncate),
            ("Bo'lakni dublikat qilish", self.duplicate),
            ("Asl holatga qaytarish", self.restore),
        ]:
            b = QPushButton(label)
            b.setObjectName("Danger" if "qaytarish" not in label else "Ghost")
            b.clicked.connect(slot)
            arow.addWidget(b)
        arow.addStretch(1)
        self.verdict = Badge("tekshirilmagan", T.DIM)
        arow.addWidget(self.verdict)
        atk.add(arow)
        self.detail = QLabel("")
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet(f"color:{T.MUTED}; font-size:12px;")
        atk.add(self.detail)
        root.addWidget(atk)

        # ---------------- bo'laklar ----------------
        ch = Card("Bo'laklar va Merkle barglari")
        self.table = Table(["#", "ciphertext", "leaf = SHA3-256", "holat"])
        self.table.setMinimumHeight(280)
        ch.add(self.table)
        root.addWidget(ch)
        root.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll_page(inner))
        self.state.world_changed.connect(self.reset)

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.world = None
        self.enc = None
        self.table.clear_rows()
        self.verdict.set("tekshirilmagan", T.DIM)
        self.detail.setText("")
        for k in self.kv._rows:
            self.kv.set(k, "—", T.DIM)

    def _cfg(self):
        return replace(self.state.cfg, chunk_size=self.chunk_box.value() * 1024)

    def encrypt_random(self) -> None:
        n = self.size_box.currentData()
        self._encrypt(random_bytes(n), f"tasodifiy-{n}.bin", "application/octet-stream")

    def encrypt_from_disk(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Fayl tanlang")
        if not path:
            return
        try:
            with open(path, "rb") as fh:
                data = fh.read(16 * 1024 * 1024)
        except OSError as exc:
            self.detail.setText(f"O'qib bo'lmadi: {exc}")
            return
        self._encrypt(data, os.path.basename(path), "application/octet-stream")

    def _encrypt(self, data: bytes, name: str, mime: str) -> None:
        cfg = self._cfg()
        self.world = World(cfg, self.state.trace)
        self.world.handshake()
        self.enc, res = self.world.send_file(self.world.alice, data, name, mime)
        self._fill_manifest(res)
        self._fill_chunks(res)

    # ------------------------------------------------------------------
    def _fill_manifest(self, res=None) -> None:
        if self.enc is None:
            return
        m = self.enc.manifest
        cfg = self.world.cfg
        self.kv.set("file_id", m["file_id"].hex(), T.ACCENT)
        self.kv.set("plaintext_size", f"{m['plaintext_size']:,} bayt")
        self.kv.set("chunk_size", f"{m['chunk_size']:,} bayt")
        self.kv.set("total_chunks", str(m["total_chunks"]))
        self.kv.set("file_salt", fmt_hex(m["file_salt"], 16), T.ACCENT)
        self.kv.set("root_hash", m["root_hash"].hex(), T.VIOLET)
        meta = decrypt_metadata(m, self.enc.fk, cfg)
        self.kv.set("name (deshifrlangan)", str(meta["name"]), T.OK)
        self.kv.set("mime (deshifrlangan)", str(meta["mime"]), T.OK)
        self.kv.set("ciphertext hajmi", f"{self.enc.total_ciphertext:,} bayt")
        if res is not None:
            self._verdict(res)

    def _verdict(self, res) -> None:
        if res.ok:
            self.verdict.set("QABUL QILINDI", T.OK)
            self.detail.setText(
                "Barcha bo'laklar AEAD tegidan va Merkle ildizidan o'tdi; "
                "ochiq matn to'liq tiklandi."
            )
        else:
            self.verdict.set("RAD ETILDI", T.FAIL)
            bad = ", ".join(map(str, res.failed)) or "—"
            self.detail.setText(
                f"Sabab: {res.error}. Muvaffaqiyatsiz bo'laklar: {bad}. "
                f"root_hash tekshiruvi: {'o`tdi' if res.root_ok else 'o`tmadi'}."
            )

    def _fill_chunks(self, res=None) -> None:
        self.table.clear_rows()
        if self.enc is None:
            return
        status = {}
        if res is not None:
            status = {r.index: r for r in res.reports}
        for c in self.enc.chunks:
            r = status.get(c.index)
            if r is None:
                st, col = ("—", T.DIM)
            elif r.ok:
                st, col = ("OK", T.OK)
            else:
                st, col = (r.reason[:40], T.FAIL)
            self.table.add_row(
                [c.index, f"{c.size:,} B", fmt_hex(c.leaf, 16), st],
                [T.DIM, T.MUTED, T.ACCENT, col],
                mono_cols=(2,),
            )
        self.table.resizeColumnsToContents()

    # ------------------------------------------------------------------
    def _need(self) -> bool:
        if self.enc is None or self.world is None:
            self.detail.setText("Avval faylni shifrlab yuklang.")
            return False
        return True

    def tamper(self) -> None:
        if not self._need():
            return
        idx = min(1, self.enc.manifest["total_chunks"] - 1)
        self.world.server.tamper_chunk(self.enc.file_id, idx, b"\x01")
        self._recheck()

    def truncate(self) -> None:
        if not self._need():
            return
        total = self.enc.manifest["total_chunks"]
        if total < 2:
            self.detail.setText("Qisqartirish uchun kamida 2 bo'lak kerak.")
            return
        self.world.server.truncate_file(self.enc.file_id, total - 1)
        self._recheck()

    def duplicate(self) -> None:
        if not self._need():
            return
        blob = self.world.server.blobs[self.enc.file_id]
        if len(blob.chunks) < 2:
            return
        blob.chunks[1] = blob.chunks[0]
        self.state.trace.attack("server", "1-bo'lak 0-bo'lak bilan almashtirildi")
        self._recheck()

    def restore(self) -> None:
        if not self._need():
            return
        self.world.server.upload(self.enc.file_id, self.enc.chunks)
        self._recheck()

    def _recheck(self) -> None:
        res = self.world.reverify_file(self.enc.file_id)
        self._verdict(res)
        self._fill_chunks(res)
