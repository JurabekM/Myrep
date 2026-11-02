package uz.rostor.testapk;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;

/** Bo'sh xizmat: faqat manifestda "Accessibility" belgisi bo'lishi uchun. Hech narsa qilmaydi. */
public class HelperService extends AccessibilityService {
    @Override public void onAccessibilityEvent(AccessibilityEvent event) {}
    @Override public void onInterrupt() {}
}
