"""Validate the on-device Magisk result and prepare a full-size boot image."""
from pathlib import Path
import hashlib
import json
import struct
from context import case_context, sha256_file
base, serial, rk = case_context()
original = (base / 'device-backup/boot.img').read_bytes()
candidate = (base / 'patched/new-boot.img').read_bytes()
backup = json.loads((base / 'device-backup/full-emmc-user-area.json').read_text())
if not hashlib.sha256(original).hexdigest() == backup['boot_sha256']:
    raise RuntimeError("Precondition failed: hashlib.sha256(original).hexdigest() == backup['boot_sha256']")
if not 0 < len(candidate) <= len(original) == 33554432:
    raise RuntimeError('Precondition failed: 0 < len(candidate) <= len(original) == 33554432')

def parse(data):
    if not data[:8] == b'ANDROID!':
        raise RuntimeError("Precondition failed: data[:8] == b'ANDROID!'")
    values = struct.unpack_from('<10I', data, 8)
    page = values[7]
    if not (values[8] == 2 and page == 2048):
        raise RuntimeError('Precondition failed: values[8] == 2 and page == 2048')
    result = {'fields': values, 'cmdline': data[48:576] + data[608:1632]}
    offset = page
    sizes = [('kernel', values[0]), ('ramdisk', values[2]), ('second', values[4]), ('recovery_dtbo', struct.unpack_from('<I', data, 1632)[0]), ('dtb', struct.unpack_from('<I', data, 1648)[0])]
    for name, size in sizes:
        if not offset + size <= len(data):
            raise RuntimeError('Precondition failed: offset + size <= len(data)')
        result[name] = hashlib.sha256(data[offset:offset + size]).hexdigest()
        offset += (size + page - 1) // page * page
    return result
a, b = (parse(original), parse(candidate))
for index in [0, 1, 3, 4, 5, 6, 7, 8, 9]:
    if not a['fields'][index] == b['fields'][index]:
        raise RuntimeError(f'Unexpected header change: {index}')
if not a['cmdline'] == b['cmdline']:
    raise RuntimeError("Precondition failed: a['cmdline'] == b['cmdline']")
for region in ['kernel', 'second', 'recovery_dtbo', 'dtb']:
    if not a[region] == b[region]:
        raise RuntimeError(f'Unexpected change to {region}')
if not a['ramdisk'] != b['ramdisk']:
    raise RuntimeError('Ramdisk was not patched')
full = bytearray(original)
full[:len(candidate)] = candidate
target = base / 'patched/boot-for-flash.img'
if not not target.exists():
    raise RuntimeError('Precondition failed: not target.exists()')
target.write_bytes(full)
result = {'serial': serial, 'original_boot_sha256': backup['boot_sha256'], 'patched_sha256': hashlib.sha256(candidate).hexdigest(), 'flash_image': str(target), 'flash_image_sha256': hashlib.sha256(full).hexdigest(), 'flash_image_bytes': len(full), 'only_ramdisk_changed': True, 'kernel_second_dtb_and_cmdline_preserved': True, 'keepverity': True, 'keepforceencrypt': True, 'patchvbmetaflag': False}
(base / 'patched/patch-verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
