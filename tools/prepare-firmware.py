"""Verify the exact official OTA and extract only the two required local inputs."""
import argparse
import json
from pathlib import Path
import zipfile
from context import sha256_file

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('ota', type=Path)
parser.add_argument('case_dir', type=Path)
args = parser.parse_args()
expected = 'c3d02e8342a1f14fc087467b78f4178ee85485327b6794485ecab86d21016c3b'
if sha256_file(args.ota) != expected:
    raise RuntimeError('OTA hash mismatch: this tool only supports the documented 12.42 / 1.02.49 OTA')
dest = args.case_dir / 'stock-firmware'
dest.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(args.ota) as archive:
    bad = archive.testzip()
    if bad:
        raise RuntimeError('ZIP CRC mismatch: ' + bad)
    for name in ('boot.img', 'RKLoader.bin'):
        if (dest / name).exists():
            raise RuntimeError('Refusing overwrite: ' + name)
    for name in ('boot.img', 'RKLoader.bin'):
        with (dest / name).open('xb') as stream:
            stream.write(archive.read(name))
print(json.dumps({'ota_sha256': expected, 'all_zip_crc_checked': True,
                  'extracted': ['boot.img', 'RKLoader.bin']}, indent=2))
