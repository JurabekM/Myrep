package com.uzerp.mobile.core

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.File
import java.io.FileOutputStream

/**
 * Hisobot/zaxira fayllarini qurilmaning Yuklab olinganlar (Downloads)
 * papkasiga yozadi — bu ham to'liq mahalliy amal, tarmoq ishtirok etmaydi.
 * Android 10+ da MediaStore orqali (ruxsat kerak emas), undan pastda
 * qadimiy tashqi xotira yo'li orqali (manifestda faqat maxSdkVersion=28
 * uchun WRITE_EXTERNAL_STORAGE e'lon qilingan).
 */
object FileExport {
    private const val SUBDIR = "UzERP"

    fun exportText(context: Context, fileName: String, mimeType: String, content: String): Uri? =
        exportBinary(context, fileName, mimeType, content.toByteArray(Charsets.UTF_8))

    fun exportBinary(context: Context, fileName: String, mimeType: String, bytes: ByteArray): Uri? {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, fileName)
                    put(MediaStore.Downloads.MIME_TYPE, mimeType)
                    put(MediaStore.Downloads.RELATIVE_PATH, "${Environment.DIRECTORY_DOWNLOADS}/$SUBDIR")
                }
                val uri = context.contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values) ?: return null
                context.contentResolver.openOutputStream(uri)?.use { it.write(bytes) } ?: return null
                uri
            } else {
                @Suppress("DEPRECATION")
                val dir = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), SUBDIR)
                if (!dir.exists()) dir.mkdirs()
                val file = File(dir, fileName)
                FileOutputStream(file).use { it.write(bytes) }
                Uri.fromFile(file)
            }
        } catch (_: Exception) {
            null
        }
    }

    /** Oddiy CSV matn quradi (vergul/tirnoq/qator ko'chirish ekranlanadi). */
    fun toCsv(headers: List<String>, rows: List<List<String>>): String {
        val sb = StringBuilder()
        sb.append(headers.joinToString(",") { csvEscape(it) }).append("\r\n")
        for (row in rows) {
            sb.append(row.joinToString(",") { csvEscape(it) }).append("\r\n")
        }
        return sb.toString()
    }

    private fun csvEscape(value: String): String =
        if (value.contains(',') || value.contains('"') || value.contains('\n')) {
            "\"${value.replace("\"", "\"\"")}\""
        } else {
            value
        }

    /** Oddiy JSON massiv quradi (tashqi kutubxonasiz — qatorlar tekis xarita). */
    fun toJson(rows: List<Map<String, String>>): String {
        val sb = StringBuilder("[\n")
        rows.forEachIndexed { idx, row ->
            sb.append("  {")
            sb.append(row.entries.joinToString(", ") { (k, v) -> "\"${jsonEscape(k)}\": \"${jsonEscape(v)}\"" })
            sb.append("}")
            if (idx != rows.lastIndex) sb.append(",")
            sb.append("\n")
        }
        sb.append("]\n")
        return sb.toString()
    }

    private fun jsonEscape(value: String): String =
        value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
}
