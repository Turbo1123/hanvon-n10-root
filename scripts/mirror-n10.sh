#!/bin/sh
set -eu
: "${N10_EXPECT_USB_SERIAL:?Set this to your own N10 USB serial}"
exec scrcpy --serial="$N10_EXPECT_USB_SERIAL" \
  --window-title='Hanvon N10 - USB' \
  --video-codec=h264 --video-encoder=OMX.rk.video_encoder.avc \
  --max-size=1280 --max-fps=30 --video-bit-rate=8M --video-buffer=0 \
  --no-audio --stay-awake --window-height=900 "$@"
