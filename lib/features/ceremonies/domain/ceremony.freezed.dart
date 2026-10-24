// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'ceremony.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$CeremonyPlan {

 SyncMeta get meta; String get title; CeremonyType get type; CurrencyCode get currency; CeremonyStatus get status; LocalDate? get eventDate; String? get selectedScenarioId;/// «To'yona o'rniga jamg'arma» maqsadi (`Goal`).
 String? get giftGoalId;/// Qarz qismini oyiga qancha to'lay olamiz va yillik stavka (bp).
 Money? get debtMonthly; int? get debtAnnualRateBp;
/// Create a copy of CeremonyPlan
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CeremonyPlanCopyWith<CeremonyPlan> get copyWith => _$CeremonyPlanCopyWithImpl<CeremonyPlan>(this as CeremonyPlan, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is CeremonyPlan&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.type, type) || other.type == type)&&(identical(other.currency, currency) || other.currency == currency)&&(identical(other.status, status) || other.status == status)&&(identical(other.eventDate, eventDate) || other.eventDate == eventDate)&&(identical(other.selectedScenarioId, selectedScenarioId) || other.selectedScenarioId == selectedScenarioId)&&(identical(other.giftGoalId, giftGoalId) || other.giftGoalId == giftGoalId)&&(identical(other.debtMonthly, debtMonthly) || other.debtMonthly == debtMonthly)&&(identical(other.debtAnnualRateBp, debtAnnualRateBp) || other.debtAnnualRateBp == debtAnnualRateBp));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,type,currency,status,eventDate,selectedScenarioId,giftGoalId,debtMonthly,debtAnnualRateBp);

@override
String toString() {
  return 'CeremonyPlan(meta: $meta, title: $title, type: $type, currency: $currency, status: $status, eventDate: $eventDate, selectedScenarioId: $selectedScenarioId, giftGoalId: $giftGoalId, debtMonthly: $debtMonthly, debtAnnualRateBp: $debtAnnualRateBp)';
}


}

