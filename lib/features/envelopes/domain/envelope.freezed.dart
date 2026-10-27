// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'envelope.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$Envelope {

 SyncMeta get meta; String get title; Money get weeklyLimit; bool get isCash;/// Shu kategoriyalardagi xarajat (naqd ham, karta ham) konvertdan.
 List<String> get categoryIds; bool get isArchived;
/// Create a copy of Envelope
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$EnvelopeCopyWith<Envelope> get copyWith => _$EnvelopeCopyWithImpl<Envelope>(this as Envelope, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Envelope&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.weeklyLimit, weeklyLimit) || other.weeklyLimit == weeklyLimit)&&(identical(other.isCash, isCash) || other.isCash == isCash)&&const DeepCollectionEquality().equals(other.categoryIds, categoryIds)&&(identical(other.isArchived, isArchived) || other.isArchived == isArchived));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,weeklyLimit,isCash,const DeepCollectionEquality().hash(categoryIds),isArchived);

@override
String toString() {
  return 'Envelope(meta: $meta, title: $title, weeklyLimit: $weeklyLimit, isCash: $isCash, categoryIds: $categoryIds, isArchived: $isArchived)';
}


}

/// @nodoc
abstract mixin class $EnvelopeCopyWith<$Res>  {
  factory $EnvelopeCopyWith(Envelope value, $Res Function(Envelope) _then) = _$EnvelopeCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, Money weeklyLimit, bool isCash, List<String> categoryIds, bool isArchived
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$EnvelopeCopyWithImpl<$Res>
    implements $EnvelopeCopyWith<$Res> {
  _$EnvelopeCopyWithImpl(this._self, this._then);

  final Envelope _self;
  final $Res Function(Envelope) _then;

/// Create a copy of Envelope
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? weeklyLimit = null,Object? isCash = null,Object? categoryIds = null,Object? isArchived = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,weeklyLimit: null == weeklyLimit ? _self.weeklyLimit : weeklyLimit // ignore: cast_nullable_to_non_nullable
as Money,isCash: null == isCash ? _self.isCash : isCash // ignore: cast_nullable_to_non_nullable
as bool,categoryIds: null == categoryIds ? _self.categoryIds : categoryIds // ignore: cast_nullable_to_non_nullable
as List<String>,isArchived: null == isArchived ? _self.isArchived : isArchived // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}
/// Create a copy of Envelope
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Envelope].
extension EnvelopePatterns on Envelope {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Envelope value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Envelope() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Envelope value)  $default,){
final _that = this;
switch (_that) {
case _Envelope():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Envelope value)?  $default,){
final _that = this;
switch (_that) {
case _Envelope() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money weeklyLimit,  bool isCash,  List<String> categoryIds,  bool isArchived)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Envelope() when $default != null:
return $default(_that.meta,_that.title,_that.weeklyLimit,_that.isCash,_that.categoryIds,_that.isArchived);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  Money weeklyLimit,  bool isCash,  List<String> categoryIds,  bool isArchived)  $default,) {final _that = this;
switch (_that) {
case _Envelope():
return $default(_that.meta,_that.title,_that.weeklyLimit,_that.isCash,_that.categoryIds,_that.isArchived);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  Money weeklyLimit,  bool isCash,  List<String> categoryIds,  bool isArchived)?  $default,) {final _that = this;
switch (_that) {
case _Envelope() when $default != null:
return $default(_that.meta,_that.title,_that.weeklyLimit,_that.isCash,_that.categoryIds,_that.isArchived);case _:
  return null;

}
}

}

/// @nodoc


class _Envelope implements Envelope {
  const _Envelope({required this.meta, required this.title, required this.weeklyLimit, this.isCash = true, final  List<String> categoryIds = const <String>[], this.isArchived = false}): _categoryIds = categoryIds;
  

@override final  SyncMeta meta;
@override final  String title;
@override final  Money weeklyLimit;
@override@JsonKey() final  bool isCash;
/// Shu kategoriyalardagi xarajat (naqd ham, karta ham) konvertdan.
 final  List<String> _categoryIds;
/// Shu kategoriyalardagi xarajat (naqd ham, karta ham) konvertdan.
@override@JsonKey() List<String> get categoryIds {
  if (_categoryIds is EqualUnmodifiableListView) return _categoryIds;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_categoryIds);
}

@override@JsonKey() final  bool isArchived;

