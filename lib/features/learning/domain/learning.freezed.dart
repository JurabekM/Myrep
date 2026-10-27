// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'learning.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$HourlySnapshot {

 SyncMeta get meta; Money get income; int get minutesPerDay; int get daysPerMonth; int get maxMinutesPerDay;/// Saqlangan paytdagi soat qiymati.
 Money get hourly; String? get memberId;
/// Create a copy of HourlySnapshot
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$HourlySnapshotCopyWith<HourlySnapshot> get copyWith => _$HourlySnapshotCopyWithImpl<HourlySnapshot>(this as HourlySnapshot, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is HourlySnapshot&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.income, income) || other.income == income)&&(identical(other.minutesPerDay, minutesPerDay) || other.minutesPerDay == minutesPerDay)&&(identical(other.daysPerMonth, daysPerMonth) || other.daysPerMonth == daysPerMonth)&&(identical(other.maxMinutesPerDay, maxMinutesPerDay) || other.maxMinutesPerDay == maxMinutesPerDay)&&(identical(other.hourly, hourly) || other.hourly == hourly)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,income,minutesPerDay,daysPerMonth,maxMinutesPerDay,hourly,memberId);

@override
String toString() {
  return 'HourlySnapshot(meta: $meta, income: $income, minutesPerDay: $minutesPerDay, daysPerMonth: $daysPerMonth, maxMinutesPerDay: $maxMinutesPerDay, hourly: $hourly, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class $HourlySnapshotCopyWith<$Res>  {
  factory $HourlySnapshotCopyWith(HourlySnapshot value, $Res Function(HourlySnapshot) _then) = _$HourlySnapshotCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, Money income, int minutesPerDay, int daysPerMonth, int maxMinutesPerDay, Money hourly, String? memberId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$HourlySnapshotCopyWithImpl<$Res>
    implements $HourlySnapshotCopyWith<$Res> {
  _$HourlySnapshotCopyWithImpl(this._self, this._then);

  final HourlySnapshot _self;
  final $Res Function(HourlySnapshot) _then;

/// Create a copy of HourlySnapshot
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? income = null,Object? minutesPerDay = null,Object? daysPerMonth = null,Object? maxMinutesPerDay = null,Object? hourly = null,Object? memberId = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,income: null == income ? _self.income : income // ignore: cast_nullable_to_non_nullable
as Money,minutesPerDay: null == minutesPerDay ? _self.minutesPerDay : minutesPerDay // ignore: cast_nullable_to_non_nullable
as int,daysPerMonth: null == daysPerMonth ? _self.daysPerMonth : daysPerMonth // ignore: cast_nullable_to_non_nullable
as int,maxMinutesPerDay: null == maxMinutesPerDay ? _self.maxMinutesPerDay : maxMinutesPerDay // ignore: cast_nullable_to_non_nullable
as int,hourly: null == hourly ? _self.hourly : hourly // ignore: cast_nullable_to_non_nullable
as Money,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of HourlySnapshot
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [HourlySnapshot].
extension HourlySnapshotPatterns on HourlySnapshot {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _HourlySnapshot value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _HourlySnapshot() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _HourlySnapshot value)  $default,){
final _that = this;
switch (_that) {
case _HourlySnapshot():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _HourlySnapshot value)?  $default,){
final _that = this;
switch (_that) {
case _HourlySnapshot() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  Money income,  int minutesPerDay,  int daysPerMonth,  int maxMinutesPerDay,  Money hourly,  String? memberId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _HourlySnapshot() when $default != null:
return $default(_that.meta,_that.income,_that.minutesPerDay,_that.daysPerMonth,_that.maxMinutesPerDay,_that.hourly,_that.memberId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  Money income,  int minutesPerDay,  int daysPerMonth,  int maxMinutesPerDay,  Money hourly,  String? memberId)  $default,) {final _that = this;
switch (_that) {
case _HourlySnapshot():
return $default(_that.meta,_that.income,_that.minutesPerDay,_that.daysPerMonth,_that.maxMinutesPerDay,_that.hourly,_that.memberId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  Money income,  int minutesPerDay,  int daysPerMonth,  int maxMinutesPerDay,  Money hourly,  String? memberId)?  $default,) {final _that = this;
switch (_that) {
case _HourlySnapshot() when $default != null:
return $default(_that.meta,_that.income,_that.minutesPerDay,_that.daysPerMonth,_that.maxMinutesPerDay,_that.hourly,_that.memberId);case _:
  return null;

}
}

}

/// @nodoc


class _HourlySnapshot extends HourlySnapshot {
  const _HourlySnapshot({required this.meta, required this.income, required this.minutesPerDay, required this.daysPerMonth, required this.maxMinutesPerDay, required this.hourly, this.memberId}): super._();
  

@override final  SyncMeta meta;
@override final  Money income;
@override final  int minutesPerDay;
@override final  int daysPerMonth;
@override final  int maxMinutesPerDay;
/// Saqlangan paytdagi soat qiymati.
@override final  Money hourly;
@override final  String? memberId;

/// Create a copy of HourlySnapshot
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$HourlySnapshotCopyWith<_HourlySnapshot> get copyWith => __$HourlySnapshotCopyWithImpl<_HourlySnapshot>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _HourlySnapshot&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.income, income) || other.income == income)&&(identical(other.minutesPerDay, minutesPerDay) || other.minutesPerDay == minutesPerDay)&&(identical(other.daysPerMonth, daysPerMonth) || other.daysPerMonth == daysPerMonth)&&(identical(other.maxMinutesPerDay, maxMinutesPerDay) || other.maxMinutesPerDay == maxMinutesPerDay)&&(identical(other.hourly, hourly) || other.hourly == hourly)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,income,minutesPerDay,daysPerMonth,maxMinutesPerDay,hourly,memberId);

