// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'partnership.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$Partnership {

 SyncMeta get meta; String get title; PartnershipType get type; CurrencyCode get currency; int get termMonths; ReportPeriod get reportPeriod; String get endTerms; String get disputeTerms; PartnershipStatus get status; LocalDate? get startDate; int get contractVersion;/// Kapital qabul qiluvchi: «bu qarz emas» tushuntirishi o'qildi.
 bool get notDebtAcknowledged;/// Kamayib boruvchi musharaka: oyiga ulush sotib olish to'lovi.
 Money? get buyoutMonthly;
/// Create a copy of Partnership
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$PartnershipCopyWith<Partnership> get copyWith => _$PartnershipCopyWithImpl<Partnership>(this as Partnership, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Partnership&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.type, type) || other.type == type)&&(identical(other.currency, currency) || other.currency == currency)&&(identical(other.termMonths, termMonths) || other.termMonths == termMonths)&&(identical(other.reportPeriod, reportPeriod) || other.reportPeriod == reportPeriod)&&(identical(other.endTerms, endTerms) || other.endTerms == endTerms)&&(identical(other.disputeTerms, disputeTerms) || other.disputeTerms == disputeTerms)&&(identical(other.status, status) || other.status == status)&&(identical(other.startDate, startDate) || other.startDate == startDate)&&(identical(other.contractVersion, contractVersion) || other.contractVersion == contractVersion)&&(identical(other.notDebtAcknowledged, notDebtAcknowledged) || other.notDebtAcknowledged == notDebtAcknowledged)&&(identical(other.buyoutMonthly, buyoutMonthly) || other.buyoutMonthly == buyoutMonthly));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,type,currency,termMonths,reportPeriod,endTerms,disputeTerms,status,startDate,contractVersion,notDebtAcknowledged,buyoutMonthly);

@override
String toString() {
  return 'Partnership(meta: $meta, title: $title, type: $type, currency: $currency, termMonths: $termMonths, reportPeriod: $reportPeriod, endTerms: $endTerms, disputeTerms: $disputeTerms, status: $status, startDate: $startDate, contractVersion: $contractVersion, notDebtAcknowledged: $notDebtAcknowledged, buyoutMonthly: $buyoutMonthly)';
}


}

/// @nodoc
abstract mixin class $PartnershipCopyWith<$Res>  {
  factory $PartnershipCopyWith(Partnership value, $Res Function(Partnership) _then) = _$PartnershipCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String title, PartnershipType type, CurrencyCode currency, int termMonths, ReportPeriod reportPeriod, String endTerms, String disputeTerms, PartnershipStatus status, LocalDate? startDate, int contractVersion, bool notDebtAcknowledged, Money? buyoutMonthly
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$PartnershipCopyWithImpl<$Res>
    implements $PartnershipCopyWith<$Res> {
  _$PartnershipCopyWithImpl(this._self, this._then);

  final Partnership _self;
  final $Res Function(Partnership) _then;

/// Create a copy of Partnership
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? title = null,Object? type = null,Object? currency = null,Object? termMonths = null,Object? reportPeriod = null,Object? endTerms = null,Object? disputeTerms = null,Object? status = null,Object? startDate = freezed,Object? contractVersion = null,Object? notDebtAcknowledged = null,Object? buyoutMonthly = freezed,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as PartnershipType,currency: null == currency ? _self.currency : currency // ignore: cast_nullable_to_non_nullable
as CurrencyCode,termMonths: null == termMonths ? _self.termMonths : termMonths // ignore: cast_nullable_to_non_nullable
as int,reportPeriod: null == reportPeriod ? _self.reportPeriod : reportPeriod // ignore: cast_nullable_to_non_nullable
as ReportPeriod,endTerms: null == endTerms ? _self.endTerms : endTerms // ignore: cast_nullable_to_non_nullable
as String,disputeTerms: null == disputeTerms ? _self.disputeTerms : disputeTerms // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as PartnershipStatus,startDate: freezed == startDate ? _self.startDate : startDate // ignore: cast_nullable_to_non_nullable
as LocalDate?,contractVersion: null == contractVersion ? _self.contractVersion : contractVersion // ignore: cast_nullable_to_non_nullable
as int,notDebtAcknowledged: null == notDebtAcknowledged ? _self.notDebtAcknowledged : notDebtAcknowledged // ignore: cast_nullable_to_non_nullable
as bool,buyoutMonthly: freezed == buyoutMonthly ? _self.buyoutMonthly : buyoutMonthly // ignore: cast_nullable_to_non_nullable
as Money?,
  ));
}
/// Create a copy of Partnership
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Partnership].
extension PartnershipPatterns on Partnership {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Partnership value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Partnership() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Partnership value)  $default,){
final _that = this;
switch (_that) {
case _Partnership():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Partnership value)?  $default,){
final _that = this;
switch (_that) {
case _Partnership() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  PartnershipType type,  CurrencyCode currency,  int termMonths,  ReportPeriod reportPeriod,  String endTerms,  String disputeTerms,  PartnershipStatus status,  LocalDate? startDate,  int contractVersion,  bool notDebtAcknowledged,  Money? buyoutMonthly)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Partnership() when $default != null:
return $default(_that.meta,_that.title,_that.type,_that.currency,_that.termMonths,_that.reportPeriod,_that.endTerms,_that.disputeTerms,_that.status,_that.startDate,_that.contractVersion,_that.notDebtAcknowledged,_that.buyoutMonthly);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String title,  PartnershipType type,  CurrencyCode currency,  int termMonths,  ReportPeriod reportPeriod,  String endTerms,  String disputeTerms,  PartnershipStatus status,  LocalDate? startDate,  int contractVersion,  bool notDebtAcknowledged,  Money? buyoutMonthly)  $default,) {final _that = this;
switch (_that) {
case _Partnership():
return $default(_that.meta,_that.title,_that.type,_that.currency,_that.termMonths,_that.reportPeriod,_that.endTerms,_that.disputeTerms,_that.status,_that.startDate,_that.contractVersion,_that.notDebtAcknowledged,_that.buyoutMonthly);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String title,  PartnershipType type,  CurrencyCode currency,  int termMonths,  ReportPeriod reportPeriod,  String endTerms,  String disputeTerms,  PartnershipStatus status,  LocalDate? startDate,  int contractVersion,  bool notDebtAcknowledged,  Money? buyoutMonthly)?  $default,) {final _that = this;
switch (_that) {
case _Partnership() when $default != null:
return $default(_that.meta,_that.title,_that.type,_that.currency,_that.termMonths,_that.reportPeriod,_that.endTerms,_that.disputeTerms,_that.status,_that.startDate,_that.contractVersion,_that.notDebtAcknowledged,_that.buyoutMonthly);case _:
  return null;

}
}

}

