package local.learnpad.n10navigation;
import android.content.*;
import android.provider.Settings;
public class BootReceiver extends BroadcastReceiver {
  public void onReceive(Context c, Intent i) {
    if (Intent.ACTION_BOOT_COMPLETED.equals(i.getAction()) && Settings.canDrawOverlays(c)
        && c.getSharedPreferences("nav", 0).getBoolean("enabled", true))
      c.startForegroundService(new Intent(c, NavService.class));
  }
}
