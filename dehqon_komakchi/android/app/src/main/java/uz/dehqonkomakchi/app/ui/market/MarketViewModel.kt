package uz.dehqonkomakchi.app.ui.market

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import uz.dehqonkomakchi.app.data.db.entity.ListingEntity
import uz.dehqonkomakchi.app.data.db.entity.SellGroupEntity
import uz.dehqonkomakchi.app.data.repo.MarketRepository
import java.time.LocalDate
import javax.inject.Inject

@HiltViewModel
class MarketViewModel @Inject constructor(
    private val repository: MarketRepository,
) : ViewModel() {

    val listings: StateFlow<List<ListingEntity>> =
        repository.observeActiveListings().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val groups: StateFlow<List<SellGroupEntity>> =
        repository.observeGroups().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun createListing(
        variety: String,
        quantityKg: Double,
        priceSom: Double?,
        negotiable: Boolean,
        region: String,
        availabilityEpochDay: Long = LocalDate.now().toEpochDay(),
        photoPath: String?,
        contactMethod: String,
        contactValue: String,
        contactConsent: Boolean,
        ownerName: String,
        groupId: String? = null,
    ) {
        viewModelScope.launch {
            repository.createListing(
                variety, quantityKg, priceSom, negotiable, region, availabilityEpochDay,
                photoPath, contactMethod, contactValue, contactConsent, ownerName, groupId,
            )
        }
    }

    fun deleteListing(entity: ListingEntity) = viewModelScope.launch { repository.deleteListing(entity) }

    fun reportListing(listingId: String, reason: String, note: String) {
        viewModelScope.launch { repository.reportListing(listingId, reason, note) }
    }

    fun createGroup(name: String, region: String, adminName: String) {
        viewModelScope.launch { repository.createGroup(name, region, adminName) }
    }

    fun groupAggregatedQuantity(groupId: String, onResult: (Double) -> Unit) {
        viewModelScope.launch { onResult(repository.groupAggregatedQuantityKg(groupId, listings.value)) }
    }
}
