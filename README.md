# 汉王 N10 Root 研究与工具

记录一台 **汉王 N10、硬件 12.42、固件 1.02.49、Android 11 / RK3566** 的实机 root 过程，以及 USB 投屏和底部三键导航。

**2026-11-12 实机结果：Magisk 31.1 root 成功，重启后 `su -c id` 仍返回 `uid=0`，SELinux 保持 Enforcing。** root 流程中唯一写入的固件分区是 `boot`；写后完整回读与目标镜像一致。原始 eMMC 主用户区已备份并校验。其他 N10 硬件、容量、系统版本尚未验证。

这份研究利用的是该测试设备已经具备的解锁状态、Rockusb 下载模式和原机 boot 镜像，没有发现或提供新的漏洞。不要把本文当成所有 N10 的通用一键 root 包。

## 从哪里开始

| 内容 | 文档 |
| --- | --- |
| 完整流程、工具构建、备份、Magisk 修补、刷写 | [操作流程](docs/ROOT_GUIDE.zh-CN.md) |
| 32 MiB 读取限制、RAM helper 补丁、Magisk 环境问题 | [研究过程与关键判断](docs/RESEARCH.zh-CN.md) |
| 按键进入下载模式、只恢复原始 boot | [恢复说明](docs/RECOVERY.zh-CN.md) |
| 实际验证范围与未验证事项 | [验证记录](docs/TESTED.zh-CN.md) |
| Mac USB 低缓冲投屏 | [投屏说明](docs/MIRROR.zh-CN.md) |
| 可关闭的返回 / 主页 / 多任务悬浮栏 | [三键导航应用](navigation/README.md) |
| 公开内容与隐私边界 | [隐私说明](docs/PRIVACY.md) |
| 第三方工具、来源、许可证 | [第三方声明](THIRD_PARTY.md) |

## 为什么先备份

这台设备的原始 Rockusb loader 对 LBA `0x10000`（32 MiB）及以后读取返回 `0xCC` 占位数据，命令却可能报告成功。两次读出的文件大小相同、哈希相同，仍然可能都是无效备份。

我们从匹配的原厂 OTA 中取出 `RKLoader.bin`，确认 helper 的读取限制，**只修改载入 RAM 的读取 helper**，验证跨边界读取与原厂 boot 的同偏移内容一致后，才读取并验证完整 eMMC 主用户区。随后用原机 boot 修补 Magisk，只刷 `boot` 并完整回读。

官方 OTA 并非完整救砖包：它缺少独立 `recovery`、`trust`、`vbmeta`、`waveform` 等恢复镜像。eMMC 主用户区备份也不包含独立硬件 boot 区及 RPMB。**完整恢复写入尚未实际演练**，不能承诺所有故障都可恢复。

## 仓库里有什么

- 经过参数化的备份、镜像检查、boot 刷写 / 恢复 Python 工具。
- 固定原厂 loader 哈希、指令位置和输出哈希的离线 RAM helper 补丁工具。
- 实际使用的 rkdeveloptool 固定版本源码、macOS 构建修复及 USB 序列号保护补丁。
- 本地三键导航应用源码、Magisk 命令路径兼容模块文件及 scrcpy 启动脚本。
- 脱敏的型号、固件校验值和验证结论。

固件、原始 / 修补 boot、整机备份、设备序列号、私人截图、账号凭据和签名私钥均不在仓库及发行包中。下载官方文件的链接见 [固件校验清单](evidence/firmware.json)。

## 工具最小用法

需要 Python 3.9+。所有设备操作前，先阅读完整流程并在自己的终端设置自己的设备信息：

```sh
export N10_EXPECT_USB_SERIAL='YOUR_OWN_DEVICE_SERIAL'
export N10_CASE_DIR="$PWD/work/my-n10"
mkdir -p "$N10_CASE_DIR"
```

变量只写在本机终端；`work/` 已忽略，请勿提交自己的原始工作目录。刷写工具默认 dry run，只有显式 `--execute` 才会写 boot。它没有全盘擦除、刷 GPT 或更新持久 bootloader 的入口。

```sh
python3 -m unittest discover -s tests -v
sh scripts/build-rkdeveloptool.sh
python3 tools/flash-verified-boot.py root         # 本地前置检查；不访问设备
```

最初的设备专用脚本已在实机执行；公开版本移除了私人信息、补充了检查和默认 dry run，进行了离线验证，**没有为发布再次刷写设备**。详细区别见验证记录。

## 许可证

本项目新增代码和文档采用 MIT；rkdeveloptool 及其修改保留 GPL-2.0-or-later。Magisk、scrcpy 和厂商文件各自遵循上游许可，详见第三方声明。
