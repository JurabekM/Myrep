// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'household.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$Household {

 SyncMeta get meta; String? get name; CurrencyCode get baseCurrency; int get weekAnchor; int get monthStartDay;/// «Qutqarilgan pul» bazaviy oyi boshi; `null` — birinchi audit oyi.
 LocalDate? get rescueBaselineStart;/// Oylik zarur + kerak taxminiy summasi (zaxira maqsadi uchun, v8).
 Money? get reserveMonthlyEstimate;/// Tayyorgarlik darvozasi ongli chetlab o'tilgan vaqt (UTC, v8).
 DateTime? get gateBypassedAt;/// Byudjet rejimi va «Qarzdan chiqish» ulushlari (v10, SPEC 2D.1).
 BudgetMode get budgetMode; RecoverySplit get recoverySplit;/// Rejim odatiyga qaytgach bo'shagan 20 % ni yo'naltirish taklifi.
 bool get freedShareOfferPending;/// Onboarding yakunlangan vaqt (UTC, v14) va daromad turi.
 DateTime? get onboardedAt; IncomeKind? get incomeKind;
/// Create a copy of Household
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$HouseholdCopyWith<Household> get copyWith => _$HouseholdCopyWithImpl<Household>(this as Household, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Household&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.name, name) || other.name == name)&&(identical(other.baseCurrency, baseCurrency) || other.baseCurrency == baseCurrency)&&(identical(other.weekAnchor, weekAnchor) || other.weekAnchor == weekAnchor)&&(identical(other.monthStartDay, monthStartDay) || other.monthStartDay == monthStartDay)&&(identical(other.rescueBaselineStart, rescueBaselineStart) || other.rescueBaselineStart == rescueBaselineStart)&&(identical(other.reserveMonthlyEstimate, reserveMonthlyEstimate) || other.reserveMonthlyEstimate == reserveMonthlyEstimate)&&(identical(other.gateBypassedAt, gateBypassedAt) || other.gateBypassedAt == gateBypassedAt)&&(identical(other.budgetMode, budgetMode) || other.budgetMode == budgetMode)&&(identical(other.recoverySplit, recoverySplit) || other.recoverySplit == recoverySplit)&&(identical(other.freedShareOfferPending, freedShareOfferPending) || other.freedShareOfferPending == freedShareOfferPending)&&(identical(other.onboardedAt, onboardedAt) || other.onboardedAt == onboardedAt)&&(identical(other.incomeKind, incomeKind) || other.incomeKind == incomeKind));
}


@override
int get hashCode => Object.hash(runtimeType,meta,name,baseCurrency,weekAnchor,monthStartDay,rescueBaselineStart,reserveMonthlyEstimate,gateBypassedAt,budgetMode,recoverySplit,freedShareOfferPending,onboardedAt,incomeKind);

@override
String toString() {
  return 'Household(meta: $meta, name: $name, baseCurrency: $baseCurrency, weekAnchor: $weekAnchor, monthStartDay: $monthStartDay, rescueBaselineStart: $rescueBaselineStart, reserveMonthlyEstimate: $reserveMonthlyEstimate, gateBypassedAt: $gateBypassedAt, budgetMode: $budgetMode, recoverySplit: $recoverySplit, freedShareOfferPending: $freedShareOfferPending, onboardedAt: $onboardedAt, incomeKind: $incomeKind)';
}


}

