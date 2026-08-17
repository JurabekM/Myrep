package com.uzerp.mobile.ui.nav

/** Ilova marshrutlari (Navigation-Compose route matnlari). */
object Routes {
    const val DASHBOARD = "dashboard"

    const val PRODUCTS = "products"
    const val PRODUCT_FORM = "product_form?id={id}"
    fun productForm(id: Long? = null) = "product_form?id=${id ?: -1}"

    const val STOCK = "stock"

    const val POS = "pos"

    const val SALES_LIST = "sales_list"
    const val SALES_DETAIL = "sales_detail/{id}"
    fun salesDetail(id: Long) = "sales_detail/$id"
    const val SALES_FORM = "sales_form?type={type}"
    fun salesForm(type: String) = "sales_form?type=$type"
    const val SALES_RETURN = "sales_return/{id}"
    fun salesReturn(id: Long) = "sales_return/$id"

    const val PURCHASES_LIST = "purchases_list"
    const val PURCHASE_DETAIL = "purchase_detail/{id}"
    fun purchaseDetail(id: Long) = "purchase_detail/$id"
    const val PURCHASE_FORM = "purchase_form"

    const val CUSTOMERS = "customers"
    const val SUPPLIERS = "suppliers"

    const val CRM_LEADS = "crm_leads"

    const val CASH = "cash"
    const val ACCOUNTING = "accounting"

    const val HR = "hr"

    const val PAYROLL_LIST = "payroll_list"
    const val PAYROLL_CREATE = "payroll_create"
    const val PAYROLL_DETAIL = "payroll_detail/{id}"
    fun payrollDetail(id: Long) = "payroll_detail/$id"

    const val REPORTS = "reports"
    const val ANALYTICS = "analytics"
    const val BACKUP = "backup"

    const val PROFILE = "profile"
}