/// @nodoc


class _Partnership implements Partnership {
  const _Partnership({required this.meta, required this.title, required this.type, required this.currency, required this.termMonths, required this.reportPeriod, required this.endTerms, required this.disputeTerms, this.status = PartnershipStatus.draft, this.startDate, this.contractVersion = 1, this.notDebtAcknowledged = false, this.buyoutMonthly});
  

@override final  SyncMeta meta;
@override final  String title;
@override final  PartnershipType type;
@override final  CurrencyCode currency;
@override final  int termMonths;
@override final  ReportPeriod reportPeriod;
@override final  String endTerms;
@override final  String disputeTerms;
@override@JsonKey() final  PartnershipStatus status;
@override final  LocalDate? startDate;
@override@JsonKey() final  int contractVersion;
/// Kapital qabul qiluvchi: «bu qarz emas» tushuntirishi o'qildi.
@override@JsonKey() final  bool notDebtAcknowledged;
/// Kamayib boruvchi musharaka: oyiga ulush sotib olish to'lovi.
@override final  Money? buyoutMonthly;

/// Create a copy of Partnership
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$PartnershipCopyWith<_Partnership> get copyWith => __$PartnershipCopyWithImpl<_Partnership>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Partnership&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.title, title) || other.title == title)&&(identical(other.type, type) || other.type == type)&&(identical(other.currency, currency) || other.currency == currency)&&(identical(other.termMonths, termMonths) || other.termMonths == termMonths)&&(identical(other.reportPeriod, reportPeriod) || other.reportPeriod == reportPeriod)&&(identical(other.endTerms, endTerms) || other.endTerms == endTerms)&&(identical(other.disputeTerms, disputeTerms) || other.disputeTerms == disputeTerms)&&(identical(other.status, status) || other.status == status)&&(identical(other.startDate, startDate) || other.startDate == startDate)&&(identical(other.contractVersion, contractVersion) || other.contractVersion == contractVersion)&&(identical(other.notDebtAcknowledged, notDebtAcknowledged) || other.notDebtAcknowledged == notDebtAcknowledged)&&(identical(other.buyoutMonthly, buyoutMonthly) || other.buyoutMonthly == buyoutMonthly));
}


