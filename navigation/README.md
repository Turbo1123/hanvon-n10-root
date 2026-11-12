# N10 底部导航键

本地悬浮栏：返回、主页、多任务，以及右侧关闭按钮。可从「N10 导航键」应用重新开启。

实机点击和 Mac USB 投屏点击均已验证。三键栏是悬浮层，会覆盖屏幕底部约 54 dp；遇到按钮遮挡时可点右侧 `×` 暂时关闭。代码包含开机启动接收器，但开机自动恢复三键栏尚未单独验证。

本应用需要悬浮窗授权，以及 Magisk 中对「N10 导航键」的 root 授权。没有网络权限，不使用无障碍读取服务。返回和主页通过 `su` 执行对应按键；多任务直接启动本机原有的 `com.hanvon.recents/.MainActivity`，因为该固件把 `KEYCODE_APP_SWITCH` 改成了应用列表。

## 编译

安装 JDK 17、Android SDK platform 33 和 build-tools 35.0.1。将自己的签名 key 放在仓库以外，并在当前终端设置：

```sh
export ANDROID_HOME="$HOME/Library/Android/sdk"
export N10_SIGNING_KEYSTORE="$HOME/.local/share/n10/navigation.keystore"
export N10_SIGNING_ALIAS=navigation
# 在本机交互式设置 N10_SIGNING_PASSWORD，不要写入提交或工单。
python3 navigation/build.py
```

安装后先在系统设置中允许悬浮窗，并在 Magisk 的超级用户页允许本应用，再打开应用点「显示底部三键」。不建议把 root 权限授予来源不明的导航应用。

发行版 APK 如有提供，只包含这里的应用源码；签名私钥从不随仓库或发行包分发。