@override
String toString() {
  return 'HourlySnapshot(meta: $meta, income: $income, minutesPerDay: $minutesPerDay, daysPerMonth: $daysPerMonth, maxMinutesPerDay: $maxMinutesPerDay, hourly: $hourly, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class _$HourlySnapshotCopyWith<$Res> implements $HourlySnapshotCopyWith<$Res> {
  factory _$HourlySnapshotCopyWith(_HourlySnapshot value, $Res Function(_HourlySnapshot) _then) = __$HourlySnapshotCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, Money income, int minutesPerDay, int daysPerMonth, int maxMinutesPerDay, Money hourly, String? memberId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$HourlySnapshotCopyWithImpl<$Res>
    implements _$HourlySnapshotCopyWith<$Res> {
  __$HourlySnapshotCopyWithImpl(this._self, this._then);

  final _HourlySnapshot _self;
  final $Res Function(_HourlySnapshot) _then;

/// Create a copy of HourlySnapshot
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? income = null,Object? minutesPerDay = null,Object? daysPerMonth = null,Object? maxMinutesPerDay = null,Object? hourly = null,Object? memberId = freezed,}) {
  return _then(_HourlySnapshot(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,income: null == income ? _self.income : income // ignore: cast_nullable_to_non_nullable
as Money,minutesPerDay: null == minutesPerDay ? _self.minutesPerDay : minutesPerDay // ignore: cast_nullable_to_non_nullable
as int,daysPerMonth: null == daysPerMonth ? _self.daysPerMonth : daysPerMonth // ignore: cast_nullable_to_non_nullable
as int,maxMinutesPerDay: null == maxMinutesPerDay ? _self.maxMinutesPerDay : maxMinutesPerDay // ignore: cast_nullable_to_non_nullable
as int,hourly: null == hourly ? _self.hourly : hourly // ignore: cast_nullable_to_non_nullable
as Money,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of HourlySnapshot
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
mixin _$LearningGoal {

 SyncMeta get meta; String get title; Money get baseHourly; Money get targetHourly; LearningGoalStatus get status; String? get why; String? get memberId;/// `DONE` yoki `DROPPED` bo'lgan vaqt (UTC).
 DateTime? get closedAt;
/// Create a copy of LearningGoal
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$LearningGoalCopyWith<LearningGoal> get copyWith => _$LearningGoalCopyWithImpl<LearningGoal>(this as LearningGoal, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is LearningGoal&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.baseHourly, baseHourly) || other.baseHourly == baseHourly)&&(identical(other.targetHourly, targetHourly) || other.targetHourly == targetHourly)&&(identical(other.status, status) || other.status == status)&&(identical(other.why, why) || other.why == why)&&(identical(other.memberId, memberId) || other.memberId == memberId)&&(identical(other.closedAt, closedAt) || other.closedAt == closedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,baseHourly,targetHourly,status,why,memberId,closedAt);

@override
String toString() {
  return 'LearningGoal(meta: $meta, title: $title, baseHourly: $baseHourly, targetHourly: $targetHourly, status: $status, why: $why, memberId: $memberId, closedAt: $closedAt)';
}


}

/// @nodoc
abstract mixin class $LearningGoalCopyWith<$Res>  {
  factory $LearningGoalCopyWith(LearningGoal value, $Res Function(LearningGoal) _then) = _$LearningGoalCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, Money baseHourly, Money targetHourly, LearningGoalStatus status, String? why, String? memberId, DateTime? closedAt
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$LearningGoalCopyWithImpl<$Res>
    implements $LearningGoalCopyWith<$Res> {
  _$LearningGoalCopyWithImpl(this._self, this._then);

  final LearningGoal _self;
  final $Res Function(LearningGoal) _then;

/// Create a copy of LearningGoal
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? baseHourly = null,Object? targetHourly = null,Object? status = null,Object? why = freezed,Object? memberId = freezed,Object? closedAt = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,baseHourly: null == baseHourly ? _self.baseHourly : baseHourly // ignore: cast_nullable_to_non_nullable
as Money,targetHourly: null == targetHourly ? _self.targetHourly : targetHourly // ignore: cast_nullable_to_non_nullable
as Money,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as LearningGoalStatus,why: freezed == why ? _self.why : why // ignore: cast_nullable_to_non_nullable
as String?,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,closedAt: freezed == closedAt ? _self.closedAt : closedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}
/// Create a copy of LearningGoal
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [LearningGoal].
extension LearningGoalPatterns on LearningGoal {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _LearningGoal value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _LearningGoal() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _LearningGoal value)  $default,){
final _that = this;
switch (_that) {
case _LearningGoal():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _LearningGoal value)?  $default,){
final _that = this;
switch (_that) {
case _LearningGoal() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money baseHourly,  Money targetHourly,  LearningGoalStatus status,  String? why,  String? memberId,  DateTime? closedAt)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _LearningGoal() when $default != null:
return $default(_that.meta,_that.title,_that.baseHourly,_that.targetHourly,_that.status,_that.why,_that.memberId,_that.closedAt);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money baseHourly,  Money targetHourly,  LearningGoalStatus status,  String? why,  String? memberId,  DateTime? closedAt)  $default,) {final _that = this;
switch (_that) {
case _LearningGoal():
return $default(_that.meta,_that.title,_that.baseHourly,_that.targetHourly,_that.status,_that.why,_that.memberId,_that.closedAt);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  Money baseHourly,  Money targetHourly,  LearningGoalStatus status,  String? why,  String? memberId,  DateTime? closedAt)?  $default,) {final _that = this;
switch (_that) {
case _LearningGoal() when $default != null:
return $default(_that.meta,_that.title,_that.baseHourly,_that.targetHourly,_that.status,_that.why,_that.memberId,_that.closedAt);case _:
  return null;

}
}

}

