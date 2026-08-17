package com.smartmoliya.app.core.network.dto

data class FamilyGroupCreateDto(val name: String)

data class FamilyGroupDto(
    val id: String,
    val name: String,
    val owner_user_id: String
)

data class FamilyMemberDto(
    val id: String,
    val full_name: String?,
    val phone: String?
)

data class FamilyGroupWithMembersDto(
    val group: FamilyGroupDto,
    val members: List<FamilyMemberDto>
)

data class AllowanceRequestDto(
    val child_wallet_id: String,
    val amount: Double,
    val note: String? = null
)

data class TaskRewardCreateDto(
    val assigned_to_user_id: String,
    val title: String,
    val reward_amount: Double
)

data class TaskRewardApproveDto(val wallet_id: String)

data class TaskRewardDto(
    val id: String,
    val assigned_to_user_id: String,
    val title: String,
    val reward_amount: Double,
    val status: String // pending | done | approved
)
