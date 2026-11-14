package uz.mpay.core

/**
 * BER-TLV parser/encoder — `crates/mpay-common/src/tlv.rs` bilan bir xil qoidalar:
 * 1–4 baytli teglar, uzunlik `< 0x80` yoki `0x81`–`0x84` (noaniq uzunlik rad), konstruktiv
 * obyektlar (chuqurlik ≤ 16), obyektlar orasidagi `0x00` to'ldiruvchi, minimal qayta kodlash.
 * Umumiy test vektorlari: `testvectors/tlv-vectors.json`.
 */
class TlvException(message: String) : Exception(message)

sealed class Tlv(val tag: Int) {
    class Primitive(tag: Int, val value: ByteArray) : Tlv(tag)
    class Constructed(tag: Int, val children: List<Tlv>) : Tlv(tag)

    /** Qiymat (konstruktiv bo'lsa — null). */
    fun bytes(): ByteArray? = (this as? Primitive)?.value

    fun children(): List<Tlv> = (this as? Constructed)?.children ?: emptyList()

    /** Chuqurlik bo'yicha birinchi mos teg. */
    fun find(t: Int): Tlv? {
        if (tag == t) return this
        for (c in children()) c.find(t)?.let { return it }
        return null
    }

    fun encode(): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        encodeInto(out)
        return out.toByteArray()
    }

    internal fun encodeInto(out: java.io.ByteArrayOutputStream) {
        writeTag(tag, out)
        val v = when (this) {
            is Primitive -> value
            is Constructed -> java.io.ByteArrayOutputStream().also { b -> children.forEach { it.encodeInto(b) } }.toByteArray()
        }
        writeLength(v.size, out)
        out.write(v)
    }

    override fun equals(other: Any?): Boolean {
        if (other !is Tlv || other.tag != tag) return false
        return when {
            this is Primitive && other is Primitive -> value.contentEquals(other.value)
            this is Constructed && other is Constructed -> children == other.children
            else -> false
        }
    }

    override fun hashCode(): Int = tag

    /** Qiymatlarsiz — kriptogramma va Track 2 logga tushmasin. */
    override fun toString(): String = when (this) {
        is Primitive -> "%X[%d bayt]".format(tag, value.size)
        is Constructed -> "%X%s".format(tag, children)
    }

    companion object {
        const val MAX_DEPTH = 16

        fun primitive(tag: Int, value: ByteArray): Tlv = Primitive(tag, value)
        fun constructed(tag: Int, vararg children: Tlv): Tlv = Constructed(tag, children.toList())

        fun tagLen(tag: Int): Int = when {
            tag and 0xFFFFFF00.toInt() == 0 -> 1
            tag and 0xFFFF0000.toInt() == 0 -> 2
            tag and 0xFF000000.toInt() == 0 -> 3
            else -> 4
        }

        fun isConstructed(tag: Int): Boolean {
            val n = tagLen(tag)
            val first = (tag ushr (8 * (n - 1))) and 0xFF
            return first and 0x20 != 0
        }

        private fun writeTag(tag: Int, out: java.io.ByteArrayOutputStream) {
            val n = tagLen(tag)
            for (i in n - 1 downTo 0) out.write((tag ushr (8 * i)) and 0xFF)
        }

        private fun writeLength(len: Int, out: java.io.ByteArrayOutputStream) {
            when {
                len < 0x80 -> out.write(len)
                len <= 0xFF -> { out.write(0x81); out.write(len) }
                len <= 0xFFFF -> { out.write(0x82); out.write(len ushr 8); out.write(len and 0xFF) }
                else -> { out.write(0x83); out.write(len ushr 16); out.write((len ushr 8) and 0xFF); out.write(len and 0xFF) }
            }
        }

        fun parseAll(data: ByteArray): List<Tlv> = Parser(data).list(data.size, 0)

        fun encodeAll(list: List<Tlv>): ByteArray {
            val out = java.io.ByteArrayOutputStream()
            list.forEach { it.encodeInto(out) }
            return out.toByteArray()
        }

        fun find(list: List<Tlv>, tag: Int): Tlv? {
            for (t in list) t.find(tag)?.let { return it }
            return null
        }

        fun require(list: List<Tlv>, tag: Int): ByteArray =
            find(list, tag)?.bytes() ?: throw TlvException("teg %X topilmadi".format(tag))

        /** DOL: (teg, uzunlik) juftliklari. */
        fun parseDol(data: ByteArray): List<Pair<Int, Int>> {
            val p = Parser(data)
            val out = ArrayList<Pair<Int, Int>>()
            while (p.pos < data.size) out.add(p.tag() to p.length())
            return out
        }

        fun encodeDol(entries: List<Pair<Int, Int>>): ByteArray {
            val out = java.io.ByteArrayOutputStream()
            entries.forEach { (t, l) -> writeTag(t, out); writeLength(l, out) }
            return out.toByteArray()
        }
    }

    private class Parser(val data: ByteArray) {
        var pos = 0

        fun byte(): Int {
            if (pos >= data.size) throw TlvException("qisqa ma'lumot (offset $pos)")
            return data[pos++].toInt() and 0xFF
        }

        fun tag(): Int {
            val start = pos
            val first = byte()
            var tag = first
            if (first and 0x1F == 0x1F) {
                while (true) {
                    val b = byte()
                    if (pos - start > 4) throw TlvException("teg 4 baytdan uzun (offset $start)")
                    tag = (tag shl 8) or b
                    if (b and 0x80 == 0) break
                }
            }
            return tag
        }

        fun length(): Int {
            val start = pos
            val first = byte()
            if (first < 0x80) return first
            val n = first and 0x7F
            if (n == 0 || n > 4) throw TlvException("noto'g'ri uzunlik (offset $start)")
            var len = 0L
            repeat(n) { len = (len shl 8) or byte().toLong() }
            if (len > Int.MAX_VALUE) throw TlvException("uzunlik juda katta")
            return len.toInt()
        }

        fun list(end: Int, depth: Int): List<Tlv> {
            val out = ArrayList<Tlv>()
            while (pos < end) {
                if (data[pos].toInt() == 0) { pos++; continue }
                val start = pos
                val t = tlv(depth)
                if (pos > end) throw TlvException("ichki obyekt chegaradan chiqdi (offset $start)")
                out.add(t)
            }
            return out
        }

        fun tlv(depth: Int): Tlv {
            if (depth >= MAX_DEPTH) throw TlvException("chuqurlik $MAX_DEPTH dan oshdi")
            val start = pos
            val tag = tag()
            val len = length()
            val end = pos.toLong() + len
            if (end > data.size) throw TlvException("qisqa ma'lumot (offset $start)")
            return if (isConstructed(tag)) {
                Constructed(tag, list(end.toInt(), depth + 1))
            } else {
                val v = data.copyOfRange(pos, end.toInt())
                pos = end.toInt()
                Primitive(tag, v)
            }
        }
    }
}

/** Hex yordamchilari. */
object Hex {
    private const val DIGITS = "0123456789ABCDEF"

    fun encode(b: ByteArray): String {
        val sb = StringBuilder(b.size * 2)
        for (x in b) { sb.append(DIGITS[(x.toInt() ushr 4) and 0xF]); sb.append(DIGITS[x.toInt() and 0xF]) }
        return sb.toString()
    }

    fun decode(s: String): ByteArray {
        val t = s.replace(" ", "")
        require(t.length % 2 == 0) { "hex uzunligi toq" }
        return ByteArray(t.length / 2) { i -> t.substring(2 * i, 2 * i + 2).toInt(16).toByte() }
    }
}