/// @nodoc
abstract mixin class $CeremonyPlanCopyWith<$Res>  {
  factory $CeremonyPlanCopyWith(CeremonyPlan value, $Res Function(CeremonyPlan) _then) = _$CeremonyPlanCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, CeremonyType type, CurrencyCode currency, CeremonyStatus status, LocalDate? eventDate, String? selectedScenarioId, String? giftGoalId, Money? debtMonthly, int? debtAnnualRateBp
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$CeremonyPlanCopyWithImpl<$Res>
    implements $CeremonyPlanCopyWith<$Res> {
  _$CeremonyPlanCopyWithImpl(this._self, this._then);

  final CeremonyPlan _self;
  final $Res Function(CeremonyPlan) _then;

/// Create a copy of CeremonyPlan
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? type = null,Object? currency = null,Object? status = null,Object? eventDate = freezed,Object? selectedScenarioId = freezed,Object? giftGoalId = freezed,Object? debtMonthly = freezed,Object? debtAnnualRateBp = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as CeremonyType,currency: null == currency ? _self.currency : currency // ignore: cast_nullable_to_non_nullable
as CurrencyCode,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as CeremonyStatus,eventDate: freezed == eventDate ? _self.eventDate : eventDate // ignore: cast_nullable_to_non_nullable
as LocalDate?,selectedScenarioId: freezed == selectedScenarioId ? _self.selectedScenarioId : selectedScenarioId // ignore: cast_nullable_to_non_nullable
as String?,giftGoalId: freezed == giftGoalId ? _self.giftGoalId : giftGoalId // ignore: cast_nullable_to_non_nullable
as String?,debtMonthly: freezed == debtMonthly ? _self.debtMonthly : debtMonthly // ignore: cast_nullable_to_non_nullable
as Money?,debtAnnualRateBp: freezed == debtAnnualRateBp ? _self.debtAnnualRateBp : debtAnnualRateBp // ignore: cast_nullable_to_non_nullable
as int?,
  ));
}
/// Create a copy of CeremonyPlan
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [CeremonyPlan].
extension CeremonyPlanPatterns on CeremonyPlan {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _CeremonyPlan value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _CeremonyPlan() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _CeremonyPlan value)  $default,){
final _that = this;
switch (_that) {
case _CeremonyPlan():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _CeremonyPlan value)?  $default,){
final _that = this;
switch (_that) {
case _CeremonyPlan() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  CeremonyType type,  CurrencyCode currency,  CeremonyStatus status,  LocalDate? eventDate,  String? selectedScenarioId,  String? giftGoalId,  Money? debtMonthly,  int? debtAnnualRateBp)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _CeremonyPlan() when $default != null:
return $default(_that.meta,_that.title,_that.type,_that.currency,_that.status,_that.eventDate,_that.selectedScenarioId,_that.giftGoalId,_that.debtMonthly,_that.debtAnnualRateBp);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  CeremonyType type,  CurrencyCode currency,  CeremonyStatus status,  LocalDate? eventDate,  String? selectedScenarioId,  String? giftGoalId,  Money? debtMonthly,  int? debtAnnualRateBp)  $default,) {final _that = this;
switch (_that) {
case _CeremonyPlan():
return $default(_that.meta,_that.title,_that.type,_that.currency,_that.status,_that.eventDate,_that.selectedScenarioId,_that.giftGoalId,_that.debtMonthly,_that.debtAnnualRateBp);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  CeremonyType type,  CurrencyCode currency,  CeremonyStatus status,  LocalDate? eventDate,  String? selectedScenarioId,  String? giftGoalId,  Money? debtMonthly,  int? debtAnnualRateBp)?  $default,) {final _that = this;
switch (_that) {
case _CeremonyPlan() when $default != null:
return $default(_that.meta,_that.title,_that.type,_that.currency,_that.status,_that.eventDate,_that.selectedScenarioId,_that.giftGoalId,_that.debtMonthly,_that.debtAnnualRateBp);case _:
  return null;

}
}

}

/// @nodoc


class _CeremonyPlan implements CeremonyPlan {
  const _CeremonyPlan({required this.meta, required this.title, required this.type, required this.currency, this.status = CeremonyStatus.draft, this.eventDate, this.selectedScenarioId, this.giftGoalId, this.debtMonthly, this.debtAnnualRateBp});
  

@override final  SyncMeta meta;
@override final  String title;
@override final  CeremonyType type;
@override final  CurrencyCode currency;
@override@JsonKey() final  CeremonyStatus status;
@override final  LocalDate? eventDate;
@override final  String? selectedScenarioId;
/// «To'yona o'rniga jamg'arma» maqsadi (`Goal`).
@override final  String? giftGoalId;
/// Qarz qismini oyiga qancha to'lay olamiz va yillik stavka (bp).
@override final  Money? debtMonthly;
@override final  int? debtAnnualRateBp;

/// Create a copy of CeremonyPlan
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CeremonyPlanCopyWith<_CeremonyPlan> get copyWith => __$CeremonyPlanCopyWithImpl<_CeremonyPlan>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _CeremonyPlan&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.type, type) || other.type == type)&&(identical(other.currency, currency) || other.currency == currency)&&(identical(other.status, status) || other.status == status)&&(identical(other.eventDate, eventDate) || other.eventDate == eventDate)&&(identical(other.selectedScenarioId, selectedScenarioId) || other.selectedScenarioId == selectedScenarioId)&&(identical(other.giftGoalId, giftGoalId) || other.giftGoalId == giftGoalId)&&(identical(other.debtMonthly, debtMonthly) || other.debtMonthly == debtMonthly)&&(identical(other.debtAnnualRateBp, debtAnnualRateBp) || other.debtAnnualRateBp == debtAnnualRateBp));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,type,currency,status,eventDate,selectedScenarioId,giftGoalId,debtMonthly,debtAnnualRateBp);

