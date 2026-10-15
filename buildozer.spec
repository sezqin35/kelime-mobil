[app]
title = Kelime Avcıları
package.name = kelimeavcilari
package.domain = org.szggames

source.dir = .
source.include_exts = py,png,jpg,mp3,txt

version = 1.0.0

requirements = python3,kivy,kivmob

orientation = portrait
fullscreen = 1

android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 34
android.minapi = 24
android.ndk = 25b

android.release_artifact = apk

icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/Kelime_oyunu.png

android.archs = arm64-v8a, armeabi-v7a
android.gradle_dependencies = 'com.google.android.gms:play-services-ads:23.0.0'
android.meta_data = com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-4733411214953557~3933038318