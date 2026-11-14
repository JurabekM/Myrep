"""Reliz APK'ning Q5 kafolatlarini yig'ilgan faylning o'zida tekshiradi (manba kodga ishonmasdan).

  py tools/check_release.py <apk|aab> [...] [--allow-debug] [--expect-cert AB:CD:...]

1. Manifestda INTERNET va ACCESS_NETWORK_STATE ruxsatlari YO'Q (aapt2 dump permissions).
2. Faqat kutilgan ruxsatlar bor (yangi ruxsat qo'shilsa, ataylab ko'rib chiqish uchun yiqiladi).
3. assets/db/rostor-db.bundle.json mavjud va imzosi DbKeys.kt dagi ochiq kalit bilan haqiqiy.
4. debuggable emas.
5. (F4) apksigner bilan imzo haqiqiy, v2+ sxema bor, kalit debug emas (--allow-debug faqat SINOV
   nusxalari uchun); --expect-cert berilsa APK sertifikati SHA-256 shu xeshga teng.

AAB (Play'ga yuklanadigan fayl): manifest proto formatida, shuning uchun ehtiyotkor tekshiruv —
INTERNET / ACCESS_NETWORK_STATE manifestning HECH bir joyida uchramasligi, baza imzosi va upload
sertifikati debug emasligi (keytool). AAB upload kaliti bilan imzolanadi, Play esa app signing
kaliti bilan qayta imzolaydi — shuning uchun --expect-cert AAB'ga qo'llanmaydi.
"""
import argparse
import base64
import os
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "rostor_db"))
from rostor_db import DOMAIN, KEYS_KT, hybrid_verify, key_id, sha3  # noqa: E402

SDK = Path.home() / "AppData" / "Local" / "Android" / "Sdk"
ALLOWED = {
    "android.permission.QUERY_ALL_PACKAGES",
    "android.permission.POST_NOTIFICATIONS",  # F2: Qo'ng'iroq Qalqoni ogohlantirishi
    "uz.rostor.rostor2.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
}
FORBIDDEN = {"android.permission.INTERNET", "android.permission.ACCESS_NETWORK_STATE"}


def aapt2() -> str:
    tools = sorted((SDK / "build-tools").iterdir(), reverse=True)
    return str(tools[0] / "aapt2.exe")


def apksigner() -> str:
    tools = sorted((SDK / "build-tools").iterdir(), reverse=True)
    return str(tools[0] / ("apksigner.bat" if os.name == "nt" else "apksigner"))


def check_signature(apk: Path, allow_debug: bool, expect: str | None) -> tuple[list[str], str]:
    r = subprocess.run([apksigner(), "verify", "--print-certs", "-v", str(apk)], capture_output=True, text=True)
    out = r.stdout + r.stderr
    if r.returncode != 0 or "Verifies" not in out:
        return [f"apksigner imzoni tasdiqlamadi: {out.strip()[:300]}"], ""
    errors = []
    if not re.search(r"Verified using v[234](\.\d)? scheme.*: true", out):
        errors.append("v2/v3 imzo sxemasi yo'q")
    # "-v" bilan apksigner "V2 Signer: certificate DN:" yozadi, "-v" siz — "Signer #1 certificate DN:".
    dn = re.search(r"Signer(?: #1)?:? certificate DN: (.+)", out)
    sha = re.search(r"Signer(?: #1)?:? certificate SHA-256 digest: ([0-9a-f]{64})", out)
    if not dn or not sha:
        # Yopiq holatda yiqilamiz: imzolovchini o'qiy olmasak, debug emasligini ham bilmaymiz.
        return errors + ["imzolovchi sertifikati o'qilmadi (apksigner chiqishi o'zgarganmi?)"], "?"
    dn = dn.group(1).strip()
    sha = sha.group(1)
    if "CN=Android Debug" in dn and not allow_debug:
        errors.append("APK debug kaliti bilan imzolangan (reliz kaliti: tools/create_upload_key.ps1)")
    if expect and sha != expect:
        errors.append(f"sertifikat xeshi kutilganidan farq qiladi: {sha} != {expect}")
    return errors, f"{dn} sha256={sha}"


def pinned_keys() -> tuple[bytes, bytes]:
    src = KEYS_KT.read_text(encoding="utf-8")
    ed = re.search(r'ED25519_PK: ByteArray = "([0-9a-f]+)"', src).group(1)
    ml = "".join(re.findall(r'"([0-9a-f]{2,})"', src.split("MLDSA65_PK")[1]))
    return bytes.fromhex(ed), bytes.fromhex(ml)


