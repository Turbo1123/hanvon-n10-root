# rkdeveloptool changes

The vendored source already includes `rkdeveloptool-macos-target-guard.patch` applied to upstream commit `e7794bbdc28311b706f6298fd4de30ac17981a0b` from <https://github.com/DorianRudolph/rkdeveloptool>.

The patch adds an optional expected USB serial check before claiming a device interface, and limits Linux udev dependency/rules installation to Linux builds. The serial check is active when `N10_EXPECT_USB_SERIAL` is set. It does not authenticate a serial-less MaskROM device; physical-port and single-device checks remain manual prerequisites for RAM download.

These modifications to rkdeveloptool are distributed under GPL-2.0-or-later, consistent with its source headers. See `LICENSES/GPL-2.0.txt` and preserved upstream notices. Do not apply the patch a second time to this vendored tree.
