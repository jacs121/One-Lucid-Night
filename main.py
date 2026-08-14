import atexit
from ursina import *

print("frozen execution:", getattr(sys, 'frozen', False))
if getattr(sys, 'frozen', False) and len(sys.argv) == 3:
    os.makedirs("./logs", exist_ok=True)
    if sys.argv[1] == "--loggingFile":
        sys.stdout = open("./logs/"+sys.argv[2]+".log", "w")
    else:
        sys.stdout = open("./logs/latest.log", "w")

if getattr(sys, 'frozen', False):
    application.asset_folder = (Path(sys._MEIPASS) / "assets").absolute()
else:
    application.asset_folder = (Path(__file__).parent  / "assets").absolute()

print("assets located at:", application.asset_folder)
save_location = application.asset_folder / ".." / "save_data.cmp"
print("game save located at:", save_location)

from entities import *
from items import *
from enemies import *
from runes import *

if os.path.exists(save_location):
    saveStates = SaveStates.load_file(save_location)
else:
    saveStates = SaveStates.init()

def input(key):
    if gameState.scene_type == SceneTypes.MAIN_MENU:
        window.exit_button.disable()
        if key == "space" and void_fade_in.finished:
            print("starting game")
            gameState.scene_type = "GAME"
            start_game()
        elif key == "enter" and void_fade_in.finished:
            print("starting game")
            gameState.scene_type = "GAME"
            start_game(True)
        return
    elif gameState.scene_type == SceneTypes.GAME and key == "escape":
        window.exit_button.enable()
        gameState.scene_type = "ESCAPE"
    elif gameState.scene_type == SceneTypes.ESCAPE and key == "escape":
        window.exit_button.disable()
        gameState.scene_type = "GAME"

    if not player.reloading and player.enabled:
        if key == 'left mouse down' and player.shotgun_ammo_count > 0:
            player.shoot()
        elif key == "left mouse down" and player.shotgun_ammo_count == 0:
            Audio("audio/shotgun/empty_clink.mp3")
        elif key == 'r' and (player.shotgun_ammo_count < SHOTGUN_MAX_AMMO_COUNT and gameState.tutorial_ended or tutorial.text == "TUTORIAL: PRESS R TO LOAD SHOTGUN"):
            player.reloading = True
            reload_image.enable()
            shotgun_ammo_ui.text = f"AMMO: {player.shotgun_ammo_count}/{SHOTGUN_MAX_AMMO_COUNT}"
            experience_amount_ui.text = f"{player.experience} PROFICIENCY" if player.experience > 0 else "NO PROFICIENCY"
            shotgun_ammo_ui.enable()
            experience_amount_ui.enable()
            ammo_packets_count_ui.enable()
            ammo_packets_count_ui.color=color.orange if player.ammo_packets_count > 0 else color.red
            shotgun_ammo_ui.color = color.orange if player.shotgun_ammo_count > 0 else color.red
            experience_amount_ui.color = color.orange if player.shotgun_ammo_count > 0 else color.red
            if player.ammo_packets_count > 0:
                tutorial.text = "TUTORIAL: PRESS LEFT ARROW TO GET A BULLET"
                ammo_packets_count_ui.text = f"{player.ammo_packets_count} AMMO PACKETS"
                player.reload_step = 1
                reload_image.texture = '/textures/reloading/get_bullet.png'
            else:
                ammo_packets_count_ui.text = "[OUT OF AMMO PACKETS]"
                player.reload_step = 3
                reload_image.texture = '/textures/reloading/close_chamber.png'
        elif key == 'c' and (gameState.tutorial_ended or tutorial.text == "TUTORIAL: PRESS C TO CHECK SHOTGUN AMMO"):
            player.reloading = True
            reload_image.enable()
            shotgun_ammo_ui.text = f"AMMO: {player.shotgun_ammo_count}/{SHOTGUN_MAX_AMMO_COUNT}"
            shotgun_ammo_ui.enable()
            experience_amount_ui.enable()
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

    if (player.reload_step == 3 or (player.reload_step == 1 and gameState.tutorial_ended)) and (key == 'up arrow up' or key == "w up"):
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
        experience_amount_ui.disable()
        if len(gameState.enemies) <= 0:
            if player.shotgun_ammo_count < SHOTGUN_MAX_AMMO_COUNT:
                tutorial.text = "TUTORIAL: TOUCH THE ITEM"
                player.can_move = True
            else:
                gameState.enemies.append(StaticonEnemy((15, 0.3, 15)))
                tutorial.text = "TUTORIAL: KILL A STATICON"

