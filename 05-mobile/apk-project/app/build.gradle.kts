plugins {
    id("com.android.application")
}

android {
    namespace = "com.mira.client"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.mira.client"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    signingConfigs {
        create("release") {
            storeFile = file("${rootProject.projectDir}/mira.keystore")
            storePassword = "mira123"
            keyAlias = "mira"
            keyPassword = "mira123"
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.webkit:webkit:1.9.0")
}
