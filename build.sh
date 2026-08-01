#!/bin/bash

PLATFORM=$1
pip install --no-input pyinstaller numpy panda3d pillow pyvirtualcam requests

case "$PLATFORM" in
    windows)
        SEP=";"
        ;;
    linux|macos)
        SEP=":"
        ;;
    *)
        echo "Usage: build.sh [windows|linux|macos]"
        exit 1
        ;;
esac

DATA_PAIRS=(
    "models/conctus:models/conctus"
    "models/conctus.glb:models"
    "models/maime:models/maime"
    "models/maime.glb:models"
    "models/obeliskus:models/obeliskus"
    "models/obeliskus.glb:models"
    "models/player:models/player"
    "models/player.glb:models"
    "models/staticon:models/staticon"
    "models/staticon.glb:models"
    "models/conctus/animated.glb:models/conctus"
    "models/conctus/entity.blend1:models/conctus"
    "models/maime/animation.glb:models/maime"
    "models/maime/basic.fbx:models/maime"
    "models/maime/entity.blend1:models/maime"
    "models/obeliskus/entity.blend1:models/obeliskus"
    "models/player/idle.fbx:models/player"
    "models/player/player.blend1:models/player"
    "models/player/walk:models/player/walk"
    "models/staticon/animations.glb:models/staticon"
    "models/staticon/base.fbx:models/staticon"
    "models/staticon/staticon.blend1:models/staticon"
    "models/player/walk/backwards.fbx:models/player/walk"
    "models/player/walk/forwards.fbx:models/player/walk"
    "models/player/walk/left.fbx:models/player/walk"
    "models/player/walk/right.fbx:models/player/walk"
    "textures/crosshair.png:textures"
    "textures/crosshair_ring.png:textures"
    "textures/reloading:textures/reloading"
    "textures/shotgun.png:textures"
    "textures/shotgun_pump.png:textures"
    "textures/reloading/close_chamber.png:textures/reloading"
    "textures/reloading/continue.png:textures/reloading"
    "textures/reloading/get_bullet.png:textures/reloading"
    "textures/reloading/insert_bullet.png:textures/reloading"
    "audio/ambient.wav:audio"
    "audio/dialog_pop.mp3:audio"
    "audio/main_menu.wav:audio"
    "audio/runes:audio/runes"
    "audio/shotgun:audio/shotgun"
    "audio/spider:audio/spider"
    "audio/step.mp3:audio"
    "audio/runes/advancing_rune.mp3:audio/runes"
    "audio/shotgun/clink.mp3:audio/shotgun"
    "audio/shotgun/close_chamber.mp3:audio/shotgun"
    "audio/shotgun/empty_clink.mp3:audio/shotgun"
    "audio/shotgun/insert_bullet.mp3:audio/shotgun"
    "audio/shotgun/pump_back.mp3:audio/shotgun"
    "audio/shotgun/pump_forth.mp3:audio/shotgun"
    "audio/spider/death.mp3:audio/spider"
    "audio/spider/hit.mp3:audio/spider"
    "build.py:."
    "enemies.py:."
    "entities.py:."
    "imports.py:."
    "items.py:."
    "main.py:."
    "runes.py:."
    "util.py:."
    "waves.json:."
)

ADD_DATA_ARGS=()
for pair in "${DATA_PAIRS[@]}"; do

    arg="${pair/:/$SEP}"
    ADD_DATA_ARGS+=( --add-data="$arg" )
done

case "$PLATFORM" in
    windows)
        pyinstaller --noconfirm --onefile --noconsole \
            --name "one-lucid-night-windows" \
            "${ADD_DATA_ARGS[@]}" \
            --clean main.py
        ;;
    linux)
        pyinstaller --noconfirm --onefile --noconsole \
            --name "one-lucid-night-linux" \
            "${ADD_DATA_ARGS[@]}" \
            --noupx \
            --clean main.py
        ;;
    macos)
        pyinstaller --noconfirm --onefile --noconsole \
            --name "one-lucid-night-macos" \
            "${ADD_DATA_ARGS[@]}" \
            --clean main.py
        ;;
esac