// Release'da qo'shimcha konsol oynasi ochilmasin.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tamga_studio_lib::run();
}
