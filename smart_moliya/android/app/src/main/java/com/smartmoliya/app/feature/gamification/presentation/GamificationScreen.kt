package com.smartmoliya.app.feature.gamification.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.smartmoliya.app.core.network.dto.ChallengeDto
import com.smartmoliya.app.core.network.dto.UserChallengeDto

private const val XP_PER_LEVEL = 1000

@Composable
fun GamificationScreen(viewModel: GamificationViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(text = "Yutuqlarim", style = MaterialTheme.typography.titleLarge)
            state.message?.let { Text(text = it, style = MaterialTheme.typography.labelSmall) }
        }

        state.progress?.let { progress ->
            item {
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(text = "Level ${progress.level}", fontWeight = FontWeight.SemiBold)
                        val xpInLevel = progress.xp % XP_PER_LEVEL
                        LinearProgressIndicator(
                            progress = { xpInLevel / XP_PER_LEVEL.toFloat() },
                            modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)
                        )
                        Text(text = "$xpInLevel / $XP_PER_LEVEL XP", style = MaterialTheme.typography.labelSmall)
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(text = "🔥 Joriy streak: ${progress.current_streak} kun")
                            Text(text = "Eng uzun: ${progress.longest_streak} kun")
                        }
                    }
                }
            }
        }

        if (com.smartmoliya.app.BuildConfig.OFFLINE_MODE) {
            // --- Offline: lokal challenge'lar va nishonlar (tranzaksiyalardan hisoblanadi) ---
            item { Text(text = "Challenge'lar", style = MaterialTheme.typography.titleLarge) }
            items(state.localChallenges, key = { it.title }) { challenge ->
                LocalChallengeCard(challenge)
            }

            item { Text(text = "Nishonlar", style = MaterialTheme.typography.titleLarge) }
            items(state.localBadges, key = { it.badge.code }) { localBadge ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(
                            text = (if (localBadge.earned) "🏅 " else "🔒 ") +
                                "${localBadge.badge.name} (+${localBadge.badge.xp_reward} XP)",
                            fontWeight = FontWeight.Medium
                        )
                        Text(text = localBadge.badge.description, style = MaterialTheme.typography.labelSmall)
                    }
                }
            }
        } else {
            item { Text(text = "Mening challenge'larim", style = MaterialTheme.typography.titleLarge) }
            if (state.myChallenges.isEmpty()) {
                item { Text(text = "Hali challenge'ga qo'shilmagansiz") }
            } else {
                items(state.myChallenges, key = { it.id }) { userChallenge ->
                    MyChallengeCard(userChallenge, onRefresh = {
                        viewModel.refreshChallengeProgress(userChallenge.challenge.id)
                    })
                }
            }

            item { Text(text = "Faol challenge'lar", style = MaterialTheme.typography.titleLarge) }
            val joinedIds = state.myChallenges.map { it.challenge.id }.toSet()
            val available = state.activeChallenges.filter { it.id !in joinedIds }
            if (available.isEmpty()) {
                item { Text(text = "Yangi challenge yo'q") }
            } else {
                items(available, key = { it.id }) { challenge ->
                    AvailableChallengeCard(challenge, onJoin = { viewModel.joinChallenge(challenge.id) })
                }
            }

            item { Text(text = "Nishonlar katalogi", style = MaterialTheme.typography.titleLarge) }
            items(state.badges, key = { it.code }) { badge ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(text = "🏅 ${badge.name} (+${badge.xp_reward} XP)", fontWeight = FontWeight.Medium)
                        Text(text = badge.description, style = MaterialTheme.typography.labelSmall)
                    }
                }
            }

            item { Text(text = "Peshqadamlar", style = MaterialTheme.typography.titleLarge) }
            if (state.leaderboard.isEmpty()) {
                item { Text(text = "Reyting hali bo'sh") }
            } else {
                items(state.leaderboard, key = { it.user_id }) { entry ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(text = "Level ${entry.level} foydalanuvchi")
                        Text(text = "${entry.xp} XP")
                    }
                }
            }
        }
    }
}

@Composable
private fun LocalChallengeCard(challenge: LocalChallenge) {
    val fraction = if (challenge.targetValue > 0) {
        (challenge.progressValue / challenge.targetValue).toFloat().coerceIn(0f, 1f)
    } else 0f

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(text = challenge.title, fontWeight = FontWeight.Medium)
            Text(text = challenge.description, style = MaterialTheme.typography.labelSmall)
            LinearProgressIndicator(
                progress = { fraction },
                modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)
            )
            Text(
                text = if (challenge.completed) "Bajarildi ✅ (+${challenge.xpReward} XP)"
                else "${challenge.progressValue.toLong()} / ${challenge.targetValue.toLong()}",
                style = MaterialTheme.typography.labelSmall
            )
        }
    }
}

@Composable
private fun MyChallengeCard(userChallenge: UserChallengeDto, onRefresh: () -> Unit) {
    val challenge = userChallenge.challenge
    val fraction = if (challenge.target_value > 0) {
        (userChallenge.progress_value / challenge.target_value).toFloat().coerceIn(0f, 1f)
    } else 0f

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(text = challenge.title, fontWeight = FontWeight.Medium)
            LinearProgressIndicator(
                progress = { fraction },
                modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)
            )
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = if (userChallenge.completed_at != null) "Yakunlandi ✅ (+${challenge.xp_reward} XP)"
                    else "${userChallenge.progress_value.toLong()} / ${challenge.target_value.toLong()}",
                    style = MaterialTheme.typography.labelSmall
                )
                if (userChallenge.completed_at == null) {
                    TextButton(onClick = onRefresh) { Text("Yangilash") }
                }
            }
        }
    }
}

@Composable
private fun AvailableChallengeCard(challenge: ChallengeDto, onJoin: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(text = challenge.title, fontWeight = FontWeight.Medium)
            Text(text = challenge.description, style = MaterialTheme.typography.labelSmall)
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(text = "+${challenge.xp_reward} XP", style = MaterialTheme.typography.labelSmall)
                TextButton(onClick = onJoin) { Text("Qo'shilish") }
            }
        }
    }
}
