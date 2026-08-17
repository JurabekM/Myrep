package uz.buildcontrol.mobile

import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import uz.buildcontrol.mobile.data.sync.ColKind
import uz.buildcontrol.mobile.data.sync.SPEC_BY_ENTITY
import uz.buildcontrol.mobile.data.sync.SYNC_TABLES
import uz.buildcontrol.mobile.data.sync.SyncJson

/**
 * Guards wire compatibility with the desktop application.
 *
 * `desktop_schema.json` is exported from the Python `app.sync.registry`, so any
 * column added there without mirroring it here fails the build instead of
 * silently dropping data during replication.
 */
class SchemaCompatibilityTest {

    private data class Desktop(
        val entity: String,
        val table: String,
        val cols: List<Pair<String, String>>,
        val fks: Map<String, String>,
    )

    private fun loadDesktop(): List<Desktop> {
        val stream = javaClass.classLoader!!.getResourceAsStream("desktop_schema.json")
            ?: error("desktop_schema.json missing")
        val text = stream.bufferedReader().readText().removePrefix("﻿")
        val array: JsonArray = SyncJson.parseToJsonElement(text).jsonArray
        return array.map { element ->
            val obj = element.jsonObject
            Desktop(
                entity = obj["entity"]!!.jsonPrimitive.content,
                table = obj["table"]!!.jsonPrimitive.content,
                cols = obj["cols"]!!.jsonArray.map { pair ->
                    val values = pair.jsonArray
                    values[0].jsonPrimitive.content to values[1].jsonPrimitive.content
                },
                fks = obj["fks"]!!.jsonObject.mapValues { it.value.jsonPrimitive.content },
            )
        }
    }

    @Test
    fun `every desktop entity is replicated`() {
        val desktop = loadDesktop()
        assertEquals(
            "entity list differs",
            desktop.map { it.entity },
            SYNC_TABLES.map { it.entity },
        )
    }

    @Test
    fun `table names match`() {
        loadDesktop().forEach { row ->
            val spec = SPEC_BY_ENTITY.getValue(row.entity)
            assertEquals("table name for ${row.entity}", row.table, spec.table)
        }
    }

    @Test
    fun `column sets match exactly`() {
        loadDesktop().forEach { row ->
            val spec = SPEC_BY_ENTITY.getValue(row.entity)
            assertEquals(
                "columns of ${row.entity}",
                row.cols.map { it.first }.sorted(),
                spec.cols.map { it.name }.sorted(),
            )
        }
    }

    @Test
    fun `column kinds match the python types`() {
        loadDesktop().forEach { row ->
            val spec = SPEC_BY_ENTITY.getValue(row.entity)
            row.cols.forEach { (name, pythonType) ->
                val col = spec.byName.getValue(name)
                val expected = when (pythonType) {
                    "String", "Text" -> ColKind.TEXT
                    "Integer" -> ColKind.INT
                    "Float" -> ColKind.REAL
                    "Boolean" -> ColKind.BOOL
                    "DateTime" -> ColKind.DATETIME
                    "Date" -> ColKind.DATE
                    else -> error("unhandled python type $pythonType")
                }
                // Foreign keys are integers locally but travel as uid strings.
                if (col.fk == null) {
                    assertEquals("${row.entity}.$name", expected, col.kind)
                } else {
                    assertEquals("${row.entity}.$name is a FK", ColKind.INT, col.kind)
                }
            }
        }
    }

    @Test
    fun `foreign keys point at the same tables`() {
        loadDesktop().forEach { row ->
            val spec = SPEC_BY_ENTITY.getValue(row.entity)
            val ours = spec.cols.filter { it.fk != null }.associate { it.name to it.fk!! }
            assertEquals("foreign keys of ${row.entity}", row.fks, ours)
        }
    }

    @Test
    fun `every table carries the replication identity`() {
        SYNC_TABLES.forEach { spec ->
            assertTrue("${spec.entity} needs uid", spec.byName.containsKey("uid"))
            assertEquals(ColKind.DATETIME, spec.byName.getValue("sync_ts").kind)
        }
    }
}