@override
int get hashCode => Object.hash(runtimeType,meta,title,type,currency,termMonths,reportPeriod,endTerms,disputeTerms,status,startDate,contractVersion,notDebtAcknowledged,buyoutMonthly);

@override
String toString() {
  return 'Partnership(meta: $meta, title: $title, type: $type, currency: $currency, termMonths: $termMonths, reportPeriod: $reportPeriod, endTerms: $endTerms, disputeTerms: $disputeTerms, status: $status, startDate: $startDate, contractVersion: $contractVersion, notDebtAcknowledged: $notDebtAcknowledged, buyoutMonthly: $buyoutMonthly)';
}


}

/// @nodoc
abstract mixin class _$PartnershipCopyWith<$Res> implements $PartnershipCopyWith<$Res> {
  factory _$PartnershipCopyWith(_Partnership value, $Res Function(_Partnership) _then) = __$PartnershipCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String title, PartnershipType type, CurrencyCode currency, int termMonths, ReportPeriod reportPeriod, String endTerms, String disputeTerms, PartnershipStatus status, LocalDate? startDate, int contractVersion, bool notDebtAcknowledged, Money? buyoutMonthly
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$PartnershipCopyWithImpl<$Res>
    implements _$PartnershipCopyWith<$Res> {
  __$PartnershipCopyWithImpl(this._self, this._then);

  final _Partnership _self;
  final $Res Function(_Partnership) _then;

/// Create a copy of Partnership
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? title = null,Object? type = null,Object? currency = null,Object? termMonths = null,Object? reportPeriod = null,Object? endTerms = null,Object? disputeTerms = null,Object? status = null,Object? startDate = freezed,Object? contractVersion = null,Object? notDebtAcknowledged = null,Object? buyoutMonthly = freezed,}) {
  return _then(_Partnership(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as PartnershipType,currency: null == currency ? _self.currency : currency // ignore: cast_nullable_to_non_nullable
as CurrencyCode,termMonths: null == termMonths ? _self.termMonths : termMonths // ignore: cast_nullable_to_non_nullable
as int,reportPeriod: null == reportPeriod ? _self.reportPeriod : reportPeriod // ignore: cast_nullable_to_non_nullable
as ReportPeriod,endTerms: null == endTerms ? _self.endTerms : endTerms // ignore: cast_nullable_to_non_nullable
as String,disputeTerms: null == disputeTerms ? _self.disputeTerms : disputeTerms // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as PartnershipStatus,startDate: freezed == startDate ? _self.startDate : startDate // ignore: cast_nullable_to_non_nullable
as LocalDate?,contractVersion: null == contractVersion ? _self.contractVersion : contractVersion // ignore: cast_nullable_to_non_nullable
as int,notDebtAcknowledged: null == notDebtAcknowledged ? _self.notDebtAcknowledged : notDebtAcknowledged // ignore: cast_nullable_to_non_nullable
as bool,buyoutMonthly: freezed == buyoutMonthly ? _self.buyoutMonthly : buyoutMonthly // ignore: cast_nullable_to_non_nullable
as Money?,
  ));
}

/// Create a copy of Partnership
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
mixin _$Partner {

 SyncMeta get meta; String get partnershipId; String get name; PartnerRole get role; int get profitShareBp; bool get isMe; int get sortOrder;
/// Create a copy of Partner
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$PartnerCopyWith<Partner> get copyWith => _$PartnerCopyWithImpl<Partner>(this as Partner, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Partner&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.name, name) || other.name == name)&&(identical(other.role, role) || other.role == role)&&(identical(other.profitShareBp, profitShareBp) || other.profitShareBp == profitShareBp)&&(identical(other.isMe, isMe) || other.isMe == isMe)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,name,role,profitShareBp,isMe,sortOrder);

@override
String toString() {
  return 'Partner(meta: $meta, partnershipId: $partnershipId, name: $name, role: $role, profitShareBp: $profitShareBp, isMe: $isMe, sortOrder: $sortOrder)';
}


}

