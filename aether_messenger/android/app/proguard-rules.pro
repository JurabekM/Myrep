# UniFFI/JNA generated bindings use reflection-free direct native calls; JNA itself
# needs its structure classes kept if minification is ever enabled for release.
-keep class com.sun.jna.** { *; }
-keep class uniffi.aether_ffi.** { *; }
