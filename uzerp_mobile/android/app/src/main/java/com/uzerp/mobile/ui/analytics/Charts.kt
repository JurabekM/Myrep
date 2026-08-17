package com.uzerp.mobile.ui.analytics

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.uzerp.mobile.core.money
import com.uzerp.mobile.data.local.dao.MonthlySalesRow
import com.uzerp.mobile.data.local.dao.TopProductRow
import com.uzerp.mobile.ui.theme.UzAccent
import com.uzerp.mobile.ui.theme.UzBorder
import com.uzerp.mobile.ui.theme.UzGreen
import com.uzerp.mobile.ui.theme.UzMuted
import java.math.BigDecimal

/** Oylik savdo dinamikasi — sof Compose layout ustunlar (Canvas'siz, aniq sinovdan o'tkazish oson). */
@Composable
fun MonthlyBarChart(points: List<MonthlySalesRow>, modifier: Modifier = Modifier) {
    val maxValue = points.maxOfOrNull { it.total } ?: BigDecimal.ZERO
    val safeMax = if (maxValue.signum() > 0) maxValue.toFloat() else 1f

    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth().height(140.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.Bottom,
        ) {
            points.forEach { point ->
                val fraction = (point.total.toFloat() / safeMax).coerceIn(0.02f, 1f)
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .padding(horizontal = 4.dp)
                        .fillMaxHeight(fraction)
                        .background(UzAccent, RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp)),
                )
            }
        }
        Row(modifier = Modifier.fillMaxWidth().padding(top = 6.dp)) {
            points.forEach { point ->
                Text(
                    monthShortLabel(point.ym),
                    modifier = Modifier.weight(1f),
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.labelSmall,
                    color = UzMuted,
                )
            }
        }
    }
}

/** Top mahsulotlar — gorizontal progress-bar ro'yxati (daromad bo'yicha). */
@Composable
fun TopProductsBars(items: List<TopProductRow>, modifier: Modifier = Modifier) {
    val maxRevenue = items.maxOfOrNull { it.totalRevenue } ?: BigDecimal.ZERO
    val safeMax = if (maxRevenue.signum() > 0) maxRevenue.toFloat() else 1f

    Column(modifier = modifier.fillMaxWidth()) {
        items.forEach { item ->
            val fraction = (item.totalRevenue.toFloat() / safeMax).coerceIn(0.02f, 1f)
            Column(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(item.productName, style = MaterialTheme.typography.bodyMedium, maxLines = 1, modifier = Modifier.weight(1f))
                    Text(money(item.totalRevenue), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                }
                Box(modifier = Modifier.fillMaxWidth().height(10.dp).padding(top = 4.dp).background(UzBorder, RoundedCornerShape(4.dp))) {
                    Box(modifier = Modifier.fillMaxWidth(fraction).height(10.dp).background(UzGreen, RoundedCornerShape(4.dp)))
                }
            }
        }
        if (items.isEmpty()) {
            Spacer(Modifier.height(4.dp))
            Text("Ma'lumot yo'q.", color = UzMuted, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

private fun monthShortLabel(ym: String): String {
    val month = ym.takeLast(2).toIntOrNull() ?: return ym
    val names = listOf("Yan", "Fev", "Mar", "Apr", "May", "Iyun", "Iyul", "Avg", "Sen", "Okt", "Noy", "Dek")
    return names.getOrElse(month - 1) { ym }
}
