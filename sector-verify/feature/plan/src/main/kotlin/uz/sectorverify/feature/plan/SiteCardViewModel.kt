package uz.sectorverify.feature.plan

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import uz.sectorverify.data.db.SessionEntity
import uz.sectorverify.data.repo.PlanRepository
import uz.sectorverify.data.repo.SessionRepository
import uz.sectorverify.model.SitePlan

@HiltViewModel
class SiteCardViewModel @Inject constructor(
    savedState: SavedStateHandle,
    plans: PlanRepository,
    sessions: SessionRepository,
) : ViewModel() {
    val siteId: Long = checkNotNull(savedState.get<Long>(ARG_SITE_ID))
    private val _plan = MutableStateFlow<SitePlan?>(null)
    val plan: StateFlow<SitePlan?> = _plan.asStateFlow()
    val history: StateFlow<List<SessionEntity>> = sessions.observeForSite(siteId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_MS), emptyList())

    init {
        viewModelScope.launch { _plan.value = plans.site(siteId)?.plan }
    }

    companion object {
        const val ARG_SITE_ID = "siteId"
        private const val STOP_MS = 5_000L
    }
}
