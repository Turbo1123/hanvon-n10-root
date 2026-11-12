"""Check a boundary probe against known official boot content before a full read."""
import json
import struct
from context import case_context

base, serial, rk = case_context()
prefix = (base / 'device-backup/first-32MiB.img').read_bytes()
if len(prefix) != 33554432 or prefix[512:520] != b'EFI PART':
    raise RuntimeError('Missing independent first-32MiB GPT capture')
entries_lba, count, size = struct.unpack_from('<QII', prefix, 512 + 72)
if not (size >= 128 and 0 < count <= 4096 and (entries_lba * 512 + count * size) <= len(prefix)):
    raise RuntimeError('Unexpected GPT entry bounds')
boot = []
for index in range(count):
    entry = prefix[entries_lba * 512 + index * size:entries_lba * 512 + (index + 1) * size]
    if entry[:16] == bytes(16):
        continue
    if entry[56:128].decode('utf-16le').rstrip('\0') == 'boot':
        boot.append(struct.unpack_from('<QQ', entry, 32))
if boot != [(55296, 120831)]:
    raise RuntimeError('Boot partition differs from the only tested layout')
probe = (base / 'device-backup/boundary-probe.bin').read_bytes()
official = (base / 'stock-firmware/boot.img').read_bytes()
offset = (65536 - boot[0][0]) * 512
if len(probe) != 65536 or probe != official[offset:offset + len(probe)]:
    raise RuntimeError('Boundary probe differs from official boot; do not accept a backup')
record = {'probe_matches_official_boot_at_same_sector': True,
          'probe_sector': 65536, 'probe_bytes': 65536}
with (base / 'unrestricted-reader-verification.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print('Boundary probe matches independent official content')
