#!/usr/bin/env bash
set -e

PLATFORM=$1

python -m pip install --upgrade pip
pip install -r requirements.txt

pyinstaller \
    --noconfirm \
    --clean \
    game.spec


mkdir -p releases


case "$PLATFORM" in

windows)
    cd dist

    zip -r \
        ../releases/one-lucid-night-windows.zip \
        one-lucid-night

    tar -czf \
        ../releases/one-lucid-night-windows.tar.gz \
        one-lucid-night

    cd ..
;;

linux)
    cd dist

    zip -r \
        ../releases/one-lucid-night-linux.zip \
        one-lucid-night

    tar -czf \
        ../releases/one-lucid-night-linux.tar.gz \
        one-lucid-night

    cd ..
;;

macos)
    ditto \
        -c \
        -k \
        --keepParent \
        dist/one-lucid-night.app \
        releases/one-lucid-night-macos.zip

    tar -czf \
        releases/one-lucid-night-macos.tar.gz \
        -C dist \
        one-lucid-night.app
;;

*)

    echo "Unknown platform: $PLATFORM"
    exit 1

;;

esac

cd releases
sha256sum * > SHA256SUMS.txt
cd ..