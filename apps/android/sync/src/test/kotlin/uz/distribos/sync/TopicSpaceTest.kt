package uz.distribos.sync

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Topik fazasining tengligi.
 *
 * Bu sinov jonli sinovda topilgan xatodan keyin yozildi: ulash paytida
 * faza ikki joydan o'rnatilardi (taklifdan va kompaniya qabul
 * qilinganda). Ikkalasi ham BIR XIL fazani berardi, lekin transport
 * buni bilmagani uchun bir xil topikka ikki marta obuna bo'lardi.
 *
 * Natijada telefon har xabarni ikki nusxada olardi va ikkinchisini
 * takror himoyasi «HUJUM» deb qayd etardi: 3 daqiqada 45 ta soxta
 * xavfsizlik ogohlantirishi. Haqiqiy hujum ular orasida ko'rinmasdi.
 */
class TopicSpaceTest {

    private val tenantId = ByteArray(16) { it.toByte() }

    @Test
    fun `bir xil kompaniya fazalari teng`() {
        assertEquals(
            Topics.Space.create(tenantId, "pilot"),
            Topics.Space.create(tenantId, "pilot"),
        )
    }

    @Test
    fun `taklifdan qurilgan faza kompaniyanikiga teng`() {
        // AYNAN shu tenglik ikki marta obunani to'xtatadi.
        val kompaniya = Topics.Space.create(tenantId, "pilot")
        val taklifdan = Topics.Space.fromTopicId(
            Topics.opaqueTenantId(tenantId), "pilot"
        )
        assertEquals(kompaniya, taklifdan)
        assertEquals(kompaniya.hashCode(), taklifdan.hashCode())
    }

    @Test
    fun `boshqa kompaniya fazasi teng emas`() {
        val boshqa = ByteArray(16) { (it + 1).toByte() }
        assertNotEquals(
            Topics.Space.create(tenantId, "pilot"),
            Topics.Space.create(boshqa, "pilot"),
        )
    }

    @Test
    fun `boshqa muhit fazasi teng emas`() {
        assertNotEquals(
            Topics.Space.create(tenantId, "pilot"),
            Topics.Space.create(tenantId, "production"),
        )
    }

    @Test
    fun `obunalar bir-birini qoplamaydi`() {
        // Ikki obuna bir xil xabarga mos kelsa, xabar ikki marta
        // yetkaziladi — bu ham soxta «replay» yasaydi.
        val obunalar = Topics.Space.create(tenantId, "pilot")
            .subscriptions(ByteArray(16) { 7 })
            .map { it.first }

        assertEquals(obunalar.size, obunalar.toSet().size)
        for (a in obunalar) {
            for (b in obunalar) {
                if (a == b) continue
                assertTrue(
                    "«$a» va «$b» bir-birini qoplaydi",
                    !mosKeladi(a, b) && !mosKeladi(b, a),
                )
            }
        }
    }

    /** MQTT naqshi (`+`) berilgan topikka mos keladimi. */
    private fun mosKeladi(naqsh: String, topic: String): Boolean {
        val n = naqsh.split("/")
        val t = topic.split("/")
        if (n.size != t.size) return false
        return n.indices.all { n[it] == "+" || n[it] == t[it] }
    }
}
