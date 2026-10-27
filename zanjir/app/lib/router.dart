import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/providers.dart';
import 'features/auth/join_screen.dart';
import 'features/auth/login_screen.dart';
import 'features/auth/onboarding_screen.dart';
import 'features/graph/node_card_screen.dart';
import 'features/graph/node_form_screen.dart';
import 'features/graph/site_screen.dart';
import 'features/isolation/isolation_screen.dart';
import 'features/isolation/plan_screen.dart';
import 'features/isolation/plans_screen.dart';
import 'features/session/measure_screen.dart';
import 'features/session/protocol_screen.dart';
import 'features/session/start_session_screen.dart';
import 'features/session/summary_screen.dart';
import 'features/settings/instrument_form_screen.dart';
import 'features/settings/settings_screen.dart';
import 'features/sites/site_form_screen.dart';
import 'features/sites/sites_screen.dart';

const _public = {'/login', '/onboarding', '/join'};

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier(0);
  ref.listen(profileProvider, (_, _) => refresh.value++);
  ref.onDispose(refresh.dispose);
  return GoRouter(
    refreshListenable: refresh,
    redirect: (context, state) {
      final profile = ref.read(profileProvider);
      if (profile.isLoading) return null;
      final loggedIn = profile.value != null;
      final public = _public.contains(state.matchedLocation);
      if (!loggedIn && !public) return '/login';
      if (loggedIn && public) return '/';
      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (_, _) => const SitesScreen()),
      GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
      GoRoute(path: '/onboarding', builder: (_, _) => const OnboardingScreen()),
      GoRoute(path: '/join', builder: (_, _) => const JoinScreen()),
      GoRoute(path: '/settings', builder: (_, _) => const SettingsScreen()),
      GoRoute(path: '/settings/instruments/new', builder: (_, _) => const InstrumentFormScreen()),
      GoRoute(path: '/sites/new', builder: (_, _) => const SiteFormScreen()),
      GoRoute(
        path: '/sites/:siteId',
        builder: (_, s) => SiteScreen(siteId: s.pathParameters['siteId']!),
      ),
      GoRoute(
        path: '/sites/:siteId/edit',
        builder: (_, s) => SiteFormScreen(siteId: s.pathParameters['siteId']),
      ),
      GoRoute(
        path: '/sites/:siteId/nodes/new',
        builder: (_, s) => NodeFormScreen(siteId: s.pathParameters['siteId']!),
      ),
      GoRoute(
        path: '/sites/:siteId/nodes/:nodeId/edit',
        builder: (_, s) => NodeFormScreen(siteId: s.pathParameters['siteId']!, nodeId: s.pathParameters['nodeId']),
      ),
      GoRoute(
        path: '/sites/:siteId/sessions/new',
        builder: (_, s) => StartSessionScreen(siteId: s.pathParameters['siteId']!),
      ),
      GoRoute(
        path: '/sites/:siteId/plans',
        builder: (_, s) => PlansScreen(siteId: s.pathParameters['siteId']!),
      ),
      GoRoute(
        path: '/plans/:planId',
        builder: (_, s) => PlanScreen(planId: s.pathParameters['planId']!),
      ),
      GoRoute(
        path: '/sites/:siteId/isolation',
        builder: (_, s) => IsolationScreen(siteId: s.pathParameters['siteId']!),
      ),
      GoRoute(
        path: '/nodes/:nodeId',
        builder: (_, s) => NodeCardScreen(nodeId: s.pathParameters['nodeId']!),
      ),
      // QR deep link: zanjir://app/n/<id>
      GoRoute(path: '/n/:nodeId', redirect: (_, s) => '/nodes/${s.pathParameters['nodeId']}'),
      // Protokol QR havolasi: zanjir://app/v/<qr_token> (server domeni bo'lmaganda)
      GoRoute(
        path: '/v/:token',
        builder: (_, s) => ProtocolVerifyScreen(token: s.pathParameters['token']!),
      ),
      GoRoute(
        path: '/sessions/:sessionId',
        builder: (_, s) => SummaryScreen(sessionId: s.pathParameters['sessionId']!),
      ),
      GoRoute(
        path: '/sessions/:sessionId/measure',
        builder: (_, s) => MeasureScreen(
          sessionId: s.pathParameters['sessionId']!,
          nodeId: s.uri.queryParameters['node'],
          supersedesId: s.uri.queryParameters['supersedes'],
        ),
      ),
      GoRoute(
        path: '/sessions/:sessionId/protocol',
        builder: (_, s) => ProtocolScreen(sessionId: s.pathParameters['sessionId']!),
      ),
    ],
  );
});
