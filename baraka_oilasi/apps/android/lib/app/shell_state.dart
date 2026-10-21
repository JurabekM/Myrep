import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Faqat UI holati (ma'lumot — yadrodan, `query()` orqali): tanlangan bo'lim va makon.
/// Desktop'dagi `state/ui.ts` bilan bir xil ma'noda.
class ShellState {
  const ShellState({this.screen = 'home', this.spaceId, this.focus});

  final String screen;
  final String? spaceId;

  /// Eslatma yoki kelishuvlar markazidan ochiladigan obyekt (masalan, sheriklik va bo'limi).
  final Map<String, String>? focus;

  ShellState copyWith({String? screen, String? spaceId, Map<String, String>? focus, bool clearFocus = false}) =>
      ShellState(
        screen: screen ?? this.screen,
        spaceId: spaceId ?? this.spaceId,
        focus: clearFocus ? null : (focus ?? this.focus),
      );
}

class ShellNotifier extends StateNotifier<ShellState> {
  ShellNotifier() : super(const ShellState());

  void go(String screen, {Map<String, String>? focus}) =>
      state = state.copyWith(screen: screen, focus: focus, clearFocus: focus == null);

  void setSpace(String spaceId) => state = state.copyWith(spaceId: spaceId, screen: 'home', clearFocus: true);

  void clearFocus() => state = state.copyWith(clearFocus: true);
}

final shellProvider = StateNotifierProvider<ShellNotifier, ShellState>((ref) => ShellNotifier());