/// @nodoc
abstract mixin class $PartnerCopyWith<$Res>  {
  factory $PartnerCopyWith(Partner value, $Res Function(Partner) _then) = _$PartnerCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String partnershipId, String name, PartnerRole role, int profitShareBp, bool isMe, int sortOrder
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$PartnerCopyWithImpl<$Res>
    implements $PartnerCopyWith<$Res> {
  _$PartnerCopyWithImpl(this._self, this._then);

  final Partner _self;
  final $Res Function(Partner) _then;

/// Create a copy of Partner
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? partnershipId = null,Object? name = null,Object? role = null,Object? profitShareBp = null,Object? isMe = null,Object? sortOrder = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,role: null == role ? _self.role : role // ignore: cast_nullable_to_non_nullable
as PartnerRole,profitShareBp: null == profitShareBp ? _self.profitShareBp : profitShareBp // ignore: cast_nullable_to_non_nullable
as int,isMe: null == isMe ? _self.isMe : isMe // ignore: cast_nullable_to_non_nullable
as bool,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,
  ));
}
/// Create a copy of Partner
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [Partner].
extension PartnerPatterns on Partner {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Partner value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Partner() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Partner value)  $default,){
final _that = this;
switch (_that) {
case _Partner():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Partner value)?  $default,){
final _that = this;
switch (_that) {
case _Partner() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  String name,  PartnerRole role,  int profitShareBp,  bool isMe,  int sortOrder)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Partner() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.name,_that.role,_that.profitShareBp,_that.isMe,_that.sortOrder);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  String name,  PartnerRole role,  int profitShareBp,  bool isMe,  int sortOrder)  $default,) {final _that = this;
switch (_that) {
case _Partner():
return $default(_that.meta,_that.partnershipId,_that.name,_that.role,_that.profitShareBp,_that.isMe,_that.sortOrder);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String partnershipId,  String name,  PartnerRole role,  int profitShareBp,  bool isMe,  int sortOrder)?  $default,) {final _that = this;
switch (_that) {
case _Partner() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.name,_that.role,_that.profitShareBp,_that.isMe,_that.sortOrder);case _:
  return null;

}
}

}

/// @nodoc


class _Partner extends Partner {
  const _Partner({required this.meta, required this.partnershipId, required this.name, required this.role, required this.profitShareBp, this.isMe = false, this.sortOrder = 0}): super._();
  

@override final  SyncMeta meta;
@override final  String partnershipId;
@override final  String name;
@override final  PartnerRole role;
@override final  int profitShareBp;
@override@JsonKey() final  bool isMe;
@override@JsonKey() final  int sortOrder;

/// Create a copy of Partner
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$PartnerCopyWith<_Partner> get copyWith => __$PartnerCopyWithImpl<_Partner>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Partner&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.name, name) || other.name == name)&&(identical(other.role, role) || other.role == role)&&(identical(other.profitShareBp, profitShareBp) || other.profitShareBp == profitShareBp)&&(identical(other.isMe, isMe) || other.isMe == isMe)&&(identical(other.sortOrder, sortOrder) || other.sortOrder == sortOrder));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,name,role,profitShareBp,isMe,sortOrder);

@override
String toString() {
  return 'Partner(meta: $meta, partnershipId: $partnershipId, name: $name, role: $role, profitShareBp: $profitShareBp, isMe: $isMe, sortOrder: $sortOrder)';
}


}

/// @nodoc
abstract mixin class _$PartnerCopyWith<$Res> implements $PartnerCopyWith<$Res> {
  factory _$PartnerCopyWith(_Partner value, $Res Function(_Partner) _then) = __$PartnerCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String partnershipId, String name, PartnerRole role, int profitShareBp, bool isMe, int sortOrder
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$PartnerCopyWithImpl<$Res>
    implements _$PartnerCopyWith<$Res> {
  __$PartnerCopyWithImpl(this._self, this._then);

  final _Partner _self;
  final $Res Function(_Partner) _then;

/// Create a copy of Partner
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? partnershipId = null,Object? name = null,Object? role = null,Object? profitShareBp = null,Object? isMe = null,Object? sortOrder = null,}) {
  return _then(_Partner(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,role: null == role ? _self.role : role // ignore: cast_nullable_to_non_nullable
as PartnerRole,profitShareBp: null == profitShareBp ? _self.profitShareBp : profitShareBp // ignore: cast_nullable_to_non_nullable
as int,isMe: null == isMe ? _self.isMe : isMe // ignore: cast_nullable_to_non_nullable
as bool,sortOrder: null == sortOrder ? _self.sortOrder : sortOrder // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

/// Create a copy of Partner
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
mixin _$CapitalContribution {

 SyncMeta get meta; String get partnershipId; String get partnerId; CapitalKind get kind; String get title; Money get amount;
/// Create a copy of CapitalContribution
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$CapitalContributionCopyWith<CapitalContribution> get copyWith => _$CapitalContributionCopyWithImpl<CapitalContribution>(this as CapitalContribution, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is CapitalContribution&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.partnerId, partnerId) || other.partnerId == partnerId)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.title, title) || other.title == title)&&(identical(other.amount, amount) || other.amount == amount));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,partnerId,kind,title,amount);

