# 研究过程与关键判断

## 1. 把型号和可恢复条件放在 root 前面

测试对象是 N10 / HWV 12.42 / 系统 1.02.49，指纹为：

```text
HANVON/rk3566_eink/rk3566_eink:11/RQ2A.210505.003/eng.hanvon.20231116.173723:user/release-keys
```

测试开始时 `ro.boot.flash.locked=0`、verified boot 为 orange。本文没有证明仍然锁定的设备能够使用同样流程，也没有执行会清空用户数据的解锁步骤。

从原厂更新配置定位了对应完整 block OTA。文件 MD5 与原厂配置一致，SHA-256 固定记录，ZIP 中所有条目的 CRC 验证通过，包内指纹与设备一致。这里的“完整 OTA”指系统分区更新内容完整，不代表涵盖所有救援分区。

## 2. 备份成功提示不等于读到了真实内容

最初两次 boot 读取的大小与哈希一致，但进一步检查发现超过物理 LBA `65536` 的部分被 `0xCC` 填充。原机 boot 跨过该边界，因此它们不能用于恢复。

这个判断通过三类独立证据建立：原厂 boot 对照、边界前后内容、读取 helper 的反汇编。原版 loader 和原版 RAM helper 都有该限制；简单重新读取或换一次普通 helper 不能解决。

检测 `0xCC` 连续段只是保守的拒绝条件，不足以独立证明一个备份有效。我们同时检查 GPT CRC、独立低地址读取、原厂 boot 对照以及实际 recovery 镜像头。

## 3. 补丁只作用于临时 RAM helper

匹配的 `RKLoader.bin` 大小 428480 字节，SHA-256：

```text
75fa0a96d16d9afb1aee35bb51fee33d1a2ff9106dcca43151e30bbf10c53902
```

其中 helper 位于文件偏移 49596，长度 100352。启动代码将 helper 内文件偏移 `0x800` 的代码复制到 RAM `0x03001000`。阈值位于 RAM `0x0334d604`，普通与流水读取路径共用该值。

| 项目 | 原始 | 补丁 |
| --- | --- | --- |
| helper 内偏移 | `0x9924` | 同位置 |
| 指令字节 | `e9 03 10 32` | `09 00 80 12` |
| 含义 | `mov w9, #0x10000` | `mov w9, #-1` |
| 包 CRC | 验证原值 | 更新为新值 |

正常读取路径在 `0xA170` 附近比较阈值，填充分支在 `0xA1E0` 使用 `0xCC`；另一读取路径在 `0xA26C` 附近访问相同阈值。补丁工具同时检查这些相关指令，并拒绝任何不同的源文件。

包 CRC 使用多项式 **`0x04C10DB7`**、初值 0，结果小端存于文件尾；不能直接使用标准 zlib CRC-32。最终只改变一个 4 字节指令和 4 字节包 CRC，输出哈希为：

```text
d7c5e4cc07f21ecb0910b3943ffff0d21f8f312a582bcdfef9c3346e69dc6df2
```

通过 `rkdeveloptool boot` 从 MaskROM 临时下载，未写持久 loader。**不得把这个文件交给 `upgrade-loader`，也不得写入任何闪存分区。** 候选 helper 没有经过跨版本、跨 SoC、跨容量测试。

## 4. 用已知内容验证读取能力

测试设备 boot 起始 LBA 为 55296，大小为 33554432 字节。边界探针从 LBA 65536 读取 65536 字节，对应原厂 boot 内 `(65536 - 55296) × 512` 的偏移。跨边界探针逐字节一致后才继续全盘读取。

完整 eMMC 主用户区为 60620800 个 512 字节扇区，31037849600 字节（约 28.91 GiB）。备份包含 GPT、系统、恢复分区和 userdata；不含独立 eMMC 硬件 boot 区与 RPMB。个人备份和它的整盘哈希不公开。

## 5. 原机修补、只写 boot、完整回读

Magisk v31.1 APK 从上游正式 release 获取并校验。使用原机上执行的 arm64 工具修补该机原始 boot，设置：

```text
KEEPVERITY=true
KEEPFORCEENCRYPT=true
PATCHVBMETAFLAG=false
RECOVERYMODE=false
LEGACYSAR=false
```

修补后检查 boot v2 头、kernel、second、DTB、cmdline 保持一致，仅 ramdisk 内容发生所需变化。没有关闭 SELinux，没有刷 vbmeta，也没有变更 uboot、trust、waveform、GPT 或 system 镜像。写入 boot 后将整个 32 MiB boot 分区回读，大小与 SHA-256 都匹配。

## 6. root 存在与 Magisk 环境完整是两件事

本固件的普通 PATH 没有 `/debug_ramdisk`。初期 `/debug_ramdisk/su` 可用，但 `su` 命令不可用，所以增加了一个 systemless 模块，将已有客户端链接到 `/system/bin`。

还发现手动 boot 修补后 `/data/adb/magisk` 环境不完整，导致模块在下一次启动时未正确加载。使用**同一份已验证 APK**的完整 assets / arm64 文件，通过官方 `app_functions.sh` 的 `fix_env` 修复；`env_check 31.1 31100` 返回 0。之后重启，模块挂载与普通 `su` 均正常。

不能用“当前一次 `/debug_ramdisk/su` 成功”代替重启后检查完整启动日志、模块和普通 `su`。

Magisk v31.1 已移除临时弹出的 root 授权请求，需要先在超级用户页授予具体应用。上游说明见 [v31.1 release](https://github.com/topjohnwu/Magisk/releases/tag/v31.1)。

## 7. 汉王导航栏并非普通开关问题

本机 SystemUI 的 `StatusBar.createNavigationBar(...)` 是空方法。`qemu.hw.mainkeys=0` 与 stock three-button overlay 无法让它创建导航栏。测试这些开关后已撤回。

采用独立、可关闭的本地悬浮三键栏。另一个定制是 `KEYCODE_APP_SWITCH` 打开“已安装应用”，所以多任务按钮直接调用原有 `com.hanvon.recents/.MainActivity`。返回、主页、多任务均通过 Mac 投屏鼠标实际点击验证。没有发布反编译的厂商源码。
