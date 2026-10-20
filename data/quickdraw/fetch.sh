#!/usr/bin/env bash
# Fetch the Quick, Draw! slices the shot scripts read: the first 2,500,001 bytes of each
# simplified category file (the scripts drop the last, partial line). Same bytes every time.
# Quick, Draw! by Google Creative Lab, CC BY 4.0.
set -euo pipefail
cd "$(dirname "$0")"
for cat in "${@:-cloud bush grass giraffe tree dog}"; do
  for c in $cat; do
    url="https://storage.googleapis.com/quickdraw_dataset/full/simplified/${c// /%20}.ndjson"
    curl -sSf -r 0-2500000 "$url" -o "$c.part" && echo "$c.part $(wc -c < "$c.part") bytes"
  done
done
