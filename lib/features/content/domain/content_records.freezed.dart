// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'content_records.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$DaftarPage {

 SyncMeta get meta; String get chapterId; int get lawNumber; String get body;
/// Create a copy of DaftarPage
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DaftarPageCopyWith<DaftarPage> get copyWith => _$DaftarPageCopyWithImpl<DaftarPage>(this as DaftarPage, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DaftarPage&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.chapterId, chapterId) || other.chapterId == chapterId)&&(identical(other.lawNumber, lawNumber) || other.lawNumber == lawNumber)&&(identical(other.body, body) || other.body == body));
}


@override
int get hashCode => Object.hash(runtimeType,meta,chapterId,lawNumber,body);

@override
String toString() {
  return 'DaftarPage(meta: $meta, chapterId: $chapterId, lawNumber: $lawNumber, body: $body)';
}


}

/// @nodoc
abstract mixin class $DaftarPageCopyWith<$Res>  {
  factory $DaftarPageCopyWith(DaftarPage value, $Res Function(DaftarPage) _then) = _$DaftarPageCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String chapterId, int lawNumber, String body
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$DaftarPageCopyWithImpl<$Res>
    implements $DaftarPageCopyWith<$Res> {
  _$DaftarPageCopyWithImpl(this._self, this._then);

  final DaftarPage _self;
  final $Res Function(DaftarPage) _then;

/// Create a copy of DaftarPage
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? chapterId = null,Object? lawNumber = null,Object? body = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,chapterId: null == chapterId ? _self.chapterId : chapterId // ignore: cast_nullable_to_non_nullable
as String,lawNumber: null == lawNumber ? _self.lawNumber : lawNumber // ignore: cast_nullable_to_non_nullable
as int,body: null == body ? _self.body : body // ignore: cast_nullable_to_non_nullable
as String,
  ));
}
/// Create a copy of DaftarPage
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [DaftarPage].
extension DaftarPagePatterns on DaftarPage {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DaftarPage value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DaftarPage() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DaftarPage value)  $default,){
final _that = this;
switch (_that) {
case _DaftarPage():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DaftarPage value)?  $default,){
final _that = this;
switch (_that) {
case _DaftarPage() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String chapterId,  int lawNumber,  String body)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DaftarPage() when $default != null:
return $default(_that.meta,_that.chapterId,_that.lawNumber,_that.body);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String chapterId,  int lawNumber,  String body)  $default,) {final _that = this;
switch (_that) {
case _DaftarPage():
return $default(_that.meta,_that.chapterId,_that.lawNumber,_that.body);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String chapterId,  int lawNumber,  String body)?  $default,) {final _that = this;
switch (_that) {
case _DaftarPage() when $default != null:
return $default(_that.meta,_that.chapterId,_that.lawNumber,_that.body);case _:
  return null;

}
}

}

/// @nodoc


class _DaftarPage implements DaftarPage {
  const _DaftarPage({required this.meta, required this.chapterId, required this.lawNumber, required this.body});
  

@override final  SyncMeta meta;
@override final  String chapterId;
@override final  int lawNumber;
@override final  String body;

/// Create a copy of DaftarPage
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DaftarPageCopyWith<_DaftarPage> get copyWith => __$DaftarPageCopyWithImpl<_DaftarPage>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DaftarPage&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.chapterId, chapterId) || other.chapterId == chapterId)&&(identical(other.lawNumber, lawNumber) || other.lawNumber == lawNumber)&&(identical(other.body, body) || other.body == body));
}


@override
int get hashCode => Object.hash(runtimeType,meta,chapterId,lawNumber,body);

@override
String toString() {
  return 'DaftarPage(meta: $meta, chapterId: $chapterId, lawNumber: $lawNumber, body: $body)';
}


}

/// @nodoc
abstract mixin class _$DaftarPageCopyWith<$Res> implements $DaftarPageCopyWith<$Res> {
  factory _$DaftarPageCopyWith(_DaftarPage value, $Res Function(_DaftarPage) _then) = __$DaftarPageCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String chapterId, int lawNumber, String body
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$DaftarPageCopyWithImpl<$Res>
    implements _$DaftarPageCopyWith<$Res> {
  __$DaftarPageCopyWithImpl(this._self, this._then);

  final _DaftarPage _self;
  final $Res Function(_DaftarPage) _then;

/// Create a copy of DaftarPage
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? chapterId = null,Object? lawNumber = null,Object? body = null,}) {
  return _then(_DaftarPage(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,chapterId: null == chapterId ? _self.chapterId : chapterId // ignore: cast_nullable_to_non_nullable
as String,lawNumber: null == lawNumber ? _self.lawNumber : lawNumber // ignore: cast_nullable_to_non_nullable
as int,body: null == body ? _self.body : body // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

/// Create a copy of DaftarPage
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
mixin _$TaskCompletion {

 SyncMeta get meta; String get taskId; LocalDate get weekStart; bool get isAuto;
/// Create a copy of TaskCompletion
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$TaskCompletionCopyWith<TaskCompletion> get copyWith => _$TaskCompletionCopyWithImpl<TaskCompletion>(this as TaskCompletion, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is TaskCompletion&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.taskId, taskId) || other.taskId == taskId)&&(identical(other.weekStart, weekStart) || other.weekStart == weekStart)&&(identical(other.isAuto, isAuto) || other.isAuto == isAuto));
}


@override
int get hashCode => Object.hash(runtimeType,meta,taskId,weekStart,isAuto);

@override
String toString() {
  return 'TaskCompletion(meta: $meta, taskId: $taskId, weekStart: $weekStart, isAuto: $isAuto)';
}


}

