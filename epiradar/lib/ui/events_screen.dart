import 'package:flutter/material.dart';

import '../data/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import 'home_screen.dart';
import 'settings_screen.dart';
import 'widgets.dart';

enum EventFilter { all, important, near, watched }

enum EventSort { personal, global, recent }

/// Barcha avj olish hodisalari: filtr, qidiruv, saralash.
class EventsScreen extends StatefulWidget {
  const EventsScreen({super.key});

  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  EventFilter filter = EventFilter.all;
  EventSort sort = EventSort.personal;
  String query = '';

  static const _filterNames = {
    EventFilter.all: 'Hammasi',
    EventFilter.important: 'Ogohlik va yuqori',
    EventFilter.near: 'Yaqin hududlar',
    EventFilter.watched: "Kuzatuv ro'yxati",
  };

  static const _sortNames = {
    EventSort.personal: 'Siz uchun xavf',
    EventSort.global: 'Dunyo miqyosidagi xavf',
    EventSort.recent: 'Eng yangi',
  };

  List<OutbreakEvent> _apply(List<OutbreakEvent> events, Settings settings) {
    final q = query.trim().toLowerCase();
    final list = events.where((e) {
      final ok = switch (filter) {
        EventFilter.all => true,
        EventFilter.important => e.personal.rank >= 2,
        EventFilter.near => e.distanceKm != null && e.distanceKm! <= 3000,
        EventFilter.watched => e.countries.any((c) => settings.watchCountries.contains(c.iso3) || c.iso3 == settings.country),
      };
      if (!ok) return false;
      if (q.isEmpty) return true;
      return e.title.toLowerCase().contains(q) ||
          e.diseaseName.toLowerCase().contains(q) ||
          e.countries.any((c) => c.name.toLowerCase().contains(q) || c.iso3.toLowerCase() == q) ||
          e.signals.any((s) => s.title.toLowerCase().contains(q));
    }).toList();
    switch (sort) {
      case EventSort.personal:
        list.sort((a, b) => b.personal.score.compareTo(a.personal.score));
      case EventSort.global:
        list.sort((a, b) => b.global.score.compareTo(a.global.score));
      case EventSort.recent:
        list.sort((a, b) => b.lastUpdated.compareTo(a.lastUpdated));
    }
    return list;
  }

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final t = context.tokens;
    final events = _apply(state.snapshot?.events ?? const [], state.settings);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Signallar'),
        actions: [
          PopupMenuButton<EventSort>(
            tooltip: 'Saralash',
            icon: const Icon(Icons.sort),
            initialValue: sort,
            onSelected: (s) => setState(() => sort = s),
            itemBuilder: (_) => [for (final s in EventSort.values) PopupMenuItem(value: s, child: Text(_sortNames[s]!))],
          ),
          const SettingsButton(),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: state.refresh,
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
                child: TextField(
                  decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Kasallik yoki mamlakat'),
                  onChanged: (v) => setState(() => query = v),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  children: [
                    for (final f in EventFilter.values)
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: FilterChip(
                          label: Text(_filterNames[f]!),
                          selected: filter == f,
                          onSelected: (_) => setState(() => filter = f),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 10, 20, 4),
                child: Text('${events.length} ta hodisa · ${_sortNames[sort]}', style: TextStyle(color: t.inkMuted, fontSize: 12)),
              ),
            ),
            if (events.isEmpty)
              const SliverFillRemaining(
                hasScrollBody: false,
                child: EmptyState(icon: Icons.search_off, title: 'Mos hodisa topilmadi', message: "Filtr yoki qidiruvni o'zgartirib ko'ring."),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
                sliver: SliverList.separated(
                  itemCount: events.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 10),
                  itemBuilder: (context, i) => EventTile(event: events[i], onTap: () => openEvent(context, events[i])),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
