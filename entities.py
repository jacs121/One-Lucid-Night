from util import *

class Player(Entity):
    def __init__(self, speed: int = 2.5, view_cone_range: int = 90, max_health: int = 100):
        super().__init__(
            model=load_model("models/player.glb", use_deepcopy=True),
            rotation=(0,0,0),
            y=0.3,
            unlit=True,
            shader=triplanar_shader,
            enabled=False
        )

        self.speed = speed
        self.attack_damage = 12.5
        self.max_health = self.health = max_health
        self.view_cone_half_angle = view_cone_range / 2
        self.set_shader_input(
            "texture_scale",
            self.texture_scale
        )
        self.set_shader_input(
            "position",
            self.texture_offset
        )
        char = self.model.find("**/+Character").node()
        part_bundle = char.getBundle(0)

        self.shotgun_ready = True
        self.shotgun_pumping = False
        self.can_move = False
        self.pump_progress = 0.0
        self.last_mouse_x = mouse.x
        self.last_mouse_y = mouse.y
        self.direction = Vec3(0)
        self.experience = 0
        self.shotgun_pellet_count = 2

        self.shotgun_ammo_count = 0
        self.ammo_packets_count = 0
        self.reloading = False
        self.reload_step = 0

        self.shotgun_recoil = 0.0
        self.pump_back_amount = 0.0
        self.camera_shake = 0.0

        self.pump_stroke_dir = 0
        self.pump_stroke_dist = 0.0
        self.pump_strokes = 0

        self.anim_controls = {}

        for node in self.model.findAllMatches("**/+AnimBundleNode"):
            bundle = node.node().getBundle()

            control = part_bundle.bindAnim(
                bundle,
                part_bundle.HMF_ok_anim_extra |
                part_bundle.HMF_ok_part_extra |
                part_bundle.HMF_ok_wrong_root_name,
                PartSubset(),
            )
            self.anim_controls[bundle.getName()] = control

        self.anim_controls["idle"].play()
        self.prev_frame_num = -1
        self.animation = "idle"
        if self.enabled:
            print("player initialized:")
            print("    model:", self.model)
            print("    available animation:")
            print("\n        "+"\n        ".join(self.anim_controls.keys()))
            print("    animation:", self.animation)

    def update_player(self, dt):
        self.update_shotgun(dt)

        rad = -math.radians(self.rotation_y)
        if self.shotgun_ready:
            self.rotation_y = lerp_angle(self.rotation_y, math.degrees(
                math.atan2(-mouse.y, mouse.x)
            ), dt*10)
            self.direction = Vec3(math.cos(rad), 0, math.sin(rad))

        if not gameState.tutorial_ended and tutorial.text == "TUTORIAL: FIND THE RUNE":
            if len(gameState.runes) and distance_2d(gameState.runes[0].position.xz, self.position.xz - self.direction.xz/2) <= gameState.runes[0].activation_distance:
                tutorial.text = "TUTORIAL: INTERACT WITH A RUNE BY PRESSING SPACE"

        if not self.reloading:
            self.move_input = Vec3(
                (held_keys['d'] or held_keys["right arrow"]) - (held_keys['a'] or held_keys["left arrow"]),
                0,
                (held_keys['w'] or held_keys["up arrow"]) - (held_keys['s'] or held_keys["down arrow"])
            )
            if self.move_input.length() and self.can_move:
                self.move_input = self.move_input.normalized()
                movement = Vec3(
                    self.move_input.x * math.sin(rad) +
                    self.move_input.z * math.cos(rad),
                    0,
                    self.move_input.x * math.cos(rad) +
                    self.move_input.z * math.sin(rad)
                )
                if self.move_input.x == -1 and not self.anim_controls["right"].playing:
                    self.anim_controls["right"].play()
                    self.animation = "right"
                elif self.move_input.x == 1 and not self.anim_controls["left"].playing:
                    self.anim_controls["left"].play()
                    self.animation = "left"
                elif self.move_input.z == 1 and not self.anim_controls["forwards"].playing:
                    self.anim_controls["forwards"].play()
                    self.animation = "forwards"
                elif self.move_input.z == -1 and not self.anim_controls["backwards"].playing:
                    self.anim_controls["backwards"].play()
                    self.animation = "backwards"

                if self.prev_frame_num != self.anim_controls[self.animation].getFrame() and self.anim_controls[self.animation].getFrame() % (self.anim_controls[self.animation].getNumFrames()//2) == 5:
                    Audio("audio/step.mp3", 2)

                self.prev_frame_num = self.anim_controls[self.animation].getFrame()
                self.position += movement * (self.speed * (2 if held_keys["left shift"] else 1)) * dt
            elif not self.anim_controls["idle"].playing:
                self.animation = "idle"
                self.anim_controls["idle"].play()
                self.prev_frame_num = -1

            if self.animation != "idle":
                if held_keys["left shift"]:
                    self.anim_controls[self.animation].setPlayRate(2)
                else:
                    self.anim_controls[self.animation].setPlayRate(1)

        if self.camera_shake > 0:
            self.camera_shake -= dt * 3
            shake = max(0, self.camera_shake) * 0.15
            camera.position = (
                self.x + random.uniform(-shake, shake),
                camera.y,
                self.z + random.uniform(-shake, shake)
            )
        else:
            camera.position = (self.x, camera.y, self.z)

        self.position = Vec3(clamp(self.position.x,
                                    max(BOUNDARY_REGION[0]+self.direction.x, BOUNDARY_REGION[0]),
                                    min(BOUNDARY_REGION[2]+self.direction.x, BOUNDARY_REGION[2])),
                            0.3,
                            clamp(self.position.z,
                                    max(BOUNDARY_REGION[1]+self.direction.z, BOUNDARY_REGION[1]),
                                    min(BOUNDARY_REGION[3]+self.direction.z, BOUNDARY_REGION[3]))
                            )

    def shoot(self):
        """Fire the shotgun. Each bullets is ray-cast and checked against the entity."""
        if not self.shotgun_ready:
            return

        self.shotgun_ready = False
        self.shotgun_pumping = True
        self.pump_progress = 0
        self.shotgun_recoil = 1.0
        self.camera_shake = 0.4
        self.pump_stroke_dir = 0
        self.pump_stroke_dist = 0.0
        self.pump_strokes = 0
        self.shotgun_ammo_count -= 1
        Audio("audio/shotgun/clink.mp3")

        bullets_hit: dict[Entity, float] = {}
        player_angle = - math.radians(self.rotation_y)
        player_dir = Vec3(math.cos(player_angle), 0, math.sin(player_angle))
        for _ in range(self.shotgun_pellet_count):
            spread = random.uniform(-SHOTGUN_SPREAD, SHOTGUN_SPREAD)/(1 + 0.5*(self.move_input.length() == 0 and not held_keys["left shift"]))
            bullets_angle = - math.radians(self.rotation_y+spread)

            dir_x =  math.cos(bullets_angle)
            dir_z =  math.sin(bullets_angle)

            hit = False
            for entity in gameState.enemies:
                dx = entity.x - self.x
                dz = entity.z - self.z

                t = dx * dir_x + dz * dir_z-1

                if 0 < t < SHOTGUN_RANGE:
                    closest_x = self.x + t * dir_x
                    closest_z = self.z + t * dir_z

                    ox = closest_x - entity.x
                    oz = closest_z - entity.z

                    angle = - math.radians(entity.rotation_y)
                    c = cos(angle)
                    s = sin(angle)
                    local_x = ox * c - oz * s
                    local_z = ox * s + oz * c

                    half_x = entity.scale.x * 2
                    half_z = entity.scale.z * 2

                    if abs(local_x) <= half_x and abs(local_z) <= half_z:
                        if (t <= 1.5):
                            rangeMultiplier = 1.0
                        else:
                            rangeMultiplier = max(0.0, 1.0 - ((t - 1.5) / 23.5))

                        bullets_hit[entity] = bullets_hit.get(entity, 0) + (self.attack_damage * rangeMultiplier * random.uniform(0.95, 1.05))
                        hit = True
                        ray = Entity(
                            model='quad',
                            scale=(0.05, t),
                            position=self.position+player_dir/2,
                            rotation=(90, self.rotation_y+90+spread, 0),
                            origin=(0, -.5),
                            color=color.red,
                        )
                        ray.fade_out(0, 1)
                        destroy(ray, 1)
                        continue

            if not hit:
                ray = Entity(
                    model='quad',
                    scale=(0.05, SHOTGUN_RANGE),
                    position=self.position+player_dir/2,
                    rotation=(90, self.rotation_y+90+spread, 0),
                    origin=(0, -0.5),
                    color=color.red
                )
                ray.fade_out(0, 1)
                destroy(ray, 1)

        for entity, damage in bullets_hit.items():
            entity.damage(damage)
            if entity.health == 0:
                self.experience += damage

    def update_shotgun(self, dt):
        if self.shotgun_pumping:
            pump_bar_bg.enable()
            pump_bar_fill.enable()
            if self.pump_strokes >= PUMP_STROKES_NEEDED:
                self.shotgun_ready = True
                self.shotgun_pumping = False
                self.pump_back_amount = 0
                Audio("audio/shotgun/pump_forth.mp3")
        if self.shotgun_pumping:
            angle = math.radians(self.rotation_y)

            aim_dir = Vec2(
                cos(angle),
                - sin(angle)
            )

            mouse_delta = (mouse.x - self.last_mouse_x) * aim_dir.x + (mouse.y - self.last_mouse_y) * aim_dir.y
            if abs(mouse_delta) > 0.0001:
                current_dir = 1 if mouse_delta > 0 else -1
                if self.pump_stroke_dir == 0 and current_dir == -1:
                    self.pump_stroke_dir = current_dir
                    self.pump_stroke_dist = abs(mouse_delta)
                if current_dir == self.pump_stroke_dir:
                    self.pump_stroke_dist += abs(mouse_delta)
                    if self.pump_stroke_dist > PUMP_TARGET/(2-self.pump_strokes):
                        Audio("audio/shotgun/pump_back.mp3")
                        self.pump_stroke_dist = PUMP_TARGET/(2-self.pump_strokes)
                        self.pump_stroke_dir *= -1
                        self.pump_strokes += 1

            self.pump_progress = clamp(self.pump_stroke_dist/PUMP_TARGET, 0, 1)
        else:
            self.pump_stroke_dir = 0
            self.pump_stroke_dist = 0
            self.pump_back_amount = 0

            pump_bar_bg.disable()
            pump_bar_fill.disable()

        angle = math.radians(self.rotation_z)

        aim_dir = Vec2(
            cos(angle),
            sin(angle)
        )

        self.shotgun_recoil = max(0, self.shotgun_recoil - dt * 6)
        recoil_offset = -aim_dir * self.shotgun_recoil * 0.12

        pump_offset = -aim_dir * (1 - abs(2*self.pump_progress - 1)) * 0.25

        shotgun.position = (
            recoil_offset.x,
            shotgun.y,
            recoil_offset.y,
        )
        shotgun_pump.position = (
            pump_offset.x + recoil_offset.x,
            shotgun_pump.y,
            pump_offset.y + recoil_offset.y
        )

        if self.shotgun_pumping:
            if gameState.update_crosshair == True:
                crosshair.color = color.rgb32(255, 0, 0)
            crosshair_ring.color = color.rgb32(255, 0, 0)

            crosshair.position = (mouse.x, mouse.y, -2)

            fill = self.pump_progress
            pump_bar_fill.scale_x = (fill - 0.01) / 2
            pump_bar_fill.x = 0
            pump_bar_fill.color = color.rgba32(255, 200, 50, 220)
        elif self.shotgun_ready:
            if gameState.update_crosshair == True:
                crosshair.color = color.rgb32(200, 200, 200)
                crosshair_ring.color = color.rgb32(200, 200, 200)

            crosshair.position = (mouse.x, mouse.y, -1)
            crosshair_ring.position = (mouse.x, mouse.y, -2)

            pump_bar_fill.scale_x = 0.49
            pump_bar_fill.x = 0
            pump_bar_fill.color = color.rgba32(80, 220, 80, 220)
        else:
            pump_bar_fill.scale_x = 0.49
            pump_bar_fill.x = 0
            pump_bar_fill.color = color.rgba32(100, 100, 100, 100)

        self.last_mouse_x = mouse.x
        self.last_mouse_y = mouse.y

player = Player()

def reposition():
    shotgun_ammo_ui.x = -window.aspect_ratio / 2 + .02
    ammo_packets_count_ui.x = -window.aspect_ratio / 2 + .02
    tutorial.x = -window.aspect_ratio / 2 + .02

class ShowDialog(Entity):
    def __init__(self, text: str = "", dialog_speed: float = 1/15):
        super().__init__()
        self.label = Text(
            origin=(0, -0.5),
            position=(0, -0.475)
        )

        self.dialog_text = text
        self.dialog_speed = dialog_speed
        self.dialog_timer = 0

    def update(self):
        dt = time.dt
        if self.dialog_timer < len(self.dialog_text) + 2/self.dialog_speed:
            self.dialog_timer += dt/self.dialog_speed
            if self.label.text != self.dialog_text[:int(min(self.dialog_timer, len(self.dialog_text)))]:
                Audio("audio/dialog_pop.mp3", autoplay=True, auto_destroy=True)
                self.label.text = self.dialog_text[:int(min(self.dialog_timer, len(self.dialog_text)))]
        else:
            self.dialog_callback()

            destroy(self.label)
            destroy(self)

    def input(self, key):
        if key == "enter" and self.dialog_timer < len(self.dialog_text):
            self.dialog_timer = len(self.dialog_text) + 1/self.dialog_speed
        elif key == "enter" and self.dialog_timer >= len(self.dialog_text):
            self.dialog_timer = len(self.dialog_text) + 2/self.dialog_speed

    def dialog_callback(self):
        pass

def init_entities():
    global tutorial, shotgun, shotgun_ammo_ui
    global shotgun_pump, ammo_packets_count_ui, crosshair
    global crosshair_ring, pump_bar_bg, pump_bar_fill
    global screen_shift, win_text, void_fade_in
    global title_text, start_game_text, void
    global ground, reload_image, experience_amount_ui
    global reset_game, escape_background

    if "experience_amount_ui" in globals():
        destroy(experience_amount_ui)
    
    if "escape_background" in globals():
        destroy(escape_background)

    if "reset_game" in globals():
        destroy(reset_game)

    if "tutorial" in globals():
        destroy(tutorial)

    if "reload_image" in globals():
        destroy(reload_image)

    if "shotgun" in globals():
        destroy(shotgun)

    if "shotgun_ammo_ui" in globals():
        destroy(shotgun_ammo_ui)

    if "shotgun_pump" in globals():
        destroy(shotgun_pump)

    if "ammo_packets_count_ui" in globals():
        destroy(ammo_packets_count_ui)

    if "crosshair" in globals():
        destroy(crosshair)

    if "crosshair_ring" in globals():
        destroy(crosshair_ring)

    if "pump_bar_bg" in globals():
        destroy(pump_bar_bg)

    if "pump_bar_fill" in globals():
        destroy(pump_bar_fill)

    if "screen_shift" in globals():
        destroy(screen_shift)

    if "win_text" in globals():
        destroy(win_text)

    if "title_text" in globals():
        destroy(title_text)

    if "start_game_text" in globals():
        destroy(start_game_text)

    if "void" in globals():
        destroy(void)

    if "ground" in globals():
        destroy(ground)

    tutorial = Text(
        text="",
        color=color.yellow,
        origin=(-0.5, -0.5),
        position=(-0.5, -0.475),
    )

    shotgun_ammo_ui = Text(
        text="AMMO: 0/0",
        color=color.orange if player.shotgun_ammo_count > 0 else color.red,
        origin=(-0.5, 0.5),
        position=(-0.5, 0.45),
        enabled=False
    )

    ammo_packets_count_ui = Text(
        text=f"{player.ammo_packets_count} MAGAZINES" if player.ammo_packets_count > 0 else "[OUT OF MAGAZINES]",
        color=color.orange if player.ammo_packets_count > 0 else color.red,
        origin=(-0.5, 0.5),
        position=(-0.5, 0.475),
        enabled=False
    )

    experience_amount_ui = Text(
        text=f"{player.experience} PROFICIENCY" if player.experience > 0 else "NO PROFICIENCY",
        color=color.orange if player.experience > 0 else color.red,
        origin=(-0.5, 0.5),
        position=(-0.5, 0.425),
        enabled=False
    )

    shotgun_pump = Entity(
        parent=player,
        model='quad',
        texture="textures/shotgun_pump.png",
        scale=(1.125, 0.125),
        position=(0, 1.512, 0),
        rotation=(90, 0, 0),
        unlit=True,
        enabled=False
    )

    crosshair = Entity(
        parent=camera.ui,
        model='quad',
        texture="textures/crosshair.png",
        color=color.rgba32(255, 60, 60, 220),
        scale=(0.05, 0.05),
        z=-1,
        enabled=False
    )

    crosshair_ring = Entity(
        parent=camera.ui,
        model='quad',
        texture="textures/crosshair_ring.png",
        color=color.rgba32(255, 60, 60, 80),
        scale=(0.05, 0.05),
        z=-2,
        enabled=False
    )

    pump_bar_bg = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba32(0, 0, 0, 130),
        scale=(0.5, 0.022),
        position=(0, -0.45),
        z=-1,
        enabled=False
    )

    # Pump progress bar fill
    pump_bar_fill = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba32(255, 200, 50, 220),
        scale=(0.0, 0.018),
        position=(0.0, -0.45),
        z=-2,
        enabled=False
    )

    screen_shift = Entity(
        parent=camera.ui,
        model='quad',
        scale=2,
        color=color.rgba(1, 0, 0, 0),
        z=10
    )

    win_text = Text(
        parent=camera.ui,
        text="",
        color=color.rgba(0.5, 0, 0, 0),
        position=(-0.2,0),
        scale=1
    )

    ground = Entity(
        model='cube',
        scale=(width, 0, height),
        shader=triplanar_shader,
        position=(center_x, center_y),
        texture=generate_noise_texture("world"),
        color=color.rgba(0.5,0.5,0.5,0),
        unlit=True
    )


    void = Entity(
        model='plane',
        texture=generate_noise_texture("void", max_value=25),
        scale=125,
        y=-0.1,
        texture_scale=(5, 5),
        color=color.rgb(1, 1, 1, 0),
        unlit=True
    )

    void_fade_in = void.fade_in(1, duration=3, curve=curve.linear)

    ground.set_shader_input(
        "position", Vec2(0)
    )

    ground.set_shader_input(
        "texture_scale", Vec2(0.05)
    )

    title_text = Text(
        text=title.upper(),
        origin=(0, -0.35),
        position=(0, 0.35),
        scale=5,
        color=color.red
    )

    start_game_text = Text(
        text="press space to start",
        origin=(0, -0.45),
        position=(0, -0.45),
        color=color.rgba(1,1,1,0)
    )

    reload_image = Entity(
        parent=camera.ui,
        model='quad',
        texture='textures/reloading/get_bullet.png',
        scale=(87/100, 13/100),
        position=(0, 0),
        color=color.white,
        enabled=False
    )

    shotgun = Entity(
        parent=player,
        model='quad',
        texture="textures/shotgun.png",
        scale=(1.125, 0.125),
        position=(0, 1.512, 0),
        rotation=(90, 0, 0),
        unlit=True,
        enabled=False
    )

    reset_game = Button(
        "RESET",
        disabled=True,
    )

    escape_background = Entity(
        model='plane',
        scale=125,
        y=0.15,
        texture_scale=(5, 5),
        color=color.rgb(1, 1, 1, 0.5),
        unlit=True,
        enabled=False
    )

init_entities()
window.on_window_resize = reposition
reposition()