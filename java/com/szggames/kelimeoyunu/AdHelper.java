package com.szggames.kelimeoyunu;

import android.app.Activity;
import android.util.Log;

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

    public static void init(final Activity activity, final String adUnitId) {
        unitId = adUnitId;
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                try {
                    MobileAds.initialize(activity, new OnInitializationCompleteListener() {
                        @Override
                        public void onInitializationComplete(InitializationStatus status) {
                            doLoad(activity);
                        }
                    });
                } catch (Throwable t) {
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
        try {
            InterstitialAd.load(activity, unitId, new AdRequest.Builder().build(),
                    new InterstitialAdLoadCallback() {
                        @Override
                        public void onAdLoaded(InterstitialAd ad) {
                            interstitial = ad;
                            loading = false;
                        }

                        @Override
                        public void onAdFailedToLoad(LoadAdError error) {
                            interstitial = null;
                            loading = false;
                            Log.w(TAG, "Reklam yuklenemedi: " + error.getMessage());
                        }
                    });
        } catch (Throwable t) {
            loading = false;
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
                        interstitial = null;
                        doLoad(activity);
                    }
                });
                try {
                    ad.show(activity);
                } catch (Throwable t) {
                    interstitial = null;
                    Log.w(TAG, "Reklam gosterilemedi", t);
                }
            }
        });
    }
}
