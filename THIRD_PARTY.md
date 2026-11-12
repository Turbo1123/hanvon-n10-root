# Third-party sources and redistribution

The root method builds on existing work; it is not a new bootloader exploit.

| Component | Source/version used | License/distribution here |
| --- | --- | --- |
| rkdeveloptool | [DorianRudolph/rkdeveloptool](https://github.com/DorianRudolph/rkdeveloptool), commit `e7794bbdc28311b706f6298fd4de30ac17981a0b` | GPL-2.0-or-later source headers; complete tracked source is vendored under `third_party/rkdeveloptool`, including upstream `license.txt`. Two local changes are recorded in `patches/`. |
| Magisk | [topjohnwu/Magisk v31.1](https://github.com/topjohnwu/Magisk/releases/tag/v31.1) | GPL-3.0; obtain the APK from upstream. No Magisk APK, native library, or Magisk script is redistributed here. |
| scrcpy | [Genymobile/scrcpy](https://github.com/Genymobile/scrcpy), tested 4.1 | Apache-2.0; install separately. Only a launcher invoking the installed copy is included. |
| libusb, Meson, Ninja, pkg-config | Build dependencies of rkdeveloptool | Install separately; no dependency binaries bundled. |
| Hanvon OTA / RKLoader / boot images | Official vendor update endpoints in `evidence/firmware.json` | Vendor binaries are not redistributed. Download the matching original file yourself and verify the recorded hashes. |
| Android SDK tools / framework APIs | Android platform build tools | Install separately; no SDK or vendor APK code is bundled. |

New Python, shell and navigation application code and documentation are covered by the root MIT license. The rkdeveloptool source and the patch to that source retain GPL-2.0-or-later terms; the root MIT license does not relicense them. Upstream Rockchip and contributor notices are preserved.

Decompilation was used locally to understand the device. Decompilers, decompiled vendor framework classes, firmware, stock applications and personal screenshots are not included.
