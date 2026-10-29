package uz.mpay.core

import com.code_intelligence.jazzer.api.FuzzedDataProvider
import com.code_intelligence.jazzer.junit.FuzzTest
import org.json.JSONException
import uz.mpay.core.pqlink.ClientHandshake
import uz.mpay.core.pqlink.DeviceKey
import uz.mpay.core.pqlink.PqLink
import uz.mpay.core.pqlink.PqLinkException
import uz.mpay.core.pqlink.ServerIdentity
import java.security.cert.CertificateException

/**
 * Kotlin yadrosi uchun Jazzer fuzz testlari (3-faza tayyorgarligi). Oddiy `test` da — regressiya
 * rejimi (`src/test/resources/.../FuzzTestsInputs/<test>/` kirishlari); haqiqiy fuzzing:
 * `JAZZER_FUZZ=1 ./gradlew :mpay-core:test --tests 'uz.mpay.core.FuzzTests.<test>'`
 * (`scripts/android-fuzz.sh`).
 *
 * Har testda faqat **hujjatlashtirilgan** xatolar ushlanadi — boshqa har qanday istisno (indeks,
 * null, arifmetika) topilma hisoblanadi.
 */
class FuzzTests {
    /** BER-TLV: tahlil → qayta kodlash → qayta tahlil = o'sha daraxt. */
    @FuzzTest(maxDuration = "60s")
    fun tlvRoundtrip(data: ByteArray) {
        val list = try {
            Tlv.parseAll(data)
        } catch (e: TlvException) {
            return
        }
        val again = Tlv.parseAll(Tlv.encodeAll(list))
        check(again.size == list.size) { "TLV roundtrip: element soni" }
        check(Tlv.encodeAll(again).contentEquals(Tlv.encodeAll(list))) { "TLV roundtrip: baytlar" }
    }

    /** Hex: muvaffaqiyatli dekodlangan satr qat'iy hex bo'lishi shart (`decode → encode` = kirish). */
    @FuzzTest(maxDuration = "30s")
    fun hexStrict(s: String?) {
        if (s == null) return
        val b = try {
            Hex.decode(s)
        } catch (e: IllegalArgumentException) {
            return
        }
        val norm = s.replace(" ", "")
        check(Hex.encode(b).equals(norm, ignoreCase = true)) { "hex qat'iy emas: '$s' qabul qilindi" }
    }

    /** HCE applet: ixtiyoriy C-APDU ketma-ketligi. Istisno yo'q, javob ≥ 2 bayt, ATC kamaymaydi, LUK limiti. */
    @FuzzTest(maxDuration = "60s")
    fun appletApduSequence(d: FuzzedDataProvider) {
        val luk = ByteArray(16) { 7 }
        val p = CardProfile(
            "tok_00000000000000000000000000000001", "9900770000001230", "2912", 0,
            mutableListOf(CardLuk(3, luk, Long.MAX_VALUE, 2)), 0,
        )
        var verified = false
        val gate = object : CdcvmGate {
            override fun isVerified() = verified
            override fun consume() { verified = false }
        }
        val applet = CardApplet({ p }, gate, now = { 1_800_000_000 })
        var lastAtc = p.atc
        repeat(d.consumeInt(1, 12)) {
            verified = d.consumeBoolean()
            val apdu = d.consumeBytes(d.consumeInt(0, 300))
            val r = applet.process(apdu)
            check(r.size >= 2) { "javob 2 baytdan qisqa" }
            check(p.atc >= lastAtc) { "ATC kamaydi" }
            check(p.atc <= 2) { "LUK limiti (2) oshdi: ATC ${p.atc}" }
            check(p.luks.all { it.usesLeft >= 0 }) { "LUK foydalanishi manfiy" }
            lastAtc = p.atc
        }
    }

    /** MITM serverdan ixtiyoriy ServerHello: faqat `PqLinkException`, hech qachon muvaffaqiyat. */
    @FuzzTest(maxDuration = "60s")
    fun serverHello(d: FuzzedDataProvider) {
        val pinned = ServerIdentity(ByteArray(32) { 1 }, ByteArray(PqLink.MLDSA65_PK_LEN) { 2 })
        val device = object : DeviceKey {
            override fun certChain() = listOf(byteArrayOf(0x30, 0x00))
            override fun sign(message: ByteArray) = byteArrayOf(0x30, 0x00)
        }
        val hs = ClientHandshake.start(pinned)
        try {
            hs.onServerHello(d.consumeRemainingAsBytes(), device)
        } catch (e: PqLinkException) {
            return
        }
        error("soxta ServerHello qabul qilindi (pinlangan identifikator imzosiz)")
    }

    /** PQ Link yozuvi: kalitsiz soxta yozuv hech qachon ochilmaydi. */
    @FuzzTest(maxDuration = "30s")
    fun recordOpen(d: FuzzedDataProvider) {
        val key = ByteArray(32) { 9 }
        val sid = d.consumeBytes(16).copyOf(16)
        try {
            PqLink.open(key, PqLink.T_RECORD, sid, d.consumeRemainingAsBytes(), PqLink.DIR_S2C)
        } catch (e: PqLinkException) {
            return
        }
        error("soxta yozuv ochildi")
    }

    /** Bekor qilish ro'yxati: imzosiz JSON hech qachon qabul qilinmaydi. */
    @FuzzTest(maxDuration = "30s")
    fun revocationsJson(json: String?) {
        if (json == null) return
        try {
            Revocations.verify(json, "ab".repeat(32))
        } catch (e: JSONException) {
            return
        } catch (e: PinException) {
            return
        } catch (e: IllegalArgumentException) {
            return
        }
        error("imzosiz bekor qilish ro'yxati qabul qilindi")
    }

    /** Terminal paketi: buzilgan JSON/PEM — faqat hujjatlashtirilgan xatolar. */
    @FuzzTest(maxDuration = "30s")
    fun terminalBundle(json: String?) {
        if (json == null) return
        try {
            TerminalBundle.parse(json)
        } catch (e: JSONException) {
        } catch (e: IllegalArgumentException) {
        } catch (e: CertificateException) {
        }
    }
}