def check_db(raw: bytes) -> tuple[list[str], str]:
    bundle = json.loads(raw)
    ed, ml = pinned_keys()
    manifest = base64.b64decode(bundle["manifest"])
    payload = base64.b64decode(bundle["payload"])
    errors = []
    if not hybrid_verify(ed, ml, base64.b64decode(bundle["sig"]), DOMAIN + manifest):
        errors.append("baza imzosi DbKeys bilan tasdiqlanmadi")
    m = json.loads(manifest)
    if m["payload_sha3_256"] != sha3(payload).hex() or m["key_id"] != key_id(ed, ml):
        errors.append("baza manifesti mos emas")
    return errors, f"baza v{m['db_version']} key_id={m['key_id']}"


def keytool() -> str:
    for jdk in (os.environ.get("JAVA_HOME"), r"C:\Program Files\Android\Android Studio\jbr"):
        if jdk and (Path(jdk) / "bin" / "keytool.exe").exists():
            return str(Path(jdk) / "bin" / "keytool.exe")
    return "keytool"


def check_aab(aab: Path, allow_debug: bool) -> list[str]:
    errors = []
    with zipfile.ZipFile(aab) as z:
        manifest = z.read("base/manifest/AndroidManifest.xml")
        try:
            db_raw = z.read("base/assets/db/rostor-db.bundle.json")
        except KeyError:
            db_raw = None
    for p in sorted(FORBIDDEN):
        if p.encode() in manifest:
            errors.append(f"taqiqlangan ruxsat AAB manifestida: {p}")
    if db_raw is None:
        errors.append("baza fayli AAB ichida yo'q")
        info = "baza yo'q"
    else:
        e, info = check_db(db_raw)
        errors += e
    out = subprocess.run([keytool(), "-printcert", "-jarfile", str(aab)], capture_output=True, text=True).stdout
    owner = re.search(r"Owner: (.+)", out)
    sha = re.search(r"SHA256: ([0-9A-F:]{95})", out)
    if not owner or not sha:
        errors.append("AAB imzolanmagan yoki sertifikat o'qilmadi")
        signer = "?"
    else:
        signer = f"{owner.group(1).strip()} sha256={sha.group(1).replace(':', '').lower()}"
        if "CN=Android Debug" in owner.group(1) and not allow_debug:
            errors.append("AAB debug kaliti bilan imzolangan (Play qabul qilmaydi)")
    print(f"{aab.name}: {info}")
    print(f"  upload imzo: {signer}")
    return errors


def check(apk: Path, allow_debug: bool = False, expect: str | None = None) -> list[str]:
    if apk.suffix == ".aab":
        return check_aab(apk, allow_debug)
    errors, signer = check_signature(apk, allow_debug, expect)
    out = subprocess.run([aapt2(), "dump", "permissions", str(apk)], capture_output=True, text=True, check=True).stdout
    perms = set(re.findall(r"uses-permission: name='([^']+)'", out))
    for p in sorted(perms & FORBIDDEN):
        errors.append(f"taqiqlangan ruxsat bor: {p}")
    for p in sorted(perms - ALLOWED - FORBIDDEN):
        errors.append(f"kutilmagan ruxsat: {p}")
    badging = subprocess.run([aapt2(), "dump", "badging", str(apk)], capture_output=True, text=True, check=True).stdout
    if "application-debuggable" in badging:
        errors.append("APK debuggable")
    with zipfile.ZipFile(apk) as z:
        try:
            db_raw = z.read("assets/db/rostor-db.bundle.json")
        except KeyError:
            return errors + ["baza fayli APK ichida yo'q"]
    e, info = check_db(db_raw)
    errors += e
    print(f"{apk.name}: ruxsatlar={sorted(perms)}, {info}")
    print(f"  imzo: {signer}")
    return errors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("apks", nargs="+")
    ap.add_argument("--allow-debug", action="store_true", help="debug imzoli SINOV nusxasiga ruxsat")
    ap.add_argument("--expect-cert", help="kutilgan sertifikat SHA-256 (ikki nuqtali yoki yo'q)")
    a = ap.parse_args()
    expect = a.expect_cert.replace(":", "").lower() if a.expect_cert else None
    failed = False
    for apk in a.apks:
        errs = check(Path(apk), a.allow_debug, expect)
        for e in errs:
            print(f"  XATO: {e}")
        failed |= bool(errs)
        if not errs:
            print("  OK: INTERNET yo'q, baza imzosi haqiqiy" + ("" if apk.endswith(".aab") else ", ruxsatlar kutilgandek, debuggable emas") + (", imzo: SINOV (debug kaliti)" if a.allow_debug else ", imzo reliz uchun yaroqli"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
