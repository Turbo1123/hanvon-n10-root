"""Package only committed source plus the explicitly built navigation APK."""
from pathlib import Path
import hashlib
import io
import subprocess
import zipfile

repo = Path(__file__).resolve().parents[1]
subprocess.run(['git', '-C', str(repo), 'diff', '--exit-code', 'HEAD'], check=True)
out = repo / 'dist'
apk = out / 'navigation/n10-navigation.apk'
if not apk.is_file():
    raise RuntimeError('Build the navigation APK first')
source = subprocess.check_output(['git', '-C', str(repo), 'archive', '--format=zip', 'HEAD'])
bundle = out / 'hanvon-n10-root-tools-v0.1.0.zip'
release_apk = out / 'n10-navigation-v0.1.0.apk'
release_apk.write_bytes(apk.read_bytes())
with zipfile.ZipFile(io.BytesIO(source)) as committed, zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
    for item in committed.infolist():
        archive.writestr('hanvon-n10-root/' + item.filename, committed.read(item.filename))
    archive.write(apk, 'hanvon-n10-root/extras/n10-navigation.apk')
    archive.writestr('hanvon-n10-root/extras/README.txt',
                     'This APK is built from navigation/. Requires Android 11+, root authorization and overlay permission.\n'
                     'Firmware, RAM helper binaries, device backups, private logs and signing keys are not included.\n'
                     'Build rkdeveloptool from the included GPL source; install Magisk and scrcpy from upstream.\n')
checksums = out / 'SHA256SUMS.txt'
checksums.write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n'
                             for path in [bundle, release_apk]))
print('Packaged committed source, navigation APK and SHA256SUMS in dist/')