@override
String toString() {
  return 'CapitalContribution(meta: $meta, partnershipId: $partnershipId, partnerId: $partnerId, kind: $kind, title: $title, amount: $amount)';
}


}

/// @nodoc
abstract mixin class $CapitalContributionCopyWith<$Res>  {
  factory $CapitalContributionCopyWith(CapitalContribution value, $Res Function(CapitalContribution) _then) = _$CapitalContributionCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String partnershipId, String partnerId, CapitalKind kind, String title, Money amount
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$CapitalContributionCopyWithImpl<$Res>
    implements $CapitalContributionCopyWith<$Res> {
  _$CapitalContributionCopyWithImpl(this._self, this._then);

  final CapitalContribution _self;
  final $Res Function(CapitalContribution) _then;

/// Create a copy of CapitalContribution
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? partnershipId = null,Object? partnerId = null,Object? kind = null,Object? title = null,Object? amount = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,partnerId: null == partnerId ? _self.partnerId : partnerId // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as CapitalKind,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,
  ));
}
/// Create a copy of CapitalContribution
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [CapitalContribution].
extension CapitalContributionPatterns on CapitalContribution {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _CapitalContribution value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _CapitalContribution() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _CapitalContribution value)  $default,){
final _that = this;
switch (_that) {
case _CapitalContribution():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _CapitalContribution value)?  $default,){
final _that = this;
switch (_that) {
case _CapitalContribution() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  String partnerId,  CapitalKind kind,  String title,  Money amount)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _CapitalContribution() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.partnerId,_that.kind,_that.title,_that.amount);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  String partnerId,  CapitalKind kind,  String title,  Money amount)  $default,) {final _that = this;
switch (_that) {
case _CapitalContribution():
return $default(_that.meta,_that.partnershipId,_that.partnerId,_that.kind,_that.title,_that.amount);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String partnershipId,  String partnerId,  CapitalKind kind,  String title,  Money amount)?  $default,) {final _that = this;
switch (_that) {
case _CapitalContribution() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.partnerId,_that.kind,_that.title,_that.amount);case _:
  return null;

}
}

}

/// @nodoc


class _CapitalContribution implements CapitalContribution {
  const _CapitalContribution({required this.meta, required this.partnershipId, required this.partnerId, required this.kind, required this.title, required this.amount});
  

@override final  SyncMeta meta;
@override final  String partnershipId;
@override final  String partnerId;
@override final  CapitalKind kind;
@override final  String title;
@override final  Money amount;

/// Create a copy of CapitalContribution
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$CapitalContributionCopyWith<_CapitalContribution> get copyWith => __$CapitalContributionCopyWithImpl<_CapitalContribution>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _CapitalContribution&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.partnerId, partnerId) || other.partnerId == partnerId)&&(identical(other.kind, kind) || other.kind == kind)&&(identical(other.title, title) || other.title == title)&&(identical(other.amount, amount) || other.amount == amount));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,partnerId,kind,title,amount);

@override
String toString() {
  return 'CapitalContribution(meta: $meta, partnershipId: $partnershipId, partnerId: $partnerId, kind: $kind, title: $title, amount: $amount)';
}


}

/// @nodoc
abstract mixin class _$CapitalContributionCopyWith<$Res> implements $CapitalContributionCopyWith<$Res> {
  factory _$CapitalContributionCopyWith(_CapitalContribution value, $Res Function(_CapitalContribution) _then) = __$CapitalContributionCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String partnershipId, String partnerId, CapitalKind kind, String title, Money amount
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$CapitalContributionCopyWithImpl<$Res>
    implements _$CapitalContributionCopyWith<$Res> {
  __$CapitalContributionCopyWithImpl(this._self, this._then);

  final _CapitalContribution _self;
  final $Res Function(_CapitalContribution) _then;

/// Create a copy of CapitalContribution
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? partnershipId = null,Object? partnerId = null,Object? kind = null,Object? title = null,Object? amount = null,}) {
  return _then(_CapitalContribution(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,partnerId: null == partnerId ? _self.partnerId : partnerId // ignore: cast_nullable_to_non_nullable
as String,kind: null == kind ? _self.kind : kind // ignore: cast_nullable_to_non_nullable
as CapitalKind,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,
  ));
}

