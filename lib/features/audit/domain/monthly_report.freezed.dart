// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'monthly_report.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$MonthlyReport {

 SyncMeta get meta; LocalDate get periodStart; LocalDate get periodEnd; Money get income; Money get obligations; Money get expenses; Money get savings; Money get unexplained;/// UTC.
 DateTime get completedAt;
/// Create a copy of MonthlyReport
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MonthlyReportCopyWith<MonthlyReport> get copyWith => _$MonthlyReportCopyWithImpl<MonthlyReport>(this as MonthlyReport, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is MonthlyReport&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.periodStart, periodStart) || other.periodStart == periodStart)&&(identical(other.periodEnd, periodEnd) || other.periodEnd == periodEnd)&&(identical(other.income, income) || other.income == income)&&(identical(other.obligations, obligations) || other.obligations == obligations)&&(identical(other.expenses, expenses) || other.expenses == expenses)&&(identical(other.savings, savings) || other.savings == savings)&&(identical(other.unexplained, unexplained) || other.unexplained == unexplained)&&(identical(other.completedAt, completedAt) || other.completedAt == completedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,periodStart,periodEnd,income,obligations,expenses,savings,unexplained,completedAt);

@override
String toString() {
  return 'MonthlyReport(meta: $meta, periodStart: $periodStart, periodEnd: $periodEnd, income: $income, obligations: $obligations, expenses: $expenses, savings: $savings, unexplained: $unexplained, completedAt: $completedAt)';
}


}

/// @nodoc
abstract mixin class $MonthlyReportCopyWith<$Res>  {
  factory $MonthlyReportCopyWith(MonthlyReport value, $Res Function(MonthlyReport) _then) = _$MonthlyReportCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, LocalDate periodStart, LocalDate periodEnd, Money income, Money obligations, Money expenses, Money savings, Money unexplained, DateTime completedAt
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$MonthlyReportCopyWithImpl<$Res>
    implements $MonthlyReportCopyWith<$Res> {
  _$MonthlyReportCopyWithImpl(this._self, this._then);

  final MonthlyReport _self;
  final $Res Function(MonthlyReport) _then;

/// Create a copy of MonthlyReport
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? periodStart = null,Object? periodEnd = null,Object? income = null,Object? obligations = null,Object? expenses = null,Object? savings = null,Object? unexplained = null,Object? completedAt = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,periodStart: null == periodStart ? _self.periodStart : periodStart // ignore: cast_nullable_to_non_nullable
as LocalDate,periodEnd: null == periodEnd ? _self.periodEnd : periodEnd // ignore: cast_nullable_to_non_nullable
as LocalDate,income: null == income ? _self.income : income // ignore: cast_nullable_to_non_nullable
as Money,obligations: null == obligations ? _self.obligations : obligations // ignore: cast_nullable_to_non_nullable
as Money,expenses: null == expenses ? _self.expenses : expenses // ignore: cast_nullable_to_non_nullable
as Money,savings: null == savings ? _self.savings : savings // ignore: cast_nullable_to_non_nullable
as Money,unexplained: null == unexplained ? _self.unexplained : unexplained // ignore: cast_nullable_to_non_nullable
as Money,completedAt: null == completedAt ? _self.completedAt : completedAt // ignore: cast_nullable_to_non_nullable
as DateTime,
  ));
}
/// Create a copy of MonthlyReport
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [MonthlyReport].
extension MonthlyReportPatterns on MonthlyReport {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _MonthlyReport value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _MonthlyReport() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _MonthlyReport value)  $default,){
final _that = this;
switch (_that) {
case _MonthlyReport():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _MonthlyReport value)?  $default,){
final _that = this;
switch (_that) {
case _MonthlyReport() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  LocalDate periodStart,  LocalDate periodEnd,  Money income,  Money obligations,  Money expenses,  Money savings,  Money unexplained,  DateTime completedAt)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _MonthlyReport() when $default != null:
return $default(_that.meta,_that.periodStart,_that.periodEnd,_that.income,_that.obligations,_that.expenses,_that.savings,_that.unexplained,_that.completedAt);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  LocalDate periodStart,  LocalDate periodEnd,  Money income,  Money obligations,  Money expenses,  Money savings,  Money unexplained,  DateTime completedAt)  $default,) {final _that = this;
switch (_that) {
case _MonthlyReport():
return $default(_that.meta,_that.periodStart,_that.periodEnd,_that.income,_that.obligations,_that.expenses,_that.savings,_that.unexplained,_that.completedAt);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  LocalDate periodStart,  LocalDate periodEnd,  Money income,  Money obligations,  Money expenses,  Money savings,  Money unexplained,  DateTime completedAt)?  $default,) {final _that = this;
switch (_that) {
case _MonthlyReport() when $default != null:
return $default(_that.meta,_that.periodStart,_that.periodEnd,_that.income,_that.obligations,_that.expenses,_that.savings,_that.unexplained,_that.completedAt);case _:
  return null;

}
}

}

