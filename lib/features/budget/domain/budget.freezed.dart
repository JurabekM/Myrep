// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'budget.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$HavasLimit {

 SyncMeta get meta; Money get amount; String? get proposedBy;
/// Create a copy of HavasLimit
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$HavasLimitCopyWith<HavasLimit> get copyWith => _$HavasLimitCopyWithImpl<HavasLimit>(this as HavasLimit, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is HavasLimit&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.proposedBy, proposedBy) || other.proposedBy == proposedBy));
}


@override
int get hashCode => Object.hash(runtimeType,meta,amount,proposedBy);

@override
String toString() {
  return 'HavasLimit(meta: $meta, amount: $amount, proposedBy: $proposedBy)';
}


}

/// @nodoc
abstract mixin class $HavasLimitCopyWith<$Res>  {
  factory $HavasLimitCopyWith(HavasLimit value, $Res Function(HavasLimit) _then) = _$HavasLimitCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, Money amount, String? proposedBy
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$HavasLimitCopyWithImpl<$Res>
    implements $HavasLimitCopyWith<$Res> {
  _$HavasLimitCopyWithImpl(this._self, this._then);

  final HavasLimit _self;
  final $Res Function(HavasLimit) _then;

/// Create a copy of HavasLimit
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? amount = null,Object? proposedBy = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,proposedBy: freezed == proposedBy ? _self.proposedBy : proposedBy // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of HavasLimit
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [HavasLimit].
extension HavasLimitPatterns on HavasLimit {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _HavasLimit value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _HavasLimit() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _HavasLimit value)  $default,){
final _that = this;
switch (_that) {
case _HavasLimit():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _HavasLimit value)?  $default,){
final _that = this;
switch (_that) {
case _HavasLimit() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  Money amount,  String? proposedBy)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _HavasLimit() when $default != null:
return $default(_that.meta,_that.amount,_that.proposedBy);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  Money amount,  String? proposedBy)  $default,) {final _that = this;
switch (_that) {
case _HavasLimit():
return $default(_that.meta,_that.amount,_that.proposedBy);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  Money amount,  String? proposedBy)?  $default,) {final _that = this;
switch (_that) {
case _HavasLimit() when $default != null:
return $default(_that.meta,_that.amount,_that.proposedBy);case _:
  return null;

}
}

}

/// @nodoc


class _HavasLimit implements HavasLimit {
  const _HavasLimit({required this.meta, required this.amount, this.proposedBy});
  

@override final  SyncMeta meta;
@override final  Money amount;
@override final  String? proposedBy;

/// Create a copy of HavasLimit
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$HavasLimitCopyWith<_HavasLimit> get copyWith => __$HavasLimitCopyWithImpl<_HavasLimit>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _HavasLimit&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.proposedBy, proposedBy) || other.proposedBy == proposedBy));
}


@override
int get hashCode => Object.hash(runtimeType,meta,amount,proposedBy);

@override
String toString() {
  return 'HavasLimit(meta: $meta, amount: $amount, proposedBy: $proposedBy)';
}


}

/// @nodoc
abstract mixin class _$HavasLimitCopyWith<$Res> implements $HavasLimitCopyWith<$Res> {
  factory _$HavasLimitCopyWith(_HavasLimit value, $Res Function(_HavasLimit) _then) = __$HavasLimitCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, Money amount, String? proposedBy
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$HavasLimitCopyWithImpl<$Res>
    implements _$HavasLimitCopyWith<$Res> {
  __$HavasLimitCopyWithImpl(this._self, this._then);

  final _HavasLimit _self;
  final $Res Function(_HavasLimit) _then;

/// Create a copy of HavasLimit
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? amount = null,Object? proposedBy = freezed,}) {
  return _then(_HavasLimit(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,proposedBy: freezed == proposedBy ? _self.proposedBy : proposedBy // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of HavasLimit
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
mixin _$LimitConsent {

 SyncMeta get meta; String get limitId; String get memberId;
/// Create a copy of LimitConsent
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$LimitConsentCopyWith<LimitConsent> get copyWith => _$LimitConsentCopyWithImpl<LimitConsent>(this as LimitConsent, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is LimitConsent&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.limitId, limitId) || other.limitId == limitId)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,limitId,memberId);

@override
String toString() {
  return 'LimitConsent(meta: $meta, limitId: $limitId, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class $LimitConsentCopyWith<$Res>  {
  factory $LimitConsentCopyWith(LimitConsent value, $Res Function(LimitConsent) _then) = _$LimitConsentCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String limitId, String memberId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$LimitConsentCopyWithImpl<$Res>
    implements $LimitConsentCopyWith<$Res> {
  _$LimitConsentCopyWithImpl(this._self, this._then);

  final LimitConsent _self;
  final $Res Function(LimitConsent) _then;

/// Create a copy of LimitConsent
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? limitId = null,Object? memberId = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,limitId: null == limitId ? _self.limitId : limitId // ignore: cast_nullable_to_non_nullable
as String,memberId: null == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String,
  ));
}
/// Create a copy of LimitConsent
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [LimitConsent].
extension LimitConsentPatterns on LimitConsent {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _LimitConsent value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _LimitConsent() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _LimitConsent value)  $default,){
final _that = this;
switch (_that) {
case _LimitConsent():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _LimitConsent value)?  $default,){
final _that = this;
switch (_that) {
case _LimitConsent() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String limitId,  String memberId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _LimitConsent() when $default != null:
return $default(_that.meta,_that.limitId,_that.memberId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String limitId,  String memberId)  $default,) {final _that = this;
switch (_that) {
case _LimitConsent():
return $default(_that.meta,_that.limitId,_that.memberId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String limitId,  String memberId)?  $default,) {final _that = this;
switch (_that) {
case _LimitConsent() when $default != null:
return $default(_that.meta,_that.limitId,_that.memberId);case _:
  return null;

}
}

}

/// @nodoc


class _LimitConsent implements LimitConsent {
  const _LimitConsent({required this.meta, required this.limitId, required this.memberId});
  

@override final  SyncMeta meta;
@override final  String limitId;
@override final  String memberId;

/// Create a copy of LimitConsent
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$LimitConsentCopyWith<_LimitConsent> get copyWith => __$LimitConsentCopyWithImpl<_LimitConsent>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _LimitConsent&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.limitId, limitId) || other.limitId == limitId)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,limitId,memberId);

