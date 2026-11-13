import 'package:flutter/material.dart';
import 'package:zanjir_core/zanjir_core.dart';

IconData nodeIcon(NodeKind k) => switch (k) {
  NodeKind.srcGrid || NodeKind.srcTransformer => Icons.electrical_services,
  NodeKind.srcGenerator => Icons.settings_input_component,
  NodeKind.srcPvInverter => Icons.solar_power,
  NodeKind.srcUps || NodeKind.srcBattery => Icons.battery_charging_full,
  NodeKind.srcCapacitor => Icons.battery_unknown,
  NodeKind.breaker || NodeKind.rcbo || NodeKind.fuse => Icons.toggle_on,
  NodeKind.rcd => Icons.shield,
  NodeKind.loadSwitch || NodeKind.ats || NodeKind.contactor => Icons.swap_horiz,
  NodeKind.busbar => Icons.horizontal_rule,
  NodeKind.panel => Icons.dashboard,
  NodeKind.cable => Icons.cable,
  NodeKind.load => Icons.power,
  NodeKind.socketGroup => Icons.outlet,
  NodeKind.earthElectrode || NodeKind.peBar => Icons.vertical_align_bottom,
};
