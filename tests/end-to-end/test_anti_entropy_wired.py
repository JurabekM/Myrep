"""Anti-entropiya ILOVAGA ulanganini tekshiradi.

Bu sinov jonli sinovda topilgan bo'shliqdan keyin yozildi: anti-entropiya
kodi bor edi, sinov stendida ishlardi, lekin ishlayotgan ilovaning
sinxronizatsiya aylanishida HECH QACHON chaqirilmasdi. Natijada telefon
ulanishdan oldin kompyuterda yaratilgan mahsulotni hech qachon olmadi —
u faqat o'zi tinglab turgan paytdagi hodisalarni ko'rardi.

Ya'ni «kod bor» va «kod ishlaydi» boshqa narsa. Bu sinov aynan shu
ulanishni qulflaydi.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field

from distribos.app_context import AppContext


@dataclass
class _Dvigatel:
    """Faqat aylanish nimani chaqirishini kuzatadi."""

    digestlar: int = 0
    yiqilsin: bool = False
    hodisalar: list[str] = field(default_factory=list)

    def publish_pending(self) -> int:
        return 0

    def send_digest(self) -> None:
        self.digestlar += 1
        if self.yiqilsin:
            raise RuntimeError("tarmoq yo'q")

    def queue_depth(self) -> tuple[int, int]:
        return 0, 0

    class _Stats:
        received_events = 0

    stats = _Stats()


class _Baza:
    @contextlib.contextmanager
    def unit_of_work(self):
        yield None

    def dispose(self) -> None:
        pass


class _Buyruq:
    def replay_pending(self, session) -> None:
        pass


def _kontekst(dvigatel: _Dvigatel) -> AppContext:
    return AppContext(
        settings=None, database=_Baza(), provider=None, store=None,
        command=_Buyruq(), engine=dvigatel, invitations=None,
        provisioning=None, secret_store=None,
        device_id=b"" * 16, tenant_id=b"" * 16,
    )


def test_aylanish_digest_yuboradi():
    dvigatel = _Dvigatel()
    _kontekst(dvigatel).run_sync_cycle()
    assert dvigatel.digestlar == 1, "sinxronizatsiya aylanishi digest yubormadi"


def test_digest_har_aylanishda_yuborilmaydi():
    """Ochiq brokerda keraksiz trafik bo'lmasin."""
    dvigatel = _Dvigatel()
    kontekst = _kontekst(dvigatel)
    for _ in range(5):
        kontekst.run_sync_cycle()
    assert dvigatel.digestlar == 1, "digest har aylanishda yuborilyapti"


def test_oraliq_otgach_qayta_yuboriladi():
    dvigatel = _Dvigatel()
    kontekst = _kontekst(dvigatel)
    kontekst.run_sync_cycle()
    kontekst._last_digest_at -= kontekst.digest_interval_seconds + 1
    kontekst.run_sync_cycle()
    assert dvigatel.digestlar == 2


def test_digest_xatosi_ishni_toxtatmaydi():
    """Digest yuborilmasa ham biznes aylanishi davom etsin."""
    dvigatel = _Dvigatel(yiqilsin=True)
    kontekst = _kontekst(dvigatel)

    kontekst.run_sync_cycle()   # xato ko'tarilmasligi kerak

    assert dvigatel.digestlar == 1
