#!/usr/bin/env bash
set -euo pipefail

PLATFORM="${1:-}"
if [ -z "$PLATFORM" ]; then
    echo "Usage: $0 {windows|linux|macos}"
    exit 1
fi

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m PyInstaller \
    --noconfirm \
    --clean \
    game.spec


mkdir -p releases


case "$PLATFORM" in

windows)
    cd dist

    python <<-'PY'
    import shutil

    shutil.make_archive(
        "../releases/one-lucid-night-windows",
        "zip",
        "one-lucid-night"
    )

    shutil.make_archive(
        "../releases/one-lucid-night-windows",
        "gztar",
        "one-lucid-night"
    )
PY

    cd ..
;;

linux)
    cd dist

    python - <<'PY'
    import shutil

    shutil.make_archive(
        "../releases/one-lucid-night-linux",
        "zip",
        "one-lucid-night"
    )

    shutil.make_archive(
        "../releases/one-lucid-night-linux",
        "gztar",
        "one-lucid-night"
    )
PY

cd ..

    cd ..
;;

macos)
    cd dist

    ditto \
        -c \
        -k \
        --keepParent \
        one-lucid-night \
        ../releases/one-lucid-night-macos.zip

    python - <<'PY'
    import shutil

    shutil.make_archive(
        "../releases/one-lucid-night-macos",
        "gztar",
        "one-lucid-night"
    )
PY
;;

*)

    echo "Unknown platform: $PLATFORM"
    exit 1

;;

esac

cd releases

if command -v sha256sum >/dev/null; then
    sha256sum *
else
    shasum -a 256 *
fi > SHA256SUMS.txt

cd ..