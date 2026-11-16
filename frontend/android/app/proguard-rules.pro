# Release R8 rules for the Capacitor shell.
# Debug stays unminified. Do not blanket-keep a whole SDK: Play flagged this
# app because too little of the DEX was obfuscated.

# Line numbers stay in the mapping file. The source name is rewritten to
# "SourceFile" so traces remain deobfuscatable without original paths.
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile

# Annotations, generic signatures, and inner-class metadata. Plugin lookup
# reads @CapacitorPlugin and @PluginMethod at runtime. R8 full mode drops
# those annotations unless the attributes and the annotation types are kept.
-keepattributes AnnotationDefault,
                EnclosingMethod,
                InnerClasses,
                RuntimeVisibleAnnotations,
                RuntimeVisibleParameterAnnotations,
                RuntimeVisibleTypeAnnotations,
                Signature

# Javascript interface methods are invoked by name from the WebView.
# Capacitor uses this for MessageHandler.postMessage ("androidBridge") and
# for CapacitorHttp / CapacitorCookies. proguard-android-optimize.txt has
# the same rule; it is repeated because those methods are the native bridge.
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# Capacitor loads installed plugins with Class.forName on the classpath
# strings in assets/capacitor.plugins.json, then reflects on
# @CapacitorPlugin / @PluginMethod (including non-public callback methods).
# :capacitor-android publishes the same rules as consumer ProGuard rules.
# They are repeated here so the plugin classes stay kept if that consumer
# file changes. Plugins in this app:
#   com.capacitorjs.plugins.app.AppPlugin                                 (@capacitor/app)
#   com.capacitorjs.plugins.browser.BrowserPlugin                         (@capacitor/browser)
#   com.capacitorjs.plugins.pushnotifications.PushNotificationsPlugin     (@capacitor/push-notifications)
#   com.capacitorjs.plugins.splashscreen.SplashScreenPlugin               (@capacitor/splash-screen)
#   com.revenuecat.purchases.capacitor.PurchasesPlugin                    (@revenuecat/purchases-capacitor)
# WebView, SystemBars, CapacitorHttp, and CapacitorCookies are registered
# by class literal inside Bridge and are covered by the Plugin subclass rule.

-keep @com.getcapacitor.annotation.CapacitorPlugin public class * {
    @com.getcapacitor.annotation.PermissionCallback <methods>;
    @com.getcapacitor.annotation.ActivityCallback <methods>;
    @com.getcapacitor.annotation.Permission <methods>;
    @com.getcapacitor.PluginMethod public <methods>;
}

-keep public class * extends com.getcapacitor.Plugin { *; }

-keep @interface com.getcapacitor.annotation.** { *; }
-keep @interface com.getcapacitor.PluginMethod { *; }

-keepclassmembers class * extends com.getcapacitor.Plugin {
    @com.getcapacitor.annotation.ActivityCallback <methods>;
    @com.getcapacitor.annotation.PermissionCallback <methods>;
}

-keep @com.getcapacitor.NativePlugin public class * {
    @com.getcapacitor.PluginMethod public <methods>;
}
-keep @interface com.getcapacitor.NativePlugin { *; }

# Firebase instantiates this from the merged manifest class name. It does
# not extend Plugin, so the rules above do not cover it.
-keep class com.capacitorjs.plugins.pushnotifications.MessagingService { *; }

# No Cordova plugins are installed. capacitor-cordova-android-plugins has an
# empty dependency block, and org.apache.cordova:framework is only here
# because Capacitor still dispatches legacy "cordova" messages by class name.
# This matches Capacitor's consumer rule and matches nothing until a plugin
# subclass exists.
-keep public class * extends org.apache.cordova.* {
    public <methods>;
    public <fields>;
}

# RevenueCat purchases:11.0.0 (via purchases-hybrid-common:20.0.0) ships
# consumer rules. Enum names are matched against JSON with Class.enumConstants,
# and Parcelables are instantiated through CREATOR. Those are the reflective
# entry points. PurchasesPlugin is already kept above. A blanket keep of
# com.revenuecat.purchases.** is intentionally not added.
-keepclassmembers enum com.revenuecat.** {
    <fields>;
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

-keepclassmembers class com.revenuecat.** implements android.os.Parcelable {
    public static final ** CREATOR;
}

# Play Billing 9.1.0 ships these consumer rules. The AIDL types and the
# proxy activities are started by name. Proto fields are read reflectively.
-keep class com.android.vending.billing.** { *; }
-keep class com.google.android.apps.play.billingtestcompanion.aidl.** { *; }
-keepnames class com.android.billingclient.api.ProxyBillingActivity
-keepnames class com.android.billingclient.api.ProxyBillingActivityV2
-keepclassmembers class * extends com.google.android.gms.internal.play_billing.zzgp {
    <fields>;
}

# Not on the Android classpath, so they have no keep rules:
#   @clerk/nextjs (Clerk runs in the hosted WebView)
#   Google Sign-In
#   Credential Manager (androidx.credentials)
# play-services-auth-blockstore is RevenueCat's Block Store client, not
# Sign-In, and is invoked directly. kotlinx-serialization, AndroidX, and
# firebase-components ship their own consumer rules (ComponentRegistrar).
