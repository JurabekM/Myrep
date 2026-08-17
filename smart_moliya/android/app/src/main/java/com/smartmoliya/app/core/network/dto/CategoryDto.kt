package com.smartmoliya.app.core.network.dto

data class CategoryDto(
    val id: String,
    val user_id: String?,
    val name: String,
    val type: String,
    val icon: String
)
