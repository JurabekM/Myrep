// Release build'da Windows konsol oynasi ochilmaydi.
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

fn main() {
    baraka_desktop_lib::run();
}