/// @nodoc


class _LearningGoal implements LearningGoal {
  const _LearningGoal({required this.meta, required this.title, required this.baseHourly, required this.targetHourly, required this.status, this.why, this.memberId, this.closedAt});
  

@override final  SyncMeta meta;
@override final  String title;
@override final  Money baseHourly;
@override final  Money targetHourly;
@override final  LearningGoalStatus status;
@override final  String? why;
@override final  String? memberId;
/// `DONE` yoki `DROPPED` bo'lgan vaqt (UTC).
@override final  DateTime? closedAt;

/// Create a copy of LearningGoal
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$LearningGoalCopyWith<_LearningGoal> get copyWith => __$LearningGoalCopyWithImpl<_LearningGoal>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _LearningGoal&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.baseHourly, baseHourly) || other.baseHourly == baseHourly)&&(identical(other.targetHourly, targetHourly) || other.targetHourly == targetHourly)&&(identical(other.status, status) || other.status == status)&&(identical(other.why, why) || other.why == why)&&(identical(other.memberId, memberId) || other.memberId == memberId)&&(identical(other.closedAt, closedAt) || other.closedAt == closedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,baseHourly,targetHourly,status,why,memberId,closedAt);

@override
String toString() {
  return 'LearningGoal(meta: $meta, title: $title, baseHourly: $baseHourly, targetHourly: $targetHourly, status: $status, why: $why, memberId: $memberId, closedAt: $closedAt)';
}


}