def power_lerp(x, a=1):
    return 1-math.log(math.cosh((1-2*x)/a))+math.log(math.cosh(1/a))-1

available_items = {}
available_runes = {}
available_enemies = {}

for (item, rune, enemy) in zip_longest(Item.__subclasses__(), Rune.__subclasses__(), Enemy.__subclasses__()):
    if item:
        available_items.update({item.__name__[:-4]: item})
    if rune:
        available_runes.update({rune.__name__[:-4]: rune})
    if enemy:
        available_enemies.update({enemy.__name__[:-5]: enemy})

wave_location = "./waves.json"

if not os.path.exists(wave_location):
    wave_location = application.asset_folder / "waves.json"

print("wave data located at:", wave_location)

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

def load_waves(filepath: str):
    waves = []
    waves_data = json.load(open(filepath, "r"))

    for wave_data in waves_data:
        waves.append({"items": [], "enemies": [], "runes": []})
        for element in wave_data:
            position = element.pop("position")
            element["position"] = (element_number_converter(position[0]), 1, element_number_converter(position[1]))
            element_type = element.pop("type")
            if element_type == "item":
                elementIndex = random.choice(element.pop("items"))
                waves[-1]["items"].append({"item": available_items[elementIndex], "position": position})
                waves[-1]["items"][-1].update(element)
            elif element_type == "rune":
                elementIndex = random.choice(element.pop("runes"))
                waves[-1]["runes"].append({"rune": available_runes[elementIndex], "position": position})
                waves[-1]["runes"][-1].update(element)
            elif element_type == "enemy":
                elementIndex = random.choice(element.pop("enemies"))

                kwargs = {"enemy": available_enemies[elementIndex], "position": position}
                kwargs.update(element)
            
                if kwargs["enemy"] == MaimeEnemy:
                    kwargs["item"] = {"entity": random.choice(available_items), "position": position}

                waves[-1]["enemies"].append(kwargs)

    return waves

gameState.waves = load_waves(wave_location)

def dialogCallback3():

    crosshair_ring.color = color.rgb(crosshair_ring.color.r, crosshair_ring.color.g, crosshair_ring.color.b, 1)
    crosshair.color = color.rgb(crosshair.color.r, crosshair.color.g, crosshair.color.b, 1)
    tutorial.text = "TUTORIAL: PRESS C TO CHECK SHOTGUN AMMO"
    gameState.items.append(AmmoBoxItem((random.choice([-1, 1])*random.uniform(1.5, 3), 0.3, random.choice([-1, 1])*random.uniform(1.5, 3))))
    gameState.items.append(AmmoBoxItem((random.choice([-1, 1])*random.uniform(1.5, 3), 0.3, random.choice([-1, 1])*random.uniform(1.5, 3))))

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

def restart_game():
    global gameState

    global tutorial, shotgun_ammo_ui, ammo_packets_count_ui
    global crosshair, crosshair_ring, player
    global screen_shift, win_text, void_fade_in
    global start_game_text, ground, main_menu_music

    destroy(player)
    player = Player()
    for rune in gameState.runes:
        rune.sound.stop()
        destroy(rune)

    for entity in gameState.enemies+gameState.items:
        destroy(entity)

    gameState = GameState.default()
    gameState.waves = load_waves(wave_location)

    init_entities()

    main_menu_music = Audio("audio/main_menu.wav", loop=True, pitch=0.25, volume=0, autoplay=True)
    main_menu_music.animate("pitch", 1, 1.5, curve=curve.linear)
    main_menu_music.animate("volume", 0.75, 2, curve=curve.linear)

