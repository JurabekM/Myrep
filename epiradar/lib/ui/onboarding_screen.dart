import 'package:flutter/material.dart';

import '../state/app_state.dart';
import '../theme.dart';
import 'settings_screen.dart';

/// Birinchi ishga tushish: ilova nima qilishi, mamlakat tanlash, bildirishnomalarga ruxsat.
class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  bool busy = false;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final t = context.tokens;
    final s = state.settings;
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
          children: [
            Icon(Icons.radar, size: 64, color: t.accent),
            const SizedBox(height: 16),
            Text('EpiRadar', style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700, color: t.ink)),
            const SizedBox(height: 8),
            Text(
              'Epidemiya va pandemiyalardan oldindan ogohlantiruvchi tizim.',
              style: TextStyle(fontSize: 16, color: t.ink, height: 1.4),
            ),
            const SizedBox(height: 24),
            const _Point(
              icon: Icons.verified_outlined,
              title: 'Faqat ishonchli manbalar',
              text: "JSST kasallik avj olishi xabarlari, Yevropa CDC (ECDC), AQSh CDC sayohat ogohlantirishlari "
                  "va JSST FluNet laboratoriya kuzatuvi.",
            ),
            const _Point(
              icon: Icons.insights_outlined,
              title: 'Avtomatik tahlil',
              text: "Har bir xabar tasniflanadi, hodisalarga birlashtiriladi va sizning mamlakatingiz uchun "
                  "0–100 xavf balli hisoblanadi. Gripp trendlarida g'ayritabiiy o'sish statistik usullar bilan aniqlanadi.",
            ),
            const _Point(
              icon: Icons.notifications_active_outlined,
              title: 'Oldindan ogohlantirish',
              text: "Xavf siz tanlagan darajadan oshsa — telefoningiz fon rejimida ham darhol xabar beradi.",
            ),
            const SizedBox(height: 12),
            Text('Qaysi mamlakatda yashaysiz?', style: TextStyle(fontWeight: FontWeight.w700, color: t.ink)),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () async {
                final c = await pickCountry(context);
                if (c != null) await state.updateSettings(s.copyWith(country: c));
              },
              icon: const Icon(Icons.public),
              label: Text(state.catalog.countryName(s.country)),
            ),
            const SizedBox(height: 32),
            FilledButton(
              onPressed: busy
                  ? null
                  : () async {
                      setState(() => busy = true);
                      await state.requestNotifications();
                      await state.updateSettings(state.settings.copyWith(onboardingDone: true));
                      await state.refresh();
                    },
              child: busy ? const Text('Tayyorlanmoqda…') : const Text('Boshlash'),
            ),
            const SizedBox(height: 12),
            Text(
              "Ilova tashxis qo'ymaydi va shifokor o'rnini bosmaydi. Shaxsiy ma'lumot yig'ilmaydi.",
              textAlign: TextAlign.center,
              style: TextStyle(color: t.inkMuted, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _Point extends StatelessWidget {
  const _Point({required this.icon, required this.title, required this.text});

  final IconData icon;
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: t.accentText),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(fontWeight: FontWeight.w700, color: t.ink)),
                const SizedBox(height: 4),
                Text(text, style: TextStyle(color: t.inkMuted, height: 1.4)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