/// @nodoc
abstract mixin class $HouseholdCopyWith<$Res>  {
  factory $HouseholdCopyWith(Household value, $Res Function(Household) _then) = _$HouseholdCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String? name, CurrencyCode baseCurrency, int weekAnchor, int monthStartDay, LocalDate? rescueBaselineStart, Money? reserveMonthlyEstimate, DateTime? gateBypassedAt, BudgetMode budgetMode, RecoverySplit recoverySplit, bool freedShareOfferPending, DateTime? onboardedAt, IncomeKind? incomeKind
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$HouseholdCopyWithImpl<$Res>
    implements $HouseholdCopyWith<$Res> {
  _$HouseholdCopyWithImpl(this._self, this._then);

  final Household _self;
  final $Res Function(Household) _then;

/// Create a copy of Household
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? name = freezed,Object? baseCurrency = null,Object? weekAnchor = null,Object? monthStartDay = null,Object? rescueBaselineStart = freezed,Object? reserveMonthlyEstimate = freezed,Object? gateBypassedAt = freezed,Object? budgetMode = null,Object? recoverySplit = null,Object? freedShareOfferPending = null,Object? onboardedAt = freezed,Object? incomeKind = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,name: freezed == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String?,baseCurrency: null == baseCurrency ? _self.baseCurrency : baseCurrency // ignore: cast_nullable_to_non_nullable
as CurrencyCode,weekAnchor: null == weekAnchor ? _self.weekAnchor : weekAnchor // ignore: cast_nullable_to_non_nullable
as int,monthStartDay: null == monthStartDay ? _self.monthStartDay : monthStartDay // ignore: cast_nullable_to_non_nullable
as int,rescueBaselineStart: freezed == rescueBaselineStart ? _self.rescueBaselineStart : rescueBaselineStart // ignore: cast_nullable_to_non_nullable
as LocalDate?,reserveMonthlyEstimate: freezed == reserveMonthlyEstimate ? _self.reserveMonthlyEstimate : reserveMonthlyEstimate // ignore: cast_nullable_to_non_nullable
as Money?,gateBypassedAt: freezed == gateBypassedAt ? _self.gateBypassedAt : gateBypassedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,budgetMode: null == budgetMode ? _self.budgetMode : budgetMode // ignore: cast_nullable_to_non_nullable
as BudgetMode,recoverySplit: null == recoverySplit ? _self.recoverySplit : recoverySplit // ignore: cast_nullable_to_non_nullable
as RecoverySplit,freedShareOfferPending: null == freedShareOfferPending ? _self.freedShareOfferPending : freedShareOfferPending // ignore: cast_nullable_to_non_nullable
as bool,onboardedAt: freezed == onboardedAt ? _self.onboardedAt : onboardedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,incomeKind: freezed == incomeKind ? _self.incomeKind : incomeKind // ignore: cast_nullable_to_non_nullable
as IncomeKind?,
  ));
}
/// Create a copy of Household
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Household].
extension HouseholdPatterns on Household {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Household value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Household() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Household value)  $default,){
final _that = this;
switch (_that) {
case _Household():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Household value)?  $default,){
final _that = this;
switch (_that) {
case _Household() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String? name,  CurrencyCode baseCurrency,  int weekAnchor,  int monthStartDay,  LocalDate? rescueBaselineStart,  Money? reserveMonthlyEstimate,  DateTime? gateBypassedAt,  BudgetMode budgetMode,  RecoverySplit recoverySplit,  bool freedShareOfferPending,  DateTime? onboardedAt,  IncomeKind? incomeKind)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Household() when $default != null:
return $default(_that.meta,_that.name,_that.baseCurrency,_that.weekAnchor,_that.monthStartDay,_that.rescueBaselineStart,_that.reserveMonthlyEstimate,_that.gateBypassedAt,_that.budgetMode,_that.recoverySplit,_that.freedShareOfferPending,_that.onboardedAt,_that.incomeKind);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String? name,  CurrencyCode baseCurrency,  int weekAnchor,  int monthStartDay,  LocalDate? rescueBaselineStart,  Money? reserveMonthlyEstimate,  DateTime? gateBypassedAt,  BudgetMode budgetMode,  RecoverySplit recoverySplit,  bool freedShareOfferPending,  DateTime? onboardedAt,  IncomeKind? incomeKind)  $default,) {final _that = this;
switch (_that) {
case _Household():
return $default(_that.meta,_that.name,_that.baseCurrency,_that.weekAnchor,_that.monthStartDay,_that.rescueBaselineStart,_that.reserveMonthlyEstimate,_that.gateBypassedAt,_that.budgetMode,_that.recoverySplit,_that.freedShareOfferPending,_that.onboardedAt,_that.incomeKind);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String? name,  CurrencyCode baseCurrency,  int weekAnchor,  int monthStartDay,  LocalDate? rescueBaselineStart,  Money? reserveMonthlyEstimate,  DateTime? gateBypassedAt,  BudgetMode budgetMode,  RecoverySplit recoverySplit,  bool freedShareOfferPending,  DateTime? onboardedAt,  IncomeKind? incomeKind)?  $default,) {final _that = this;
switch (_that) {
case _Household() when $default != null:
return $default(_that.meta,_that.name,_that.baseCurrency,_that.weekAnchor,_that.monthStartDay,_that.rescueBaselineStart,_that.reserveMonthlyEstimate,_that.gateBypassedAt,_that.budgetMode,_that.recoverySplit,_that.freedShareOfferPending,_that.onboardedAt,_that.incomeKind);case _:
  return null;

}
}

}

