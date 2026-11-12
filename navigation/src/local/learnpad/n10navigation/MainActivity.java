package local.learnpad.n10navigation;
import android.app.*;
import android.os.*;
import android.content.*;
import android.provider.Settings;
import android.net.Uri;
import android.view.*;
import android.widget.*;
public class MainActivity extends Activity {
  public void onCreate(Bundle b) {
    super.onCreate(b);
    LinearLayout l = new LinearLayout(this);
    l.setOrientation(1);
    int d = (int) (24 * getResources().getDisplayMetrics().density);
    l.setPadding(d, d, d, d);
    TextView t = new TextView(this);
    t.setText(
        "N10 底部导航键\n\n返回 · 主页 · 多任务\n使用其他应用时，底部按钮也会显示。\n\n底部小 × 可以临时关闭；从这里可以重新开启。");
    t.setTextSize(22);
    l.addView(t);
    Button on = new Button(this);
    on.setText("显示底部三键");
    l.addView(on);
    on.setOnClickListener(v -> {
      if (!Settings.canDrawOverlays(this)) {
        startActivity(new Intent(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:" + getPackageName())));
        return;
      }
      getSharedPreferences("nav", 0).edit().putBoolean("enabled", true).apply();
      startForegroundService(new Intent(this, NavService.class));
    });
    Button off = new Button(this);
    off.setText("关闭底部三键");
    l.addView(off);
    off.setOnClickListener(v -> {
      getSharedPreferences("nav", 0).edit().putBoolean("enabled", false).apply();
      stopService(new Intent(this, NavService.class));
    });
    setContentView(l);
    if (Settings.canDrawOverlays(this)
        && getSharedPreferences("nav", 0).getBoolean("enabled", true))
      startForegroundService(new Intent(this, NavService.class));
  }
}