@override
String toString() {
  return 'CeremonyPlan(meta: $meta, title: $title, type: $type, currency: $currency, status: $status, eventDate: $eventDate, selectedScenarioId: $selectedScenarioId, giftGoalId: $giftGoalId, debtMonthly: $debtMonthly, debtAnnualRateBp: $debtAnnualRateBp)';
}


}

/// @nodoc
abstract mixin class _$CeremonyPlanCopyWith<$Res> implements $CeremonyPlanCopyWith<$Res> {
  factory _$CeremonyPlanCopyWith(_CeremonyPlan value, $Res Function(_CeremonyPlan) _then) = __$CeremonyPlanCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, CeremonyType type, CurrencyCode currency, CeremonyStatus status, LocalDate? eventDate, String? selectedScenarioId, String? giftGoalId, Money? debtMonthly, int? debtAnnualRateBp
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$CeremonyPlanCopyWithImpl<$Res>
    implements _$CeremonyPlanCopyWith<$Res> {
  __$CeremonyPlanCopyWithImpl(this._self, this._then);

  final _CeremonyPlan _self;
  final $Res Function(_CeremonyPlan) _then;

/// Create a copy of CeremonyPlan
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? type = null,Object? currency = null,Object? status = null,Object? eventDate = freezed,Object? selectedScenarioId = freezed,Object? giftGoalId = freezed,Object? debtMonthly = freezed,Object? debtAnnualRateBp = freezed,}) {
  return _then(_CeremonyPlan(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as CeremonyType,currency: null == currency ? _self.currency : currency // ignore: cast_nullable_to_non_nullable
as CurrencyCode,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as CeremonyStatus,eventDate: freezed == eventDate ? _self.eventDate : eventDate // ignore: cast_nullable_to_non_nullable
as LocalDate?,selectedScenarioId: freezed == selectedScenarioId ? _self.selectedScenarioId : selectedScenarioId // ignore: cast_nullable_to_non_nullable
as String?,giftGoalId: freezed == giftGoalId ? _self.giftGoalId : giftGoalId // ignore: cast_nullable_to_non_nullable
as String?,debtMonthly: freezed == debtMonthly ? _self.debtMonthly : debtMonthly // ignore: cast_nullable_to_non_nullable
as Money?,debtAnnualRateBp: freezed == debtAnnualRateBp ? _self.debtAnnualRateBp : debtAnnualRateBp // ignore: cast_nullable_to_non_nullable
as int?,
  ));
}

/// Create a copy of CeremonyPlan
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}

/// @nodoc
mixin _$CeremonyScenario {

 SyncMeta get meta; String get planId; String get name; int get guests; int get sortOrder;
/// Create a copy of CeremonyScenario
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CeremonyScenarioCopyWith<CeremonyScenario> get copyWith => _$CeremonyScenarioCopyWithImpl<CeremonyScenario>(this as CeremonyScenario, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is CeremonyScenario&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.planId, planId) || other.planId == planId)&&(identical(other.name, name) || other.name == name)&&(identical(other.guests, guests) || other.guests == guests)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder));
}


@override
int get hashCode => Object.hash(runtimeType,meta,planId,name,guests,sortOrder);

@override
String toString() {
  return 'CeremonyScenario(meta: $meta, planId: $planId, name: $name, guests: $guests, sortOrder: $sortOrder)';
}


}

