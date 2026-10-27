package uz.barakadaftari.app.native

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class SecurityApiImplTest {
    @get:Rule
    val tmp = TemporaryFolder()

    private fun api(picker: DocumentPicker? = null): SecurityApiImpl {
        val blobs = SecureBlobStore(tmp.newFolder(), AesGcmKeyWrapper(softwareAesKey().let { k -> { k } }))
        return SecurityApiImpl(
            databaseKeys = DatabaseKeyStore(blobs),
            blobs = blobs,
            biometrics = BiometricAuthenticator { null },
            integrity = { error("ishlatilmaydi") },
            activityProvider = { null },
            documentPicker = picker,
            sdkInt = 34,
            deliver = { it.run() },
        )
    }

    private fun <T> await(call: ((Result<T>) -> Unit) -> Unit): Result<T> {
        val latch = CountDownLatch(1)
        var out: Result<T>? = null
        call { out = it; latch.countDown() }
        assertTrue("javob kelmadi", latch.await(30, TimeUnit.SECONDS))
        return out!!
    }

    @Test
    fun pingReturnsContractVersionAndSdk() {
        val info = api().ping()
        assertEquals(SecurityApiImpl.API_VERSION, info.apiVersion)
        assertEquals(34L, info.androidSdkInt)
    }

    @Test
    fun databaseKeyIsReturnedThroughCallback() {
        val api = api()
        val first = await { api.getOrCreateDatabaseKey(it) }.getOrThrow()
        val second = await { api.getOrCreateDatabaseKey(it) }.getOrThrow()
        assertEquals(32, first.size)
        assertArrayEquals(first, second)
    }

    @Test
    fun derivePinKeyMatchesKdf() {
        val salt = ByteArray(16) { it.toByte() }
        val out = await { api().derivePinKey("258036", salt, 310_000, it) }.getOrThrow()
        assertArrayEquals(PinKdf.derive("258036".toCharArray(), salt, 310_000), out)
    }

    @Test
    fun weakKdfParametersAreRejected() {
        val api = api()
        val lowIterations = await { api.derivePinKey("258036", ByteArray(16), 1000, it) }
        assertEquals(SecurityApiImpl.CODE_INVALID_ARGUMENT, (lowIterations.exceptionOrNull() as FlutterError).code)
        val shortSalt = await { api.derivePinKey("258036", ByteArray(4), 310_000, it) }
        assertEquals(SecurityApiImpl.CODE_INVALID_ARGUMENT, (shortSalt.exceptionOrNull() as FlutterError).code)
    }

    @Test
    fun invalidBlobNameBecomesFlutterError() {
        val e = assertThrows(FlutterError::class.java) { api().writeSecureBlob("../x", byteArrayOf()) }
        assertEquals(SecurityApiImpl.CODE_INVALID_ARGUMENT, e.code)
    }

    @Test
    fun blobRoundTripThroughApi() {
        val api = api()
        api.writeSecureBlob("pin_record", byteArrayOf(9, 8, 7))
        assertArrayEquals(byteArrayOf(9, 8, 7), api.readSecureBlob("pin_record"))
        api.deleteSecureBlob("pin_record")
        assertEquals(null, api.readSecureBlob("pin_record"))
    }

    @Test
    fun biometricMapping() {
        assertEquals(BiometricOutcome.CANCELLED, BiometricAuthenticator.mapError(androidx.biometric.BiometricPrompt.ERROR_USER_CANCELED))
        assertEquals(BiometricOutcome.LOCKED_OUT, BiometricAuthenticator.mapError(androidx.biometric.BiometricPrompt.ERROR_LOCKOUT))
        assertEquals(BiometricOutcome.FAILED, BiometricAuthenticator.mapError(androidx.biometric.BiometricPrompt.ERROR_TIMEOUT))
    }

    @Test
    fun pickBackupFileReadsBytesOrReturnsNullOnCancel() {
        val bytes = byteArrayOf(66, 82, 75, 68, 1)
        val picked = await<ByteArray?> { api(DocumentPicker { it { bytes } }).pickBackupFile(it) }
        assertArrayEquals(bytes, picked.getOrThrow())
        val cancelled = await<ByteArray?> { api(DocumentPicker { it(null) }).pickBackupFile(it) }
        assertEquals(null, cancelled.getOrThrow())
        val tooLarge = await<ByteArray?> {
            api(DocumentPicker { it { throw FlutterError("PICK_TOO_LARGE", null, null) } }).pickBackupFile(it)
        }
        assertEquals("PICK_TOO_LARGE", (tooLarge.exceptionOrNull() as FlutterError).code)
        val none = await<ByteArray?> { api().pickBackupFile(it) }
        assertEquals("PICK_UNAVAILABLE", (none.exceptionOrNull() as FlutterError).code)
    }
}
