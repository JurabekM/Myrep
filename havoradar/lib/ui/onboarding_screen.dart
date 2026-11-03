import 'package:flutter/material.dart';

import '../state/app_state.dart';
import '../theme.dart';
import 'settings_screen.dart';

/// Birinchi ishga tushish: ilova nima qilishi, shahar, sezgir guruhlar, bildirishnomalarga ruxsat.
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
            Icon(Icons.wb_sunny_outlined, size: 64, color: t.accent),
            const SizedBox(height: 16),
            Text('HavoRadar', style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700, color: t.ink)),
            const SizedBox(height: 8),
            Text(
              "Kuchli issiqlik va havo ifloslanishidan oldindan ogohlantiradi.",
              style: TextStyle(fontSize: 16, color: t.ink, height: 1.4),
            ),
            const SizedBox(height: 24),
            const _Point(
              icon: Icons.thermostat,
              title: 'Issiqlik',
              text: "7 kunlik prognoz bo'yicha issiqlik ko'rsatkichi (AQSh NWS usuli), salqinlamaydigan tunlar va "
                  "ketma-ket issiq kunlar hisobga olinadi.",
            ),
            const _Point(
              icon: Icons.air,
              title: 'Havo sifati',
              text: "PM2.5, PM10, ozon va azot dioksidi JSST 2021 tavsiyalari bilan solishtiriladi.",
            ),
            const _Point(
              icon: Icons.notifications_active_outlined,
              title: 'Oldindan ogohlantirish',
              text: "Bugun yoki ertaga xavf siz tanlagan darajadan oshsa — xabar keladi. Bir issiqlik to'lqini haqida "
                  "bir marta, tunda esa faqat favqulodda holatda.",
            ),
            const SizedBox(height: 4),
            Text('Qayerda yashaysiz?', style: TextStyle(fontWeight: FontWeight.w700, color: t.ink)),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () async {
                final id = await pickPlace(context);
                if (id != null) await state.updateSettings(s.copyWith(placeId: id));
              },
              icon: const Icon(Icons.location_city),
              label: Text(state.catalog.placeName(s.placeId)),
            ),
            const SizedBox(height: 20),
            Text('Siz yoki oilangizda bormi? (ixtiyoriy)', style: TextStyle(fontWeight: FontWeight.w700, color: t.ink)),
            const SizedBox(height: 4),
            Text(
              "Belgilangan guruhlar uchun ogohlantirish ertaroq keladi. Ma'lumot faqat telefoningizda saqlanadi.",
              style: TextStyle(color: t.inkMuted, fontSize: 13),
            ),
            const ProfilePicker(),
            const SizedBox(height: 24),
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
              "Ilova tashxis qo'ymaydi va shifokor o'rnini bosmaydi. GPS ishlatilmaydi, shaxsiy ma'lumot yig'ilmaydi.",
              textAlign: TextAlign.center,
              style: TextStyle(color: t.inkMuted, fontSize: 12),
            ),
            TextButton(
              onPressed: () => state.engine.openUrl(privacyPolicyUrl),
              child: const Text('Maxfiylik siyosati'),
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
