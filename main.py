import sys

print("frozen execution:", getattr(sys, 'frozen', False))
if getattr(sys, 'frozen', False) and len(sys.argv) == 3 and sys.argv[1] == "--loggingName":
    sys.stdout = open(sys.argv[2]+".txt", "w")

from ursina import *

if getattr(sys, 'frozen', False):
    if hasattr(window, "fps_counter"):
        window.fps_counter.enabled = False
    if hasattr(window, "entity_counter"):
        window.entity_counter.enabled = False
    application.asset_folder = (Path(sys._MEIPASS) / "assets").absolute()
else:
    application.asset_folder = (Path(__file__).parent  / "assets").absolute()

print("assets located at:", application.asset_folder)

from entities import *
from items import *
from enemies import *
from runes import *

def input(key):
    global enemies, main_menu, tutorial_enemy
    if main_menu:
        if key == "space" and void_fade_in.finished:
            print("starting game")
            main_menu = False
            start_game()
        return

    if not player.reloading and player.enabled:
        if key == 'left mouse down' and player.shotgun_ammo_count > 0:
            player.shoot()
        elif key == "left mouse down" and player.shotgun_ammo_count == 0:
            Audio("audio/shotgun/empty_clink.mp3")
        elif key == 'r' and player.shotgun_ammo_count < SHOTGUN_MAX_AMMO_COUNT and not tutorial_ended and tutorial.text == "TUTORIAL: PRESS R TO LOAD SHOTGUN":
            player.reloading = True
            reload_image.enable()
            shotgun_ammo_ui.text = f"AMMO: {player.shotgun_ammo_count}/{SHOTGUN_MAX_AMMO_COUNT}"
            shotgun_ammo_ui.enable()
            ammo_packets_count_ui.enable()
            ammo_packets_count_ui.color=color.orange if player.ammo_packets_count > 0 else color.red
            if player.ammo_packets_count > 0:
                tutorial.text = "TUTORIAL: PRESS LEFT ARROW TO GET A BULLET"
                shotgun_ammo_ui.color = color.orange if player.shotgun_ammo_count > 0 else color.red
                ammo_packets_count_ui.text = f"{player.ammo_packets_count} AMMO PACKETS"
                player.reload_step = 1
                reload_image.texture = '/textures/reloading/get_bullet.png'
            else:
                ammo_packets_count_ui.text = "[OUT OF AMMO PACKETS]"
                player.reload_step = 3
                reload_image.texture = '/textures/reloading/close_chamber.png'
        elif key == 'c' and tutorial_enemy == None:
            player.reloading = True
            reload_image.enable()
            shotgun_ammo_ui.text = f"AMMO: {player.shotgun_ammo_count}/{SHOTGUN_MAX_AMMO_COUNT}"
            shotgun_ammo_ui.enable()
            ammo_packets_count_ui.enable()
            shotgun_ammo_ui.color = color.orange if player.shotgun_ammo_count > 0 else color.red
            ammo_packets_count_ui.color=color.orange if player.ammo_packets_count > 0 else color.red
            player.reload_step = 3
            reload_image.texture = '/textures/reloading/close_chamber.png'
        return

    # ---------- Reload controls ----------
    if player.reload_step == 1 and (key == 'left arrow up' or key == "a up"):
        tutorial.text = "TUTORIAL: PRESS RIGHT ARROW TO INSERT A BULLET"
        player.reload_step = 2
        reload_image.texture = '/textures/reloading/insert_bullet.png'

    elif player.reload_step == 2 and (key == 'right arrow up' or key == "d up"):
        player.shotgun_ammo_count += 1
        player.ammo_packets_count -= 1
        ammo_packets_count_ui.text = f"{player.ammo_packets_count} MAGAZINES"
        ammo_packets_count_ui.color=color.orange if player.ammo_packets_count > 0 else color.red
        shotgun_ammo_ui.text = f"AMMO: {player.shotgun_ammo_count}/{SHOTGUN_MAX_AMMO_COUNT}"
        shotgun_ammo_ui.color = color.orange if player.shotgun_ammo_count > 0 else color.red
        Audio("audio/shotgun/insert_bullet.mp3")

        if player.shotgun_ammo_count >= SHOTGUN_MAX_AMMO_COUNT:
            player.reload_step = 3
            reload_image.texture = '/textures/reloading/close_chamber.png'
            tutorial.text = "TUTORIAL: PRESS UP ARROW TO CLOSE THE CHAMBER"
            player.shotgun_ammo_count = SHOTGUN_MAX_AMMO_COUNT
        elif player.ammo_packets_count > 0:
            player.reload_step = 1
            tutorial.text = "TUTORIAL: PRESS LEFT ARROW TO GET A BULLET"
            reload_image.texture = '/textures/reloading/get_bullet.png'
        else:
            ammo_packets_count_ui.text = "[OUT OF AMMO PACKETS]"
            ammo_packets_count_ui.color=color.orange if player.ammo_packets_count > 0 else color.red
            player.reload_step = 3
            reload_image.texture = '/textures/reloading/close_chamber.png'

    if (player.reload_step == 3 or (player.reload_step == 1 and tutorial_enemy == None)) and (key == 'up arrow up' or key == "w up"):
        tutorial.text = "TUTORIAL: PRESS ESCAPE TO GO BACK"
        Audio("audio/shotgun/close_chamber.mp3")
        reload_image.texture = '/textures/reloading/continue.png'
        shotgun_ammo_ui.disable()
        player.reload_step = 4

    elif player.reload_step == 4 and key == 'escape':
        player.reloading = False
        player.reload_step = 0
        reload_image.disable()
        ammo_packets_count_ui.disable()
        if tutorial_enemy == None:
            enemies.append(Staticon((15, 0.3, 15), enabled=True))
            tutorial.text = "TUTORIAL: KILL A STATICON"

