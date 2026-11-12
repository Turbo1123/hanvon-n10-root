"""Extract original Magisk assets for local reproduction; no APK is redistributed."""
import argparse
from pathlib import Path
import zipfile
from context import sha256_file

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('apk', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
if sha256_file(args.apk) != '89cefac0a318afa39fb3880c45c87b036c05bc1ebf02a7a715b7f8d7c26ac6e7':
    raise RuntimeError('APK does not match the tested official Magisk v31.1 release')
args.output.mkdir(parents=True, exist_ok=False)
with zipfile.ZipFile(args.apk) as archive:
    for item in archive.namelist():
        path = Path(item)
        if item.startswith('assets/') and not item.endswith('/'):
            name = str(path.relative_to('assets'))
        elif item.startswith('lib/arm64-v8a/lib') and item.endswith('.so'):
            name = path.name[3:-3]
        else:
            continue
        output = args.output / name
        if '..' in Path(name).parts:
            raise RuntimeError('Unexpected asset path')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(archive.read(item))
        output.chmod(0o755)
print('Extracted official assets and arm64 executables into a new private directory')
