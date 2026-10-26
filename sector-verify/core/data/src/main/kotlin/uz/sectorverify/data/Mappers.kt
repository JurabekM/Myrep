package uz.sectorverify.data

import kotlinx.serialization.builtins.MapSerializer
import kotlinx.serialization.builtins.serializer
import uz.sectorverify.data.db.CellSampleEntity
import uz.sectorverify.data.db.FindingEntity
import uz.sectorverify.data.db.GnssFixEntity
import uz.sectorverify.data.db.SectorEntity
import uz.sectorverify.data.db.SectorResultEntity
import uz.sectorverify.data.db.SiteEntity
import uz.sectorverify.format.SvJson
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.Finding
import uz.sectorverify.model.FindingType
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Sector
import uz.sectorverify.model.SectorResult
import uz.sectorverify.model.SitePlan

private val detailSerializer = MapSerializer(String.serializer(), String.serializer())

fun CellSample.toEntity(sessionId: String) =
    CellSampleEntity(0, sessionId, tNanos, rxNanos, rat, arfcn, pci, registered, rsrp, rsrq, sinr, ta, ci, tac)

fun CellSampleEntity.toModel() = CellSample(tNanos, rat, arfcn, pci, registered, rsrp, rsrq, sinr, ta, ci, tac, rxNanos)

fun GnssFix.toEntity(sessionId: String) = GnssFixEntity(0, sessionId, tNanos, utcMs, lat, lon, accM, speedMps, bearingDeg)

fun GnssFixEntity.toModel() = GnssFix(tNanos, utcMs, lat, lon, accM, speedMps, bearingDeg)

fun Sector.toEntity(siteId: Long) =
    SectorEntity(0, siteId, label, rat, band, arfcn, pci, azimuthDeg, hpbwDeg, mechTiltDeg, elecTiltDeg, heightM)

fun SectorEntity.toModel() = Sector(label, rat, band, arfcn, pci, azimuthDeg, hpbwDeg, mechTiltDeg, elecTiltDeg, heightM)

fun SitePlan.toEntity(importedAt: Long) = SiteEntity(0, code, name, lat, lon, mccMnc, importedAt)

fun SiteEntity.toModel(sectors: List<SectorEntity>) = SitePlan(code, name, lat, lon, mccMnc, sectors.map { it.toModel() })

fun SectorResult.toEntity(sessionId: String, sectorId: Long?) = SectorResultEntity(
    sessionId = sessionId,
    sectorId = sectorId,
    rat = key.rat,
    arfcn = key.arfcn,
    pci = key.pci,
    azimuthEst = estimate?.alphaDeg,
    ciLow = estimate?.ciLowDeg,
    ciHigh = estimate?.ciHighDeg,
    azimuthB = estimate?.alphaBDeg,
    errorDeg = errorDeg,
    nSamples = nSamples,
    nBins = estimate?.nBins ?: 0,
    rmseDb = estimate?.rmseDb,
    verdict = verdict,
    causeCode = cause,
    detailJson = SvJson.compact.encodeToString(SectorResult.serializer(), this),
)

fun SectorResultEntity.toModel(): SectorResult = SvJson.compact.decodeFromString(SectorResult.serializer(), detailJson)

fun Finding.toEntity(sessionId: String) =
    FindingEntity(0, sessionId, type.name, severity, SvJson.compact.encodeToString(detailSerializer, detail))

fun FindingEntity.toModel() = Finding(FindingType.valueOf(type), severity, SvJson.compact.decodeFromString(detailSerializer, detailJson))