/// @nodoc
abstract mixin class _$LearningGoalCopyWith<$Res> implements $LearningGoalCopyWith<$Res> {
  factory _$LearningGoalCopyWith(_LearningGoal value, $Res Function(_LearningGoal) _then) = __$LearningGoalCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, Money baseHourly, Money targetHourly, LearningGoalStatus status, String? why, String? memberId, DateTime? closedAt
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$LearningGoalCopyWithImpl<$Res>
    implements _$LearningGoalCopyWith<$Res> {
  __$LearningGoalCopyWithImpl(this._self, this._then);

  final _LearningGoal _self;
  final $Res Function(_LearningGoal) _then;

/// Create a copy of LearningGoal
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? baseHourly = null,Object? targetHourly = null,Object? status = null,Object? why = freezed,Object? memberId = freezed,Object? closedAt = freezed,}) {
  return _then(_LearningGoal(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,baseHourly: null == baseHourly ? _self.baseHourly : baseHourly // ignore: cast_nullable_to_non_nullable
as Money,targetHourly: null == targetHourly ? _self.targetHourly : targetHourly // ignore: cast_nullable_to_non_nullable
as Money,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as LearningGoalStatus,why: freezed == why ? _self.why : why // ignore: cast_nullable_to_non_nullable
as String?,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,closedAt: freezed == closedAt ? _self.closedAt : closedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}

/// Create a copy of LearningGoal
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
mixin _$LearningItem {

 SyncMeta get meta; String get goalId; LearningItemKind get kind; String get title;/// «Buni o'rgangach nimani qila olaman?»
 String get purpose; LearningItemStatus get status; Money? get cost; int? get studyMinutes; String? get outcome;/// Kurs tekshiruvi (SPEC 2H.5): javoblar JSON va baho.
 String? get courseAnswersJson; OfferVerdict? get courseVerdict;/// `DONE` bo'lgan vaqt (UTC).
 DateTime? get completedAt;
/// Create a copy of LearningItem
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$LearningItemCopyWith<LearningItem> get copyWith => _$LearningItemCopyWithImpl<LearningItem>(this as LearningItem, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is LearningItem&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.goalId, goalId) || other.goalId == goalId)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.title, title) || other.title == title)&&(identical(other.purpose, purpose) || other.purpose == purpose)&&(identical(other.status, status) || other.status == status)&&(identical(other.cost, cost) || other.cost == cost)&&(identical(other.studyMinutes, studyMinutes) || other.studyMinutes == studyMinutes)&&(identical(other.outcome, outcome) || other.outcome == outcome)&&(identical(other.courseAnswersJson, courseAnswersJson) || other.courseAnswersJson == courseAnswersJson)&&(identical(other.courseVerdict, courseVerdict) || other.courseVerdict == courseVerdict)&&(identical(other.completedAt, completedAt) || other.completedAt == completedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,goalId,kind,title,purpose,status,cost,studyMinutes,outcome,courseAnswersJson,courseVerdict,completedAt);

@override
String toString() {
  return 'LearningItem(meta: $meta, goalId: $goalId, kind: $kind, title: $title, purpose: $purpose, status: $status, cost: $cost, studyMinutes: $studyMinutes, outcome: $outcome, courseAnswersJson: $courseAnswersJson, courseVerdict: $courseVerdict, completedAt: $completedAt)';
}


}

