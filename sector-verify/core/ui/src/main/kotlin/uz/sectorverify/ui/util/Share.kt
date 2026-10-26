package uz.sectorverify.ui.util

import android.content.Context
import android.content.Intent
import androidx.core.content.FileProvider
import java.io.File

/** Exported files leave the app only through FileProvider (§5 security); authority = "<applicationId>.files". */
object Share {
    fun authority(context: Context) = "${context.packageName}.files"

    /** Exports must be written under cacheDir/exports (see app res/xml/file_paths.xml). */
    fun exportsDir(context: Context): File = File(context.cacheDir, "exports").apply { mkdirs() }

    fun send(context: Context, file: File, mime: String, chooserTitle: String) {
        val uri = FileProvider.getUriForFile(context, authority(context), file)
        val send = Intent(Intent.ACTION_SEND)
            .setType(mime)
            .putExtra(Intent.EXTRA_STREAM, uri)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        context.startActivity(Intent.createChooser(send, chooserTitle).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    fun view(context: Context, file: File, mime: String) {
        val uri = FileProvider.getUriForFile(context, authority(context), file)
        context.startActivity(
            Intent(Intent.ACTION_VIEW).setDataAndType(uri, mime).addFlags(
                Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK,
            ),
        )
    }
}
