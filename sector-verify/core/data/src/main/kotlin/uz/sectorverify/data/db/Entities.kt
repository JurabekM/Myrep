package uz.sectorverify.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey
import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.Rat
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionStatus
import uz.sectorverify.model.Severity
import uz.sectorverify.model.Verdict

@Entity(tableName = "site", indices = [Index(value = ["code"], unique = true)])
data class SiteEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String,
    val name: String,
    val lat: Double,
    val lon: Double,
    @ColumnInfo(name = "mcc_mnc") val mccMnc: String,
    @ColumnInfo(name = "imported_at") val importedAt: Long,
)

@Entity(
    tableName = "sector",
    foreignKeys = [
        ForeignKey(
            entity = SiteEntity::class,
            parentColumns = ["id"],
            childColumns = ["site_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index(value = ["site_id", "rat", "arfcn", "pci"], unique = true)],
)
data class SectorEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "site_id") val siteId: Long,
    val label: String,
    val rat: Rat,
    val band: String,
    val arfcn: Int,
    val pci: Int,
    @ColumnInfo(name = "azimuth_deg") val azimuthDeg: Double,
    @ColumnInfo(name = "hpbw_deg") val hpbwDeg: Double,
    @ColumnInfo(name = "mech_tilt_deg") val mechTiltDeg: Double?,
    @ColumnInfo(name = "elec_tilt_deg") val elecTiltDeg: Double?,
    @ColumnInfo(name = "height_m") val heightM: Double?,
)

@Entity(
    tableName = "session",
    foreignKeys = [
        ForeignKey(
            entity = SiteEntity::class,
            parentColumns = ["id"],
            childColumns = ["site_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index("site_id"), Index("status")],
)
data class SessionEntity(
    @PrimaryKey val id: String,
    @ColumnInfo(name = "site_id") val siteId: Long,
    val mode: SessionMode,
    @ColumnInfo(name = "started_at") val startedAt: Long,
    @ColumnInfo(name = "ended_at") val endedAt: Long?,
    @ColumnInfo(name = "device_model") val deviceModel: String,
    @ColumnInfo(name = "api_level") val apiLevel: Int,
    val baseband: String?,
    @ColumnInfo(name = "app_version") val appVersion: String,
    @ColumnInfo(name = "algo_version") val algoVersion: String,
    @ColumnInfo(name = "config_json") val configJson: String,
    @ColumnInfo(name = "measured_rate_hz") val measuredRateHz: Double?,
    val status: SessionStatus,
    /** Session verdict after the final analysis (null while RUNNING). ADR-010. */
    val verdict: Verdict? = null,
    @ColumnInfo(name = "coverage_pct") val coveragePct: Double? = null,
    @ColumnInfo(name = "subscription_id") val subscriptionId: Int? = null,
)

/** Raw table: rows are inserted once and never updated. */
@Entity(
    tableName = "gnss_fix",
    foreignKeys = [
        ForeignKey(
            entity = SessionEntity::class,
            parentColumns = ["id"],
            childColumns = ["session_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index(value = ["session_id", "t_nanos"])],
)
data class GnssFixEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "session_id") val sessionId: String,
    @ColumnInfo(name = "t_nanos") val tNanos: Long,
    @ColumnInfo(name = "utc_ms") val utcMs: Long,
    val lat: Double,
    val lon: Double,
    @ColumnInfo(name = "acc_m") val accM: Double,
    @ColumnInfo(name = "speed_mps") val speedMps: Double?,
    @ColumnInfo(name = "bearing_deg") val bearingDeg: Double?,
)

/** Raw table: rows are inserted once and never updated. */
@Entity(
    tableName = "cell_sample",
    foreignKeys = [
        ForeignKey(
            entity = SessionEntity::class,
            parentColumns = ["id"],
            childColumns = ["session_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index(value = ["session_id", "arfcn", "pci"])],
)
data class CellSampleEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "session_id") val sessionId: String,
    @ColumnInfo(name = "t_nanos") val tNanos: Long,
    @ColumnInfo(name = "rx_nanos") val rxNanos: Long?,
    val rat: Rat,
    val arfcn: Int,
    val pci: Int,
    val registered: Boolean,
    val rsrp: Double?,
    val rsrq: Double?,
    val sinr: Double?,
    val ta: Int?,
    val ci: Long?,
    val tac: Int?,
)

@Entity(
    tableName = "sector_result",
    foreignKeys = [
        ForeignKey(entity = SessionEntity::class, parentColumns = ["id"], childColumns = ["session_id"], onDelete = ForeignKey.CASCADE),
        ForeignKey(entity = SectorEntity::class, parentColumns = ["id"], childColumns = ["sector_id"], onDelete = ForeignKey.SET_NULL),
    ],
    indices = [Index("session_id"), Index("sector_id")],
)
data class SectorResultEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "session_id") val sessionId: String,
    @ColumnInfo(name = "sector_id") val sectorId: Long?,
    val rat: Rat,
    val arfcn: Int,
    val pci: Int,
    @ColumnInfo(name = "azimuth_est") val azimuthEst: Double?,
    @ColumnInfo(name = "ci_low") val ciLow: Double?,
    @ColumnInfo(name = "ci_high") val ciHigh: Double?,
    @ColumnInfo(name = "azimuth_b") val azimuthB: Double?,
    @ColumnInfo(name = "error_deg") val errorDeg: Double?,
    @ColumnInfo(name = "n_samples") val nSamples: Int,
    @ColumnInfo(name = "n_bins") val nBins: Int,
    @ColumnInfo(name = "rmse_db") val rmseDb: Double?,
    val verdict: Verdict,
    @ColumnInfo(name = "cause_code") val causeCode: CauseCode,
    /** Full SectorResult as JSON (CI half-width, coverage, missing bins) for the result screen. */
    @ColumnInfo(name = "detail_json") val detailJson: String,
)

@Entity(
    tableName = "finding",
    foreignKeys = [
        ForeignKey(
            entity = SessionEntity::class,
            parentColumns = ["id"],
            childColumns = ["session_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index("session_id")],
)
data class FindingEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "session_id") val sessionId: String,
    val type: String,
    val severity: Severity,
    @ColumnInfo(name = "detail_json") val detailJson: String,
)

@Entity(
    tableName = "report",
    foreignKeys = [
        ForeignKey(
            entity = SessionEntity::class,
            parentColumns = ["id"],
            childColumns = ["session_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index("session_id")],
)
data class ReportEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "session_id") val sessionId: String,
    @ColumnInfo(name = "pdf_path") val pdfPath: String,
    @ColumnInfo(name = "json_path") val jsonPath: String,
    @ColumnInfo(name = "zip_path") val zipPath: String,
    val sha256: String,
    @ColumnInfo(name = "signature_b64") val signatureB64: String,
    @ColumnInfo(name = "created_at") val createdAt: Long,
)