/// Create a copy of CapitalContribution
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
mixin _$PartnershipContract {

 SyncMeta get meta; String get partnershipId; int get version; String get templateId; String get termsJson;
/// Create a copy of PartnershipContract
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$PartnershipContractCopyWith<PartnershipContract> get copyWith => _$PartnershipContractCopyWithImpl<PartnershipContract>(this as PartnershipContract, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is PartnershipContract&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.version, version) || other.version == version)&&(identical(other.templateId, templateId) || other.templateId == templateId)&&(identical(other.termsJson, termsJson) || other.termsJson == termsJson));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,version,templateId,termsJson);

@override
String toString() {
  return 'PartnershipContract(meta: $meta, partnershipId: $partnershipId, version: $version, templateId: $templateId, termsJson: $termsJson)';
}


}

/// @nodoc
abstract mixin class $PartnershipContractCopyWith<$Res>  {
  factory $PartnershipContractCopyWith(PartnershipContract value, $Res Function(PartnershipContract) _then) = _$PartnershipContractCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String partnershipId, int version, String templateId, String termsJson
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$PartnershipContractCopyWithImpl<$Res>
    implements $PartnershipContractCopyWith<$Res> {
  _$PartnershipContractCopyWithImpl(this._self, this._then);

  final PartnershipContract _self;
  final $Res Function(PartnershipContract) _then;

/// Create a copy of PartnershipContract
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? partnershipId = null,Object? version = null,Object? templateId = null,Object? termsJson = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,version: null == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as int,templateId: null == templateId ? _self.templateId : templateId // ignore: cast_nullable_to_non_nullable
as String,termsJson: null == termsJson ? _self.termsJson : termsJson // ignore: cast_nullable_to_non_nullable
as String,
  ));
}
/// Create a copy of PartnershipContract
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [PartnershipContract].
extension PartnershipContractPatterns on PartnershipContract {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _PartnershipContract value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _PartnershipContract() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _PartnershipContract value)  $default,){
final _that = this;
switch (_that) {
case _PartnershipContract():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _PartnershipContract value)?  $default,){
final _that = this;
switch (_that) {
case _PartnershipContract() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  int version,  String templateId,  String termsJson)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _PartnershipContract() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.version,_that.templateId,_that.termsJson);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  int version,  String templateId,  String termsJson)  $default,) {final _that = this;
switch (_that) {
case _PartnershipContract():
return $default(_that.meta,_that.partnershipId,_that.version,_that.templateId,_that.termsJson);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String partnershipId,  int version,  String templateId,  String termsJson)?  $default,) {final _that = this;
switch (_that) {
case _PartnershipContract() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.version,_that.templateId,_that.termsJson);case _:
  return null;

}
}

}

/// @nodoc


class _PartnershipContract implements PartnershipContract {
  const _PartnershipContract({required this.meta, required this.partnershipId, required this.version, required this.templateId, required this.termsJson});
  

@override final  SyncMeta meta;
@override final  String partnershipId;
@override final  int version;
@override final  String templateId;
@override final  String termsJson;

/// Create a copy of PartnershipContract
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$PartnershipContractCopyWith<_PartnershipContract> get copyWith => __$PartnershipContractCopyWithImpl<_PartnershipContract>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _PartnershipContract&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.version, version) || other.version == version)&&(identical(other.templateId, templateId) || other.templateId == templateId)&&(identical(other.termsJson, termsJson) || other.termsJson == termsJson));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,version,templateId,termsJson);

@override
String toString() {
  return 'PartnershipContract(meta: $meta, partnershipId: $partnershipId, version: $version, templateId: $templateId, termsJson: $termsJson)';
}


}

/// @nodoc
abstract mixin class _$PartnershipContractCopyWith<$Res> implements $PartnershipContractCopyWith<$Res> {
  factory _$PartnershipContractCopyWith(_PartnershipContract value, $Res Function(_PartnershipContract) _then) = __$PartnershipContractCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String partnershipId, int version, String templateId, String termsJson
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$PartnershipContractCopyWithImpl<$Res>
    implements _$PartnershipContractCopyWith<$Res> {
  __$PartnershipContractCopyWithImpl(this._self, this._then);

  final _PartnershipContract _self;
  final $Res Function(_PartnershipContract) _then;

/// Create a copy of PartnershipContract
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? partnershipId = null,Object? version = null,Object? templateId = null,Object? termsJson = null,}) {
  return _then(_PartnershipContract(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,version: null == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as int,templateId: null == templateId ? _self.templateId : templateId // ignore: cast_nullable_to_non_nullable
as String,termsJson: null == termsJson ? _self.termsJson : termsJson // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

/// Create a copy of PartnershipContract
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
mixin _$BuyoutPayment {

 SyncMeta get meta; String get partnershipId; Money get amount; LocalDate get paidOn;
/// Create a copy of BuyoutPayment
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$BuyoutPaymentCopyWith<BuyoutPayment> get copyWith => _$BuyoutPaymentCopyWithImpl<BuyoutPayment>(this as BuyoutPayment, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is BuyoutPayment&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.paidOn, paidOn) || other.paidOn == paidOn));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,amount,paidOn);

@override
String toString() {
  return 'BuyoutPayment(meta: $meta, partnershipId: $partnershipId, amount: $amount, paidOn: $paidOn)';
}


}

