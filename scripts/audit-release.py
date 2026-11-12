"""Audit tracked files without printing detected secret values. Run before publishing."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--forbid-file', type=Path, help='Private local newline-delimited values; never commit it')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
patterns = {
    'macOS user directory': rb'/Users/[A-Za-z0-9_.-]+/',
    'access token': rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-proj-[A-Za-z0-9_-]{20,})',
    'private key': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'unredacted device serial': rb'(?<!0x)(?<!0X)(?<![0-9A-Fa-f])[0-9]{16}(?![0-9A-Fa-f])',
}
private_values = []
if args.forbid_file:
    private_values = [line for line in args.forbid_file.read_bytes().splitlines() if line]
failures = []
for relative in filter(None, paths):
    path = root / relative
    if path.is_symlink():
        failures.append((relative, 'symlink is not allowed'))
        continue
    if path.suffix.lower() in {'.img', '.bin', '.apk', '.keystore', '.jks', '.pem', '.log', '.png', '.jpg'}:
        failures.append((relative, 'excluded raw/binary/private artifact'))
        continue
    data = path.read_bytes()
    for label, pattern in patterns.items():
        if re.search(pattern, data):
            failures.append((relative, label))
    if any(value in data for value in private_values):
        failures.append((relative, 'private denylist match'))
if failures:
    for path, reason in failures:
        print(f'REJECTED {path}: {reason}', file=sys.stderr)
    raise SystemExit(1)
print(f'PASS: {len(list(filter(None, paths)))} tracked files; no matched private values, raw artifacts or symlinks')
