#!/system/bin/sh
# Run as already-authorized root AFTER boot patching. Does not flash firmware.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Run with the already-working Magisk su'; exit 1; }
[ "$(getprop ro.product.hw.version)" = 12.42 ] || exit 1
[ "$(/debug_ramdisk/magisk -V)" = 31100 ] || exit 1
envdir=/data/local/tmp/n10-magisk-complete-env
[ -f "$envdir/app_functions.sh" ] || exit 1
grep -xq "MAGISK_VER_CODE=31100" "$envdir/util_functions.sh" || exit 1
for file in busybox magiskboot magiskinit magiskpolicy magisk main.jar; do
  [ -f "$envdir/$file" ] || exit 1
done
MAGISKBIN=/data/adb/magisk
. "$envdir/app_functions.sh"
# Upstream fix_env replaces the Magisk support environment and removes envdir.
# It must be a fresh assets-only directory, not the boot patch work directory.
fix_env "$envdir"
MAGISKTMP=$(/debug_ramdisk/magisk --path)
env_check 31.1 31100
echo 'Official Magisk environment check passed; no firmware partition written.'