/// @nodoc
abstract mixin class $BuyoutPaymentCopyWith<$Res>  {
  factory $BuyoutPaymentCopyWith(BuyoutPayment value, $Res Function(BuyoutPayment) _then) = _$BuyoutPaymentCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String partnershipId, Money amount, LocalDate paidOn
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$BuyoutPaymentCopyWithImpl<$Res>
    implements $BuyoutPaymentCopyWith<$Res> {
  _$BuyoutPaymentCopyWithImpl(this._self, this._then);

  final BuyoutPayment _self;
  final $Res Function(BuyoutPayment) _then;

/// Create a copy of BuyoutPayment
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? partnershipId = null,Object? amount = null,Object? paidOn = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,paidOn: null == paidOn ? _self.paidOn : paidOn // ignore: cast_nullable_to_non_nullable
as LocalDate,
  ));
}
/// Create a copy of BuyoutPayment
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [BuyoutPayment].
extension BuyoutPaymentPatterns on BuyoutPayment {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _BuyoutPayment value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _BuyoutPayment() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _BuyoutPayment value)  $default,){
final _that = this;
switch (_that) {
case _BuyoutPayment():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _BuyoutPayment value)?  $default,){
final _that = this;
switch (_that) {
case _BuyoutPayment() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  Money amount,  LocalDate paidOn)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _BuyoutPayment() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.amount,_that.paidOn);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  Money amount,  LocalDate paidOn)  $default,) {final _that = this;
switch (_that) {
case _BuyoutPayment():
return $default(_that.meta,_that.partnershipId,_that.amount,_that.paidOn);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String partnershipId,  Money amount,  LocalDate paidOn)?  $default,) {final _that = this;
switch (_that) {
case _BuyoutPayment() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.amount,_that.paidOn);case _:
  return null;

}
}

}

/// @nodoc


class _BuyoutPayment implements BuyoutPayment {
  const _BuyoutPayment({required this.meta, required this.partnershipId, required this.amount, required this.paidOn});
  

@override final  SyncMeta meta;
@override final  String partnershipId;
@override final  Money amount;
@override final  LocalDate paidOn;

/// Create a copy of BuyoutPayment
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$BuyoutPaymentCopyWith<_BuyoutPayment> get copyWith => __$BuyoutPaymentCopyWithImpl<_BuyoutPayment>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _BuyoutPayment&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.amount, amount) || other.amount == amount)&&(identical(other.paidOn, paidOn) || other.paidOn == paidOn));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,amount,paidOn);

@override
String toString() {
  return 'BuyoutPayment(meta: $meta, partnershipId: $partnershipId, amount: $amount, paidOn: $paidOn)';
}


}

/// @nodoc
abstract mixin class _$BuyoutPaymentCopyWith<$Res> implements $BuyoutPaymentCopyWith<$Res> {
  factory _$BuyoutPaymentCopyWith(_BuyoutPayment value, $Res Function(_BuyoutPayment) _then) = __$BuyoutPaymentCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String partnershipId, Money amount, LocalDate paidOn
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$BuyoutPaymentCopyWithImpl<$Res>
    implements _$BuyoutPaymentCopyWith<$Res> {
  __$BuyoutPaymentCopyWithImpl(this._self, this._then);

  final _BuyoutPayment _self;
  final $Res Function(_BuyoutPayment) _then;

/// Create a copy of BuyoutPayment
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? partnershipId = null,Object? amount = null,Object? paidOn = null,}) {
  return _then(_BuyoutPayment(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,amount: null == amount ? _self.amount : amount // ignore: cast_nullable_to_non_nullable
as Money,paidOn: null == paidOn ? _self.paidOn : paidOn // ignore: cast_nullable_to_non_nullable
as LocalDate,
  ));
}