/// Create a copy of Envelope
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$EnvelopeCopyWith<_Envelope> get copyWith => __$EnvelopeCopyWithImpl<_Envelope>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Envelope&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.weeklyLimit, weeklyLimit) || other.weeklyLimit == weeklyLimit)&&(identical(other.isCash, isCash) || other.isCash == isCash)&&const DeepCollectionEquality().equals(other._categoryIds, _categoryIds)&&(identical(other.isArchived, isArchived) || other.isArchived == isArchived));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,weeklyLimit,isCash,const DeepCollectionEquality().hash(_categoryIds),isArchived);

@override
String toString() {
  return 'Envelope(meta: $meta, title: $title, weeklyLimit: $weeklyLimit, isCash: $isCash, categoryIds: $categoryIds, isArchived: $isArchived)';
}


}

/// @nodoc
abstract mixin class _$EnvelopeCopyWith<$Res> implements $EnvelopeCopyWith<$Res> {
  factory _$EnvelopeCopyWith(_Envelope value, $Res Function(_Envelope) _then) = __$EnvelopeCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, Money weeklyLimit, bool isCash, List<String> categoryIds, bool isArchived
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$EnvelopeCopyWithImpl<$Res>
    implements _$EnvelopeCopyWith<$Res> {
  __$EnvelopeCopyWithImpl(this._self, this._then);

  final _Envelope _self;
  final $Res Function(_Envelope) _then;

/// Create a copy of Envelope
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? weeklyLimit = null,Object? isCash = null,Object? categoryIds = null,Object? isArchived = null,}) {
  return _then(_Envelope(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,weeklyLimit: null == weeklyLimit ? _self.weeklyLimit : weeklyLimit // ignore: cast_nullable_to_non_nullable
as Money,isCash: null == isCash ? _self.isCash : isCash // ignore: cast_nullable_to_non_nullable
as bool,categoryIds: null == categoryIds ? _self._categoryIds : categoryIds // ignore: cast_nullable_to_non_nullable
as List<String>,isArchived: null == isArchived ? _self.isArchived : isArchived // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

/// Create a copy of Envelope
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
mixin _$EnvelopePeriod {

 SyncMeta get meta; String get envelopeId; LocalDate get weekStart;/// Hafta boshidagi limit surati (keyin limit o'zgarsa ham shu).
 Money get limit;/// Yopilganda qolgan pul.
 Money? get leftover;/// UTC; `null` — hali yopilmagan.
 DateTime? get closedAt;
/// Create a copy of EnvelopePeriod
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$EnvelopePeriodCopyWith<EnvelopePeriod> get copyWith => _$EnvelopePeriodCopyWithImpl<EnvelopePeriod>(this as EnvelopePeriod, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is EnvelopePeriod&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.envelopeId, envelopeId) || other.envelopeId == envelopeId)&&(identical(other.weekStart, weekStart) || other.weekStart == weekStart)&&(identical(other.limit, limit) || other.limit == limit)&&(identical(other.leftover, leftover) || other.leftover == leftover)&&(identical(other.closedAt, closedAt) || other.closedAt == closedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,envelopeId,weekStart,limit,leftover,closedAt);

@override
String toString() {
  return 'EnvelopePeriod(meta: $meta, envelopeId: $envelopeId, weekStart: $weekStart, limit: $limit, leftover: $leftover, closedAt: $closedAt)';
}


}

/// @nodoc
abstract mixin class $EnvelopePeriodCopyWith<$Res>  {
  factory $EnvelopePeriodCopyWith(EnvelopePeriod value, $Res Function(EnvelopePeriod) _then) = _$EnvelopePeriodCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String envelopeId, LocalDate weekStart, Money limit, Money? leftover, DateTime? closedAt
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$EnvelopePeriodCopyWithImpl<$Res>
    implements $EnvelopePeriodCopyWith<$Res> {
  _$EnvelopePeriodCopyWithImpl(this._self, this._then);

  final EnvelopePeriod _self;
  final $Res Function(EnvelopePeriod) _then;

/// Create a copy of EnvelopePeriod
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? envelopeId = null,Object? weekStart = null,Object? limit = null,Object? leftover = freezed,Object? closedAt = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,envelopeId: null == envelopeId ? _self.envelopeId : envelopeId // ignore: cast_nullable_to_non_nullable
as String,weekStart: null == weekStart ? _self.weekStart : weekStart // ignore: cast_nullable_to_non_nullable
as LocalDate,limit: null == limit ? _self.limit : limit // ignore: cast_nullable_to_non_nullable
as Money,leftover: freezed == leftover ? _self.leftover : leftover // ignore: cast_nullable_to_non_nullable
as Money?,closedAt: freezed == closedAt ? _self.closedAt : closedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}
/// Create a copy of EnvelopePeriod
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [EnvelopePeriod].
extension EnvelopePeriodPatterns on EnvelopePeriod {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _EnvelopePeriod value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _EnvelopePeriod() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _EnvelopePeriod value)  $default,){
final _that = this;
switch (_that) {
case _EnvelopePeriod():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _EnvelopePeriod value)?  $default,){
final _that = this;
switch (_that) {
case _EnvelopePeriod() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String envelopeId,  LocalDate weekStart,  Money limit,  Money? leftover,  DateTime? closedAt)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _EnvelopePeriod() when $default != null:
return $default(_that.meta,_that.envelopeId,_that.weekStart,_that.limit,_that.leftover,_that.closedAt);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String envelopeId,  LocalDate weekStart,  Money limit,  Money? leftover,  DateTime? closedAt)  $default,) {final _that = this;
switch (_that) {
case _EnvelopePeriod():
return $default(_that.meta,_that.envelopeId,_that.weekStart,_that.limit,_that.leftover,_that.closedAt);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String envelopeId,  LocalDate weekStart,  Money limit,  Money? leftover,  DateTime? closedAt)?  $default,) {final _that = this;
switch (_that) {
case _EnvelopePeriod() when $default != null:
return $default(_that.meta,_that.envelopeId,_that.weekStart,_that.limit,_that.leftover,_that.closedAt);case _:
  return null;

}
}

}

