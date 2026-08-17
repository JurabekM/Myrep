package com.uzerp.mobile.core

/**
 * RBAC — Rol asosidagi kirish nazorati.
 *
 * Python backend (`src/auth/rbac.py`) bilan AYNAN bir xil 9 rol va
 * ruxsatlar matritsasi (Permission Matrix). Ruxsatlar `modul.harakat`
 * ko'rinishida; `administrator` uchun `*` (hamma narsa).
 */
object Rbac {

    val roleLabels: Map<String, String> = linkedMapOf(
        "administrator" to "Administrator",
        "owner" to "Rahbar (Owner)",
        "accountant" to "Buxgalter",
        "cashier" to "Kassir",
        "warehouse" to "Omborchi",
        "sales_manager" to "Savdo menejeri",
        "hr" to "HR menejer",
        "auditor" to "Auditor",
        "guest" to "Mehmon",
    )

    private val modules: Map<String, List<String>> = linkedMapOf(
        "dashboard" to listOf("view"),
        "sales" to listOf("view", "create", "edit", "delete", "approve", "export"),
        "pos" to listOf("operate"),
        "inventory" to listOf("view", "create", "edit", "delete", "adjust", "transfer", "export"),
        "purchases" to listOf("view", "create", "edit", "delete", "receive", "export"),
        "customers" to listOf("view", "create", "edit", "delete", "export"),
        "suppliers" to listOf("view", "create", "edit", "delete", "export"),
        "accounting" to listOf("view", "create", "edit", "post", "export"),
        "cash" to listOf("view", "operate"),
        "bank" to listOf("view", "operate"),
        "hr" to listOf("view", "create", "edit", "delete", "export"),
        "payroll" to listOf("view", "create", "approve", "export"),
        "crm" to listOf("view", "create", "edit", "delete"),
        "reports" to listOf("view", "export"),
        "analytics" to listOf("view"),
        "users" to listOf("manage"),
        "settings" to listOf("manage"),
        "backup" to listOf("manage"),
        "audit" to listOf("view"),
    )

    private fun module(name: String): Set<String> =
        modules.getValue(name).map { "$name.$it" }.toSet()

    private val allPermissions: Set<String> = modules.keys.flatMap { module(it) }.toSet()

    private val allViews: Set<String> =
        modules.filterValues { "view" in it }.keys.map { "$it.view" }.toSet()

    val permissionMatrix: Map<String, Set<String>> = mapOf(
        "administrator" to setOf("*"),
        "owner" to (allPermissions - "users.manage"),
        "accountant" to (
            module("accounting") + module("cash") + module("bank") + module("payroll") +
                module("reports") + setOf(
                "dashboard.view", "analytics.view", "sales.view", "purchases.view",
                "customers.view", "suppliers.view",
            )
            ),
        "cashier" to setOf(
            "dashboard.view", "pos.operate", "sales.view", "sales.create",
            "cash.view", "cash.operate", "customers.view", "customers.create",
        ),
        "warehouse" to (
            module("inventory") + setOf(
                "dashboard.view", "purchases.view", "purchases.create",
                "purchases.receive", "suppliers.view",
            )
            ),
        "sales_manager" to (
            module("sales") + module("crm") + module("customers") + setOf(
                "dashboard.view", "pos.operate", "inventory.view",
                "reports.view", "reports.export", "analytics.view",
            )
            ),
        "hr" to (
            module("hr") + setOf(
                "dashboard.view", "payroll.view", "payroll.create",
                "payroll.export", "reports.view",
            )
            ),
        "auditor" to (allViews + setOf("audit.view", "reports.export", "analytics.view")),
        "guest" to setOf("dashboard.view"),
    )

    /** Rol berilgan ruxsatga ega yoki yo'qligini tekshiradi. */
    fun hasPermission(role: String, permission: String): Boolean {
        val perms = permissionMatrix[role] ?: return false
        return "*" in perms || permission in perms
    }

    /** Rolning to'liq ruxsatlar to'plami (UI matritsa uchun). */
    fun rolePermissions(role: String): Set<String> {
        val perms = permissionMatrix[role] ?: return emptySet()
        return if ("*" in perms) allPermissions else perms
    }

    fun validRoles(): List<String> = roleLabels.keys.toList()
}