/// @nodoc


class _MonthlyReport implements MonthlyReport {
  const _MonthlyReport({required this.meta, required this.periodStart, required this.periodEnd, required this.income, required this.obligations, required this.expenses, required this.savings, required this.unexplained, required this.completedAt});
  

@override final  SyncMeta meta;
@override final  LocalDate periodStart;
@override final  LocalDate periodEnd;
@override final  Money income;
@override final  Money obligations;
@override final  Money expenses;
@override final  Money savings;
@override final  Money unexplained;
/// UTC.
@override final  DateTime completedAt;

/// Create a copy of MonthlyReport
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$MonthlyReportCopyWith<_MonthlyReport> get copyWith => __$MonthlyReportCopyWithImpl<_MonthlyReport>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _MonthlyReport&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.periodStart, periodStart) || other.periodStart == periodStart)&&(identical(other.periodEnd, periodEnd) || other.periodEnd == periodEnd)&&(identical(other.income, income) || other.income == income)&&(identical(other.obligations, obligations) || other.obligations == obligations)&&(identical(other.expenses, expenses) || other.expenses == expenses)&&(identical(other.savings, savings) || other.savings == savings)&&(identical(other.unexplained, unexplained) || other.unexplained == unexplained)&&(identical(other.completedAt, completedAt) || other.completedAt == completedAt));
}


@override
int get hashCode => Object.hash(runtimeType,meta,periodStart,periodEnd,income,obligations,expenses,savings,unexplained,completedAt);

@override
String toString() {
  return 'MonthlyReport(meta: $meta, periodStart: $periodStart, periodEnd: $periodEnd, income: $income, obligations: $obligations, expenses: $expenses, savings: $savings, unexplained: $unexplained, completedAt: $completedAt)';
}


}

/// @nodoc
abstract mixin class _$MonthlyReportCopyWith<$Res> implements $MonthlyReportCopyWith<$Res> {
  factory _$MonthlyReportCopyWith(_MonthlyReport value, $Res Function(_MonthlyReport) _then) = __$MonthlyReportCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, LocalDate periodStart, LocalDate periodEnd, Money income, Money obligations, Money expenses, Money savings, Money unexplained, DateTime completedAt
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$MonthlyReportCopyWithImpl<$Res>
    implements _$MonthlyReportCopyWith<$Res> {
  __$MonthlyReportCopyWithImpl(this._self, this._then);

  final _MonthlyReport _self;
  final $Res Function(_MonthlyReport) _then;

/// Create a copy of MonthlyReport
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? periodStart = null,Object? periodEnd = null,Object? income = null,Object? obligations = null,Object? expenses = null,Object? savings = null,Object? unexplained = null,Object? completedAt = null,}) {
  return _then(_MonthlyReport(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,periodStart: null == periodStart ? _self.periodStart : periodStart // ignore: cast_nullable_to_non_nullable
as LocalDate,periodEnd: null == periodEnd ? _self.periodEnd : periodEnd // ignore: cast_nullable_to_non_nullable
as LocalDate,income: null == income ? _self.income : income // ignore: cast_nullable_to_non_nullable
as Money,obligations: null == obligations ? _self.obligations : obligations // ignore: cast_nullable_to_non_nullable
as Money,expenses: null == expenses ? _self.expenses : expenses // ignore: cast_nullable_to_non_nullable
as Money,savings: null == savings ? _self.savings : savings // ignore: cast_nullable_to_non_nullable
as Money,unexplained: null == unexplained ? _self.unexplained : unexplained // ignore: cast_nullable_to_non_nullable
as Money,completedAt: null == completedAt ? _self.completedAt : completedAt // ignore: cast_nullable_to_non_nullable
as DateTime,
  ));
}

/// Create a copy of MonthlyReport
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
