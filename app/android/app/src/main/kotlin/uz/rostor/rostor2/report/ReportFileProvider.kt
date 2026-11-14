package uz.rostor.rostor2.report

import android.content.ContentProvider
import android.content.ContentValues
import android.database.Cursor
import android.database.MatrixCursor
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.provider.OpenableColumns
import java.io.File
import java.io.FileNotFoundException

/**
 * Hisobot faylini "Ulashish" orqali boshqa ilovaga (Telegram, pochta) faqat o'qish uchun beradi.
 * androidx FileProvider o'rniga — qo'shimcha kutubxonasiz. Faqat filesDir/reports ichidagi
 * oddiy nomli fayllar beriladi; provider eksport qilinmagan, ruxsat har safar URI bo'yicha beriladi.
 */
class ReportFileProvider : ContentProvider() {
    companion object {
        const val AUTHORITY = "uz.rostor.rostor2.reports"
        fun uriFor(name: String): Uri = Uri.parse("content://$AUTHORITY/$name")
        private val SAFE = Regex("[A-Za-z0-9._-]{1,80}")
    }

    private fun file(uri: Uri): File {
        val name = uri.lastPathSegment ?: throw FileNotFoundException()
        if (!SAFE.matches(name) || uri.pathSegments.size != 1) throw FileNotFoundException()
        val f = File(File(context!!.filesDir, "reports"), name)
        if (!f.isFile) throw FileNotFoundException()
        return f
    }

    override fun onCreate() = true

    override fun getType(uri: Uri): String = if (uri.lastPathSegment?.endsWith(".txt") == true) "text/plain" else "application/json"

    override fun openFile(uri: Uri, mode: String): ParcelFileDescriptor {
        if (mode != "r") throw SecurityException("faqat o'qish")
        return ParcelFileDescriptor.open(file(uri), ParcelFileDescriptor.MODE_READ_ONLY)
    }

    override fun query(uri: Uri, projection: Array<out String>?, selection: String?, selectionArgs: Array<out String>?, sortOrder: String?): Cursor {
        val f = file(uri)
        val cols = projection ?: arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE)
        val row = cols.map { if (it == OpenableColumns.DISPLAY_NAME) f.name else if (it == OpenableColumns.SIZE) f.length() else null }
        return MatrixCursor(cols).apply { addRow(row) }
    }

    override fun insert(uri: Uri, values: ContentValues?): Uri? = null
    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?) = 0
    override fun update(uri: Uri, values: ContentValues?, selection: String?, selectionArgs: Array<out String>?) = 0
}
