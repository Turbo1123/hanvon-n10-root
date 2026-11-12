"""Capture the N10 eMMC user area using only guarded sector reads."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import struct
import subprocess
import time
import zlib
from context import case_context, sha256_file
base, serial, rk = case_context()
dest = base / 'device-backup'
dest.mkdir(parents=True, exist_ok=True)
total_sectors = 60620800
expected_bytes = total_sectors * 512
partial = dest / 'full-emmc-user-area.img.part'
final = dest / 'full-emmc-user-area.img'
manifest_file = dest / 'full-emmc-user-area.json'
if not not any((p.exists() for p in [partial, final, manifest_file, dest / 'boot.img', dest / 'recovery.img'])):
    raise RuntimeError('Refusing overwrite')
if not shutil.disk_usage(dest).free > expected_bytes + 10 * 1024 ** 3:
    raise RuntimeError('Precondition failed: shutil.disk_usage(dest).free > expected_bytes + 10 * 1024 ** 3')
verification = json.loads((base / 'unrestricted-reader-verification.json').read_text())
if not verification['probe_matches_official_boot_at_same_sector']:
    raise RuntimeError("Precondition failed: verification['probe_matches_official_boot_at_same_sector']")
env = os.environ.copy()
env['N10_EXPECT_USB_SERIAL'] = serial
start = last = time.monotonic()
print(f'Backing up {expected_bytes} bytes ({expected_bytes / 1024 ** 3:.2f} GiB); sector reads only.', flush=True)
log_path = dest / 'full-emmc-read.log'
with log_path.open('wb') as log:
    child = subprocess.Popen([str(rk), 'read', '0', str(expected_bytes), str(partial)], stdout=log, stderr=subprocess.STDOUT, cwd=base, env=env)
    while child.poll() is None:
        now = time.monotonic()
        if now - start > 2400:
            child.kill()
            child.wait()
            raise RuntimeError('Read timeout; incomplete backup retained as .part')
        if now - last >= 15:
            size = partial.stat().st_size if partial.exists() else 0
            speed = size / 1024 ** 2 / (now - start)
            eta = (expected_bytes - size) / (speed * 1024 ** 2) if speed else 0
            print(f'{size / expected_bytes:.1%}: {size / 1024 ** 3:.2f} GiB, {speed:.1f} MiB/s, estimated {eta / 60:.1f} min remaining', flush=True)
            last = now
        time.sleep(1)
if not child.returncode == 0:
    raise RuntimeError(f'Read failed with exit {child.returncode}')
if not partial.stat().st_size == expected_bytes:
    raise RuntimeError('Incomplete image')
log_text = log_path.read_text(errors='replace')
if not ('Read LBA to file (100%)' in log_text and 'failed' not in log_text.lower()):
    raise RuntimeError("Precondition failed: 'Read LBA to file (100%)' in log_text and 'failed' not in log_text.lower()")
print('All sectors received; hashing and checking for known filler.', flush=True)
digest = hashlib.sha256()
previous = b''
filler = b'\xcc' * 65536
with partial.open('rb') as stream:
    while (chunk := stream.read(8 * 1024 * 1024)):
        digest.update(chunk)
        if not filler not in previous + chunk:
            raise RuntimeError('Potential loader filler found; image not accepted')
        previous = chunk[-65535:]
with partial.open('rb') as stream:
    prefix = stream.read(33554432)
    if not prefix == (dest / 'first-32MiB.img').read_bytes():
        raise RuntimeError('Low region changed')
    header = bytearray(prefix[512:1024])
    if header[:8] != b'EFI PART':
        raise RuntimeError('Primary GPT signature mismatch')
    length = struct.unpack_from('<I', header, 12)[0]
    stored_crc = struct.unpack_from('<I', header, 16)[0]
    header[16:20] = bytes(4)
    if not zlib.crc32(header[:length]) == stored_crc:
        raise RuntimeError('Precondition failed: zlib.crc32(header[:length]) == stored_crc')
    entries_lba, entry_count, entry_size, entries_crc = struct.unpack_from('<QIII', prefix, 512 + 72)
    entries = prefix[entries_lba * 512:entries_lba * 512 + entry_count * entry_size]
    if not zlib.crc32(entries) == entries_crc:
        raise RuntimeError('Precondition failed: zlib.crc32(entries) == entries_crc')
    backup_lba = struct.unpack_from('<Q', prefix, 512 + 32)[0]
    stream.seek(backup_lba * 512)
    backup_header = bytearray(stream.read(512))
    if not backup_header[:8] == b'EFI PART':
        raise RuntimeError("Precondition failed: backup_header[:8] == b'EFI PART'")
    length = struct.unpack_from('<I', backup_header, 12)[0]
    stored_crc = struct.unpack_from('<I', backup_header, 16)[0]
    backup_header[16:20] = bytes(4)
    if not zlib.crc32(backup_header[:length]) == stored_crc:
        raise RuntimeError('Precondition failed: zlib.crc32(backup_header[:length]) == stored_crc')
    backup_entries_lba, backup_count, backup_size, backup_entries_crc = struct.unpack_from('<QIII', backup_header, 72)
    if (backup_count, backup_size, backup_entries_crc) != (entry_count, entry_size, entries_crc):
        raise RuntimeError('Backup GPT table metadata differs')
    stream.seek(backup_entries_lba * 512)
    backup_entries = stream.read(backup_count * backup_size)
    if backup_entries != entries or zlib.crc32(backup_entries) != backup_entries_crc:
        raise RuntimeError('Backup GPT table contents or CRC differ')
    partitions = []
    for index in range(entry_count):
        entry = entries[index * entry_size:(index + 1) * entry_size]
        if entry[:16] == bytes(16):
            continue
        first, last = struct.unpack_from('<QQ', entry, 32)
        name = entry[56:128].decode('utf-16le').rstrip('\x00')
        partitions.append({'name': name, 'start_sector': first, 'end_sector': last, 'bytes': (last - first + 1) * 512})
    boot = next((p for p in partitions if p['name'] == 'boot'))
    stream.seek(boot['start_sector'] * 512)
    boot_data = stream.read(boot['bytes'])
    stock_boot = (base / 'stock-firmware/boot.img').read_bytes()
    if not boot_data[:len(stock_boot)] == stock_boot:
        raise RuntimeError('Boot does not match official package')
    (dest / 'boot.img').write_bytes(boot_data)
    recovery = next((p for p in partitions if p['name'] == 'recovery'))
    stream.seek(recovery['start_sector'] * 512)
    recovery_data = stream.read(recovery['bytes'])
    if not recovery_data[:8] == b'ANDROID!':
        raise RuntimeError('Unexpected recovery image')
    (dest / 'recovery.img').write_bytes(recovery_data)
partial.rename(final)
result = {'serial': serial, 'file': str(final), 'bytes': expected_bytes, 'sha256': digest.hexdigest(), 'sector_count': total_sectors, 'scope': 'Complete eMMC user area including GPT, system partitions and userdata. Excludes separate eMMC boot hardware areas and RPMB.', 'primary_and_backup_gpt_crc_verified': True, 'no_64KiB_cc_filler_runs': True, 'first_32MiB_matches_independent_read': True, 'boot_matches_official_ota': True, 'boot_sha256': hashlib.sha256(boot_data).hexdigest(), 'recovery_sha256': hashlib.sha256(recovery_data).hexdigest(), 'elapsed_seconds': round(time.monotonic() - start, 1), 'partitions': partitions, 'partition_writes_performed': False}
manifest_file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print('VERIFIED BACKUP: ' + json.dumps({k: result[k] for k in ['file', 'bytes', 'sha256', 'elapsed_seconds']}), flush=True)
