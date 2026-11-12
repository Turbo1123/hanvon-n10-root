"""Reproduce the exact, hash-locked read-limit change. Offline operation only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

SOURCE_SHA256 = '75fa0a96d16d9afb1aee35bb51fee33d1a2ff9106dcca43151e30bbf10c53902'
HELPER_SHA256 = 'c8e9bc964634ba9aae2d5d7bb762a3139105e0387eabf751e59ea1e66e84ed80'
OUTPUT_SHA256 = 'd7c5e4cc07f21ecb0910b3943ffff0d21f8f312a582bcdfef9c3346e69dc6df2'
HELPER_OFFSET, HELPER_SIZE = 49596, 100352


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rockchip_crc(payload):
    """Rockchip loader package CRC, not the standard CRC-32 polynomial."""
    value = 0
    for byte in payload:
        value ^= byte << 24
        for _ in range(8):
            value = ((value << 1) ^ (0x04C10DB7 if value & 0x80000000 else 0)) & 0xFFFFFFFF
    return value


def patch(data):
    require(hashlib.sha256(data).hexdigest() == SOURCE_SHA256, 'Unknown loader: refusing patch')
    helper = data[HELPER_OFFSET:HELPER_OFFSET + HELPER_SIZE]
    require(hashlib.sha256(helper).hexdigest() == HELPER_SHA256, 'Helper hash mismatch')
    require(struct.unpack_from('<QQQ', helper, 0x360) == (0x800, 0x03001000, 0x03018D10),
            'Unexpected helper relocation header')
    # Initialization and both normal/pipelined readers share RAM threshold 0x0334d604.
    instructions = {
        0x991C: '081a00f0', 0x9924: 'e9031032', 0x9938: '090506b9',
        0xA170: '290546b9', 0xA174: '1f01096b', 0xA178: '02030054',
        0xA1E0: '81198052', 0xA26C: '290546b9', 0xA270: '1f01096b',
        0xA274: 'c2000054', 0xA290: '81198052',
    }
    for offset, expected in instructions.items():
        require(helper[offset:offset + 4].hex() == expected, f'Unexpected instruction at {offset:#x}')
    require(rockchip_crc(data[:-4]) == struct.unpack_from('<I', data, len(data) - 4)[0],
            'Original package CRC mismatch')
    result = bytearray(data)
    offset = HELPER_OFFSET + 0x9924
    # mov w9, #0x10000 -> mov w9, #-1; all other executable bytes preserved.
    result[offset:offset + 4] = bytes.fromhex('09008012')
    struct.pack_into('<I', result, len(result) - 4, rockchip_crc(result[:-4]))
    changed = [i for i, (a, b) in enumerate(zip(data, result)) if a != b]
    require(set(changed) <= set(range(offset, offset + 4)) | set(range(len(data) - 4, len(data))),
            'Change outside instruction/package CRC')
    require(hashlib.sha256(result).hexdigest() == OUTPUT_SHA256, 'Unexpected result hash')
    return bytes(result), changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    manifest = args.output.with_suffix('.json')
    require(not args.output.exists() and not manifest.exists(), 'Refusing overwrite')
    result, changed = patch(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(result)
    record = {'source_sha256': SOURCE_SHA256, 'output_sha256': OUTPUT_SHA256,
              'changed_file_offsets': changed, 'source_crc_verified': True,
              'use': 'RAM download only; never flash or use upgrade-loader',
              'persistent_firmware_changes': False}
    with manifest.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
