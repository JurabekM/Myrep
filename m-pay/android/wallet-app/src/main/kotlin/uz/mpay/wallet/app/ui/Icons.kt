package uz.mpay.wallet.app.ui

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.path
import androidx.compose.ui.unit.dp

/**
 * Ilovaning o'z ikonkalari (24×24, chiziqli): karta, kontaktsiz to'lov, tarix, qalqon, barmoq izi.
 * Islomiy grafika qoidasi: jonzot, piggy bank, qimor belgilari yo'q (`IconPolicyTest`).
 */
object MpayIcons {
    private fun icon(name: String, block: ImageVector.Builder.() -> Unit): ImageVector =
        ImageVector.Builder(name, 24.dp, 24.dp, 24f, 24f).apply(block).build()

    private fun ImageVector.Builder.stroke(d: androidx.compose.ui.graphics.vector.PathBuilder.() -> Unit) = path(
        fill = null,
        stroke = SolidColor(Color.Black),
        strokeLineWidth = 2f,
        strokeLineCap = StrokeCap.Round,
        strokeLineJoin = StrokeJoin.Round,
        pathBuilder = d,
    )

    val Card: ImageVector = icon("card") {
        stroke {
            moveTo(5f, 5f); lineTo(19f, 5f); arcToRelative(2f, 2f, 0f, false, true, 2f, 2f)
            lineTo(21f, 17f); arcToRelative(2f, 2f, 0f, false, true, -2f, 2f)
            lineTo(5f, 19f); arcToRelative(2f, 2f, 0f, false, true, -2f, -2f)
            lineTo(3f, 7f); arcToRelative(2f, 2f, 0f, false, true, 2f, -2f); close()
        }
        stroke { moveTo(3f, 10f); lineTo(21f, 10f) }
        stroke { moveTo(7f, 15f); lineTo(10f, 15f) }
    }

    val Contactless: ImageVector = icon("contactless") {
        stroke { moveTo(7f, 8.5f); arcToRelative(5f, 5f, 0f, false, true, 0f, 7f) }
        stroke { moveTo(10.5f, 6f); arcToRelative(8.5f, 8.5f, 0f, false, true, 0f, 12f) }
        stroke { moveTo(14f, 3.5f); arcToRelative(12f, 12f, 0f, false, true, 0f, 17f) }
    }

    val History: ImageVector = icon("history") {
        stroke {
            moveTo(3.5f, 12f); arcToRelative(8.5f, 8.5f, 0f, true, false, 2.5f, -6f)
        }
        stroke { moveTo(3.5f, 3.5f); lineTo(3.5f, 7.5f); lineTo(7.5f, 7.5f) }
        stroke { moveTo(12f, 8f); lineTo(12f, 12f); lineTo(15f, 14f) }
    }

    val Shield: ImageVector = icon("shield") {
        stroke {
            moveTo(12f, 3f); lineTo(19f, 6f); lineTo(19f, 11f)
            curveTo(19f, 15.5f, 16f, 19f, 12f, 21f)
            curveTo(8f, 19f, 5f, 15.5f, 5f, 11f); lineTo(5f, 6f); close()
        }
        stroke { moveTo(9f, 12f); lineTo(11f, 14f); lineTo(15f, 10f) }
    }

    val Fingerprint: ImageVector = icon("fingerprint") {
        stroke { moveTo(6f, 9f); arcToRelative(6.5f, 6.5f, 0f, false, true, 12f, 0f) }
        stroke { moveTo(5.5f, 14f); curveTo(5.5f, 12f, 6f, 11f, 6.5f, 10.5f) }
        stroke { moveTo(9f, 19f); curveTo(8f, 17f, 8f, 15f, 8f, 13f); arcToRelative(4f, 4f, 0f, false, true, 8f, 0f); lineTo(16f, 14f) }
        stroke { moveTo(12f, 13f); curveTo(12f, 16f, 12.5f, 18f, 14f, 20f) }
        stroke { moveTo(18.5f, 12.5f); curveTo(18.5f, 15f, 18f, 17f, 17f, 18.5f) }
    }

    val Key: ImageVector = icon("key") {
        stroke { moveTo(8f, 15f); arcToRelative(4f, 4f, 0f, true, true, 3.5f, -6f); lineTo(20f, 9f); lineTo(20f, 12f); lineTo(17f, 12f); lineTo(17f, 14f); lineTo(14f, 14f) }
    }

    val Globe: ImageVector = icon("globe") {
        stroke { moveTo(12f, 3f); arcToRelative(9f, 9f, 0f, true, true, 0f, 18f); arcToRelative(9f, 9f, 0f, true, true, 0f, -18f) }
        stroke { moveTo(3f, 12f); lineTo(21f, 12f) }
        stroke { moveTo(12f, 3f); curveTo(9.5f, 6f, 9.5f, 18f, 12f, 21f); curveTo(14.5f, 18f, 14.5f, 6f, 12f, 3f) }
    }

    val Pause: ImageVector = icon("pause") {
        stroke { moveTo(9f, 6f); lineTo(9f, 18f) }
        stroke { moveTo(15f, 6f); lineTo(15f, 18f) }
    }

    val Play: ImageVector = icon("play") {
        stroke { moveTo(8f, 5.5f); lineTo(18.5f, 12f); lineTo(8f, 18.5f); close() }
    }
}