def power_lerp(x, a=1):
    return 1-math.log(math.cosh((1-2*x)/a))+math.log(math.cosh(1/a))-1

available_items = [ammoBox, medicine, fullMedicineKit]
available_runes = [HarmRune, WhisperRune, AdvancingRune, sharpenRune]
available_enemies = [Staticon, Obeliskus, Maime]

wave_filepath = "./waves.json"

if not os.path.exists(wave_filepath):
    wave_filepath = application.asset_folder / "waves.json"


def element_number_converter(value) -> float:
    if isinstance(value, str):
        return {"l": left, "r": right, "t": top, "b": bottom}[value]
    elif isinstance(value, dict):
        minimum = element_number_converter(value["min"])
        maximum = element_number_converter(value["max"])
        return random.uniform(minimum, maximum)
    elif isinstance(value, list):
        return random.choice([element_number_converter(v) for v in value])
    return value

waves_data = json.load(open(wave_filepath))

for wave_num, wave_data in enumerate(waves_data):
    waves.append({"items": [], "enemies": [], "runes": []})
    for element in wave_data:
        position = element.pop("position")
        element["position"] = (element_number_converter(position[0]), 1, element_number_converter(position[1]))
        if element["type"] == "item":
            elementIndex = random.choice(element["items"])
            waves[-1]["items"].append({"items": available_items[elementIndex], "position": position})
            waves[-1]["items"][-1].update(kwargs)
        elif element["type"] == "rune":
            elementIndex = random.choice(element["runes"])
            waves[-1]["runes"].append({"rune": available_runes[elementIndex], "position": position})
            waves[-1]["runes"][-1].update(kwargs)
        elif element["type"] == "enemy":
            elementIndex = random.choice(element["enemies"])

            kwargs = {"enemy": available_enemies[elementIndex], "position": position}
            if kwargs["enemy"] == Maime:
                kwargs["item"] = {"entity": random.choice(available_items), "position": position}

            waves[-1]["enemies"].append(kwargs)

def dialogCallback3():
    global items

    crosshair_ring.color = color.rgb(crosshair_ring.color.r, crosshair_ring.color.g, crosshair_ring.color.b, 1)
    crosshair.color = color.rgb(crosshair.color.r, crosshair.color.g, crosshair.color.b, 1)
    tutorial.text = "TUTORIAL: TOUCH THE ITEM"
    items.append(ammoBox((random.uniform(1, 3), 0.3, random.uniform(0, 5))))
    items.append(ammoBox((-random.uniform(1, 3), 0.3, random.uniform(0, 5))))
    player.can_move = True

