package uz.sectorverify.format

/** Minimal RFC 4180 CSV: quoted fields, doubled quotes, comma or semicolon separator. */
object Csv {
    /** Picks ';' when the header has more semicolons than commas (Excel in uz/ru locales). */
    fun detectSeparator(headerLine: String): Char = if (headerLine.count { it == ';' } > headerLine.count { it == ',' }) ';' else ','

    fun parseLine(line: String, sep: Char): List<String> {
        val out = ArrayList<String>()
        val cur = StringBuilder()
        var quoted = false
        var i = 0
        while (i < line.length) {
            val c = line[i]
            when {
                quoted && c == '"' && line.getOrNull(i + 1) == '"' -> {
                    cur.append('"')
                    i++
                }
                c == '"' -> quoted = !quoted
                !quoted && c == sep -> {
                    out += cur.toString().trim()
                    cur.clear()
                }
                else -> cur.append(c)
            }
            i++
        }
        out += cur.toString().trim()
        return out
    }

    private const val SPECIAL = "\"\n\r"

    fun escape(value: String, sep: Char = ','): String =
        if (value.any { it == sep || it in SPECIAL }) "\"" + value.replace("\"", "\"\"") + "\"" else value

    fun row(values: List<Any?>, sep: Char = ','): String = values.joinToString(sep.toString()) { escape(it?.toString() ?: "", sep) }

    /** Splits text into lines (CRLF/LF), removing a UTF-8 BOM. */
    fun lines(text: String): List<String> = text.removePrefix("﻿").split("\r\n", "\n")
}