/// Create a copy of BuyoutPayment
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
mixin _$PartnershipConsent {

 SyncMeta get meta; String get partnershipId; String get memberId;
/// Create a copy of PartnershipConsent
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$PartnershipConsentCopyWith<PartnershipConsent> get copyWith => _$PartnershipConsentCopyWithImpl<PartnershipConsent>(this as PartnershipConsent, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is PartnershipConsent&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,memberId);

@override
String toString() {
  return 'PartnershipConsent(meta: $meta, partnershipId: $partnershipId, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class $PartnershipConsentCopyWith<$Res>  {
  factory $PartnershipConsentCopyWith(PartnershipConsent value, $Res Function(PartnershipConsent) _then) = _$PartnershipConsentCopyWithImpl;
@useResult
$Res call({
 SyncMeta meta, String partnershipId, String memberId
});


$SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class _$PartnershipConsentCopyWithImpl<$Res>
    implements $PartnershipConsentCopyWith<$Res> {
  _$PartnershipConsentCopyWithImpl(this._self, this._then);

  final PartnershipConsent _self;
  final $Res Function(PartnershipConsent) _then;

/// Create a copy of PartnershipConsent
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? meta = null,Object? partnershipId = null,Object? memberId = null,}) {
  return _then(_self.copyWith(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,memberId: null == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String,
  ));
}
/// Create a copy of PartnershipConsent
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SyncMetaCopyWith<$Res> get meta {
  
  return $SyncMetaCopyWith<$Res>(_self.meta, (value) {
    return _then(_self.copyWith(meta: value));
  });
}
}


/// Adds pattern-matching-related methods to [PartnershipConsent].
extension PartnershipConsentPatterns on PartnershipConsent {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _PartnershipConsent value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _PartnershipConsent() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _PartnershipConsent value)  $default,){
final _that = this;
switch (_that) {
case _PartnershipConsent():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _PartnershipConsent value)?  $default,){
final _that = this;
switch (_that) {
case _PartnershipConsent() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  String memberId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _PartnershipConsent() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.memberId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( SyncMeta meta,  String partnershipId,  String memberId)  $default,) {final _that = this;
switch (_that) {
case _PartnershipConsent():
return $default(_that.meta,_that.partnershipId,_that.memberId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( SyncMeta meta,  String partnershipId,  String memberId)?  $default,) {final _that = this;
switch (_that) {
case _PartnershipConsent() when $default != null:
return $default(_that.meta,_that.partnershipId,_that.memberId);case _:
  return null;

}
}

}

/// @nodoc


class _PartnershipConsent implements PartnershipConsent {
  const _PartnershipConsent({required this.meta, required this.partnershipId, required this.memberId});
  

@override final  SyncMeta meta;
@override final  String partnershipId;
@override final  String memberId;

/// Create a copy of PartnershipConsent
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$PartnershipConsentCopyWith<_PartnershipConsent> get copyWith => __$PartnershipConsentCopyWithImpl<_PartnershipConsent>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _PartnershipConsent&&(identical(other.meta, meta) || other.meta == meta)&&(identical(other.partnershipId, partnershipId) || other.partnershipId == partnershipId)&&(identical(other.memberId, memberId) || other.memberId == memberId));
}


@override
int get hashCode => Object.hash(runtimeType,meta,partnershipId,memberId);

@override
String toString() {
  return 'PartnershipConsent(meta: $meta, partnershipId: $partnershipId, memberId: $memberId)';
}


}

/// @nodoc
abstract mixin class _$PartnershipConsentCopyWith<$Res> implements $PartnershipConsentCopyWith<$Res> {
  factory _$PartnershipConsentCopyWith(_PartnershipConsent value, $Res Function(_PartnershipConsent) _then) = __$PartnershipConsentCopyWithImpl;
@override @useResult
$Res call({
 SyncMeta meta, String partnershipId, String memberId
});


@override $SyncMetaCopyWith<$Res> get meta;

}
/// @nodoc
class __$PartnershipConsentCopyWithImpl<$Res>
    implements _$PartnershipConsentCopyWith<$Res> {
  __$PartnershipConsentCopyWithImpl(this._self, this._then);

  final _PartnershipConsent _self;
  final $Res Function(_PartnershipConsent) _then;

/// Create a copy of PartnershipConsent
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? meta = null,Object? partnershipId = null,Object? memberId = null,}) {
  return _then(_PartnershipConsent(
meta: null == meta ? _self.meta : meta // ignore: cast_nullable_to_non_nullable
as SyncMeta,partnershipId: null == partnershipId ? _self.partnershipId : partnershipId // ignore: cast_nullable_to_non_nullable
as String,memberId: null == memberId ? _self.memberId : memberId // ignore: cast_nullable_to_non_nullable
as String,
  ));
}

/// Create a copy of PartnershipConsent
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
