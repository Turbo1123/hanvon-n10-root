import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reader_patch', ROOT / 'tools/patch-ram-reader.py')
reader_patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader_patch)


class ReaderGuards(unittest.TestCase):
    def test_unknown_loader_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown loader'):
            reader_patch.patch(bytes(428480))


class BootGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.case = Path(self.temp.name)
        for name in ['device-backup', 'patched', 'stock-firmware']:
            (self.case / name).mkdir()
        image = bytearray(33554432)
        image[:8] = b'ANDROID!'
        struct.pack_into('<10I', image, 8, 4096, 0, 1024, 0, 512, 0, 0, 2048, 2, 0)
        struct.pack_into('<I', image, 1644, 1660)
        struct.pack_into('<I', image, 1648, 32)
        image[64:68] = b'test'
        image[2048:6144] = b'K' * 4096
        image[6144:7168] = b'R' * 1024
        image[8192:8704] = b'S' * 512
        image[10240:10272] = b'D' * 32
        self.original = bytes(image)
        image[6144] ^= 1
        self.candidate = bytes(image)
        (self.case / 'device-backup/boot.img').write_bytes(self.original)
        (self.case / 'patched/new-boot.img').write_bytes(self.candidate)
        (self.case / 'device-backup/full-emmc-user-area.img').write_bytes(b'unit-test-fixture')
        self.backup = {
            'serial': 'TEST_N10', 'boot_sha256': hashlib.sha256(self.original).hexdigest(),
            'boot_matches_official_ota': True, 'primary_and_backup_gpt_crc_verified': True,
            'sha256': hashlib.sha256(b'unit-test-fixture').hexdigest(), 'bytes': 17,
            'partitions': [{'name': 'boot', 'start_sector': 55296, 'bytes': 33554432}],
        }
        self.backup['bytes'] = len(b'unit-test-fixture')
        (self.case / 'device-backup/full-emmc-user-area.json').write_text(json.dumps(self.backup))
        (self.case / 'device-backup/first-32MiB.img').write_bytes(b'G' * 17408)
        (self.case / 'stock-firmware/boot.img').write_bytes(self.original)
        (self.case / 'recovery-plan.json').write_text('{"hardware_button_entry_verified":true}')
        self.env = dict(os.environ, N10_EXPECT_USB_SERIAL='TEST_N10', N10_CASE_DIR=str(self.case))

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, tool, *args, optimized=False):
        return subprocess.run([sys.executable, *(['-O'] if optimized else []),
                               str(ROOT / 'tools' / tool), *args],
                              env=self.env, capture_output=True, text=True)

    def test_ramdisk_only_patch_accepted(self):
        result = self.invoke('verify-boot-patch.py')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.case / 'patched/boot-for-flash.img').read_bytes(), self.candidate)

    def test_kernel_mutation_rejected_even_with_python_optimized(self):
        altered = bytearray(self.candidate)
        altered[2048] ^= 1
        (self.case / 'patched/new-boot.img').write_bytes(altered)
        result = self.invoke('verify-boot-patch.py', optimized=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unexpected change to kernel', result.stderr)
        self.assertFalse((self.case / 'patched/boot-for-flash.img').exists())

    def test_missing_serial_rejected(self):
        self.env.pop('N10_EXPECT_USB_SERIAL')
        result = self.invoke('verify-boot-patch.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Set N10_EXPECT_USB_SERIAL', result.stderr)

    def test_default_dry_run_does_not_launch_usb_tool(self):
        self.assertEqual(self.invoke('verify-boot-patch.py').returncode, 0)
        self.env['N10_RKDEVELOPTOOL'] = str(self.case / 'must-not-exist')
        result = self.invoke('flash-verified-boot.py', 'root')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('DRY RUN', result.stdout)
        self.assertFalse((self.case / 'flash-journal').exists())

    def test_restricted_reader_aborts_before_write(self):
        self.assertEqual(self.invoke('verify-boot-patch.py').returncode, 0)
        fake = self.case / 'fake-rk'
        fake.write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
args=sys.argv[1:]
base=Path(os.environ['N10_CASE_DIR'])
if args[:3]==['read','0','17408']:
    Path(args[3]).write_bytes(b'G'*17408)
elif args[:3]==['read','65536','65536']:
    Path(args[3]).write_bytes(b'\\xcc'*65536)
else:
    (base/'unexpected-device-mutation').write_text(repr(args))
    sys.exit(9)
''')
        fake.chmod(0o755)
        self.env['N10_RKDEVELOPTOOL'] = str(fake)
        result = self.invoke('flash-verified-boot.py', 'root', '--execute', optimized=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Current reader still restricted', result.stderr)
        self.assertFalse((self.case / 'unexpected-device-mutation').exists())


if __name__ == '__main__':
    unittest.main()
