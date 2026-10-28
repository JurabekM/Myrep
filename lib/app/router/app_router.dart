import 'package:baraka_daftari/app/router/app_routes.dart';
import 'package:baraka_daftari/features/about/presentation/about_screen.dart';
import 'package:baraka_daftari/features/about/presentation/privacy_screen.dart';
import 'package:baraka_daftari/features/agreements/presentation/agreement_screen.dart';
import 'package:baraka_daftari/features/agreements/presentation/dispute_screen.dart';
import 'package:baraka_daftari/features/agreements/presentation/review_screen.dart';
import 'package:baraka_daftari/features/audit/presentation/audit_screen.dart';
import 'package:baraka_daftari/features/audit/presentation/whose_money_screen.dart';
import 'package:baraka_daftari/features/backup/presentation/backup_screen.dart';
import 'package:baraka_daftari/features/budget/presentation/havas_screen.dart';
import 'package:baraka_daftari/features/budget/presentation/rescue_screen.dart';
import 'package:baraka_daftari/features/ceremonies/presentation/ceremonies_screen.dart';
import 'package:baraka_daftari/features/ceremonies/presentation/ceremony_screen.dart';
import 'package:baraka_daftari/features/content/presentation/chapter_screen.dart';
import 'package:baraka_daftari/features/content/presentation/content_screen.dart';
import 'package:baraka_daftari/features/content/presentation/daftar_page_screen.dart';
import 'package:baraka_daftari/features/debts/presentation/debt_detail_screen.dart';
import 'package:baraka_daftari/features/debts/presentation/debt_new_screen.dart';
import 'package:baraka_daftari/features/debts/presentation/debts_screen.dart';
import 'package:baraka_daftari/features/debts/presentation/payoff_screen.dart';
import 'package:baraka_daftari/features/debts/presentation/receipt_screen.dart';
import 'package:baraka_daftari/features/debts/presentation/recovery_screen.dart';
import 'package:baraka_daftari/features/debts/presentation/sellables_screen.dart';
import 'package:baraka_daftari/features/envelopes/presentation/envelopes_screen.dart';
import 'package:baraka_daftari/features/expenses/presentation/categories_screen.dart';
import 'package:baraka_daftari/features/expenses/presentation/expense_new_screen.dart';
import 'package:baraka_daftari/features/expenses/presentation/expenses_screen.dart';
import 'package:baraka_daftari/features/expenses/presentation/templates_screen.dart';
import 'package:baraka_daftari/features/home/presentation/home_screen.dart';
import 'package:baraka_daftari/features/household/presentation/members_screen.dart';
import 'package:baraka_daftari/features/household/presentation/settings_screen.dart';
import 'package:baraka_daftari/features/income/presentation/income_new_screen.dart';
import 'package:baraka_daftari/features/learning/presentation/hourly_value_screen.dart';
import 'package:baraka_daftari/features/learning/presentation/learning_goal_screen.dart';
import 'package:baraka_daftari/features/learning/presentation/learning_screen.dart';
import 'package:baraka_daftari/features/lock/domain/lock_status.dart';
import 'package:baraka_daftari/features/lock/presentation/app_lock_controller.dart';
import 'package:baraka_daftari/features/lock/presentation/lock_screen.dart';
import 'package:baraka_daftari/features/lock/presentation/pin_setup_screen.dart';
import 'package:baraka_daftari/features/obligations/presentation/nasiya_screen.dart';
import 'package:baraka_daftari/features/obligations/presentation/obligations_screen.dart';
import 'package:baraka_daftari/features/onboarding/data/onboarding_providers.dart';
import 'package:baraka_daftari/features/onboarding/presentation/onboarding_screen.dart';
import 'package:baraka_daftari/features/partnerships/presentation/ideas_screen.dart';
import 'package:baraka_daftari/features/partnerships/presentation/ledger_screen.dart';
import 'package:baraka_daftari/features/partnerships/presentation/offer_check_screen.dart';
import 'package:baraka_daftari/features/partnerships/presentation/partnership_screen.dart';
import 'package:baraka_daftari/features/partnerships/presentation/partnership_wizard_screen.dart';
import 'package:baraka_daftari/features/partnerships/presentation/partnerships_screen.dart';
import 'package:baraka_daftari/features/prices/presentation/mouse_screen.dart';
import 'package:baraka_daftari/features/prices/presentation/prices_screen.dart';
import 'package:baraka_daftari/features/subscriptions/presentation/subscriptions_screen.dart';
import 'package:baraka_daftari/features/vault/presentation/allocation_rule_screen.dart';
import 'package:baraka_daftari/features/vault/presentation/lump_sum_screen.dart';
import 'package:baraka_daftari/features/vault/presentation/vault_screen.dart';
import 'package:baraka_daftari/features/vault/presentation/withdraw_screen.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'app_router.g.dart';

