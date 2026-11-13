import 'dart:io';

import 'package:zanjir_core/zanjir_core.dart';
import 'package:zanjir_protocol/zanjir_protocol.dart';

/// Ilova shriftlari (`app/assets/fonts`) — PDF ilovada ham shu fayllar bilan yaratiladi.
ProtocolFonts loadFonts() {
  final dir = '${Directory.current.path}/../../app/assets/fonts';
  return ProtocolFonts(
    regular: File('$dir/NotoSans-Regular.ttf').readAsBytesSync(),
    bold: File('$dir/NotoSans-Bold.ttf').readAsBytesSync(),
    symbols: File('$dir/NotoSansMath-Regular.ttf').readAsBytesSync(),
  );
}

Map<String, Object?> measurement(int i, {String verdict = 'PASS', String? reason}) => {
  'id': '0192f000-0000-7000-8000-${i.toString().padLeft(12, '0')}',
  'node_id': 'node-$i',
  'node_label': 'QF$i',
  'node_kind': 'BREAKER',
  'type': 'LOOP_IMPEDANCE',
  'instrument_id': 'inst-1',
  'entered_via': 'MANUAL',
  'created_at': '2026-10-20T09:${(i % 60).toString().padLeft(2, '0')}:00.000Z',
  'values': {'pair': 'L1-PE', 'zs_ohm': 0.42 + i / 100},
  'verdict': verdict,
  'norm_id': 'LOOP-TN-AUTO',
  'reason': ?reason,
  'formula': 'value ≤ max · (1 − margin)',
  'limit': 1.4375,
};

/// To'liq, haqiqatga yaqin payload (`zanjir.protocol/1`).
Map<String, Object?> samplePayload({String language = 'uz', int extraMeasurements = 0}) {
  final ms = <Map<String, Object?>>[
    {
      'id': '0192f000-0000-7000-8000-a00000000001',
      'node_id': 'node-cable',
      'node_label': 'W1',
      'node_kind': 'CABLE',
      'type': 'INSULATION',
      'instrument_id': 'inst-1',
      'entered_via': 'MANUAL',
      'created_at': '2026-10-20T08:10:00.000Z',
      'values': {
        'test_voltage_v': 1000,
        'pairs': [
          {'pair': 'L1-N', 'mohm': 520},
          {'pair': 'L1-PE', 'mohm': 0.84},
        ],
      },
      'verdict': 'PASS',
      'norm_id': 'INS-CABLE-LV',
      'formula': 'value ≥ min · (1 + margin)',
      'limit': 0.5,
    },
    {
      'id': '0192f000-0000-7000-8000-a00000000002',
      'node_id': 'node-rcd',
      'node_label': 'QD1',
      'node_kind': 'RCD',
      'type': 'RCD_TRIP',
      'instrument_id': 'inst-1',
      'entered_via': 'MANUAL',
      'created_at': '2026-10-20T08:20:00.000Z',
      'values': {'multiplier': 1, 'trip_time_ms': 320, 'trip_current_ma': 21},
      'verdict': 'FAIL',
      'norm_id': 'RCD-TIME-1X',
      'reason': 'out_of_limit',
      'formula': 't ≤ max_time · (1 − margin)',
      'limit': 300,
    },
    {
      'id': '0192f000-0000-7000-8000-a00000000003',
      'node_id': 'node-earth',
      'node_label': 'ZE1',
      'node_kind': 'EARTH_ELECTRODE',
      'type': 'EARTH_RESISTANCE',
      'instrument_id': 'inst-2',
      'entered_via': 'MANUAL',
      'created_at': '2026-10-20T08:30:00.000Z',
      'values': {'r_ohm': 3.2},
      'verdict': 'NEEDS_REVIEW',
      'norm_id': null,
      'reason': 'season_coeff_missing',
    },
    for (var i = 1; i <= extraMeasurements; i++) measurement(i),
  ];
  return {
    'schema': protocolPayloadSchema,
    'protocol': {
      'number': '2026-3F9A1C-001',
      'qr_token': '9f86d081884c7d659a2feaa0c55ad015',
      'verify_url': 'zanjir://app/v/9f86d081884c7d659a2feaa0c55ad015',
      'language': language,
    },
    'lab': {
      'org_id': 'org-1',
      'name': 'Elektrolab MChJ',
      'license_no': 'EL-0042',
      'license_valid_until': '2027-12-31T00:00:00.000Z',
    },
    'site': {
      'id': 'site-1',
      'name': 'Toshkent, 5-maktab',
      'address': 'Chilonzor tumani, 12-kvartal',
      'customer': 'Xalq ta\'limi bo\'limi',
      'earthing_system': 'TN-C-S',
      'u0_volts': 230,
    },
    'session': {
      'id': 'sess-1',
      'kind': 'DAVRIY',
      'started_at': '2026-10-20T08:00:00.000Z',
      'closed_at': '2026-10-20T11:30:00.000Z',
      'ambient_temp_c': 18.5,
      'humidity_pct': 61,
    },
    'engineer': {'id': 'user-eng', 'full_name': 'Aliyev Bobur', 'safety_group': 'IV'},
    'signer': {
      'id': 'user-lead',
      'full_name': 'Karimova Dilnoza',
      'role': 'LEAD',
      'device_id': 'dev-1',
      'public_key': 'd75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a',
    },
    'signed_at': '2026-10-20T12:00:00.000Z',
    'lead_comment': 'ZE1: mavsumiy koeffitsient keyingi tashrifda aniqlanadi.',
    'norm_set': {
      'version': 'uz-2026.0',
      'sha256': 'a' * 64,
      'reviewed_by': 'TEST FIXTURE — haqiqiy tekshiruv emas',
      'reviewed_at': '2026-10-01',
      'margin_pct': 0,
    },
    'settings': {'k_corr': 0.8, 'margin_pct': 5},
    'instruments': [
      {
        'id': 'inst-1',
        'kind': 'MULTIFUNCTION',
        'model': 'Fluke 1664 FC',
        'serial_no': '4711',
        'cert_no': 'Q-2026/118',
        'verified_until': '2027-03-01T00:00:00.000Z',
      },
      {
        'id': 'inst-2',
        'kind': 'EARTH',
        'model': 'Sonel MRU-120',
        'serial_no': 'B0815',
        'cert_no': null,
        'verified_until': '2026-12-01T00:00:00.000Z',
      },
    ],
    'measurements': ms,
    'summary': verdictCounts([for (final m in ms) _verdict(m['verdict']! as String)]),
  };
}

Verdict _verdict(String code) => Verdict.values.firstWhere((v) => v.code == code);
