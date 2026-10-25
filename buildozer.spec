[app]
title = Kelime Avcıları
package.name = kelimeoyunu
package.domain = com.szggames.kelimeoyunu
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,mp3,wav,txt
source.exclude_dirs = bin,.buildozer,.github,.git
version = 1.0.0
requirements = python3==3.11.5,hostpython3==3.11.5,kivy==2.3.0,pyjnius,kivmob
orientation = portrait
fullscreen = 1
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/Kelime_oyunu.png
android.presplash_color = #000000

p4a.branch = v2024.01.21

android.api = 33
android.minapi = 21
android.ndk_api = 21
android.archs = arm64-v8a
android.accept_sdk_license = True
android.enable_androidx = True
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.meta_data = com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-4733411214953557~3933038318
android.gradle_dependencies = com.google.android.gms:play-services-ads:20.6.0

[app@play]
requirements = python3,kivy,pyjnius
p4a.branch = develop
android.api = 36
android.ndk = 29
android.archs = arm64-v8a
android.release_artifact = aab
android.numeric_version = 1
android.add_src = java
android.gradle_dependencies = com.google.android.gms:play-services-ads:23.6.0

[buildozer]
log_level = 2
warn_on_root = 1