/// @nodoc
abstract mixin class $CeremonyScenarioCopyWith<$Res>  {
  factory $CeremonyScenarioCopyWith(CeremonyScenario value, $Res Function(CeremonyScenario) _then) = _$CeremonyScenarioCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String planId, String name, int guests, int sortOrder
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$CeremonyScenarioCopyWithImpl<$Res>
    implements $CeremonyScenarioCopyWith<$Res> {
  _$CeremonyScenarioCopyWithImpl(this._self, this._then);

  final CeremonyScenario _self;
  final $Res Function(CeremonyScenario) _then;

/// Create a copy of CeremonyScenario
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? planId = null,Object? name = null,Object? guests = null,Object? sortOrder = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,planId: null == planId ? _self.planId : planId // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,guests: null == guests ? _self.guests : guests // ignore: cast_nullable_to_non_nullable
as int,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,
  ));
}
/// Create a copy of CeremonyScenario
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [CeremonyScenario].
extension CeremonyScenarioPatterns on CeremonyScenario {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _CeremonyScenario value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _CeremonyScenario() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _CeremonyScenario value)  $default,){
final _that = this;
switch (_that) {
case _CeremonyScenario():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _CeremonyScenario value)?  $default,){
final _that = this;
switch (_that) {
case _CeremonyScenario() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String planId,  String name,  int guests,  int sortOrder)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _CeremonyScenario() when $default != null:
return $default(_that.meta,_that.planId,_that.name,_that.guests,_that.sortOrder);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String planId,  String name,  int guests,  int sortOrder)  $default,) {final _that = this;
switch (_that) {
case _CeremonyScenario():
return $default(_that.meta,_that.planId,_that.name,_that.guests,_that.sortOrder);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String planId,  String name,  int guests,  int sortOrder)?  $default,) {final _that = this;
switch (_that) {
case _CeremonyScenario() when $default != null:
return $default(_that.meta,_that.planId,_that.name,_that.guests,_that.sortOrder);case _:
  return null;

}
}

}

/// @nodoc


class _CeremonyScenario implements CeremonyScenario {
  const _CeremonyScenario({required this.meta, required this.planId, required this.name, this.guests = 0, this.sortOrder = 0});
  

@override final  SyncMeta meta;
@override final  String planId;
@override final  String name;
@override@JsonKey() final  int guests;
@override@JsonKey() final  int sortOrder;

/// Create a copy of CeremonyScenario
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CeremonyScenarioCopyWith<_CeremonyScenario> get copyWith => __$CeremonyScenarioCopyWithImpl<_CeremonyScenario>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _CeremonyScenario&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.planId, planId) || other.planId == planId)&&(identical(other.name, name) || other.name == name)&&(identical(other.guests, guests) || other.guests == guests)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder));
}


@override
int get hashCode => Object.hash(runtimeType,meta,planId,name,guests,sortOrder);

@override
String toString() {
  return 'CeremonyScenario(meta: $meta, planId: $planId, name: $name, guests: $guests, sortOrder: $sortOrder)';
}


}

/// @nodoc
abstract mixin class _$CeremonyScenarioCopyWith<$Res> implements $CeremonyScenarioCopyWith<$Res> {
  factory _$CeremonyScenarioCopyWith(_CeremonyScenario value, $Res Function(_CeremonyScenario) _then) = __$CeremonyScenarioCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String planId, String name, int guests, int sortOrder
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$CeremonyScenarioCopyWithImpl<$Res>
    implements _$CeremonyScenarioCopyWith<$Res> {
  __$CeremonyScenarioCopyWithImpl(this._self, this._then);

  final _CeremonyScenario _self;
  final $Res Function(_CeremonyScenario) _then;

/// Create a copy of CeremonyScenario
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? planId = null,Object? name = null,Object? guests = null,Object? sortOrder = null,}) {
  return _then(_CeremonyScenario(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,planId: null == planId ? _self.planId : planId // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,guests: null == guests ? _self.guests : guests // ignore: cast_nullable_to_non_nullable
as int,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

/// Create a copy of CeremonyScenario
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}

/// @nodoc
mixin _$CeremonyBudgetLine {

 SyncMeta get meta; String get scenarioId; String get title; CeremonyLineKind get kind; Money get amount; FundingSource get source; int get sortOrder;
/// Create a copy of CeremonyBudgetLine
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CeremonyBudgetLineCopyWith<CeremonyBudgetLine> get copyWith => _$CeremonyBudgetLineCopyWithImpl<CeremonyBudgetLine>(this as CeremonyBudgetLine, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is CeremonyBudgetLine&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.scenarioId, scenarioId) || other.scenarioId == scenarioId)&&(identical(other.title, title) || other.title == title)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.source, source) || other.source == source)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder));
}


