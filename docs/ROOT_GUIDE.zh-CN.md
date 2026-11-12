# 操作流程：先恢复条件，再 root

本文对应一个已完成的实验，包含手动验证步骤。公开工具是参数化后的研究工具，不能替代操作者判断。不要跳过实际原始备份、物理恢复入口或回读验证。

## 0. 确认适用范围

只验证 N10 / 硬件 12.42 / 固件 1.02.49 / Android 11 / RK3566 / eMMC 主用户区 60620800 扇区。测试设备在开始前 `ro.boot.flash.locked=0`，verified boot 为 orange。仍锁定、硬件不同、固件不同或分区不同的设备应停止在研究阶段。

USB 调试需在平板设置中开启，并在原机屏幕允许自己的电脑。这个授权不能由投屏绕过。连接后在本机终端设置 **自己的**序列号：

```sh
adb devices -l
export N10_EXPECT_USB_SERIAL='YOUR_OWN_DEVICE_SERIAL'
export N10_CASE_DIR="$PWD/work/my-n10"
mkdir -p "$N10_CASE_DIR/device-backup" "$N10_CASE_DIR/patched"
adb -s "$N10_EXPECT_USB_SERIAL" shell getprop ro.product.hw.version
adb -s "$N10_EXPECT_USB_SERIAL" shell getprop ro.product.sw.version
adb -s "$N10_EXPECT_USB_SERIAL" shell getprop ro.build.fingerprint
adb -s "$N10_EXPECT_USB_SERIAL" shell getprop ro.boot.flash.locked
```

确保没有其他软件或聊天在同时重启、刷写同一设备。断开其他 Rockchip 下载设备。

## 1. 取得并验证原厂文件

