package uz.rostor.rostor2

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import uz.rostor.rostor2.crypto.Hybrid
import uz.rostor.rostor2.crypto.hexToBytes
import uz.rostor.rostor2.crypto.toHex
import uz.rostor.rostor2.db.DbBundle
import uz.rostor.rostor2.db.DbKeys
import java.util.Base64

/** Python (tools/rostor_db) va ROSTOR-1 referensi bilan bayt darajasidagi moslik. */
class DbBundleTest {
    private val kat = JSONObject(javaClass.classLoader!!.getResource("db-kat.json")!!.readText())
    private val edPk = kat.getString("ed25519_pk").hexToBytes()
    private val mlPk = kat.getString("mldsa65_pk").hexToBytes()
    private val bundle = kat.getString("bundle")

    private fun mutate(field: String, f: (ByteArray) -> ByteArray): String {
        val o = JSONObject(bundle)
        val b64 = Base64.getDecoder().decode(o.getString(field))
        o.put(field, Base64.getEncoder().encodeToString(f(b64)))
        return o.toString()
    }

    @Test fun pythonBundleVerifies() {
        val r = DbBundle.verify(bundle, edPk, mlPk, 0)
        assertTrue(r.error, r.ok)
        assertEquals(kat.getLong("db_version"), r.dbVersion)
        assertEquals(kat.getString("key_id"), r.keyId)
        assertEquals(kat.getString("payload_sha3_256"), Hybrid.sha3_256(r.payloadJson!!.toByteArray()).toHex())
    }

    @Test fun rostor1ReferenceSignatureVerifies() {
        val v = kat.getJSONObject("rostor1_vector")
        assertTrue(Hybrid.verify(edPk, mlPk, v.getString("sig").hexToBytes(), v.getString("msg").hexToBytes()))
    }

    @Test fun tamperedPayloadRejected() {
        val r = DbBundle.verify(mutate("payload") { it.copyOf().also { b -> b[5] = (b[5] + 1).toByte() } }, edPk, mlPk, 0)
        assertFalse(r.ok)
        assertEquals("baza xeshi mos emas", r.error)
    }

    @Test fun tamperedManifestRejected() {
        val r = DbBundle.verify(mutate("manifest") { it.copyOf().also { b -> b[10] = (b[10] + 1).toByte() } }, edPk, mlPk, 0)
        assertFalse(r.ok)
        assertEquals("baza imzosi haqiqiy emas", r.error)
    }

    @Test fun bothSignaturesRequired() {
        // Ed25519 qismi butun, faqat ML-DSA qismi buzilgan: "bittasi o'tsa bo'ldi" MUST NOT.
        val pqBroken = mutate("sig") { it.copyOf().also { b -> b[Hybrid.ED25519_SIG + 100] = (b[Hybrid.ED25519_SIG + 100] + 1).toByte() } }
        assertFalse(DbBundle.verify(pqBroken, edPk, mlPk, 0).ok)
        val edBroken = mutate("sig") { it.copyOf().also { b -> b[3] = (b[3] + 1).toByte() } }
        assertFalse(DbBundle.verify(edBroken, edPk, mlPk, 0).ok)
    }

    @Test fun rollbackRejected() {
        val r = DbBundle.verify(bundle, edPk, mlPk, 8)
        assertFalse(r.ok)
        assertTrue(r.error!!.startsWith("baza versiyasi pasaytirilgan"))
        assertTrue(DbBundle.verify(bundle, edPk, mlPk, 7).ok)
    }

    @Test fun productionKeyDoesNotAcceptTestBundle() {
        assertFalse(DbBundle.verify(bundle, DbKeys.ED25519_PK, DbKeys.MLDSA65_PK, 0).ok)
    }

    @Test fun garbageRejected() {
        assertFalse(DbBundle.verify("not json", edPk, mlPk, 0).ok)
        assertFalse(DbBundle.verify("{\"format\":\"other\"}", edPk, mlPk, 0).ok)
    }
}
