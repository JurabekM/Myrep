// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'security_settings.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$SecuritySettings {

 bool get biometricEnabled;/// Fonga o'tgandan keyin necha daqiqada qayta qulflanadi.
 int get lockTimeoutMinutes;
/// Create a copy of SecuritySettings
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$SecuritySettingsCopyWith<SecuritySettings> get copyWith => _$SecuritySettingsCopyWithImpl<SecuritySettings>(this as SecuritySettings, _$identity);

  /// Serializes this SecuritySettings to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is SecuritySettings&&(identical(other.biometricEnabled, biometricEnabled) || other.biometricEnabled == biometricEnabled)&&(identical(other.lockTimeoutMinutes, lockTimeoutMinutes) || other.lockTimeoutMinutes == lockTimeoutMinutes));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,biometricEnabled,lockTimeoutMinutes);

@override
String toString() {
  return 'SecuritySettings(biometricEnabled: $biometricEnabled, lockTimeoutMinutes: $lockTimeoutMinutes)';
}


}

/// @nodoc
abstract mixin class $SecuritySettingsCopyWith<$Res>  {
  factory $SecuritySettingsCopyWith(SecuritySettings value, $Res Function(SecuritySettings) _then) = _$SecuritySettingsCopyWithImpl;
@useResult
$Res call({
 bool biometricEnabled, int lockTimeoutMinutes
});




}
/// @nodoc
class _$SecuritySettingsCopyWithImpl<$Res>
    implements $SecuritySettingsCopyWith<$Res> {
  _$SecuritySettingsCopyWithImpl(this._self, this._then);

  final SecuritySettings _self;
  final $Res Function(SecuritySettings) _then;

/// Create a copy of SecuritySettings
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? biometricEnabled = null,Object? lockTimeoutMinutes = null,}) {
  return _then(_self.copyWith(
biometricEnabled: null == biometricEnabled ? _self.biometricEnabled : biometricEnabled // ignore: cast_nullable_to_non_nullable
as bool,lockTimeoutMinutes: null == lockTimeoutMinutes ? _self.lockTimeoutMinutes : lockTimeoutMinutes // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

}


/// Adds pattern-matching-related methods to [SecuritySettings].
extension SecuritySettingsPatterns on SecuritySettings {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _SecuritySettings value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _SecuritySettings() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _SecuritySettings value)  $default,){
final _that = this;
switch (_that) {
case _SecuritySettings():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _SecuritySettings value)?  $default,){
final _that = this;
switch (_that) {
case _SecuritySettings() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( bool biometricEnabled,  int lockTimeoutMinutes)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _SecuritySettings() when $default != null:
return $default(_that.biometricEnabled,_that.lockTimeoutMinutes);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( bool biometricEnabled,  int lockTimeoutMinutes)  $default,) {final _that = this;
switch (_that) {
case _SecuritySettings():
return $default(_that.biometricEnabled,_that.lockTimeoutMinutes);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( bool biometricEnabled,  int lockTimeoutMinutes)?  $default,) {final _that = this;
switch (_that) {
case _SecuritySettings() when $default != null:
return $default(_that.biometricEnabled,_that.lockTimeoutMinutes);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _SecuritySettings implements SecuritySettings {
  const _SecuritySettings({this.biometricEnabled = false, this.lockTimeoutMinutes = 2});
  factory _SecuritySettings.fromJson(Map<String, dynamic> json) => _$SecuritySettingsFromJson(json);

@override@JsonKey() final  bool biometricEnabled;
/// Fonga o'tgandan keyin necha daqiqada qayta qulflanadi.
@override@JsonKey() final  int lockTimeoutMinutes;

/// Create a copy of SecuritySettings
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$SecuritySettingsCopyWith<_SecuritySettings> get copyWith => __$SecuritySettingsCopyWithImpl<_SecuritySettings>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$SecuritySettingsToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _SecuritySettings&&(identical(other.biometricEnabled, biometricEnabled) || other.biometricEnabled == biometricEnabled)&&(identical(other.lockTimeoutMinutes, lockTimeoutMinutes) || other.lockTimeoutMinutes == lockTimeoutMinutes));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,biometricEnabled,lockTimeoutMinutes);

@override
String toString() {
  return 'SecuritySettings(biometricEnabled: $biometricEnabled, lockTimeoutMinutes: $lockTimeoutMinutes)';
}


}

/// @nodoc
abstract mixin class _$SecuritySettingsCopyWith<$Res> implements $SecuritySettingsCopyWith<$Res> {
  factory _$SecuritySettingsCopyWith(_SecuritySettings value, $Res Function(_SecuritySettings) _then) = __$SecuritySettingsCopyWithImpl;
@override @useResult
$Res call({
 bool biometricEnabled, int lockTimeoutMinutes
});




}
/// @nodoc
class __$SecuritySettingsCopyWithImpl<$Res>
    implements _$SecuritySettingsCopyWith<$Res> {
  __$SecuritySettingsCopyWithImpl(this._self, this._then);

  final _SecuritySettings _self;
  final $Res Function(_SecuritySettings) _then;

/// Create a copy of SecuritySettings
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? biometricEnabled = null,Object? lockTimeoutMinutes = null,}) {
  return _then(_SecuritySettings(
biometricEnabled: null == biometricEnabled ? _self.biometricEnabled : biometricEnabled // ignore: cast_nullable_to_non_nullable
as bool,lockTimeoutMinutes: null == lockTimeoutMinutes ? _self.lockTimeoutMinutes : lockTimeoutMinutes // ignore: cast_nullable_to_non_nullable
as int,
  ));
}


}

// dart format on
