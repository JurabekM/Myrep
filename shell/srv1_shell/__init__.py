"""SRV_1 shell: PyQt6 klient. Biznes-mantiq yo'q, faqat yadro API'si orqali ishlaydi."""

import os

__version__ = "1.1.1"

# pyqtgraph numpy'ni yuklaydi; numpy esa har protsessor yadrosi uchun BLAS oqim
# havzasini ochadi (8 yadroda +230 MB xususiy xotira). Shell chiziqli algebra
# qilmaydi, shuning uchun bitta oqim yetarli. numpy import bo'lishidan oldin
# o'rnatilishi shart — shu sabab paketning eng boshida.
for _variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_variable, "1")