@override
int get hashCode => Object.hash(runtimeType,meta,scenarioId,title,kind,amount,source,sortOrder);

@override
String toString() {
  return 'CeremonyBudgetLine(meta: $meta, scenarioId: $scenarioId, title: $title, kind: $kind, amount: $amount, source: $source, sortOrder: $sortOrder)';
}


}

/// @nodoc
abstract mixin class $CeremonyBudgetLineCopyWith<$Res>  {
  factory $CeremonyBudgetLineCopyWith(CeremonyBudgetLine value, $Res Function(CeremonyBudgetLine) _then) = _$CeremonyBudgetLineCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String scenarioId, String title, CeremonyLineKind kind, Money amount, FundingSource source, int sortOrder
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$CeremonyBudgetLineCopyWithImpl<$Res>
    implements $CeremonyBudgetLineCopyWith<$Res> {
  _$CeremonyBudgetLineCopyWithImpl(this._self, this._then);

  final CeremonyBudgetLine _self;
  final $Res Function(CeremonyBudgetLine) _then;

/// Create a copy of CeremonyBudgetLine
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? scenarioId = null,Object? title = null,Object? kind = null,Object? amount = null,Object? source = null,Object? sortOrder = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,scenarioId: null == scenarioId ? _self.scenarioId : scenarioId // ignore: cast_nullable_to_non_nullable
as String,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as CeremonyLineKind,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,source: null == source ? _self.source : source // ignore: cast_nullable_to_non_nullable
as FundingSource,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,
  ));
}
/// Create a copy of CeremonyBudgetLine
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [CeremonyBudgetLine].
extension CeremonyBudgetLinePatterns on CeremonyBudgetLine {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _CeremonyBudgetLine value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _CeremonyBudgetLine() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _CeremonyBudgetLine value)  $default,){
final _that = this;
switch (_that) {
case _CeremonyBudgetLine():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _CeremonyBudgetLine value)?  $default,){
final _that = this;
switch (_that) {
case _CeremonyBudgetLine() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String scenarioId,  String title,  CeremonyLineKind kind,  Money amount,  FundingSource source,  int sortOrder)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _CeremonyBudgetLine() when $default != null:
return $default(_that.meta,_that.scenarioId,_that.title,_that.kind,_that.amount,_that.source,_that.sortOrder);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String scenarioId,  String title,  CeremonyLineKind kind,  Money amount,  FundingSource source,  int sortOrder)  $default,) {final _that = this;
switch (_that) {
case _CeremonyBudgetLine():
return $default(_that.meta,_that.scenarioId,_that.title,_that.kind,_that.amount,_that.source,_that.sortOrder);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String scenarioId,  String title,  CeremonyLineKind kind,  Money amount,  FundingSource source,  int sortOrder)?  $default,) {final _that = this;
switch (_that) {
case _CeremonyBudgetLine() when $default != null:
return $default(_that.meta,_that.scenarioId,_that.title,_that.kind,_that.amount,_that.source,_that.sortOrder);case _:
  return null;

}
}

}

/// @nodoc


class _CeremonyBudgetLine extends CeremonyBudgetLine {
  const _CeremonyBudgetLine({required this.meta, required this.scenarioId, required this.title, required this.kind, required this.amount, required this.source, this.sortOrder = 0}): super._();
  

@override final  SyncMeta meta;
@override final  String scenarioId;
@override final  String title;
@override final  CeremonyLineKind kind;
@override final  Money amount;
@override final  FundingSource source;
@override@JsonKey() final  int sortOrder;

/// Create a copy of CeremonyBudgetLine
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CeremonyBudgetLineCopyWith<_CeremonyBudgetLine> get copyWith => __$CeremonyBudgetLineCopyWithImpl<_CeremonyBudgetLine>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _CeremonyBudgetLine&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.scenarioId, scenarioId) || other.scenarioId == scenarioId)&&(identical(other.title, title) || other.title == title)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.source, source) || other.source == source)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder));
}


