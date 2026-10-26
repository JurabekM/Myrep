package uz.sectorverify.format

import io.kotest.matchers.collections.shouldContain
import io.kotest.matchers.shouldBe
import io.kotest.matchers.string.shouldContain
import org.junit.jupiter.api.Test
import uz.sectorverify.model.Rat

class PlanCsvTest {
    private val header = PlanCsv.HEADER.joinToString(",")

    @Test
    fun `parses the example of 5_3`() {
        val r = PlanCsv.parse("$header\nNAV-0123,Navoiy Markaz,40.1032,65.3685,43405,S1,LTE,B3,1300,141,0,65,2,4,30\n")
        r.ok shouldBe true
        val site = r.sites.single()
        site.code shouldBe "NAV-0123"
        site.lat shouldBe 40.1032
        site.sectors.single().let {
            it.rat shouldBe Rat.LTE
            it.pci shouldBe 141
            it.hpbwDeg shouldBe 65.0
            it.heightM shouldBe 30.0
        }
    }

    @Test
    fun `semicolon separator, decimal comma, BOM, CRLF and empty HPBW`() {
        val h = PlanCsv.HEADER.joinToString(";")
        val text = "﻿$h\r\nX-1;\"Ko'l; bo'yi\";40,5;65,25;43405;S1;nr;n78;636666;1000;359,9;;;;\r\n\r\n"
        val r = PlanCsv.parse(text)
        r.errors shouldBe emptyList()
        r.sites.single().name shouldBe "Ko'l; bo'yi"
        r.sites.single().lat shouldBe 40.5
        r.sites.single().sectors.single().hpbwDeg shouldBe 65.0
        r.sites.single().sectors.single().rat shouldBe Rat.NR
    }

    @Test
    fun `every validation rule reports its line in Uzbek`() {
        val rows = listOf(
            "A,A,91,65,43405,S1,LTE,B3,1300,1,0,65,,,", // 2 lat
            "A,A,40,181,43405,S2,LTE,B3,1300,2,0,65,,,", // 3 lon
            "A,A,40,65,43405,S3,LTE,B3,1300,504,0,65,,,", // 4 LTE pci
            "A,A,40,65,43405,S4,GSM,B3,1300,4,0,65,,,", // 5 rat
            "A,A,40,65,43405,S5,LTE,B3,1300,5,360,65,,,", // 6 azimuth
            "A,A,40,65,43405,S6,LTE,B3,1300,6,0,10,,,", // 7 hpbw
            "A,A,40,65,43405,S7,LTE,B3,x,7,0,65,,,", // 8 son emas
            "A,A,40,65,43405,,LTE,B3,1300,8,0,65,,,", // 9 bo'sh sektor
            "A,A,40,65,43405,S9,LTE,B3,1300", // 10 ustunlar soni
            "B,B,40,65,43405,S1,LTE,B3,1300,9,0,65,,,", // 11 to'g'ri
            "B,B,40,65,43405,S2,LTE,B3,1300,9,0,65,,,", // 12 takror
            "B,B,40.1,65,43405,S3,LTE,B3,1300,10,0,65,,,", // 13 koordinatalar mos emas
            "C,C,40,65,43405,S1,LTE,B3,-1,1,0,65,,,", // 14 arfcn
        )
        val r = PlanCsv.parse((listOf(header) + rows).joinToString("\n"))
        r.ok shouldBe false
        r.sites shouldBe emptyList()
        val byLine = r.errors.associate { it.line to it.code }
        byLine[2] shouldBe PlanErrorCode.LAT_RANGE
        byLine[3] shouldBe PlanErrorCode.LON_RANGE
        byLine[4] shouldBe PlanErrorCode.PCI_RANGE
        byLine[5] shouldBe PlanErrorCode.BAD_RAT
        byLine[6] shouldBe PlanErrorCode.AZIMUTH_RANGE
        byLine[7] shouldBe PlanErrorCode.HPBW_RANGE
        byLine[8] shouldBe PlanErrorCode.NOT_A_NUMBER
        byLine[9] shouldBe PlanErrorCode.EMPTY_VALUE
        byLine[10] shouldBe PlanErrorCode.WRONG_COLUMN_COUNT
        byLine[12] shouldBe PlanErrorCode.DUPLICATE_CELL
        byLine[13] shouldBe PlanErrorCode.SITE_COORDS_MISMATCH
        byLine[14] shouldBe PlanErrorCode.ARFCN_RANGE
        (11 in byLine) shouldBe false
        r.errors.first().messageUz() shouldContain "2-qator"
        PlanErrorCode.entries.forEach { PlanError(1, it, "c", "v").messageUz() shouldContain "1-qator" }
    }

    @Test
    fun `missing column and empty file`() {
        PlanCsv.parse("").errors.single().code shouldBe PlanErrorCode.EMPTY_FILE
        val r = PlanCsv.parse("site_code,lat\nA,1")
        r.errors.map { it.column } shouldContain "pci"
        r.errors.all { it.code == PlanErrorCode.MISSING_COLUMN } shouldBe true
    }

    @Test
    fun `write then parse round-trips`() {
        val text = "$header\nNAV-0123,\"Navoiy, Markaz\",40.1032,65.3685,43405,S1,LTE,B3,1300,141,0,65,2,4,30\n" +
            "NAV-0123,\"Navoiy, Markaz\",40.1032,65.3685,43405,S2,LTE,B3,1300,142,120,65,,,\n"
        val sites = PlanCsv.parse(text).sites
        PlanCsv.parse(PlanCsv.write(sites)).sites shouldBe sites
    }
}
