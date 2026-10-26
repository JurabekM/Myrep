package uz.sectorverify.format

import java.security.KeyFactory
import java.security.Signature
import java.security.spec.PKCS8EncodedKeySpec

/** Test resurslaridagi faqat testlar uchun EC P-256 kalit. */
object TestSigner : ReportSigner {
    private fun res(name: String) = requireNotNull(TestSigner::class.java.getResourceAsStream("/$name")).readBytes()
    private val key = KeyFactory.getInstance("EC").generatePrivate(PKCS8EncodedKeySpec(res("test-key.pk8")))
    private val cert = res("test-cert.der")

    override fun sign(data: ByteArray): ByteArray = Signature.getInstance("SHA256withECDSA").run {
        initSign(key)
        update(data)
        sign()
    }

    override fun certificateChain(): List<ByteArray> = listOf(cert)
}
