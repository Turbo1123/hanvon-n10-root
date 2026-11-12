#!/system/bin/sh
# The actual Magisk clients remain at /debug_ramdisk on the tested N10.
mkdir -p "$MODPATH/system/bin"
ln -s /debug_ramdisk/su "$MODPATH/system/bin/su"
ln -s /debug_ramdisk/magisk "$MODPATH/system/bin/magisk"
set_perm_recursive "$MODPATH" 0 0 0755 0644