def dialogCallback2():
    crosshair.enabled=True
    crosshair_ring.enabled=True
    shotgun_pump.color = color.white
    shotgun.color = color.white
    crosshair.fade_in()
    crosshair_ring.color = color.rgba(255, 60, 60, 0)
    crosshair_ring.animate_color(color.rgba32(255, 60, 60, 80), 2, curve=curve.linear)
    
    ShowDialog("I cant wake up too.").dialog_callback = dialogCallback3

def dialogCallback1():
    shotgun_pump.enabled=True
    shotgun.enabled=True
    ground.color = color.gray
    shotgun_pump.color = color.rgba(0,0,0,0)
    shotgun.color = color.rgba(0,0,0,0)
    shotgun_pump.animate_color(color.white, 0.5, curve=curve.linear)
    shotgun.animate_color(color.white, 0.5, curve=curve.linear)
    
    ShowDialog("and why do I have a shotgun?!").dialog_callback = dialogCallback2

def update_game(dt: float):
    global screen_shift_strength, screen_fade_animation
    global game_won, waiting_to_advance
    
    if tutorial_ended and tutorial.enabled:
        tutorial.disable()

    if screen_fade_animation > 0:
        screen_fade_animation -= dt/10
        screen_shift.color = color.rgba((power_lerp(1-screen_fade_animation) if screen_fade_animation > 0 else 0), 0, 0, 1 - screen_fade_animation)
        if crosshair.enabled:
            crosshair.disable()
        if crosshair_ring.enabled:
            crosshair_ring.disable()

    if game_over or game_won:
        if screen_fade_animation <= 0:
            screen_fade_animation -= dt
            if game_won:
                win_text.text = "you wake up in a cold sweat"
                win_text.color = color.rgba(0, 0, 0, clamp(- 2*screen_fade_animation - 0.5, 0, 1))
            else:
                win_text.text = "that night you never woke up"
                win_text.color = color.rgba(0.5, 0, 0, clamp(- 2*screen_fade_animation - 0.5, 0, 1))
            if screen_fade_animation <= -2:
                app.userExit()
        return

    if screen_shift_strength > 0:
        screen_shift_strength -= dt
        screen_shift.color = color.rgba(
            1,
            0,
            0,
            screen_shift_strength
        )
    else:
        screen_shift.color = color.rgba(0, 0, 0, 0)

    player.update_player(dt)

    # Void
    void.position = (
        player.x,
        -0.1,
        player.z
    )

    alive_enemies = 0
    for entity in enemies:
        entity.update_entity(dt)
        if entity.health > 0:
            alive_enemies += 1

    for item in items:
        item.update_item(dt)

    for rune in runes:
        rune.update_rune(dt)

    if alive_enemies == 0 and not waiting_to_advance and tutorial.text == "TUTORIAL: KILL A STATICON":
        runes.append(AdvancingRune(enabled=True))
        waiting_to_advance = True

        if not tutorial_ended:
            tutorial.text = "TUTORIAL: FIND THE RUNE"

def start_game():
    main_menu_music.stop()
    Audio("audio/ambient.wav", loop=True)
    ground.fade_in(1, duration=3)
    invoke(lambda: setattr(ShowDialog("where am I..."), "dialog_callback", dialogCallback1), delay=3)
    void_fade_in.finish()
    title_text.fade_out()
    start_game_text.disable()
    player.enable()
    player.can_move = False

main_menu_music = Audio("audio/main_menu.wav", loop=True, pitch=0.25, volume=0.75, autoplay=True)
main_menu_music.animate("pitch", 1, 1.5, curve=curve.linear)

def update():
    global void_noise_timer
    dt = time.dt

    if not main_menu:
        update_game(dt)

    void_noise_timer += dt
    if void_noise_timer > 1.5:
        void_noise_timer = 0
        void.texture = generate_noise_texture("void_"+ str(int(random.random()*10)))
    
    if void_fade_in.finished:
        if start_game_text.color.a == 0:
            start_game_text.fade_in(duration=1)

app.run()