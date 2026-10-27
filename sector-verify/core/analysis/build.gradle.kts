plugins {
    alias(libs.plugins.sv.jvm.library)
}

dependencies {
    api(project(":core:model"))
}

// AC-10: :core:analysis qator qamrovi >= 90 %.
kover {
    reports {
        verify {
            rule {
                minBound(90)
            }
        }
    }
}
