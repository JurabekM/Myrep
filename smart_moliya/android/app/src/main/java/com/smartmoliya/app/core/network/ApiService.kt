package com.smartmoliya.app.core.network

import com.smartmoliya.app.core.network.dto.AllowanceRequestDto
import com.smartmoliya.app.core.network.dto.BadgeDto
import com.smartmoliya.app.core.network.dto.CategoryDto
import com.smartmoliya.app.core.network.dto.ChallengeDto
import com.smartmoliya.app.core.network.dto.FamilyGroupCreateDto
import com.smartmoliya.app.core.network.dto.FamilyGroupDto
import com.smartmoliya.app.core.network.dto.FamilyGroupWithMembersDto
import com.smartmoliya.app.core.network.dto.LeaderboardEntryDto
import com.smartmoliya.app.core.network.dto.GoogleLoginDto
import com.smartmoliya.app.core.network.dto.LoginRequestDto
import com.smartmoliya.app.core.network.dto.OtpRequestDto
import com.smartmoliya.app.core.network.dto.OtpRequestResponseDto
import com.smartmoliya.app.core.network.dto.OtpVerifyDto
import com.smartmoliya.app.core.network.dto.PaymentCreateDto
import com.smartmoliya.app.core.network.dto.PaymentDto
import com.smartmoliya.app.core.network.dto.ProgressDto
import com.smartmoliya.app.core.network.dto.RefreshRequestDto
import com.smartmoliya.app.core.network.dto.RegisterRequestDto
import com.smartmoliya.app.core.network.dto.ReportSummaryDto
import com.smartmoliya.app.core.network.dto.TaskRewardApproveDto
import com.smartmoliya.app.core.network.dto.TaskRewardCreateDto
import com.smartmoliya.app.core.network.dto.TaskRewardDto
import com.smartmoliya.app.core.network.dto.TokenPairDto
import com.smartmoliya.app.core.network.dto.TransactionCreateDto
import com.smartmoliya.app.core.network.dto.TransactionDto
import com.smartmoliya.app.core.network.dto.UserChallengeDto
import com.smartmoliya.app.core.network.dto.UserDto
import com.smartmoliya.app.core.network.dto.WalletCreateDto
import com.smartmoliya.app.core.network.dto.WalletDto
import okhttp3.ResponseBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming

interface ApiService {

    @POST("api/v1/auth/register")
    suspend fun register(@Body body: RegisterRequestDto): UserDto

    @POST("api/v1/auth/login")
    suspend fun login(@Body body: LoginRequestDto): TokenPairDto

    @POST("api/v1/auth/refresh")
    suspend fun refresh(@Body body: RefreshRequestDto): TokenPairDto

    @POST("api/v1/auth/otp/request")
    suspend fun requestOtp(@Body body: OtpRequestDto): OtpRequestResponseDto

    @POST("api/v1/auth/otp/verify")
    suspend fun verifyOtp(@Body body: OtpVerifyDto): TokenPairDto

    @POST("api/v1/auth/google")
    suspend fun googleLogin(@Body body: GoogleLoginDto): TokenPairDto

    @GET("api/v1/auth/me")
    suspend fun me(): UserDto

    @GET("api/v1/categories")
    suspend fun listCategories(): List<CategoryDto>

    @GET("api/v1/wallets")
    suspend fun listWallets(): List<WalletDto>

    @POST("api/v1/wallets")
    suspend fun createWallet(@Body body: WalletCreateDto): WalletDto

    @DELETE("api/v1/wallets/{id}")
    suspend fun deleteWallet(@Path("id") walletId: String)

    @GET("api/v1/transactions")
    suspend fun listTransactions(): List<TransactionDto>

    @POST("api/v1/transactions")
    suspend fun createTransaction(@Body body: TransactionCreateDto): TransactionDto

    @DELETE("api/v1/transactions/{id}")
    suspend fun deleteTransaction(@Path("id") transactionId: String)

    @GET("api/v1/reports/summary")
    suspend fun getReportSummary(
        @Query("start_date") startDate: String? = null,
        @Query("end_date") endDate: String? = null
    ): ReportSummaryDto

    @Streaming
    @GET("api/v1/reports/export.pdf")
    suspend fun exportReportPdf(
        @Query("start_date") startDate: String? = null,
        @Query("end_date") endDate: String? = null
    ): ResponseBody

    @Streaming
    @GET("api/v1/reports/export.xlsx")
    suspend fun exportReportExcel(
        @Query("start_date") startDate: String? = null,
        @Query("end_date") endDate: String? = null
    ): ResponseBody

    // --- Payments (hamyonni to'ldirish, mock provayderlar) ---

    @GET("api/v1/payments")
    suspend fun listPayments(): List<PaymentDto>

    @POST("api/v1/payments")
    suspend fun createPayment(@Body body: PaymentCreateDto): PaymentDto

    @POST("api/v1/payments/{id}/simulate")
    suspend fun simulatePayment(@Path("id") paymentId: String): PaymentDto

    // --- Gamification ---

    @GET("api/v1/gamification/me")
    suspend fun getMyProgress(): ProgressDto

    @GET("api/v1/gamification/leaderboard")
    suspend fun getLeaderboard(): List<LeaderboardEntryDto>

    @GET("api/v1/gamification/badges")
    suspend fun listBadges(): List<BadgeDto>

    @GET("api/v1/challenges")
    suspend fun listChallenges(): List<ChallengeDto>

    @GET("api/v1/challenges/mine")
    suspend fun listMyChallenges(): List<UserChallengeDto>

    @POST("api/v1/challenges/{id}/join")
    suspend fun joinChallenge(@Path("id") challengeId: String): UserChallengeDto

    @POST("api/v1/challenges/{id}/refresh")
    suspend fun refreshChallenge(@Path("id") challengeId: String): UserChallengeDto

    // --- Family Mode ---

    @POST("api/v1/family/groups")
    suspend fun createFamilyGroup(@Body body: FamilyGroupCreateDto): FamilyGroupDto

    @POST("api/v1/family/groups/{id}/join")
    suspend fun joinFamilyGroup(@Path("id") groupId: String): FamilyGroupDto

    @GET("api/v1/family/groups/me")
    suspend fun getMyFamilyGroup(): FamilyGroupWithMembersDto

    @POST("api/v1/family/allowance")
    suspend fun sendAllowance(@Body body: AllowanceRequestDto): TransactionDto

    @GET("api/v1/family/tasks")
    suspend fun listFamilyTasks(): List<TaskRewardDto>

    @POST("api/v1/family/tasks")
    suspend fun createFamilyTask(@Body body: TaskRewardCreateDto): TaskRewardDto

    @POST("api/v1/family/tasks/{id}/done")
    suspend fun markTaskDone(@Path("id") taskId: String): TaskRewardDto

    @POST("api/v1/family/tasks/{id}/approve")
    suspend fun approveTask(@Path("id") taskId: String, @Body body: TaskRewardApproveDto): TaskRewardDto
}