@override
int get hashCode => Object.hash(runtimeType,meta,scenarioId,title,kind,amount,source,sortOrder);

@override
String toString() {
  return 'CeremonyBudgetLine(meta: $meta, scenarioId: $scenarioId, title: $title, kind: $kind, amount: $amount, source: $source, sortOrder: $sortOrder)';
}


}

/// @nodoc
abstract mixin class _$CeremonyBudgetLineCopyWith<$Res> implements $CeremonyBudgetLineCopyWith<$Res> {
  factory _$CeremonyBudgetLineCopyWith(_CeremonyBudgetLine value, $Res Function(_CeremonyBudgetLine) _then) = __$CeremonyBudgetLineCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String scenarioId, String title, CeremonyLineKind kind, Money amount, FundingSource source, int sortOrder
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$CeremonyBudgetLineCopyWithImpl<$Res>
    implements _$CeremonyBudgetLineCopyWith<$Res> {
  __$CeremonyBudgetLineCopyWithImpl(this._self, this._then);

  final _CeremonyBudgetLine _self;
  final $Res Function(_CeremonyBudgetLine) _then;

/// Create a copy of CeremonyBudgetLine
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? scenarioId = null,Object? title = null,Object? kind = null,Object? amount = null,Object? source = null,Object? sortOrder = null,}) {
  return _then(_CeremonyBudgetLine(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,scenarioId: null == scenarioId ? _self.scenarioId : scenarioId // ignore: cast_nullable_to_non_nullable
as String,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as CeremonyLineKind,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,source: null == source ? _self.source : source // ignore: cast_nullable_to_non_nullable
as FundingSource,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

/// Create a copy of CeremonyBudgetLine
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}

/// @nodoc
mixin _$CeremonyDiscussionMark {

 SyncMeta get meta; String get planId; String get memberId;
/// Create a copy of CeremonyDiscussionMark
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CeremonyDiscussionMarkCopyWith<CeremonyDiscussionMark> get copyWith => _$CeremonyDiscussionMarkCopyWithImpl<CeremonyDiscussionMark>(this as CeremonyDiscussionMark, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is CeremonyDiscussionMark&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.planId, planId) || other.planId == planId)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,planId,memberId);

@override
String toString() {
  return 'CeremonyDiscussionMark(meta: $meta, planId: $planId, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class $CeremonyDiscussionMarkCopyWith<$Res>  {
  factory $CeremonyDiscussionMarkCopyWith(CeremonyDiscussionMark value, $Res Function(CeremonyDiscussionMark) _then) = _$CeremonyDiscussionMarkCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String planId, String memberId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$CeremonyDiscussionMarkCopyWithImpl<$Res>
    implements $CeremonyDiscussionMarkCopyWith<$Res> {
  _$CeremonyDiscussionMarkCopyWithImpl(this._self, this._then);

  final CeremonyDiscussionMark _self;
  final $Res Function(CeremonyDiscussionMark) _then;

/// Create a copy of CeremonyDiscussionMark
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? planId = null,Object? memberId = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,planId: null == planId ? _self.planId : planId // ignore: cast_nullable_to_non_nullable
as String,memberId: null == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String,
  ));
}
/// Create a copy of CeremonyDiscussionMark
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [CeremonyDiscussionMark].
extension CeremonyDiscussionMarkPatterns on CeremonyDiscussionMark {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _CeremonyDiscussionMark value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _CeremonyDiscussionMark() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _CeremonyDiscussionMark value)  $default,){
final _that = this;
switch (_that) {
case _CeremonyDiscussionMark():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _CeremonyDiscussionMark value)?  $default,){
final _that = this;
switch (_that) {
case _CeremonyDiscussionMark() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String planId,  String memberId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _CeremonyDiscussionMark() when $default != null:
return $default(_that.meta,_that.planId,_that.memberId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String planId,  String memberId)  $default,) {final _that = this;
switch (_that) {
case _CeremonyDiscussionMark():
return $default(_that.meta,_that.planId,_that.memberId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String planId,  String memberId)?  $default,) {final _that = this;
switch (_that) {
case _CeremonyDiscussionMark() when $default != null:
return $default(_that.meta,_that.planId,_that.memberId);case _:
  return null;

}
}

}

/// @nodoc


class _CeremonyDiscussionMark implements CeremonyDiscussionMark {
  const _CeremonyDiscussionMark({required this.meta, required this.planId, required this.memberId});
  

@override final  SyncMeta meta;
@override final  String planId;
@override final  String memberId;

/// Create a copy of CeremonyDiscussionMark
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CeremonyDiscussionMarkCopyWith<_CeremonyDiscussionMark> get copyWith => __$CeremonyDiscussionMarkCopyWithImpl<_CeremonyDiscussionMark>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _CeremonyDiscussionMark&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.planId, planId) || other.planId == planId)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,planId,memberId);

