package com.uzerp.mobile.data.local

import androidx.room.TypeConverter
import com.uzerp.mobile.core.d
import com.uzerp.mobile.core.toDbString
import java.math.BigDecimal

/**
 * Room uchun tip konverterlari.
 *
 * [BigDecimal] matn (TEXT) sifatida saqlanadi — Python tarafidagi
 * `Decimal` bilan bir xil tamoyil: aniqlik yo'qotilmaydi (float emas).
 */
class Converters {
    @TypeConverter
    fun fromBigDecimal(value: BigDecimal?): String = (value ?: BigDecimal.ZERO).toDbString()

    @TypeConverter
    fun toBigDecimal(value: String?): BigDecimal = d(value)
}
