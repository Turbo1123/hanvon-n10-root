# 验证记录

日期：2026-11-12。对象：一台 N10 / HWV 12.42 / 1.02.49 / Android 11，详见 [脱敏结果](../evidence/tested-result.json)。

## 实机验证通过

- 从关机状态，用圆形返回键 + 电源键进入 Rockusb Loader；不是仅依赖 ADB 重启。
- 原厂完整 block OTA 的配置 MD5、文件 SHA-256、ZIP 条目 CRC、型号 / 指纹匹配。
- 原版读取存在 32 MiB 边界后的 `0xCC` 占位行为；原版 RAM helper 也受限。
- 严格匹配的 RAM-only helper 成功下载；边界探针逐字节匹配原厂 boot 的同偏移内容。
- 31037849600 字节 eMMC 主用户区已读取，主 / 备 GPT 头 CRC、主 GPT 表 CRC、独立低地址读取、原厂 boot 和 recovery 镜像头校验通过；备份已在本地保存。
- Magisk 31.1 在原机修补原始 boot，kernel / second / DTB / cmdline 保留，设置 KEEPVERITY / KEEPFORCEENCRYPT 为 true，未请求修改 vbmeta。
- 只写固件 boot 分区；完整回读 SHA-256 与待写镜像一致。
- 官方 `fix_env` 后 `env_check 31.1 31100` 返回 0；重启后普通 `su` 返回 uid 0、模块加载、SELinux Enforcing。
- scrcpy USB H.264 硬件编码投屏显示正常，Mac 鼠标输入生效；底部返回、主页、多任务逐个点击验证。

## 为公开发行所做的离线检查

公开脚本取消写死序列号和私有目录，改从本地环境变量读取；把安全断言改为不会被 `python -O` 关闭的显式检查。刷写工具增加默认 dry run、整盘备份重新哈希、写前现场边界探针检查。备份工具增加备用 GPT 表内容 / CRC 对照。

发行前检查结果记录在 [release-validation.json](../evidence/release-validation.json)。这包括 Python 测试、实际原厂 loader 补丁哈希复现、实际原机 boot 修补结果的离线验证、rkdeveloptool macOS 构建、导航 APK 编译与签名验证、待发布内容隐私检查。

## 未验证 / 不保证

- 没有为发布而再次执行公开版刷写 / 全备份脚本的设备写入流程。实机结果来自发布前的设备专用版本。
- 没有执行恢复原始 boot 的实际写入，也没有整盘恢复演练。
- 没有备份独立 eMMC 硬件 boot 区 / RPMB。
- 没有测试仍锁定的设备、其他硬件版、其他固件、其他 eMMC 容量或其他 Rockchip SoC。
- 没有测试三键应用开机自动恢复；接收器已实现。三键是覆盖层，不会像系统导航栏那样自动给所有应用保留底部空间。
- 没有测量端到端延迟毫秒值；投屏参数只证明使用了硬件编码和零额外视频缓冲，不表示恒定 30 fps 或某个延迟承诺。
