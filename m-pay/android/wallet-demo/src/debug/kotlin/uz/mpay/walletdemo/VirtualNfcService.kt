package uz.mpay.walletdemo

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import uz.mpay.wallet.sdk.HceDispatcher
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.EOFException
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket

/**
 * **Faqat debug build** (`src/debug`) — release APK'ga kirmaydi. Emulyatorda NFC/HCE apparati yo'q,
 * shuning uchun terminal ilovasi APDU'larni shu loopback ko'prik orqali yuboradi va ular haqiqiy HCE
 * servisi bilan bir xil yo'ldan ([HceDispatcher]) o'tadi. Faqat `127.0.0.1` da tinglaydi.
 *
 * Kadr: `u16 BE uzunlik ‖ APDU`; javob ham shunday. Ulanish yopilsa — maydon yo'qoldi (`deactivated`).
 * Ishlab chiqarishda bunday ko'prik relay hujumi uchun eshik bo'lardi — release'da bo'lmasligi
 * `scripts/check-release-apk.sh` bilan tekshiriladi.
 */
class VirtualNfcService : Service() {
    @Volatile private var server: ServerSocket? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CHANNEL, "Virtual NFC (sandbox)", NotificationManager.IMPORTANCE_LOW))
        val n = Notification.Builder(this, CHANNEL)
            .setContentTitle("M-Pay: virtual NFC ko'prigi")
            .setContentText("Faqat emulyator sinovi — 127.0.0.1:$PORT")
            .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
            .build()
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(1, n)
        }
        if (server == null) {
            val s = ServerSocket(PORT, 1, InetAddress.getLoopbackAddress())
            server = s
            Thread({ acceptLoop(s) }, "virtual-nfc").start()
            Log.i(TAG, "tinglanmoqda 127.0.0.1:$PORT")
        }
        return START_STICKY
    }

    private fun acceptLoop(s: ServerSocket) {
        while (!s.isClosed) {
            val c = runCatching { s.accept() }.getOrNull() ?: break
            runCatching { serve(c) }.onFailure { Log.w(TAG, "ulanish: ${it.javaClass.simpleName}") }
        }
    }

    /** Bitta "tegish": terminal ulanadi, APDU almashinuvi, uzilish. */
    private fun serve(c: Socket) = c.use {
        c.soTimeout = 10_000
        val input = DataInputStream(c.getInputStream())
        val output = DataOutputStream(c.getOutputStream())
        try {
            while (true) {
                val len = input.readUnsignedShort()
                val apdu = ByteArray(len).also(input::readFully)
                val resp = HceDispatcher.process(this, apdu)
                output.writeShort(resp.size)
                output.write(resp)
                output.flush()
            }
        } catch (_: EOFException) {
            // Terminal uzildi.
        } finally {
            HceDispatcher.deactivated(this)
        }
    }

    override fun onDestroy() {
        runCatching { server?.close() }
        server = null
        super.onDestroy()
    }

    companion object {
        const val PORT = 47661
        private const val CHANNEL = "virtual-nfc"
        private const val TAG = "MpayVirtualNfc"
    }
}
