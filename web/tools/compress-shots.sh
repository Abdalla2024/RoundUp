#!/bin/bash
# Turns the redesign PNGs (screenshots/redesign/png, not committed) into small JPEGs for the repository (screenshots/redesign/after).
# Wider than 900 px is resampled to 900 px; narrower images are only converted. macOS (sips).
set -eu
cd "$(dirname "$0")/../screenshots/redesign"
rm -rf after; mkdir -p after
for f in png/*.png; do
  b=$(basename "$f" .png); w=$(sips -g pixelWidth "$f" | awk '/pixelWidth/{print $2}')
  if [ "$w" -gt 900 ]; then sips -s format jpeg -s formatOptions 58 --resampleWidth 900 "$f" --out "after/$b.jpg" >/dev/null 2>&1
  else sips -s format jpeg -s formatOptions 58 "$f" --out "after/$b.jpg" >/dev/null 2>&1; fi
done
echo "wrote $(ls after | wc -l) images, $(du -sh after | cut -f1)"
