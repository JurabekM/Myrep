package com.agrovision.mobile.data.repository

import com.agrovision.mobile.data.local.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class GeoRepository @Inject constructor(
    private val geoDao: GeoDao,
    private val cropDao: CropDao,
) {
    suspend fun regions(): List<RegionEntity> = geoDao.regions()
    suspend fun districts(): List<DistrictEntity> = geoDao.districts()
    suspend fun districtsByRegion(regionId: Long): List<DistrictEntity> = geoDao.districtsByRegion(regionId)
    suspend fun farms(): List<FarmEntity> = geoDao.farms()
    suspend fun fields(): List<FieldEntity> = geoDao.fields()
    suspend fun fieldsByFarm(farmId: Long): List<FieldEntity> = geoDao.fieldsByFarm(farmId)
    suspend fun fieldOptions(): List<FieldLabelRow> = geoDao.fieldOptions()
    suspend fun crops(): List<CropEntity> = cropDao.all()
    suspend fun crop(id: Long): CropEntity? = cropDao.byId(id)
    suspend fun search(query: String): List<SearchRow> =
        if (query.isBlank()) emptyList() else geoDao.search("%${query.trim()}%")

    suspend fun farmers(): List<FarmerEntity> = geoDao.farmers()

    suspend fun createFarmer(name: String, phone: String, districtId: Long): Long =
        geoDao.insertFarmers(listOf(FarmerEntity(name = name, phone = phone, districtId = districtId))).first()

    suspend fun createFarm(name: String, farmerId: Long, districtId: Long): Long =
        geoDao.insertFarms(listOf(FarmEntity(name = name, farmerId = farmerId, districtId = districtId, areaHa = 0.0))).first()

    suspend fun createField(farmId: Long, name: String, areaHa: Double, soilType: String, lat: Double, lon: Double): Long {
        val id = geoDao.insertFields(
            listOf(FieldEntity(farmId = farmId, name = name, areaHa = areaHa, soilType = soilType, lat = lat, lon = lon, polygonPoints = "")),
        ).first()
        val farm = geoDao.farm(farmId)
        if (farm != null) geoDao.updateFarm(farm.copy(areaHa = farm.areaHa + areaHa))
        return id
    }

    suspend fun farmerList(): List<FarmerListRow> = geoDao.farmerList()
    suspend fun farmList(): List<FarmListRow> = geoDao.farmList()
    suspend fun fieldList(): List<FieldListRow> = geoDao.fieldList()
}
