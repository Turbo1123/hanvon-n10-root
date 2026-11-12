#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
command -v meson >/dev/null
command -v ninja >/dev/null
command -v pkg-config >/dev/null
meson setup "$repo/third_party/rkdeveloptool/build" "$repo/third_party/rkdeveloptool" -Dman-pages=disabled
meson compile -C "$repo/third_party/rkdeveloptool/build"