对应的[官方 OTA 地址](https://cdn.os.zyeink.hwebook.cn/soft/xys/12.42/1.02.49/update.12.42.zip)和[更新配置](https://note.api.hwebook.cn/sysupdate/update.xml)来自厂商。原厂文件不随仓库分发。下载后执行：

```sh
python3 tools/prepare-firmware.py /path/to/update.12.42.zip "$N10_CASE_DIR"
```

工具固定验证这次实验使用的 OTA SHA-256 和所有 ZIP 条目 CRC，再提取 `boot.img`、`RKLoader.bin` 到私有目录。文件不匹配会拒绝继续。

固件清单见 [firmware.json](../evidence/firmware.json)。OTA 不含所有救援分区，不是通用原厂整机刷机包。

## 2. 构建带目标检查的 rkdeveloptool

macOS 可从 Homebrew 安装 `libusb`、`pkg-config`、`meson`、`ninja`；Linux 还需要 libusb 开发文件。仓库已经包含固定版本及补丁，无需再次应用补丁文件。

```sh
sh scripts/build-rkdeveloptool.sh
export N10_RKDEVELOPTOOL="$PWD/third_party/rkdeveloptool/build/rkdeveloptool"
```

序列号保护在设置 `N10_EXPECT_USB_SERIAL` 时生效，不是上游所有命令的强制策略。正常 Loader 和 RAM reader 阶段都应设置该变量。不要换用同名但不同命令格式的 Rockchip 工具。

这里 `read` 的参数是 **起始扇区、字节数、文件名**，不是两个扇区数：

```text
rkdeveloptool read START-SECTOR NUM-BYTES FILENAME
```

## 3. 实际验证物理恢复入口

按[恢复说明](RECOVERY.zh-CN.md)先完成一次从关机开始、用圆形返回键 + 电源键进入下载模式的实测，检查主机 USB 枚举。不要仅用 `adb reboot loader` 代替物理入口验证。

确认后在私有 case 目录建立 `recovery-plan.json`，只在实际成功后把布尔值设为 true：

```json
{"hardware_button_entry_verified": true}
```

确认 `list` 中只有自己的设备、序列号正确，保存独立低地址读取：

```sh
"$N10_RKDEVELOPTOOL" list
"$N10_RKDEVELOPTOOL" read-flash-info
"$N10_RKDEVELOPTOOL" list-partitions
"$N10_RKDEVELOPTOOL" read 0 33554432 "$N10_CASE_DIR/device-backup/first-32MiB.img"
```

实测固件里，超过 32 MiB 的读可能是 `0xCC`。此时不要直接把 read-partition 的输出当作恢复镜像。

## 4. 离线生成严格匹配的 RAM reader

```sh
python3 tools/patch-ram-reader.py \
  "$N10_CASE_DIR/stock-firmware/RKLoader.bin" \
  "$N10_CASE_DIR/RKLoader-read-unlimited-RAM-ONLY.bin"
```

工具验证源文件、helper、相关指令、原包 CRC 和固定输出 SHA-256。任何版本差异都拒绝。它只处理本地文件，**不得将输出写入闪存或使用 upgrade-loader**。

在匹配的普通 Loader 下执行 `reboot-maskrom`，随后重新观察 USB 枚举，确认新出现的是唯一的 Rockchip MaskROM、并位于刚才的同一物理 USB 端口。MaskROM 通常没有序列号；只有在这个身份检查完成后，才允许单次不带序列号检查的 RAM 下载：

```sh
"$N10_RKDEVELOPTOOL" reboot-maskrom
# 人工确认唯一 MaskROM 设备、同一物理 USB 端口后，再执行下一条。
env -u N10_EXPECT_USB_SERIAL "$N10_RKDEVELOPTOOL" boot \
  "$N10_CASE_DIR/RKLoader-read-unlimited-RAM-ONLY.bin"
```

RAM reader 重新枚举后，确认序列号恢复为自己的设备。不要全局 unset 序列号变量。

## 5. 跨边界对照后备份

```sh
"$N10_RKDEVELOPTOOL" list
"$N10_RKDEVELOPTOOL" read 65536 65536 "$N10_CASE_DIR/device-backup/boundary-probe.bin"
python3 tools/verify-reader.py
python3 tools/backup-emmc.py
```

`verify-reader.py` 检查已知 GPT boot 位置，并把边界内容与原厂 boot 的同偏移内容逐字节比较。全备份工具只读设备，检查主用户区大小、SHA-256、占位数据、独立低地址内容、主 / 备 GPT 头及表 CRC、原厂 boot 对照、recovery 镜像头，成功后提取完整原始 boot / recovery。公开版增加了备份 GPT 表内容检查。

需要至少约 40 GiB 空闲磁盘。得到的 `device-backup/` 含个人数据，放到第二个可靠介质保存；不要上传到 GitHub。备份范围不含独立 eMMC boot 硬件区与 RPMB。

若已有 `.part` 或旧输出，工具拒绝覆盖。失败输出应隔离分析，不应改名冒充有效备份。

## 6. 回系统，在原机修补 boot

先正常重启回系统：

```sh
"$N10_RKDEVELOPTOOL" reboot
adb -s "$N10_EXPECT_USB_SERIAL" wait-for-device
```

从 [Magisk v31.1 官方 release](https://github.com/topjohnwu/Magisk/releases/tag/v31.1)下载 APK。用工具验证固定 SHA-256 并提取完整 assets 和 arm64 工具；不使用别人的 patched boot。

```sh
python3 tools/extract-magisk.py /path/to/Magisk-v31.1.apk "$N10_CASE_DIR/magisk-assets"
adb -s "$N10_EXPECT_USB_SERIAL" install -r /path/to/Magisk-v31.1.apk
adb -s "$N10_EXPECT_USB_SERIAL" shell mkdir -p /data/local/tmp/n10-magisk-patch
adb -s "$N10_EXPECT_USB_SERIAL" push "$N10_CASE_DIR/magisk-assets/." /data/local/tmp/n10-magisk-patch/
adb -s "$N10_EXPECT_USB_SERIAL" push "$N10_CASE_DIR/device-backup/boot.img" /data/local/tmp/n10-magisk-patch/boot.img
adb -s "$N10_EXPECT_USB_SERIAL" shell 'cd /data/local/tmp/n10-magisk-patch && chmod 755 busybox magisk magiskinit magiskboot init-ld && BOOTMODE=true KEEPVERITY=true KEEPFORCEENCRYPT=true PATCHVBMETAFLAG=false RECOVERYMODE=false LEGACYSAR=false ASH_STANDALONE=1 ./busybox sh ./boot_patch.sh boot.img'
adb -s "$N10_EXPECT_USB_SERIAL" pull /data/local/tmp/n10-magisk-patch/new-boot.img "$N10_CASE_DIR/patched/new-boot.img"
python3 tools/verify-boot-patch.py
```

工具验证 kernel、second、DTB、cmdline 等保留，ramdisk 已变化，并准备完整分区大小的刷写镜像。它不会写设备。

## 7. 只写 boot 并完整回读

通过 ADB 回到普通 Loader，然后重复第 4 节的 MaskROM 身份检查和 RAM reader 下载。RAM reader 重新出现后，再做一次边界探针对照；不要把重启前临时 reader 的状态沿用到重启后。

```sh
adb -s "$N10_EXPECT_USB_SERIAL" reboot loader
# 重复第 4 节的临时 RAM reader 下载和身份确认。
python3 tools/flash-verified-boot.py root
```

默认仅做本地前置检查，会重新校验个人整机备份哈希、原始身份信息和待写 boot，不访问设备。

确认现场状态后，真正写入需要显式参数：

```sh
python3 tools/flash-verified-boot.py root --execute
```

写入模式先读取并对照现场 GPT，只调用 `write-partition boot`；然后完整回读 boot，大小与 SHA-256 匹配才重启。请不要自行加入 erase、刷 GPT、持久 loader 更新或其他分区写入。

## 8. 完整配置 Magisk，再验证重启

打开 Magisk，先在“超级用户”页允许 Shell / `com.android.shell`。v31.1 不再弹临时授权窗口。检查：

```sh
adb -s "$N10_EXPECT_USB_SERIAL" shell /debug_ramdisk/su -c id
```

如果手动修补后 Magisk 支持环境不完整，本次实验用同一份 APK 的完整 assets 通过官方 `fix_env` 修复。使用新的、只含工具的目录，不要把含原始 boot 的修补工作目录交给 `fix_env`，因为它会替换支持环境并删除来源目录：

```sh
adb -s "$N10_EXPECT_USB_SERIAL" shell mkdir -p /data/local/tmp/n10-magisk-complete-env
adb -s "$N10_EXPECT_USB_SERIAL" push "$N10_CASE_DIR/magisk-assets/." /data/local/tmp/n10-magisk-complete-env/
adb -s "$N10_EXPECT_USB_SERIAL" push tools/finish-magisk-env.sh /data/local/tmp/n10-finish-magisk-env.sh
adb -s "$N10_EXPECT_USB_SERIAL" shell chmod 755 /data/local/tmp/n10-finish-magisk-env.sh
adb -s "$N10_EXPECT_USB_SERIAL" shell /debug_ramdisk/su -c /data/local/tmp/n10-finish-magisk-env.sh
```

本机普通 PATH 缺少 `/debug_ramdisk`，可手动放入兼容模块文件并生成链接：

```sh
adb -s "$N10_EXPECT_USB_SERIAL" push modules/n10_root_path/module.prop /data/local/tmp/n10-module.prop
adb -s "$N10_EXPECT_USB_SERIAL" shell '/debug_ramdisk/su -c "mkdir -p /data/adb/modules/n10_root_path/system/bin; cp /data/local/tmp/n10-module.prop /data/adb/modules/n10_root_path/module.prop; chmod 644 /data/adb/modules/n10_root_path/module.prop; ln -sf /debug_ramdisk/su /data/adb/modules/n10_root_path/system/bin/su; ln -sf /debug_ramdisk/magisk /data/adb/modules/n10_root_path/system/bin/magisk"'
adb -s "$N10_EXPECT_USB_SERIAL" reboot
```

等系统完整启动后重新检查：

```sh
adb -s "$N10_EXPECT_USB_SERIAL" shell getprop sys.boot_completed
adb -s "$N10_EXPECT_USB_SERIAL" shell command -v su
adb -s "$N10_EXPECT_USB_SERIAL" shell su -c id
adb -s "$N10_EXPECT_USB_SERIAL" shell 'su -c "magisk -v"'
adb -s "$N10_EXPECT_USB_SERIAL" shell getenforce
adb -s "$N10_EXPECT_USB_SERIAL" shell 'su -c "cat /cache/magisk.log"'
```

接受条件：`sys.boot_completed=1`、普通 su 返回 uid 0、Magisk 版本正确、SELinux Enforcing，启动日志没有环境不完整错误，兼容模块正常加载。记录自己的本机证据，不要公开带身份信息的原始日志。