/// @nodoc


class _Household extends Household {
  const _Household({required this.meta, this.name, this.baseCurrency = CurrencyCode.uzs, this.weekAnchor = DateTime.friday, this.monthStartDay = 1, this.rescueBaselineStart, this.reserveMonthlyEstimate, this.gateBypassedAt, this.budgetMode = BudgetMode.standard, this.recoverySplit = RecoverySplit.standard, this.freedShareOfferPending = false, this.onboardedAt, this.incomeKind}): super._();
  

@override final  SyncMeta meta;
@override final  String? name;
@override@JsonKey() final  CurrencyCode baseCurrency;
@override@JsonKey() final  int weekAnchor;
@override@JsonKey() final  int monthStartDay;
/// «Qutqarilgan pul» bazaviy oyi boshi; `null` — birinchi audit oyi.
@override final  LocalDate? rescueBaselineStart;
/// Oylik zarur + kerak taxminiy summasi (zaxira maqsadi uchun, v8).
@override final  Money? reserveMonthlyEstimate;
/// Tayyorgarlik darvozasi ongli chetlab o'tilgan vaqt (UTC, v8).
@override final  DateTime? gateBypassedAt;
/// Byudjet rejimi va «Qarzdan chiqish» ulushlari (v10, SPEC 2D.1).
@override@JsonKey() final  BudgetMode budgetMode;
@override@JsonKey() final  RecoverySplit recoverySplit;
/// Rejim odatiyga qaytgach bo'shagan 20 % ni yo'naltirish taklifi.
@override@JsonKey() final  bool freedShareOfferPending;
/// Onboarding yakunlangan vaqt (UTC, v14) va daromad turi.
@override final  DateTime? onboardedAt;
@override final  IncomeKind? incomeKind;

/// Create a copy of Household
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$HouseholdCopyWith<_Household> get copyWith => __$HouseholdCopyWithImpl<_Household>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Household&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.name, name) || other.name == name)&&(identical(other.baseCurrency, baseCurrency) || other.baseCurrency == baseCurrency)&&(identical(other.weekAnchor, weekAnchor) || other.weekAnchor == weekAnchor)&&(identical(other.monthStartDay, monthStartDay) || other.monthStartDay == monthStartDay)&&(identical(other.rescueBaselineStart, rescueBaselineStart) || other.rescueBaselineStart == rescueBaselineStart)&&(identical(other.reserveMonthlyEstimate, reserveMonthlyEstimate) || other.reserveMonthlyEstimate == reserveMonthlyEstimate)&&(identical(other.gateBypassedAt, gateBypassedAt) || other.gateBypassedAt == gateBypassedAt)&&(identical(other.budgetMode, budgetMode) || other.budgetMode == budgetMode)&&(identical(other.recoverySplit, recoverySplit) || other.recoverySplit == recoverySplit)&&(identical(other.freedShareOfferPending, freedShareOfferPending) || other.freedShareOfferPending == freedShareOfferPending)&&(identical(other.onboardedAt, onboardedAt) || other.onboardedAt == onboardedAt)&&(identical(other.incomeKind, incomeKind) || other.incomeKind == incomeKind));
}


@override
int get hashCode => Object.hash(runtimeType,meta,name,baseCurrency,weekAnchor,monthStartDay,rescueBaselineStart,reserveMonthlyEstimate,gateBypassedAt,budgetMode,recoverySplit,freedShareOfferPending,onboardedAt,incomeKind);

@override
String toString() {
  return 'Household(meta: $meta, name: $name, baseCurrency: $baseCurrency, weekAnchor: $weekAnchor, monthStartDay: $monthStartDay, rescueBaselineStart: $rescueBaselineStart, reserveMonthlyEstimate: $reserveMonthlyEstimate, gateBypassedAt: $gateBypassedAt, budgetMode: $budgetMode, recoverySplit: $recoverySplit, freedShareOfferPending: $freedShareOfferPending, onboardedAt: $onboardedAt, incomeKind: $incomeKind)';
}


}