/// @nodoc
abstract mixin class $LearningItemCopyWith<$Res>  {
  factory $LearningItemCopyWith(LearningItem value, $Res Function(LearningItem) _then) = _$LearningItemCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String goalId, LearningItemKind kind, String title, String purpose, LearningItemStatus status, Money? cost, int? studyMinutes, String? outcome, String? courseAnswersJson, OfferVerdict? courseVerdict, DateTime? completedAt
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$LearningItemCopyWithImpl<$Res>
    implements $LearningItemCopyWith<$Res> {
  _$LearningItemCopyWithImpl(this._self, this._then);

  final LearningItem _self;
  final $Res Function(LearningItem) _then;

/// Create a copy of LearningItem
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? goalId = null,Object? kind = null,Object? title = null,Object? purpose = null,Object? status = null,Object? cost = freezed,Object? studyMinutes = freezed,Object? outcome = freezed,Object? courseAnswersJson = freezed,Object? courseVerdict = freezed,Object? completedAt = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,goalId: null == goalId ? _self.goalId : goalId // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as LearningItemKind,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,purpose: null == purpose ? _self.purpose : purpose // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as LearningItemStatus,cost: freezed == cost ? _self.cost : cost // ignore: cast_nullable_to_non_nullable
as Money?,studyMinutes: freezed == studyMinutes ? _self.studyMinutes : studyMinutes // ignore: cast_nullable_to_non_nullable
as int?,outcome: freezed == outcome ? _self.outcome : outcome // ignore: cast_nullable_to_non_nullable
as String?,courseAnswersJson: freezed == courseAnswersJson ? _self.courseAnswersJson : courseAnswersJson // ignore: cast_nullable_to_non_nullable
as String?,courseVerdict: freezed == courseVerdict ? _self.courseVerdict : courseVerdict // ignore: cast_nullable_to_non_nullable
as OfferVerdict?,completedAt: freezed == completedAt ? _self.completedAt : completedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}
/// Create a copy of LearningItem
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [LearningItem].
extension LearningItemPatterns on LearningItem {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _LearningItem value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _LearningItem() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _LearningItem value)  $default,){
final _that = this;
switch (_that) {
case _LearningItem():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _LearningItem value)?  $default,){
final _that = this;
switch (_that) {
case _LearningItem() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String goalId,  LearningItemKind kind,  String title,  String purpose,  LearningItemStatus status,  Money? cost,  int? studyMinutes,  String? outcome,  String? courseAnswersJson,  OfferVerdict? courseVerdict,  DateTime? completedAt)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _LearningItem() when $default != null:
return $default(_that.meta,_that.goalId,_that.kind,_that.title,_that.purpose,_that.status,_that.cost,_that.studyMinutes,_that.outcome,_that.courseAnswersJson,_that.courseVerdict,_that.completedAt);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String goalId,  LearningItemKind kind,  String title,  String purpose,  LearningItemStatus status,  Money? cost,  int? studyMinutes,  String? outcome,  String? courseAnswersJson,  OfferVerdict? courseVerdict,  DateTime? completedAt)  $default,) {final _that = this;
switch (_that) {
case _LearningItem():
return $default(_that.meta,_that.goalId,_that.kind,_that.title,_that.purpose,_that.status,_that.cost,_that.studyMinutes,_that.outcome,_that.courseAnswersJson,_that.courseVerdict,_that.completedAt);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String goalId,  LearningItemKind kind,  String title,  String purpose,  LearningItemStatus status,  Money? cost,  int? studyMinutes,  String? outcome,  String? courseAnswersJson,  OfferVerdict? courseVerdict,  DateTime? completedAt)?  $default,) {final _that = this;
switch (_that) {
case _LearningItem() when $default != null:
return $default(_that.meta,_that.goalId,_that.kind,_that.title,_that.purpose,_that.status,_that.cost,_that.studyMinutes,_that.outcome,_that.courseAnswersJson,_that.courseVerdict,_that.completedAt);case _:
  return null;

}
}

}

/// @nodoc


class _LearningItem extends LearningItem {
  const _LearningItem({required this.meta, required this.goalId, required this.kind, required this.title, required this.purpose, required this.status, this.cost, this.studyMinutes, this.outcome, this.courseAnswersJson, this.courseVerdict, this.completedAt}): super._();
  

@override final  SyncMeta meta;
@override final  String goalId;
@override final  LearningItemKind kind;
@override final  String title;
/// «Buni o'rgangach nimani qila olaman?»
@override final  String purpose;
@override final  LearningItemStatus status;
@override final  Money? cost;
@override final  int? studyMinutes;
@override final  String? outcome;
/// Kurs tekshiruvi (SPEC 2H.5): javoblar JSON va baho.
@override final  String? courseAnswersJson;
@override final  OfferVerdict? courseVerdict;
/// `DONE` bo'lgan vaqt (UTC).
@override final  DateTime? completedAt;

/// Create a copy of LearningItem
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$LearningItemCopyWith<_LearningItem> get copyWith => __$LearningItemCopyWithImpl<_LearningItem>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _LearningItem&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.goalId, goalId) || other.goalId == goalId)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.title, title) || other.title == title)&&(identical(other.purpose, purpose) || other.purpose == purpose)&&(identical(other.status, status) || other.status == status)&&(identical(other.cost, cost) || other.cost == cost)&&(identical(other.studyMinutes, studyMinutes) || other.studyMinutes == studyMinutes)&&(identical(other.outcome, outcome) || other.outcome == outcome)&&(identical(other.courseAnswersJson, courseAnswersJson) || other.courseAnswersJson == courseAnswersJson)&&(identical(other.courseVerdict, courseVerdict) || other.courseVerdict == courseVerdict)&&(identical(other.completedAt, completedAt) || other.completedAt == completedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,goalId,kind,title,purpose,status,cost,studyMinutes,outcome,courseAnswersJson,courseVerdict,completedAt);

