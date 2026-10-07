// Release'da Windows konsol oynasini yashiradi.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    baraka_desktop::run();
}
