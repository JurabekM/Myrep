package uz.rostor.rostor2.db

import android.content.Context

/**
 * Ilova ichidagi bazani o'qib, imzosini tekshiradi. UI (MainActivity) ham, Qo'ng'iroq Qalqoni
 * xizmati ham shu yo'l bilan yuklaydi — imzosiz yoki eski baza hech qayerda ishlatilmaydi.
 */
object DbLoader {
    const val PREFS = "rostor2"
    private const val ASSET = "db/rostor-db.bundle.json"

    fun load(ctx: Context): DbBundle.Result {
        val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val minVersion = prefs.getLong("db_max_version", 0)
        val raw = try {
            ctx.assets.open(ASSET).use { String(it.readBytes(), Charsets.UTF_8) }
        } catch (e: Exception) {
            return DbBundle.Result(false, "baza fayli ilovada topilmadi")
        }
        val r = DbBundle.verify(raw, DbKeys.ED25519_PK, DbKeys.MLDSA65_PK, minVersion)
        // Rollback himoyasi: ko'rilgan eng katta versiyani eslab qolamiz.
        if (r.ok && r.dbVersion > minVersion) prefs.edit().putLong("db_max_version", r.dbVersion).apply()
        return r
    }
}
