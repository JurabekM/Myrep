package com.smartmoliya.app.core.network.dto

data class ProgressDto(
    val xp: Int,
    val level: Int,
    val current_streak: Int,
    val longest_streak: Int
)

data class LeaderboardEntryDto(
    val user_id: String,
    val xp: Int,
    val level: Int
)

data class BadgeDto(
    val code: String,
    val name: String,
    val description: String,
    val xp_reward: Int
)

data class ChallengeDto(
    val id: String,
    val code: String,
    val title: String,
    val description: String,
    val period: String, // weekly | monthly
    val target_type: String, // save_amount | no_spend_days
    val target_value: Double,
    val xp_reward: Int,
    val start_date: String,
    val end_date: String
)

data class UserChallengeDto(
    val id: String,
    val challenge: ChallengeDto,
    val progress_value: Double,
    val completed_at: String?
)
