package local.learnpad.n10navigation;
import android.app.*;
import android.os.*;
import android.content.*;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.view.*;
import android.widget.*;
import java.util.concurrent.*;
public class NavService extends Service {
  WindowManager wm;
  LinearLayout bar;
  ExecutorService executor = Executors.newSingleThreadExecutor();
  int dp(int x) {
    return Math.round(x * getResources().getDisplayMetrics().density);
  }
  public void onCreate() {
    super.onCreate();
    NotificationManager nm = getSystemService(NotificationManager.class);
    nm.createNotificationChannel(
        new NotificationChannel("navigation", "底部导航键", NotificationManager.IMPORTANCE_LOW));
    PendingIntent pi = PendingIntent.getActivity(
        this, 0, new Intent(this, MainActivity.class), PendingIntent.FLAG_IMMUTABLE);
    startForeground(1,
        new Notification.Builder(this, "navigation")
            .setSmallIcon(android.R.drawable.ic_media_previous)
            .setContentTitle("N10 底部三键已开启")
            .setContentText("返回 · 主页 · 多任务，点此管理")
            .setContentIntent(pi)
            .build());
    wm = getSystemService(WindowManager.class);
    bar = new LinearLayout(this);
    bar.setOrientation(0);
    bar.setGravity(Gravity.CENTER);
    bar.setBackgroundColor(Color.WHITE);
    add("◁  返回", 4);
    add("○  主页", 3);
    add("□  多任务", 187);
    TextView close = new TextView(this);
    close.setText("×");
    close.setTextSize(22);
    close.setTextColor(Color.DKGRAY);
    close.setGravity(Gravity.CENTER);
    close.setContentDescription("关闭底部导航键");
    bar.addView(close, new LinearLayout.LayoutParams(dp(40), -1));
    close.setOnClickListener(v -> {
      getSharedPreferences("nav", 0).edit().putBoolean("enabled", false).apply();
      stopSelf();
    });
    WindowManager.LayoutParams lp = new WindowManager.LayoutParams(-1, dp(54),
        WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
            | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
            | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
        PixelFormat.OPAQUE);
    lp.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;
    lp.setTitle("N10 底部导航键");
    wm.addView(bar, lp);
  }
  void add(String text, int key) {
    Button b = new Button(this);
    b.setAllCaps(false);
    b.setText(text);
    b.setTextSize(20);
    b.setTextColor(Color.BLACK);
    b.setContentDescription(text);
    b.setPadding(0, 0, 0, 0);
    bar.addView(b, new LinearLayout.LayoutParams(0, -1, 1));
    b.setOnClickListener(v -> executor.execute(() -> {
      try {
        java.lang.Process p = new ProcessBuilder("/system/bin/su", "-c",
            key == 187 ? "/system/bin/am start -n com.hanvon.recents/.MainActivity"
                       : "/system/bin/input keyevent " + key)
                                  .start();
        int result = p.waitFor();
        if (result != 0)
          new Handler(getMainLooper())
              .post(()
                        -> Toast
                               .makeText(this, "请在 Magisk 中允许 N10 导航键使用 root",
                                   Toast.LENGTH_LONG)
                               .show());
      } catch (Exception e) {
        new Handler(getMainLooper())
            .post(() -> Toast.makeText(this, "导航执行失败", Toast.LENGTH_LONG).show());
      }
    }));
  }
  public int onStartCommand(Intent i, int f, int id) {
    return START_STICKY;
  }
  public IBinder onBind(Intent i) {
    return null;
  }
  public void onDestroy() {
    if (bar != null)
      wm.removeView(bar);
    executor.shutdownNow();
    stopForeground(true);
    super.onDestroy();
  }
}
