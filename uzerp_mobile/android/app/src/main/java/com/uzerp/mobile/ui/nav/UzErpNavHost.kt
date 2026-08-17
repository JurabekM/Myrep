package com.uzerp.mobile.ui.nav

import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.uzerp.mobile.ui.accounting.AccountingScreen
import com.uzerp.mobile.ui.analytics.AnalyticsScreen
import com.uzerp.mobile.ui.auth.AuthViewModel
import com.uzerp.mobile.ui.backup.BackupScreen
import com.uzerp.mobile.ui.cash.CashScreen
import com.uzerp.mobile.ui.crm.CrmLeadsScreen
import com.uzerp.mobile.ui.dashboard.DashboardScreen
import com.uzerp.mobile.ui.hr.HrScreen
import com.uzerp.mobile.ui.partners.CustomersScreen
import com.uzerp.mobile.ui.partners.SuppliersScreen
import com.uzerp.mobile.ui.payroll.PayrollCreateScreen
import com.uzerp.mobile.ui.payroll.PayrollDetailScreen
import com.uzerp.mobile.ui.payroll.PayrollListScreen
import com.uzerp.mobile.ui.pos.PosScreen
import com.uzerp.mobile.ui.products.ProductFormScreen
import com.uzerp.mobile.ui.products.ProductsScreen
import com.uzerp.mobile.ui.purchases.PurchaseDetailScreen
import com.uzerp.mobile.ui.purchases.PurchaseFormScreen
import com.uzerp.mobile.ui.purchases.PurchasesListScreen
import com.uzerp.mobile.ui.reports.ReportsScreen
import com.uzerp.mobile.ui.sales.SalesDetailScreen
import com.uzerp.mobile.ui.sales.SalesFormScreen
import com.uzerp.mobile.ui.sales.SalesListScreen
import com.uzerp.mobile.ui.sales.SalesReturnScreen
import com.uzerp.mobile.ui.stock.StockScreen

/** Ilovaning yagona navigatsiya grafigi — dashboard'dan barcha modullarga. */
@Composable
fun UzErpNavHost(authViewModel: AuthViewModel) {
    val navController = rememberNavController()

    NavHost(navController = navController, startDestination = Routes.DASHBOARD) {
        composable(Routes.DASHBOARD) {
            DashboardScreen(authViewModel = authViewModel, onNavigate = { route -> navController.navigate(route) })
        }

        // -- Mahsulotlar / Ombor -------------------------------------- //
        composable(Routes.PRODUCTS) {
            ProductsScreen(
                onBack = { navController.popBackStack() },
                onOpenProduct = { id -> navController.navigate(Routes.productForm(id)) },
                onAddProduct = { navController.navigate(Routes.productForm(null)) },
            )
        }
        composable(
            Routes.PRODUCT_FORM,
            arguments = listOf(navArgument("id") { type = NavType.LongType; defaultValue = -1L }),
        ) { entry ->
            val id = entry.arguments?.getLong("id")?.takeIf { it > 0 }
            ProductFormScreen(productId = id, onBack = { navController.popBackStack() })
        }
        composable(Routes.STOCK) {
            StockScreen(onBack = { navController.popBackStack() })
        }

        // -- POS --------------------------------------------------------- //
        composable(Routes.POS) {
            PosScreen(onBack = { navController.popBackStack() })
        }

        // -- Savdo ------------------------------------------------------- //
        composable(Routes.SALES_LIST) {
            SalesListScreen(
                onBack = { navController.popBackStack() },
                onOpen = { id -> navController.navigate(Routes.salesDetail(id)) },
                onCreate = { navController.navigate(Routes.salesForm("invoice")) },
            )
        }
        composable(
            Routes.SALES_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            SalesDetailScreen(
                docId = id,
                onBack = { navController.popBackStack() },
                onNavigateToDoc = { newId -> navController.navigate(Routes.salesDetail(newId)) { popUpTo(Routes.SALES_LIST) } },
                onReturn = { parentId -> navController.navigate(Routes.salesReturn(parentId)) },
            )
        }
        composable(
            Routes.SALES_FORM,
            arguments = listOf(navArgument("type") { type = NavType.StringType; defaultValue = "invoice" }),
        ) { entry ->
            val type = entry.arguments?.getString("type") ?: "invoice"
            SalesFormScreen(
                docType = type,
                onBack = { navController.popBackStack() },
                onSaved = { id -> navController.navigate(Routes.salesDetail(id)) { popUpTo(Routes.SALES_LIST) } },
            )
        }
        composable(
            Routes.SALES_RETURN,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            SalesReturnScreen(
                docId = id,
                onBack = { navController.popBackStack() },
                onSaved = { returnId -> navController.navigate(Routes.salesDetail(returnId)) { popUpTo(Routes.SALES_LIST) } },
            )
        }

        // -- Xarid ------------------------------------------------------- //
        composable(Routes.PURCHASES_LIST) {
            PurchasesListScreen(
                onBack = { navController.popBackStack() },
                onOpen = { id -> navController.navigate(Routes.purchaseDetail(id)) },
                onCreate = { navController.navigate(Routes.PURCHASE_FORM) },
            )
        }
        composable(
            Routes.PURCHASE_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            PurchaseDetailScreen(purchaseId = id, onBack = { navController.popBackStack() })
        }
        composable(Routes.PURCHASE_FORM) {
            PurchaseFormScreen(
                onBack = { navController.popBackStack() },
                onSaved = { id -> navController.navigate(Routes.purchaseDetail(id)) { popUpTo(Routes.PURCHASES_LIST) } },
            )
        }

        // -- Kontragentlar / CRM ------------------------------------------ //
        composable(Routes.CUSTOMERS) { CustomersScreen(onBack = { navController.popBackStack() }) }
        composable(Routes.SUPPLIERS) { SuppliersScreen(onBack = { navController.popBackStack() }) }
        composable(Routes.CRM_LEADS) { CrmLeadsScreen(onBack = { navController.popBackStack() }) }

        // -- Moliya: Kassa/Bank, Buxgalteriya ------------------------------ //
        composable(Routes.CASH) { CashScreen(onBack = { navController.popBackStack() }) }
        composable(Routes.ACCOUNTING) { AccountingScreen(onBack = { navController.popBackStack() }) }

        // -- HR ------------------------------------------------------------ //
        composable(Routes.HR) { HrScreen(onBack = { navController.popBackStack() }) }

        // -- Ish haqi -------------------------------------------------------- //
        composable(Routes.PAYROLL_LIST) {
            PayrollListScreen(
                onBack = { navController.popBackStack() },
                onOpen = { id -> navController.navigate(Routes.payrollDetail(id)) },
                onCreate = { navController.navigate(Routes.PAYROLL_CREATE) },
            )
        }
        composable(Routes.PAYROLL_CREATE) {
            PayrollCreateScreen(
                onBack = { navController.popBackStack() },
                onCreated = { id -> navController.navigate(Routes.payrollDetail(id)) { popUpTo(Routes.PAYROLL_LIST) } },
            )
        }
        composable(
            Routes.PAYROLL_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.LongType }),
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            PayrollDetailScreen(runId = id, onBack = { navController.popBackStack() })
        }

        // -- Hisobotlar / Analitika / Zaxira nusxa ------------------------- //
        composable(Routes.REPORTS) { ReportsScreen(onBack = { navController.popBackStack() }) }
        composable(Routes.ANALYTICS) { AnalyticsScreen(onBack = { navController.popBackStack() }) }
        composable(Routes.BACKUP) { BackupScreen(onBack = { navController.popBackStack() }) }
    }
}