@override
String toString() {
  return 'CeremonyDiscussionMark(meta: $meta, planId: $planId, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class _$CeremonyDiscussionMarkCopyWith<$Res> implements $CeremonyDiscussionMarkCopyWith<$Res> {
  factory _$CeremonyDiscussionMarkCopyWith(_CeremonyDiscussionMark value, $Res Function(_CeremonyDiscussionMark) _then) = __$CeremonyDiscussionMarkCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String planId, String memberId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$CeremonyDiscussionMarkCopyWithImpl<$Res>
    implements _$CeremonyDiscussionMarkCopyWith<$Res> {
  __$CeremonyDiscussionMarkCopyWithImpl(this._self, this._then);

  final _CeremonyDiscussionMark _self;
  final $Res Function(_CeremonyDiscussionMark) _then;

/// Create a copy of CeremonyDiscussionMark
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? planId = null,Object? memberId = null,}) {
  return _then(_CeremonyDiscussionMark(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,planId: null == planId ? _self.planId : planId // ignore: cast_nullable_to_non_nullable
as String,memberId: null == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

/// Create a copy of CeremonyDiscussionMark
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}

/// @nodoc
mixin _$GoalContribution {

 SyncMeta get meta; String get goalId; String get contributorName; Money get amount; LocalDate get receivedOn;
/// Create a copy of GoalContribution
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$GoalContributionCopyWith<GoalContribution> get copyWith => _$GoalContributionCopyWithImpl<GoalContribution>(this as GoalContribution, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is GoalContribution&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.goalId, goalId) || other.goalId == goalId)&&(identical(other.contributorName, contributorName) || other.contributorName == contributorName)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.receivedOn, receivedOn) || other.receivedOn == receivedOn));
}


@override
int get hashCode => Object.hash(runtimeType,meta,goalId,contributorName,amount,receivedOn);

@override
String toString() {
  return 'GoalContribution(meta: $meta, goalId: $goalId, contributorName: $contributorName, amount: $amount, receivedOn: $receivedOn)';
}


}

