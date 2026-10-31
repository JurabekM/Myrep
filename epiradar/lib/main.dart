import 'package:flutter/material.dart';

import 'app.dart';
import 'data/engine_api.dart';
import 'state/app_state.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final state = AppState(ChannelEngine());
  runApp(EpiRadarApp(state: state));
  state.init();
}
