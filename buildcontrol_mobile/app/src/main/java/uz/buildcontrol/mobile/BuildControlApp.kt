package uz.buildcontrol.mobile

import android.app.Application
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import uz.buildcontrol.mobile.core.I18n
import uz.buildcontrol.mobile.data.Prefs
import uz.buildcontrol.mobile.data.db.BcDatabase
import uz.buildcontrol.mobile.data.repo.AuthRepository
import uz.buildcontrol.mobile.data.repo.CounterpartyRepository
import uz.buildcontrol.mobile.data.repo.EstimateRepository
import uz.buildcontrol.mobile.data.repo.ExpenseRepository
import uz.buildcontrol.mobile.data.repo.ProjectRepository
import uz.buildcontrol.mobile.data.repo.PurchaseRepository
import uz.buildcontrol.mobile.data.repo.WarehouseRepository
import uz.buildcontrol.mobile.data.repo.WorkRepository
import uz.buildcontrol.mobile.data.sync.SyncEngine
import uz.buildcontrol.mobile.data.sync.SyncRecorder

/** Application entry point; owns the dependency container. */
class BuildControlApp : Application() {

    lateinit var container: Container
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        container = Container(this)
        container.scope.launch {
            I18n.apply(container.prefs.language.first())
            container.auth.ensureRoles()
        }
    }

    /** Manual dependency injection — the graph is small and explicit. */
    class Container(app: Application) {
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
        val db = BcDatabase.get(app)
        val prefs = Prefs(app)
        val recorder = SyncRecorder(db)
        val engine = SyncEngine(db)

        val auth = AuthRepository(db, recorder)
        val projects = ProjectRepository(db, recorder, auth)
        val estimates = EstimateRepository(db, recorder, auth)
        val warehouse = WarehouseRepository(db, recorder, estimates, auth)
        val work = WorkRepository(db, recorder, auth)
        val purchases = PurchaseRepository(db, recorder, auth)
        val expenses = ExpenseRepository(db, recorder, estimates, projects, auth)
        val counterparties = CounterpartyRepository(db, recorder)

        val sync = SyncManager(engine, prefs, scope)
    }

    companion object {
        lateinit var instance: BuildControlApp
            private set

        val container: Container get() = instance.container
    }
}