/// @nodoc
abstract mixin class $GoalContributionCopyWith<$Res>  {
  factory $GoalContributionCopyWith(GoalContribution value, $Res Function(GoalContribution) _then) = _$GoalContributionCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String goalId, String contributorName, Money amount, LocalDate receivedOn
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$GoalContributionCopyWithImpl<$Res>
    implements $GoalContributionCopyWith<$Res> {
  _$GoalContributionCopyWithImpl(this._self, this._then);

  final GoalContribution _self;
  final $Res Function(GoalContribution) _then;

/// Create a copy of GoalContribution
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? goalId = null,Object? contributorName = null,Object? amount = null,Object? receivedOn = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,goalId: null == goalId ? _self.goalId : goalId // ignore: cast_nullable_to_non_nullable
as String,contributorName: null == contributorName ? _self.contributorName : contributorName // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,receivedOn: null == receivedOn ? _self.receivedOn : receivedOn // ignore: cast_nullable_to_non_nullable
as LocalDate,
  ));
}
/// Create a copy of GoalContribution
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [GoalContribution].
extension GoalContributionPatterns on GoalContribution {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _GoalContribution value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _GoalContribution() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _GoalContribution value)  $default,){
final _that = this;
switch (_that) {
case _GoalContribution():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _GoalContribution value)?  $default,){
final _that = this;
switch (_that) {
case _GoalContribution() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String goalId,  String contributorName,  Money amount,  LocalDate receivedOn)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _GoalContribution() when $default != null:
return $default(_that.meta,_that.goalId,_that.contributorName,_that.amount,_that.receivedOn);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String goalId,  String contributorName,  Money amount,  LocalDate receivedOn)  $default,) {final _that = this;
switch (_that) {
case _GoalContribution():
return $default(_that.meta,_that.goalId,_that.contributorName,_that.amount,_that.receivedOn);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String goalId,  String contributorName,  Money amount,  LocalDate receivedOn)?  $default,) {final _that = this;
switch (_that) {
case _GoalContribution() when $default != null:
return $default(_that.meta,_that.goalId,_that.contributorName,_that.amount,_that.receivedOn);case _:
  return null;

}
}

}

/// @nodoc


class _GoalContribution implements GoalContribution {
  const _GoalContribution({required this.meta, required this.goalId, required this.contributorName, required this.amount, required this.receivedOn});
  

@override final  SyncMeta meta;
@override final  String goalId;
@override final  String contributorName;
@override final  Money amount;
@override final  LocalDate receivedOn;

/// Create a copy of GoalContribution
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$GoalContributionCopyWith<_GoalContribution> get copyWith => __$GoalContributionCopyWithImpl<_GoalContribution>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _GoalContribution&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.goalId, goalId) || other.goalId == goalId)&&(identical(other.contributorName, contributorName) || other.contributorName == contributorName)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.receivedOn, receivedOn) || other.receivedOn == receivedOn));
}


@override
int get hashCode => Object.hash(runtimeType,meta,goalId,contributorName,amount,receivedOn);

@override
String toString() {
  return 'GoalContribution(meta: $meta, goalId: $goalId, contributorName: $contributorName, amount: $amount, receivedOn: $receivedOn)';
}


}

/// @nodoc
abstract mixin class _$GoalContributionCopyWith<$Res> implements $GoalContributionCopyWith<$Res> {
  factory _$GoalContributionCopyWith(_GoalContribution value, $Res Function(_GoalContribution) _then) = __$GoalContributionCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String goalId, String contributorName, Money amount, LocalDate receivedOn
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$GoalContributionCopyWithImpl<$Res>
    implements _$GoalContributionCopyWith<$Res> {
  __$GoalContributionCopyWithImpl(this._self, this._then);

  final _GoalContribution _self;
  final $Res Function(_GoalContribution) _then;

/// Create a copy of GoalContribution
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? goalId = null,Object? contributorName = null,Object? amount = null,Object? receivedOn = null,}) {
  return _then(_GoalContribution(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,goalId: null == goalId ? _self.goalId : goalId // ignore: cast_nullable_to_non_nullable
as String,contributorName: null == contributorName ? _self.contributorName : contributorName // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,receivedOn: null == receivedOn ? _self.receivedOn : receivedOn // ignore: cast_nullable_to_non_nullable
as LocalDate,
  ));
}

/// Create a copy of GoalContribution
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}

// dart format on
