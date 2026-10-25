package com.szggames.kelimeoyunu;

import android.app.Activity;
import android.content.pm.PackageInfo;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.webkit.WebView;

import com.google.android.gms.ads.AdError;
import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.FullScreenContentCallback;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.MobileAds;
import com.google.android.gms.ads.initialization.InitializationStatus;
import com.google.android.gms.ads.initialization.OnInitializationCompleteListener;
import com.google.android.gms.ads.interstitial.InterstitialAd;
import com.google.android.gms.ads.interstitial.InterstitialAdLoadCallback;

/**
 * Güncel Google Mobile Ads SDK ile geçiş (interstitial) reklamı.
 * Python tarafından pyjnius ile çağrılır.
 */
public class AdHelper {
    private static final String TAG = "AdHelper";

    private static volatile InterstitialAd interstitial = null;
    private static volatile boolean loading = false;
    private static volatile String unitId = null;
    private static volatile String status = "baslamadi";
    private static volatile int retryCount = 0;
    private static final int MAX_RETRY = 6;
    private static final long RETRY_DELAY_MS = 12000;

    public static String getStatus() {
        return status + " | " + deviceInfo();
    }

    private static String deviceInfo() {
        String web = "WebView: yok/okunamadi";
        try {
            if (Build.VERSION.SDK_INT >= 26) {
                PackageInfo pi = WebView.getCurrentWebViewPackage();
                if (pi != null) {
                    web = "WebView: " + pi.packageName + " " + pi.versionName;
                } else {
                    web = "WebView: YOK";
                }
            }
        } catch (Throwable t) {
            web = "WebView hata: " + t.getClass().getSimpleName();
        }
        return Build.MANUFACTURER + " " + Build.MODEL + " (Android " + Build.VERSION.SDK_INT + ") " + web
                + " | deneme=" + retryCount;
    }

    public static void init(final Activity activity, final String adUnitId) {
        unitId = adUnitId;
        status = "init: baslatiliyor";
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    MobileAds.initialize(activity, new OnInitializationCompleteListener() {
                        @Override
                        public void onInitializationComplete(InitializationStatus initStatus) {
                            status = "init tamam, reklam isteniyor";
                            doLoad(activity);
                        }
                    });
                } catch (Throwable t) {
                    status = "init HATA: " + t.getClass().getSimpleName() + " " + t.getMessage();
                    Log.w(TAG, "AdMob baslatilamadi", t);
                }
            }
        });
    }

    public static void load(final Activity activity) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                doLoad(activity);
            }
        });
    }

    private static void doLoad(final Activity activity) {
        if (unitId == null || loading || interstitial != null) {
            return;
        }
        loading = true;
        status = "reklam yukleniyor";
        try {
            InterstitialAd.load(activity, unitId, new AdRequest.Builder().build(),
                    new InterstitialAdLoadCallback() {
                        @Override
                        public void onAdLoaded(InterstitialAd ad) {
                            interstitial = ad;
                            loading = false;
                            retryCount = 0;
                            status = "HAZIR (reklam yuklendi)";
                        }

                        @Override
                        public void onAdFailedToLoad(LoadAdError error) {
                            interstitial = null;
                            loading = false;
                            status = "yuklenemedi: kod=" + error.getCode() + " " + error.getMessage();
                            Log.w(TAG, "Reklam yuklenemedi: " + error.getMessage());
                            if (retryCount < MAX_RETRY) {
                                retryCount++;
                                new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
                                    @Override
                                    public void run() {
                                        doLoad(activity);
                                    }
                                }, RETRY_DELAY_MS);
                            }
                        }
                    });
        } catch (Throwable t) {
            loading = false;
            status = "yukleme HATA: " + t.getClass().getSimpleName() + " " + t.getMessage();
            Log.w(TAG, "Reklam yuklenirken hata", t);
        }
    }

    public static boolean isLoaded() {
        return interstitial != null;
    }

    public static void show(final Activity activity) {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                final InterstitialAd ad = interstitial;
                if (ad == null) {
                    status = "show: reklam hazir degildi";
                    doLoad(activity);
                    return;
                }
                ad.setFullScreenContentCallback(new FullScreenContentCallback() {
                    @Override
                    public void onAdDismissedFullScreenContent() {
                        interstitial = null;
                        doLoad(activity);
                    }

                    @Override
                    public void onAdFailedToShowFullScreenContent(AdError error) {
                        status = "gosterilemedi: " + error.getMessage();
                        interstitial = null;
                        doLoad(activity);
                    }
                });
                try {
                    status = "gosteriliyor";
                    ad.show(activity);
                } catch (Throwable t) {
                    status = "show HATA: " + t.getClass().getSimpleName() + " " + t.getMessage();
                    interstitial = null;
                    Log.w(TAG, "Reklam gosterilemedi", t);
                }
            }
        });
    }
}
