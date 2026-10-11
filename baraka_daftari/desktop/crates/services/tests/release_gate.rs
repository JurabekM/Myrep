//! Reliz to'siqlari: kod bilan hal bo'lmaydigan (yuridik/diniy) shartlar. Oddiy `cargo test` da
//! o'tkazib yuboriladi; reliz CI da `cargo test -p services --test release_gate -- --ignored`
//! ishga tushiriladi va to'siq bo'lsa qizil bo'ladi (RELEASE_CHECKLIST.md).

#[test]
#[allow(clippy::assertions_on_constants)] // tasdiq bayrog'i qo'lda o'zgartiriladigan konstanta
#[ignore = "reliz CI: --ignored bilan ishga tushiriladi"]
fn contract_template_is_approved_by_lawyer_and_scholar() {
    assert!(
        services::TEMPLATES_APPROVED,
        "sheriklik shartnomasi shabloni yurist va ulamo tasdig'idan o'tmagan (OPEN_QUESTIONS 65)"
    );
}