/// @nodoc


class _EnvelopePeriod extends EnvelopePeriod {
  const _EnvelopePeriod({required this.meta, required this.envelopeId, required this.weekStart, required this.limit, this.leftover, this.closedAt}): super._();
  

@override final  SyncMeta meta;
@override final  String envelopeId;
@override final  LocalDate weekStart;
/// Hafta boshidagi limit surati (keyin limit o'zgarsa ham shu).
@override final  Money limit;
/// Yopilganda qolgan pul.
@override final  Money? leftover;
/// UTC; `null` — hali yopilmagan.
@override final  DateTime? closedAt;

/// Create a copy of EnvelopePeriod
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$EnvelopePeriodCopyWith<_EnvelopePeriod> get copyWith => __$EnvelopePeriodCopyWithImpl<_EnvelopePeriod>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _EnvelopePeriod&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.envelopeId, envelopeId) || other.envelopeId == envelopeId)&&(identical(other.weekStart, weekStart) || other.weekStart == weekStart)&&(identical(other.limit, limit) || other.limit == limit)&&(identical(other.leftover, leftover) || other.leftover == leftover)&&(identical(other.closedAt, closedAt) || other.closedAt == closedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,envelopeId,weekStart,limit,leftover,closedAt);

@override
String toString() {
  return 'EnvelopePeriod(meta: $meta, envelopeId: $envelopeId, weekStart: $weekStart, limit: $limit, leftover: $leftover, closedAt: $closedAt)';
}


}

/// @nodoc
abstract mixin class _$EnvelopePeriodCopyWith<$Res> implements $EnvelopePeriodCopyWith<$Res> {
  factory _$EnvelopePeriodCopyWith(_EnvelopePeriod value, $Res Function(_EnvelopePeriod) _then) = __$EnvelopePeriodCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String envelopeId, LocalDate weekStart, Money limit, Money? leftover, DateTime? closedAt
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$EnvelopePeriodCopyWithImpl<$Res>
    implements _$EnvelopePeriodCopyWith<$Res> {
  __$EnvelopePeriodCopyWithImpl(this._self, this._then);

  final _EnvelopePeriod _self;
  final $Res Function(_EnvelopePeriod) _then;

/// Create a copy of EnvelopePeriod
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? envelopeId = null,Object? weekStart = null,Object? limit = null,Object? leftover = freezed,Object? closedAt = freezed,}) {
  return _then(_EnvelopePeriod(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,envelopeId: null == envelopeId ? _self.envelopeId : envelopeId // ignore: cast_nullable_to_non_nullable
as String,weekStart: null == weekStart ? _self.weekStart : weekStart // ignore: cast_nullable_to_non_nullable
as LocalDate,limit: null == limit ? _self.limit : limit // ignore: cast_nullable_to_non_nullable
as Money,leftover: freezed == leftover ? _self.leftover : leftover // ignore: cast_nullable_to_non_nullable
as Money?,closedAt: freezed == closedAt ? _self.closedAt : closedAt // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}

/// Create a copy of EnvelopePeriod
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
