"""Write only boot after verified backups; support a separately selected restore."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import time
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['root', 'restore'])
parser.add_argument('--execute', action='store_true', help='Write boot after all local preflight checks; default is dry run')
args = parser.parse_args()
action = args.action
from context import case_context, sha256_file
base, serial, rk = case_context()
backup = json.loads((base / 'device-backup/full-emmc-user-area.json').read_text())
if not (backup['serial'] == serial and backup['boot_matches_official_ota']):
    raise RuntimeError("Precondition failed: backup['serial'] == serial and backup['boot_matches_official_ota']")
if not backup['primary_and_backup_gpt_crc_verified']:
    raise RuntimeError("Precondition failed: backup['primary_and_backup_gpt_crc_verified']")
if not sha256_file(base / 'device-backup/full-emmc-user-area.img') == backup['sha256']:
    raise RuntimeError('Full backup changed')
if not (base / 'device-backup/full-emmc-user-area.img').stat().st_size == backup['bytes']:
    raise RuntimeError("Precondition failed: (base / 'device-backup/full-emmc-user-area.img').stat().st_size == backup['bytes']")
if action == 'root':
    recovery = json.loads((base / 'recovery-plan.json').read_text())
    if not recovery['hardware_button_entry_verified']:
        raise RuntimeError('Hardware recovery entry not verified')
    verification = json.loads((base / 'patched/patch-verification.json').read_text())
    image = Path(verification['flash_image'])
    expected = verification['flash_image_sha256']
else:
    image = base / 'device-backup/boot.img'
    expected = backup['boot_sha256']
if not image.stat().st_size == 33554432:
    raise RuntimeError('Precondition failed: image.stat().st_size == 33554432')
if not hashlib.sha256(image.read_bytes()).hexdigest() == expected:
    raise RuntimeError('Precondition failed: hashlib.sha256(image.read_bytes()).hexdigest() == expected')
if not args.execute:
    print(f'DRY RUN: validated {action} boot image {image.name}; no device access or writes. Add --execute to write boot.')
    raise SystemExit(0)
env = os.environ.copy()
env['N10_EXPECT_USB_SERIAL'] = serial
journal = base / 'flash-journal'
journal.mkdir(exist_ok=True)
stamp = f'{action}-{int(time.time())}'
rows = []

def run(args, timeout=45):
    result = subprocess.run([str(rk), *args], capture_output=True, text=True, timeout=timeout, env=env, cwd=base)
    rows.append({'args': args, 'exit': result.returncode, 'output': result.stdout + result.stderr})
    (journal / (stamp + '.json')).write_text(json.dumps(rows, indent=2) + '\n')
    if not result.returncode == 0:
        raise RuntimeError(f'Command failed: {args[0]}')
gpt = journal / (stamp + '-gpt.bin')
run(['read', '0', '17408', str(gpt)])
if not gpt.read_bytes() == (base / 'device-backup/first-32MiB.img').read_bytes()[:17408]:
    raise RuntimeError("Precondition failed: gpt.read_bytes() == (base / 'device-backup/first-32MiB.img').read_bytes()[:17408]")
probe = journal / (stamp + '-boundary-probe.bin')
run(['read', '65536', '65536', str(probe)])
boot_partition = next(part for part in backup['partitions'] if part['name'] == 'boot')
if (boot_partition['start_sector'], boot_partition['bytes']) != (55296, 33554432):
    raise RuntimeError('Unexpected boot layout')
offset = (65536 - boot_partition['start_sector']) * 512
official = (base / 'stock-firmware/boot.img').read_bytes()
if len(probe.read_bytes()) != 65536 or probe.read_bytes() != official[offset:offset + 65536]:
    raise RuntimeError('Current reader still restricted; refusing boot write')
print(f'Writing boot only ({action}); image SHA256 {expected}', flush=True)
run(['write-partition', 'boot', str(image)])
readback = journal / (stamp + '-readback.img')
run(['read-partition', 'boot', str(readback)])
actual = hashlib.sha256(readback.read_bytes()).hexdigest()
if not (actual == expected and readback.stat().st_size == image.stat().st_size):
    raise RuntimeError('Post-write readback mismatch')
rows.append({'boot_readback_sha256': actual, 'matches_written_image': True, 'only_persistent_partition_written': 'boot'})
(journal / (stamp + '.json')).write_text(json.dumps(rows, indent=2) + '\n')
print('Boot write verified by complete readback; rebooting normally.', flush=True)
run(['reboot'])
