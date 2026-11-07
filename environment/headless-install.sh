#!/bin/sh
# Debian 13 x86_64 cloud/container runner. No private inputs are downloaded.
set -eu
cd "$(dirname "$0")/.."
test "$(uname -m)" = x86_64 || { echo 'Requires Linux x86_64'; exit 1; }
. /etc/os-release
test "$ID" = debian && test "$VERSION_ID" = 13 || { echo 'Requires Debian 13'; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates python3 \
    fs-uae xvfb xauth libgl1-mesa-dri libglx-mesa0 libsdl2-2.0-0 \
    libopenal1 libicu76 libatomic1 libstdc++6 libfontconfig1 \
    binutils-m68k-linux-gnu gcc-m68k-linux-gnu
python3 tools/setup_mesen.py
mkdir -p build/headless
dpkg-query -W > build/headless/installed-packages.txt
