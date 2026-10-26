package uz.mpay.core

import org.json.JSONObject
import uz.mpay.core.pqlink.ServerIdentity
import java.nio.ByteBuffer
import java.security.MessageDigest

/**
 * Bekor qilingan server identifikatorlari (ADR-0014): oflayn ildiz kaliti imzolagan ro'yxat.
 * Ilovaga faqat ildiz barmoq izi joylanadi; xabar Rust `revocation_message` bilan bayt-bir xil.
 */
class Revocations(val version: Long, val revoked: Set<String>) {
    companion object {
        const val FORMAT = "mpay-pqlink-revocations/1"
        private val LABEL = "MPAY-PQLINK-V1 revocations".toByteArray(Charsets.US_ASCII)

        internal fun message(version: Long, revokedHex: Collection<String>): ByteArray {
            val list = revokedHex.map { it.lowercase() }.toSortedSet().map(Hex::decode)
            val b = ByteBuffer.allocate(LABEL.size + 12 + list.size * 32)
            b.put(LABEL).putLong(version).putInt(list.size)
            list.forEach { require(it.size == 32) { "barmoq izi 32 bayt" }; b.put(it) }
            return b.array()
        }

        /** Ildiz barmoq izi pinlanganga teng va gibrid imzo to'g'ri bo'lsagina qaytaradi. */
        fun verify(json: String, pinnedRootFingerprint: String): Revocations {
            val j = JSONObject(json)
            if (j.optString("format") != FORMAT) throw PinException("bekor qilish ro'yxati formati noma'lum")
            val root = ServerIdentity(Hex.decode(j.getString("root_ed25519")), Hex.decode(j.getString("root_mldsa65")))
            if (!MessageDigest.isEqual(root.fingerprint(), Hex.decode(pinnedRootFingerprint))) {
                throw PinException("bekor qilish ro'yxati ildizi pinlanmagan")
            }
            val version = j.getLong("version")
            val arr = j.getJSONArray("revoked")
            val revoked = (0 until arr.length()).map { arr.getString(it).lowercase() }
            val ok = root.verifyHybrid(message(version, revoked), Hex.decode(j.getString("sig_ed25519")), Hex.decode(j.getString("sig_mldsa65")))
            if (!ok) throw PinException("bekor qilish ro'yxati imzosi noto'g'ri")
            return Revocations(version, revoked.toSet())
        }
    }
}