@Riverpod(keepAlive: true)
GoRouter appRouter(Ref ref) {
  final lockChanges = ValueNotifier<LockStatus>(LockStatus.loading);
  ref
    ..listen(
      appLockControllerProvider,
      (_, next) => lockChanges.value = next,
      fireImmediately: true,
    )
    ..onDispose(lockChanges.dispose);
  // Onboarding holati (null — hali o'qilmagan). Zaxiradan tiklash yoki
  // onboarding yakuni provayderni yangilaydi va router qayta yo'naltiradi.
  final onboardedChanges = ValueNotifier<bool?>(null);
  ref
    ..listen(
      onboardedProvider,
      (_, next) => onboardedChanges.value = next.valueOrNull,
      fireImmediately: true,
    )
    ..onDispose(onboardedChanges.dispose);

  final router = GoRouter(
    initialLocation: AppRoutes.lock,
    refreshListenable: Listenable.merge([lockChanges, onboardedChanges]),
    redirect: (context, state) => appRedirect(
      lockChanges.value,
      state.matchedLocation,
      state.uri,
      onboarded: onboardedChanges.value,
    ),
    routes: [
      GoRoute(
        path: AppRoutes.lock,
        builder: (context, state) => const LockScreen(),
      ),
      GoRoute(
        path: AppRoutes.pinSetup,
        builder: (context, state) => const PinSetupScreen(),
      ),
      GoRoute(
        path: AppRoutes.home,
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: AppRoutes.onboarding,
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: AppRoutes.backup,
        builder: (context, state) => const BackupScreen(),
      ),
      GoRoute(
        path: AppRoutes.incomeNew,
        builder: (context, state) => const IncomeNewScreen(),
      ),
      GoRoute(
        path: AppRoutes.vault,
        builder: (context, state) => const VaultScreen(),
      ),
      GoRoute(
        path: AppRoutes.vaultRule,
        builder: (context, state) => const AllocationRuleScreen(),
      ),
      GoRoute(
        path: AppRoutes.vaultWithdraw,
        builder: (context, state) => const WithdrawScreen(),
      ),
      GoRoute(
        path: AppRoutes.vaultLumpSum,
        builder: (context, state) => const LumpSumScreen(),
      ),
      GoRoute(
        path: AppRoutes.expenses,
        builder: (context, state) => const ExpensesScreen(),
      ),
      GoRoute(
        path: AppRoutes.expenseNew,
        builder: (context, state) => const ExpenseNewScreen(),
      ),
      GoRoute(
        path: AppRoutes.categories,
        builder: (context, state) => const CategoriesScreen(),
      ),
      GoRoute(
        path: AppRoutes.templates,
        builder: (context, state) => const TemplatesScreen(),
      ),
      GoRoute(
        path: AppRoutes.havas,
        builder: (context, state) => const HavasScreen(),
      ),
      GoRoute(
        path: AppRoutes.subscriptions,
        builder: (context, state) => const SubscriptionsScreen(),
      ),
      GoRoute(
        path: AppRoutes.envelopes,
        builder: (context, state) => const EnvelopesScreen(),
      ),
      GoRoute(
        path: AppRoutes.rescue,
        builder: (context, state) => const RescueScreen(),
      ),
      GoRoute(
        path: AppRoutes.debts,
        builder: (context, state) => const DebtsScreen(),
      ),
      GoRoute(
        path: AppRoutes.debtNew,
        builder: (context, state) => const DebtNewScreen(),
      ),
      GoRoute(
        path: AppRoutes.partnerships,
        builder: (context, state) => const PartnershipsScreen(),
      ),
      GoRoute(
        path: AppRoutes.partnershipNew,
        builder: (context, state) => PartnershipWizardScreen(
          prefill: state.extra is PartnershipPrefill
              ? state.extra! as PartnershipPrefill
              : null,
        ),
      ),
      GoRoute(
        path: AppRoutes.partnershipLedgerPattern,
        builder: (context, state) =>
            LedgerScreen(partnershipId: state.pathParameters['partnershipId']!),
      ),
      GoRoute(
        path: AppRoutes.ideas,
        builder: (context, state) => const IdeasScreen(),
      ),
      GoRoute(
        path: AppRoutes.ideaNew,
        builder: (context, state) => const IdeaNewScreen(),
      ),
      GoRoute(
        path: AppRoutes.offerCheck,
        builder: (context, state) => const OfferCheckScreen(),
      ),
      GoRoute(
        path: AppRoutes.learning,
        builder: (context, state) => const LearningScreen(),
      ),
      GoRoute(
        path: AppRoutes.learningHourly,
        builder: (context, state) => const HourlyValueScreen(),
      ),
      GoRoute(
        path: AppRoutes.learningGoalPattern,
        builder: (context, state) =>
            LearningGoalScreen(id: state.pathParameters['goalId']!),
      ),
      GoRoute(
        path: AppRoutes.partnershipPattern,
        builder: (context, state) =>
            PartnershipScreen(id: state.pathParameters['partnershipId']!),
      ),
      GoRoute(
        path: AppRoutes.agreements,
        builder: (context, state) => const AgreementsScreen(),
      ),
      GoRoute(
        path: AppRoutes.agreementOral,
        builder: (context, state) => const OralAgreementScreen(),
      ),
      GoRoute(
        path: AppRoutes.agreementPattern,
        builder: (context, state) =>
            AgreementScreen(id: state.pathParameters['agreementId']!),
      ),
      GoRoute(
        path: AppRoutes.agreementReviewPattern,
        builder: (context, state) =>
            ReviewScreen(agreementId: state.pathParameters['agreementId']!),
      ),
      GoRoute(
        path: AppRoutes.agreementDisputePattern,
        builder: (context, state) => DisputeScreen(
          agreementId: state.pathParameters['agreementId']!,
          disputeId: state.pathParameters['disputeId']!,
        ),
      ),
      GoRoute(
        path: AppRoutes.ceremonies,
        builder: (context, state) => const CeremoniesScreen(),
      ),
      GoRoute(
        path: AppRoutes.ceremonyPattern,
        builder: (context, state) =>
            CeremonyScreen(planId: state.pathParameters['planId']!),
      ),
      GoRoute(
        path: AppRoutes.debtPlan,
        builder: (context, state) => const PayoffScreen(),
      ),
      GoRoute(
        path: AppRoutes.debtRecovery,
        builder: (context, state) => const RecoveryScreen(),
      ),
      GoRoute(
        path: AppRoutes.sellables,
        builder: (context, state) => const SellablesScreen(),
      ),
      GoRoute(
        path: AppRoutes.debtDetailPattern,
        builder: (context, state) =>
            DebtDetailScreen(debtId: state.pathParameters['debtId']!),
      ),
      GoRoute(
        path: AppRoutes.debtReceiptPattern,
        builder: (context, state) =>
            ReceiptScreen.debt(id: state.pathParameters['debtId']!),
      ),
      GoRoute(
        path: AppRoutes.receivableReceiptPattern,
        builder: (context, state) =>
            ReceiptScreen.receivable(id: state.pathParameters['receivableId']!),
      ),
      GoRoute(
        path: AppRoutes.prices,
        builder: (context, state) => const PricesScreen(),
      ),
      GoRoute(
        path: AppRoutes.mouse,
        builder: (context, state) => const MouseScreen(),
      ),
      GoRoute(
        path: AppRoutes.obligations,
        builder: (context, state) => const ObligationsScreen(),
      ),
      GoRoute(
        path: AppRoutes.nasiya,
        builder: (context, state) => const NasiyaScreen(),
      ),
      GoRoute(
        path: AppRoutes.audit,
        builder: (context, state) => const AuditScreen(),
      ),
      GoRoute(
        path: AppRoutes.whoseMoney,
        builder: (context, state) => const WhoseMoneyScreen(),
      ),
      GoRoute(
        path: AppRoutes.members,
        builder: (context, state) => const MembersScreen(),
      ),
      GoRoute(
        path: AppRoutes.settings,
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: AppRoutes.about,
        builder: (context, state) => const AboutScreen(),
      ),
      GoRoute(
        path: AppRoutes.privacy,
        builder: (context, state) => const PrivacyScreen(),
      ),
      GoRoute(
        path: AppRoutes.content,
        builder: (context, state) => const ContentScreen(),
        routes: [
          GoRoute(
            path: ':chapterId',
            builder: (context, state) =>
                ChapterScreen(chapterId: state.pathParameters['chapterId']!),
            routes: [
              GoRoute(
                path: 'daftar',
                builder: (context, state) => DaftarPageScreen(
                  chapterId: state.pathParameters['chapterId']!,
                ),
              ),
            ],
          ),
        ],
      ),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
}

/// Qulf, so'ng onboarding holatiga qarab yo'naltirish (MVP_PLAN Vazifa 15):
/// qulf ochiq, lekin onboarding tugamagan bo'lsa — faqat `/onboarding` va
/// zaxiradan tiklash (`/backup`); tugagach `/onboarding` bosh sahifaga.
@visibleForTesting
String? appRedirect(
  LockStatus status,
  String location,
  Uri uri, {
  required bool? onboarded,
}) {
  final lock = lockRedirect(status, location, uri);
  if (status != LockStatus.unlocked || onboarded == null) return lock;
  final target = Uri.parse(lock ?? location).path;
  if (!onboarded) {
    return AppRoutes.preOnboarding.contains(target)
        ? lock
        : AppRoutes.onboarding;
  }
  return target == AppRoutes.onboarding ? AppRoutes.home : lock;
}

/// Qulf holatiga qarab yo'naltirish. Qulflanganda joriy manzil `from`
/// parametrida saqlanadi va qulf ochilgach o'sha yerga qaytiladi.
@visibleForTesting
String? lockRedirect(LockStatus status, String location, Uri uri) {
  switch (status) {
    case LockStatus.loading:
      return location == AppRoutes.lock ? null : AppRoutes.lock;
    case LockStatus.needsSetup:
      return location == AppRoutes.pinSetup ? null : AppRoutes.pinSetup;
    case LockStatus.locked:
      if (location == AppRoutes.lock) return null;
      if (location == AppRoutes.pinSetup) return AppRoutes.lock;
      return Uri(
        path: AppRoutes.lock,
        queryParameters: {'from': uri.toString()},
      ).toString();
    case LockStatus.unlocked:
      if (!AppRoutes.public.contains(location)) return null;
      final from = uri.queryParameters['from'];
      final target = from == null ? null : Uri.tryParse(from);
      final isKnownPrivate =
          target != null &&
          AppRoutes.all.contains(target.path) &&
          !AppRoutes.public.contains(target.path);
      return isKnownPrivate ? target.toString() : AppRoutes.home;
  }
}