@override
String toString() {
  return 'LearningItem(meta: $meta, goalId: $goalId, kind: $kind, title: $title, purpose: $purpose, status: $status, cost: $cost, studyMinutes: $studyMinutes, outcome: $outcome, courseAnswersJson: $courseAnswersJson, courseVerdict: $courseVerdict, completedAt: $completedAt)';
}


}

/// @nodoc
abstract mixin class _$LearningItemCopyWith<$Res> implements $LearningItemCopyWith<$Res> {
  factory _$LearningItemCopyWith(_LearningItem value, $Res Function(_LearningItem) _then) = __$LearningItemCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String goalId, LearningItemKind kind, String title, String purpose, LearningItemStatus status, Money? cost, int? studyMinutes, String? outcome, String? courseAnswersJson, OfferVerdict? courseVerdict, DateTime? completedAt
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$LearningItemCopyWithImpl<$Res>
    implements _$LearningItemCopyWith<$Res> {
  __$LearningItemCopyWithImpl(this._self, this._then);

  final _LearningItem _self;
  final $Res Function(_LearningItem) _then;

/// Create a copy of LearningItem
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? goalId = null,Object? kind = null,Object? title = null,Object? purpose = null,Object? status = null,Object? cost = freezed,Object? studyMinutes = freezed,Object? outcome = freezed,Object? courseAnswersJson = freezed,Object? courseVerdict = freezed,Object? completedAt = freezed,}) {
  return _then(_LearningItem(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,goalId: null == goalId ? _self.goalId : goalId // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as LearningItemKind,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,purpose: null == purpose ? _self.purpose : purpose // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as LearningItemStatus,cost: freezed == cost ? _self.cost : cost // ignore: cast_nullable_to_non_nullable
as Money?,studyMinutes: freezed == studyMinutes ? _self.studyMinutes : studyMinutes // ignore: cast_nullable_to_non_nullable
as int?,outcome: freezed == outcome ? _self.outcome : outcome // ignore: cast_nullable_to_non_nullable
as String?,courseAnswersJson: freezed == courseAnswersJson ? _self.courseAnswersJson : courseAnswersJson // ignore: cast_nullable_to_non_nullable
as String?,courseVerdict: freezed == courseVerdict ? _self.courseVerdict : courseVerdict // ignore: cast_nullable_to_non_nullable
as OfferVerdict?,completedAt: freezed == completedAt ? _self.completedAt : completedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}

/// Create a copy of LearningItem
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
mixin _$TeachingEntry {

 SyncMeta get meta; String get learner; String get topic; LocalDate get taughtOn; int? get minutes; String? get note; String? get memberId;
/// Create a copy of TeachingEntry
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$TeachingEntryCopyWith<TeachingEntry> get copyWith => _$TeachingEntryCopyWithImpl<TeachingEntry>(this as TeachingEntry, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is TeachingEntry&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.learner, learner) || other.learner == learner)&&(identical(other.topic, topic) || other.topic == topic)&&(identical(other.taughtOn, taughtOn) || other.taughtOn == taughtOn)&&(identical(other.minutes, minutes) || other.minutes == minutes)&&(identical(other.note, note) || other.note == note)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,learner,topic,taughtOn,minutes,note,memberId);

@override
String toString() {
  return 'TeachingEntry(meta: $meta, learner: $learner, topic: $topic, taughtOn: $taughtOn, minutes: $minutes, note: $note, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class $TeachingEntryCopyWith<$Res>  {
  factory $TeachingEntryCopyWith(TeachingEntry value, $Res Function(TeachingEntry) _then) = _$TeachingEntryCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String learner, String topic, LocalDate taughtOn, int? minutes, String? note, String? memberId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$TeachingEntryCopyWithImpl<$Res>
    implements $TeachingEntryCopyWith<$Res> {
  _$TeachingEntryCopyWithImpl(this._self, this._then);

  final TeachingEntry _self;
  final $Res Function(TeachingEntry) _then;

/// Create a copy of TeachingEntry
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? learner = null,Object? topic = null,Object? taughtOn = null,Object? minutes = freezed,Object? note = freezed,Object? memberId = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,learner: null == learner ? _self.learner : learner // ignore: cast_nullable_to_non_nullable
as String,topic: null == topic ? _self.topic : topic // ignore: cast_nullable_to_non_nullable
as String,taughtOn: null == taughtOn ? _self.taughtOn : taughtOn // ignore: cast_nullable_to_non_nullable
as LocalDate,minutes: freezed == minutes ? _self.minutes : minutes // ignore: cast_nullable_to_non_nullable
as int?,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of TeachingEntry
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [TeachingEntry].
extension TeachingEntryPatterns on TeachingEntry {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _TeachingEntry value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _TeachingEntry() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _TeachingEntry value)  $default,){
final _that = this;
switch (_that) {
case _TeachingEntry():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _TeachingEntry value)?  $default,){
final _that = this;
switch (_that) {
case _TeachingEntry() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String learner,  String topic,  LocalDate taughtOn,  int? minutes,  String? note,  String? memberId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _TeachingEntry() when $default != null:
return $default(_that.meta,_that.learner,_that.topic,_that.taughtOn,_that.minutes,_that.note,_that.memberId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String learner,  String topic,  LocalDate taughtOn,  int? minutes,  String? note,  String? memberId)  $default,) {final _that = this;
switch (_that) {
case _TeachingEntry():
return $default(_that.meta,_that.learner,_that.topic,_that.taughtOn,_that.minutes,_that.note,_that.memberId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String learner,  String topic,  LocalDate taughtOn,  int? minutes,  String? note,  String? memberId)?  $default,) {final _that = this;
switch (_that) {
case _TeachingEntry() when $default != null:
return $default(_that.meta,_that.learner,_that.topic,_that.taughtOn,_that.minutes,_that.note,_that.memberId);case _:
  return null;

}
}

}

/// @nodoc


class _TeachingEntry implements TeachingEntry {
  const _TeachingEntry({required this.meta, required this.learner, required this.topic, required this.taughtOn, this.minutes, this.note, this.memberId});
  

@override final  SyncMeta meta;
@override final  String learner;
@override final  String topic;
@override final  LocalDate taughtOn;
@override final  int? minutes;
@override final  String? note;
@override final  String? memberId;

/// Create a copy of TeachingEntry
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$TeachingEntryCopyWith<_TeachingEntry> get copyWith => __$TeachingEntryCopyWithImpl<_TeachingEntry>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _TeachingEntry&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.learner, learner) || other.learner == learner)&&(identical(other.topic, topic) || other.topic == topic)&&(identical(other.taughtOn, taughtOn) || other.taughtOn == taughtOn)&&(identical(other.minutes, minutes) || other.minutes == minutes)&&(identical(other.note, note) || other.note == note)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,learner,topic,taughtOn,minutes,note,memberId);

@override
String toString() {
  return 'TeachingEntry(meta: $meta, learner: $learner, topic: $topic, taughtOn: $taughtOn, minutes: $minutes, note: $note, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class _$TeachingEntryCopyWith<$Res> implements $TeachingEntryCopyWith<$Res> {
  factory _$TeachingEntryCopyWith(_TeachingEntry value, $Res Function(_TeachingEntry) _then) = __$TeachingEntryCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String learner, String topic, LocalDate taughtOn, int? minutes, String? note, String? memberId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$TeachingEntryCopyWithImpl<$Res>
    implements _$TeachingEntryCopyWith<$Res> {
  __$TeachingEntryCopyWithImpl(this._self, this._then);

  final _TeachingEntry _self;
  final $Res Function(_TeachingEntry) _then;

/// Create a copy of TeachingEntry
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? learner = null,Object? topic = null,Object? taughtOn = null,Object? minutes = freezed,Object? note = freezed,Object? memberId = freezed,}) {
  return _then(_TeachingEntry(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,learner: null == learner ? _self.learner : learner // ignore: cast_nullable_to_non_nullable
as String,topic: null == topic ? _self.topic : topic // ignore: cast_nullable_to_non_nullable
as String,taughtOn: null == taughtOn ? _self.taughtOn : taughtOn // ignore: cast_nullable_to_non_nullable
as LocalDate,minutes: freezed == minutes ? _self.minutes : minutes // ignore: cast_nullable_to_non_nullable
as int?,note: freezed == note ? _self.note : note // ignore: cast_nullable_to_non_nullable
as String?,memberId: freezed == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of TeachingEntry
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