/// @nodoc
abstract mixin class _$HouseholdCopyWith<$Res> implements $HouseholdCopyWith<$Res> {
  factory _$HouseholdCopyWith(_Household value, $Res Function(_Household) _then) = __$HouseholdCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String? name, CurrencyCode baseCurrency, int weekAnchor, int monthStartDay, LocalDate? rescueBaselineStart, Money? reserveMonthlyEstimate, DateTime? gateBypassedAt, BudgetMode budgetMode, RecoverySplit recoverySplit, bool freedShareOfferPending, DateTime? onboardedAt, IncomeKind? incomeKind
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$HouseholdCopyWithImpl<$Res>
    implements _$HouseholdCopyWith<$Res> {
  __$HouseholdCopyWithImpl(this._self, this._then);

  final _Household _self;
  final $Res Function(_Household) _then;

/// Create a copy of Household
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? name = freezed,Object? baseCurrency = null,Object? weekAnchor = null,Object? monthStartDay = null,Object? rescueBaselineStart = freezed,Object? reserveMonthlyEstimate = freezed,Object? gateBypassedAt = freezed,Object? budgetMode = null,Object? recoverySplit = null,Object? freedShareOfferPending = null,Object? onboardedAt = freezed,Object? incomeKind = freezed,}) {
  return _then(_Household(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,name: freezed == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String?,baseCurrency: null == baseCurrency ? _self.baseCurrency : baseCurrency // ignore: cast_nullable_to_non_nullable
as CurrencyCode,weekAnchor: null == weekAnchor ? _self.weekAnchor : weekAnchor // ignore: cast_nullable_to_non_nullable
as int,monthStartDay: null == monthStartDay ? _self.monthStartDay : monthStartDay // ignore: cast_nullable_to_non_nullable
as int,rescueBaselineStart: freezed == rescueBaselineStart ? _self.rescueBaselineStart : rescueBaselineStart // ignore: cast_nullable_to_non_nullable
as LocalDate?,reserveMonthlyEstimate: freezed == reserveMonthlyEstimate ? _self.reserveMonthlyEstimate : reserveMonthlyEstimate // ignore: cast_nullable_to_non_nullable
as Money?,gateBypassedAt: freezed == gateBypassedAt ? _self.gateBypassedAt : gateBypassedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,budgetMode: null == budgetMode ? _self.budgetMode : budgetMode // ignore: cast_nullable_to_non_nullable
as BudgetMode,recoverySplit: null == recoverySplit ? _self.recoverySplit : recoverySplit // ignore: cast_nullable_to_non_nullable
as RecoverySplit,freedShareOfferPending: null == freedShareOfferPending ? _self.freedShareOfferPending : freedShareOfferPending // ignore: cast_nullable_to_non_nullable
as bool,onboardedAt: freezed == onboardedAt ? _self.onboardedAt : onboardedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,incomeKind: freezed == incomeKind ? _self.incomeKind : incomeKind // ignore: cast_nullable_to_non_nullable
as IncomeKind?,
  ));
}

/// Create a copy of Household
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
mixin _$Member {

 SyncMeta get meta; String get displayName; MemberRole get role; bool get isOwner;/// Ixtiyoriy shaxsiy PIN hosilasi (oilaviy rozilik uchun).
 PinRecord? get personalPin;
/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MemberCopyWith<Member> get copyWith => _$MemberCopyWithImpl<Member>(this as Member, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Member&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.displayName, displayName) || other.displayName == displayName)&&(identical(other.role, role) || other.role == role)&&(identical(other.isOwner, isOwner) || other.isOwner == isOwner)&&(identical(other.personalPin, personalPin) || other.personalPin == personalPin));
}


@override
int get hashCode => Object.hash(runtimeType,meta,displayName,role,isOwner,personalPin);

@override
String toString() {
  return 'Member(meta: $meta, displayName: $displayName, role: $role, isOwner: $isOwner, personalPin: $personalPin)';
}


}

/// @nodoc
abstract mixin class $MemberCopyWith<$Res>  {
  factory $MemberCopyWith(Member value, $Res Function(Member) _then) = _$MemberCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String displayName, MemberRole role, bool isOwner, PinRecord? personalPin
});


