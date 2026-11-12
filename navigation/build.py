"""Build the local three-button app with a caller-owned signing key."""
from pathlib import Path
import os
import subprocess
import zipfile

root = Path(__file__).resolve().parent
sdk = Path(os.environ['ANDROID_HOME']).expanduser()
tools = sdk / 'build-tools' / os.environ.get('N10_BUILD_TOOLS', '35.0.1')
android = sdk / 'platforms' / os.environ.get('N10_ANDROID_PLATFORM', 'android-33') / 'android.jar'
key = Path(os.environ['N10_SIGNING_KEYSTORE']).expanduser()
alias = os.environ.get('N10_SIGNING_ALIAS', 'navigation')
# apksigner reads this environment variable; do not put a password in a command-line argument.
if not os.environ.get('N10_SIGNING_PASSWORD'):
    raise RuntimeError('Set N10_SIGNING_PASSWORD locally; never commit your signing key')
out = root.parent / 'dist/navigation'
(out / 'classes').mkdir(parents=True, exist_ok=True)
(out / 'dex').mkdir(exist_ok=True)


def run(args):
    subprocess.run([str(value) for value in args], check=True)


run(['javac', '--release', '8', '-cp', android, '-d', out / 'classes',
     *sorted((root / 'src').rglob('*.java'))])
run([tools / 'aapt2', 'link', '-I', android, '--manifest', root / 'AndroidManifest.xml',
     '-o', out / 'unsigned.apk'])
run([tools / 'd8', '--min-api', '23', '--lib', android, '--output', out / 'dex',
     *sorted((out / 'classes').rglob('*.class'))])
with zipfile.ZipFile(out / 'unsigned.apk', 'a', zipfile.ZIP_DEFLATED) as archive:
    archive.write(out / 'dex/classes.dex', 'classes.dex')
run([tools / 'zipalign', '-f', '4', out / 'unsigned.apk', out / 'aligned.apk'])
run([tools / 'apksigner', 'sign', '--ks', key, '--ks-key-alias', alias,
     '--ks-pass', 'env:N10_SIGNING_PASSWORD', '--key-pass', 'env:N10_SIGNING_PASSWORD',
     '--out', out / 'n10-navigation.apk', out / 'aligned.apk'])
run([tools / 'apksigner', 'verify', out / 'n10-navigation.apk'])
print('Built dist/navigation/n10-navigation.apk')
