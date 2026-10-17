// Release build'da Windows'da qo'shimcha konsol oynasi ochilmasin.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    baraka_daftari_lib::run();
}