$SyncMetaCopyWith<$Res> get meta;$PinRecordCopyWith<$Res>? get personalPin;

}
/// @nodoc
class _$MemberCopyWithImpl<$Res>
    implements $MemberCopyWith<$Res> {
  _$MemberCopyWithImpl(this._self, this._then);

  final Member _self;
  final $Res Function(Member) _then;

/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? displayName = null,Object? role = null,Object? isOwner = null,Object? personalPin = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,role: null == role ? _self.role : role // ignore: cast_nullable_to_non_nullable
as MemberRole,isOwner: null == isOwner ? _self.isOwner : isOwner // ignore: cast_nullable_to_non_nullable
as bool,personalPin: freezed == personalPin ? _self.personalPin : personalPin // ignore: cast_nullable_to_non_nullable
as PinRecord?,
  ));
}
/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$PinRecordCopyWith<$Res>? get personalPin {
    if (_self.personalPin == null) {
    return null;
  }

  return $PinRecordCopyWith<$Res>(_self.personalPin!, (value) {
    return _then(_self.copyWith(personalPin: value));
  });
}
}


/// Adds pattern-matching-related methods to [Member].
extension MemberPatterns on Member {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Member value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Member() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Member value)  $default,){
final _that = this;
switch (_that) {
case _Member():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Member value)?  $default,){
final _that = this;
switch (_that) {
case _Member() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String displayName,  MemberRole role,  bool isOwner,  PinRecord? personalPin)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Member() when $default != null:
return $default(_that.meta,_that.displayName,_that.role,_that.isOwner,_that.personalPin);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String displayName,  MemberRole role,  bool isOwner,  PinRecord? personalPin)  $default,) {final _that = this;
switch (_that) {
case _Member():
return $default(_that.meta,_that.displayName,_that.role,_that.isOwner,_that.personalPin);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String displayName,  MemberRole role,  bool isOwner,  PinRecord? personalPin)?  $default,) {final _that = this;
switch (_that) {
case _Member() when $default != null:
return $default(_that.meta,_that.displayName,_that.role,_that.isOwner,_that.personalPin);case _:
  return null;

}
}

}

/// @nodoc


class _Member extends Member {
  const _Member({required this.meta, required this.displayName, this.role = MemberRole.adult, this.isOwner = false, this.personalPin}): super._();
  

@override final  SyncMeta meta;
@override final  String displayName;
@override@JsonKey() final  MemberRole role;
@override@JsonKey() final  bool isOwner;
/// Ixtiyoriy shaxsiy PIN hosilasi (oilaviy rozilik uchun).
@override final  PinRecord? personalPin;

/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$MemberCopyWith<_Member> get copyWith => __$MemberCopyWithImpl<_Member>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Member&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.displayName, displayName) || other.displayName == displayName)&&(identical(other.role, role) || other.role == role)&&(identical(other.isOwner, isOwner) || other.isOwner == isOwner)&&(identical(other.personalPin, personalPin) || other.personalPin == personalPin));
}


@override
int get hashCode => Object.hash(runtimeType,meta,displayName,role,isOwner,personalPin);

@override
String toString() {
  return 'Member(meta: $meta, displayName: $displayName, role: $role, isOwner: $isOwner, personalPin: $personalPin)';
}


}

/// @nodoc
abstract mixin class _$MemberCopyWith<$Res> implements $MemberCopyWith<$Res> {
  factory _$MemberCopyWith(_Member value, $Res Function(_Member) _then) = __$MemberCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String displayName, MemberRole role, bool isOwner, PinRecord? personalPin
});


@override $SyncMetaCopyWith<$Res> get meta;@override $PinRecordCopyWith<$Res>? get personalPin;

}
/// @nodoc
class __$MemberCopyWithImpl<$Res>
    implements _$MemberCopyWith<$Res> {
  __$MemberCopyWithImpl(this._self, this._then);

  final _Member _self;
  final $Res Function(_Member) _then;

/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? displayName = null,Object? role = null,Object? isOwner = null,Object? personalPin = freezed,}) {
  return _then(_Member(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,role: null == role ? _self.role : role // ignore: cast_nullable_to_non_nullable
as MemberRole,isOwner: null == isOwner ? _self.isOwner : isOwner // ignore: cast_nullable_to_non_nullable
as bool,personalPin: freezed == personalPin ? _self.personalPin : personalPin // ignore: cast_nullable_to_non_nullable
as PinRecord?,
  ));
}

/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}/// Create a copy of Member
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$PinRecordCopyWith<$Res>? get personalPin {
    if (_self.personalPin == null) {
    return null;
  }

  return $PinRecordCopyWith<$Res>(_self.personalPin!, (value) {
    return _then(_self.copyWith(personalPin: value));
  });
}
}

// dart format on
