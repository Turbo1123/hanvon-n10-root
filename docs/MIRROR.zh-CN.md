# Mac USB 投屏与操作

投屏使用 [scrcpy](https://github.com/Genymobile/scrcpy)，不依赖 root。仍需平板在正常 Android 中启动、开启 USB 调试并授权自己的电脑；Loader / MaskROM 或未启动系统时不能投屏。

macOS 安装 scrcpy 后：

```sh
export N10_EXPECT_USB_SERIAL='YOUR_OWN_DEVICE_SERIAL'
sh scripts/mirror-n10.sh --render-driver=metal
```

测试参数：硬件 H.264 编码器 `OMX.rk.video_encoder.avc`、最大边 1280、帧率上限 30、8 Mbps、`--video-buffer=0`、关闭音频。该机对应编码尺寸 960×1280。视频缓冲为零意味着不额外增加该缓冲，不等于总延迟为零。见上游 [视频配置](https://github.com/Genymobile/scrcpy/blob/master/doc/video.md)。

鼠标可以操作平板 UI。底部三键由 [N10 导航键应用](../navigation/README.md)提供，Mac 投屏内同样能点击。右侧 `×` 可临时关闭覆盖栏，避免遮挡当前应用底部内容。

这些配置已在一台 Mac 与本机 USB 连接上验证显示与控制，没有对其他系统或网络无线连接做延迟测试。