@override
String toString() {
  return 'LimitConsent(meta: $meta, limitId: $limitId, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class _$LimitConsentCopyWith<$Res> implements $LimitConsentCopyWith<$Res> {
  factory _$LimitConsentCopyWith(_LimitConsent value, $Res Function(_LimitConsent) _then) = __$LimitConsentCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String limitId, String memberId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$LimitConsentCopyWithImpl<$Res>
    implements _$LimitConsentCopyWith<$Res> {
  __$LimitConsentCopyWithImpl(this._self, this._then);

  final _LimitConsent _self;
  final $Res Function(_LimitConsent) _then;

/// Create a copy of LimitConsent
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? limitId = null,Object? memberId = null,}) {
  return _then(_LimitConsent(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,limitId: null == limitId ? _self.limitId : limitId // ignore: cast_nullable_to_non_nullable
as String,memberId: null == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

/// Create a copy of LimitConsent
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
mixin _$ScheduledTreat {

 SyncMeta get meta; String get title; Money get amount;/// `DateTime.monday` … `DateTime.sunday`.
 int get weekday; bool get isActive;
/// Create a copy of ScheduledTreat
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$ScheduledTreatCopyWith<ScheduledTreat> get copyWith => _$ScheduledTreatCopyWithImpl<ScheduledTreat>(this as ScheduledTreat, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is ScheduledTreat&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.weekday, weekday) || other.weekday == weekday)&&(identical(other.isActive, isActive) || other.isActive == isActive));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,amount,weekday,isActive);

@override
String toString() {
  return 'ScheduledTreat(meta: $meta, title: $title, amount: $amount, weekday: $weekday, isActive: $isActive)';
}


}

/// @nodoc
abstract mixin class $ScheduledTreatCopyWith<$Res>  {
  factory $ScheduledTreatCopyWith(ScheduledTreat value, $Res Function(ScheduledTreat) _then) = _$ScheduledTreatCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, Money amount, int weekday, bool isActive
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$ScheduledTreatCopyWithImpl<$Res>
    implements $ScheduledTreatCopyWith<$Res> {
  _$ScheduledTreatCopyWithImpl(this._self, this._then);

  final ScheduledTreat _self;
  final $Res Function(ScheduledTreat) _then;

/// Create a copy of ScheduledTreat
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? amount = null,Object? weekday = null,Object? isActive = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,weekday: null == weekday ? _self.weekday : weekday // ignore: cast_nullable_to_non_nullable
as int,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}
/// Create a copy of ScheduledTreat
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [ScheduledTreat].
extension ScheduledTreatPatterns on ScheduledTreat {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _ScheduledTreat value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _ScheduledTreat() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _ScheduledTreat value)  $default,){
final _that = this;
switch (_that) {
case _ScheduledTreat():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _ScheduledTreat value)?  $default,){
final _that = this;
switch (_that) {
case _ScheduledTreat() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money amount,  int weekday,  bool isActive)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _ScheduledTreat() when $default != null:
return $default(_that.meta,_that.title,_that.amount,_that.weekday,_that.isActive);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money amount,  int weekday,  bool isActive)  $default,) {final _that = this;
switch (_that) {
case _ScheduledTreat():
return $default(_that.meta,_that.title,_that.amount,_that.weekday,_that.isActive);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  Money amount,  int weekday,  bool isActive)?  $default,) {final _that = this;
switch (_that) {
case _ScheduledTreat() when $default != null:
return $default(_that.meta,_that.title,_that.amount,_that.weekday,_that.isActive);case _:
  return null;

}
}

}