def update_game(dt: float):
    if gameState.tutorial_ended and tutorial.enabled:
        tutorial.disable()

    if gameState.screen_fade_animation > 0:
        gameState.screen_fade_animation -= dt/10
        screen_shift.color = color.rgba(gameState.game_over*(power_lerp(1-gameState.screen_fade_animation) if gameState.screen_fade_animation > 0 else 0), 0, 0, 1 - gameState.screen_fade_animation)
        if crosshair.enabled:
            crosshair.disable()
        if crosshair_ring.enabled:
            crosshair_ring.disable()

    if gameState.game_over or gameState.game_won:
        if gameState.screen_fade_animation <= 0:
            gameState.screen_fade_animation -= dt
            if gameState.game_won:
                win_text.text = "you wake up in a cold sweat"
                win_text.color = color.rgba(1, 1, 1, clamp(- 2*gameState.screen_fade_animation - 0.5, 0, 1))
            else:
                win_text.text = "that night you never woke up"
                win_text.color = color.rgba(0.5, 0, 0, clamp(- 2*gameState.screen_fade_animation - 0.5, 0, 1))
            if gameState.screen_fade_animation <= -2:
                restart_game()
        return

    if gameState.screen_shift_strength > 0:
        gameState.screen_shift_strength -= dt
        screen_shift.color = color.rgba(
            1,
            0,
            0,
            gameState.screen_shift_strength
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
    
    escape_background.position = (
        player.x,
        0.15,
        player.z
    )

    gameState.alive_enemies = 0
    for enemy in gameState.enemies:
        if enemy.health > 0:
            gameState.alive_enemies += 1
        enemy.update_entity(dt)

    for item in gameState.items:
        item.update_item(dt)

    for rune in gameState.runes:
        rune.update_rune(dt)

    if ((gameState.tutorial_ended) or (not gameState.tutorial_ended and tutorial.text == "TUTORIAL: KILL A STATICON")) and gameState.alive_enemies == 0 and not gameState.waiting_to_advance:
        print("waiting to advance wave to #"+str(gameState.wave_num+1))
        gameState.runes.append(AdvancingRune((random.uniform(left + 10, right - 10), 1, random.uniform(bottom + 10, top - 10))))
        gameState.waiting_to_advance = True

        if not gameState.tutorial_ended:
            tutorial.text = "TUTORIAL: FIND THE RUNE"

    elif (gameState.alive_enemies > 0 and gameState.waiting_to_advance):
        advancing_runes = [r for r in gameState.runes if isinstance(r, AdvancingRune)]
        for rune in advancing_runes:
            try:
                gameState.runes.remove(rune)
            except ValueError:
                pass
            if hasattr(rune, 'sound') and rune.sound:
                try:
                    rune.sound.stop()
                except Exception:
                    pass
            destroy(rune)
            print("deleting unneeded advancing rune")
        gameState.waiting_to_advance = False

def start_game(skip_tutorial: bool = False):
    Audio("audio/ambient.wav", loop=True)

    if skip_tutorial:
        gameState.items.append(AmmoBoxItem((random.choice([-1, 1])*random.uniform(1.5, 3), 0.3, random.choice([-1, 1])*random.uniform(1.5, 3))))
        gameState.items.append(AmmoBoxItem((random.choice([-1, 1])*random.uniform(1.5, 3), 0.3, random.choice([-1, 1])*random.uniform(1.5, 3))))
        gameState.enemies.append(StaticonEnemy((15, 0.3, 15)))
        gameState.tutorial_ended = True
        main_menu_music.stop()
        ground.color = color.rgb(*ground.color.rgb, 1)
        tutorial.text = "TUTORIAL SKIPPED"
        invoke(tutorial.disable, delay=1)
        crosshair.enable()
        crosshair_ring.enable()
        shotgun.enable()
        title_text.disable()
    else:
        invoke(lambda: setattr(ShowDialog("where am I..."), "dialog_callback", dialogCallback1), delay=3)
        invoke(main_menu_music.stop, delay=1.5)
        ground.fade_in(1, duration=3)
        main_menu_music.animate("pitch", 0, 1.5, curve=curve.linear)
        main_menu_music.animate("volume", 0, 1.5, curve=curve.linear)
        title_text.fade_out()

    void_fade_in.finish()
    start_game_text.disable()
    player.enable()
    player.can_move = skip_tutorial

main_menu_music = Audio("audio/main_menu.wav", loop=True, pitch=0.25, volume=0, autoplay=True)
main_menu_music.animate("pitch", 1, 1.5, curve=curve.linear)
main_menu_music.animate("volume", 0.75, 2, curve=curve.linear)

def update():
    dt = time.dt

    if gameState.scene_type == SceneTypes.GAME:
        update_game(dt)
    elif gameState.scene_type == SceneTypes.ESCAPE:
        return

    gameState.void_noise_timer += dt
    if gameState.void_noise_timer > 1.5:
        gameState.void_noise_timer = 0
        void.texture = generate_noise_texture("void_"+ str(int(random.random()*10)), max_value=25)

    if void_fade_in.finished:
        if start_game_text.color.a == 0:
            start_game_text.fade_in(duration=1)

window.fps_counter.enabled = False
window.entity_counter.enabled = False
window.collider_counter.enabled = False
window.cog_button.enabled = False
reset_game.on_click = restart_game

atexit.register(lambda: (saveStates.save_data(save_location)))
app.run()