/// @nodoc
abstract mixin class $TaskCompletionCopyWith<$Res>  {
  factory $TaskCompletionCopyWith(TaskCompletion value, $Res Function(TaskCompletion) _then) = _$TaskCompletionCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String taskId, LocalDate weekStart, bool isAuto
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$TaskCompletionCopyWithImpl<$Res>
    implements $TaskCompletionCopyWith<$Res> {
  _$TaskCompletionCopyWithImpl(this._self, this._then);

  final TaskCompletion _self;
  final $Res Function(TaskCompletion) _then;

/// Create a copy of TaskCompletion
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? taskId = null,Object? weekStart = null,Object? isAuto = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,taskId: null == taskId ? _self.taskId : taskId // ignore: cast_nullable_to_non_nullable
as String,weekStart: null == weekStart ? _self.weekStart : weekStart // ignore: cast_nullable_to_non_nullable
as LocalDate,isAuto: null == isAuto ? _self.isAuto : isAuto // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}
/// Create a copy of TaskCompletion
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [TaskCompletion].
extension TaskCompletionPatterns on TaskCompletion {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _TaskCompletion value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _TaskCompletion() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _TaskCompletion value)  $default,){
final _that = this;
switch (_that) {
case _TaskCompletion():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _TaskCompletion value)?  $default,){
final _that = this;
switch (_that) {
case _TaskCompletion() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String taskId,  LocalDate weekStart,  bool isAuto)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _TaskCompletion() when $default != null:
return $default(_that.meta,_that.taskId,_that.weekStart,_that.isAuto);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String taskId,  LocalDate weekStart,  bool isAuto)  $default,) {final _that = this;
switch (_that) {
case _TaskCompletion():
return $default(_that.meta,_that.taskId,_that.weekStart,_that.isAuto);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String taskId,  LocalDate weekStart,  bool isAuto)?  $default,) {final _that = this;
switch (_that) {
case _TaskCompletion() when $default != null:
return $default(_that.meta,_that.taskId,_that.weekStart,_that.isAuto);case _:
  return null;

}
}

}

/// @nodoc


class _TaskCompletion implements TaskCompletion {
  const _TaskCompletion({required this.meta, required this.taskId, required this.weekStart, this.isAuto = false});
  

@override final  SyncMeta meta;
@override final  String taskId;
@override final  LocalDate weekStart;
@override@JsonKey() final  bool isAuto;

/// Create a copy of TaskCompletion
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$TaskCompletionCopyWith<_TaskCompletion> get copyWith => __$TaskCompletionCopyWithImpl<_TaskCompletion>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _TaskCompletion&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.taskId, taskId) || other.taskId == taskId)&&(identical(other.weekStart, weekStart) || other.weekStart == weekStart)&&(identical(other.isAuto, isAuto) || other.isAuto == isAuto));
}


@override
int get hashCode => Object.hash(runtimeType,meta,taskId,weekStart,isAuto);

@override
String toString() {
  return 'TaskCompletion(meta: $meta, taskId: $taskId, weekStart: $weekStart, isAuto: $isAuto)';
}


}

/// @nodoc
abstract mixin class _$TaskCompletionCopyWith<$Res> implements $TaskCompletionCopyWith<$Res> {
  factory _$TaskCompletionCopyWith(_TaskCompletion value, $Res Function(_TaskCompletion) _then) = __$TaskCompletionCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String taskId, LocalDate weekStart, bool isAuto
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$TaskCompletionCopyWithImpl<$Res>
    implements _$TaskCompletionCopyWith<$Res> {
  __$TaskCompletionCopyWithImpl(this._self, this._then);

  final _TaskCompletion _self;
  final $Res Function(_TaskCompletion) _then;

/// Create a copy of TaskCompletion
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? taskId = null,Object? weekStart = null,Object? isAuto = null,}) {
  return _then(_TaskCompletion(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,taskId: null == taskId ? _self.taskId : taskId // ignore: cast_nullable_to_non_nullable
as String,weekStart: null == weekStart ? _self.weekStart : weekStart // ignore: cast_nullable_to_non_nullable
as LocalDate,isAuto: null == isAuto ? _self.isAuto : isAuto // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

/// Create a copy of TaskCompletion
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