/// @nodoc


class _ScheduledTreat implements ScheduledTreat {
  const _ScheduledTreat({required this.meta, required this.title, required this.amount, this.weekday = DateTime.friday, this.isActive = true});
  

@override final  SyncMeta meta;
@override final  String title;
@override final  Money amount;
/// `DateTime.monday` … `DateTime.sunday`.
@override@JsonKey() final  int weekday;
@override@JsonKey() final  bool isActive;

/// Create a copy of ScheduledTreat
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$ScheduledTreatCopyWith<_ScheduledTreat> get copyWith => __$ScheduledTreatCopyWithImpl<_ScheduledTreat>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _ScheduledTreat&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.weekday, weekday) || other.weekday == weekday)&&(identical(other.isActive, isActive) || other.isActive == isActive));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,amount,weekday,isActive);

@override
String toString() {
  return 'ScheduledTreat(meta: $meta, title: $title, amount: $amount, weekday: $weekday, isActive: $isActive)';
}


}

/// @nodoc
abstract mixin class _$ScheduledTreatCopyWith<$Res> implements $ScheduledTreatCopyWith<$Res> {
  factory _$ScheduledTreatCopyWith(_ScheduledTreat value, $Res Function(_ScheduledTreat) _then) = __$ScheduledTreatCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, Money amount, int weekday, bool isActive
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$ScheduledTreatCopyWithImpl<$Res>
    implements _$ScheduledTreatCopyWith<$Res> {
  __$ScheduledTreatCopyWithImpl(this._self, this._then);

  final _ScheduledTreat _self;
  final $Res Function(_ScheduledTreat) _then;

/// Create a copy of ScheduledTreat
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? amount = null,Object? weekday = null,Object? isActive = null,}) {
  return _then(_ScheduledTreat(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,weekday: null == weekday ? _self.weekday : weekday // ignore: cast_nullable_to_non_nullable
as int,isActive: null == isActive ? _self.isActive : isActive // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

/// Create a copy of ScheduledTreat
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
mixin _$Habit {

 SyncMeta get meta; String get title; bool get isArchived;
/// Create a copy of Habit
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$HabitCopyWith<Habit> get copyWith => _$HabitCopyWithImpl<Habit>(this as Habit, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Habit&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.isArchived, isArchived) || other.isArchived == isArchived));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,isArchived);

@override
String toString() {
  return 'Habit(meta: $meta, title: $title, isArchived: $isArchived)';
}


}

/// @nodoc
abstract mixin class $HabitCopyWith<$Res>  {
  factory $HabitCopyWith(Habit value, $Res Function(Habit) _then) = _$HabitCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, bool isArchived
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$HabitCopyWithImpl<$Res>
    implements $HabitCopyWith<$Res> {
  _$HabitCopyWithImpl(this._self, this._then);

  final Habit _self;
  final $Res Function(Habit) _then;

/// Create a copy of Habit
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? isArchived = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,isArchived: null == isArchived ? _self.isArchived : isArchived // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}
/// Create a copy of Habit
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Habit].
extension HabitPatterns on Habit {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Habit value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Habit() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Habit value)  $default,){
final _that = this;
switch (_that) {
case _Habit():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Habit value)?  $default,){
final _that = this;
switch (_that) {
case _Habit() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  bool isArchived)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Habit() when $default != null:
return $default(_that.meta,_that.title,_that.isArchived);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  bool isArchived)  $default,) {final _that = this;
switch (_that) {
case _Habit():
return $default(_that.meta,_that.title,_that.isArchived);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  bool isArchived)?  $default,) {final _that = this;
switch (_that) {
case _Habit() when $default != null:
return $default(_that.meta,_that.title,_that.isArchived);case _:
  return null;

}
}

}

/// @nodoc


class _Habit implements Habit {
  const _Habit({required this.meta, required this.title, this.isArchived = false});
  

@override final  SyncMeta meta;
@override final  String title;
@override@JsonKey() final  bool isArchived;

/// Create a copy of Habit
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$HabitCopyWith<_Habit> get copyWith => __$HabitCopyWithImpl<_Habit>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Habit&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.isArchived, isArchived) || other.isArchived == isArchived));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,isArchived);

@override
String toString() {
  return 'Habit(meta: $meta, title: $title, isArchived: $isArchived)';
}


}

/// @nodoc
abstract mixin class _$HabitCopyWith<$Res> implements $HabitCopyWith<$Res> {
  factory _$HabitCopyWith(_Habit value, $Res Function(_Habit) _then) = __$HabitCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, bool isArchived
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$HabitCopyWithImpl<$Res>
    implements _$HabitCopyWith<$Res> {
  __$HabitCopyWithImpl(this._self, this._then);

  final _Habit _self;
  final $Res Function(_Habit) _then;

/// Create a copy of Habit
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? isArchived = null,}) {
  return _then(_Habit(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,isArchived: null == isArchived ? _self.isArchived : isArchived // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

/// Create a copy of Habit
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
