package uz.sectorverify.ui.util

import android.content.Context
import android.os.Build
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * §5 barqarorlik: ushlanmagan istisnolar lokal faylga yoziladi (tarmoqsiz). Faqat stack trace va qurilma
 * modeli saqlanadi — koordinata, IMSI va cell ma'lumoti hech qachon. Sozlamalardan FileProvider orqali ZIP qilib eksport qilinadi.
 */
object CrashLog {
    private const val DIR = "crash"
    private const val MAX_FILES = 20

    fun dir(context: Context) = File(context.filesDir, DIR)

    fun install(context: Context, versionName: String) {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        val app = context.applicationContext
        Thread.setDefaultUncaughtExceptionHandler { thread, e ->
            runCatching { write(app, versionName, thread.name, e) }
            previous?.uncaughtException(thread, e)
        }
    }

    internal fun write(context: Context, versionName: String, thread: String, e: Throwable): File {
        val d = dir(context).apply { mkdirs() }
        d.listFiles().orEmpty().sortedBy { it.lastModified() }.dropLast(MAX_FILES - 1).forEach { it.delete() }
        val trace = StringWriter().also { e.printStackTrace(PrintWriter(it)) }.toString()
        val text = buildString {
            appendLine("app=$versionName device=${Build.MANUFACTURER} ${Build.MODEL} api=${Build.VERSION.SDK_INT} thread=$thread")
            appendLine("time=${System.currentTimeMillis()}")
            append(trace)
        }
        return File(d, "crash-${System.currentTimeMillis()}.txt").apply { writeText(text) }
    }

    fun count(context: Context): Int = dir(context).listFiles().orEmpty().size

    /** Barcha crash fayllarini [out] ga ZIP qiladi; eksport qilinadigan narsa bo'lmasa null. */
    fun export(context: Context, out: File): File? {
        val files = dir(context).listFiles().orEmpty().sortedBy { it.name }
        if (files.isEmpty()) return null
        ZipOutputStream(out.outputStream()).use { zip ->
            for (f in files) {
                zip.putNextEntry(ZipEntry(f.name))
                zip.write(f.readBytes())
                zip.closeEntry()
            }
        }
        return out
    }
}
