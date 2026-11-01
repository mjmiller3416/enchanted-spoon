package com.enchantedspoon.app;

import android.content.Intent;
import android.os.Bundle;
import com.getcapacitor.BridgeActivity;
import org.json.JSONObject;

/**
 * Receives share-sheet text (TikTok, Instagram, and other apps) and tells the
 * hosted page to open recipe import. Custom-scheme launches are handled by
 * the Capacitor App plugin.
 */
public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        deliverShare(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        deliverShare(intent);
    }

    private void deliverShare(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) {
            return;
        }
        String text = intent.getStringExtra(Intent.EXTRA_TEXT);
        if (text == null || text.isEmpty() || getBridge() == null || getBridge().getWebView() == null) {
            return;
        }
        String quoted = JSONObject.quote(text);
        String script = "window.dispatchEvent(new CustomEvent('enchantedspoon:import',{detail:" + quoted + "}))";
        getBridge().getWebView().post(() -> getBridge().getWebView().evaluateJavascript(script, null));
    }
}
