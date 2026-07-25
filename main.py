import sys

print("frozen execution:", getattr(sys, 'frozen', False))
if getattr(sys, 'frozen', False) and len(sys.argv) == 3 and sys.argv[1] == "--loggingName":
    sys.stdout = open(sys.argv[2]+".txt", "w")

from ursina import *

if getattr(sys, 'frozen', False):
    application.asset_folder = Path(sys._MEIPASS).absolute()
else:
    application.asset_folder = Path(__file__).parent.absolute()

from PIL import Image
import numpy as np
import hashlib
import math
import random
from panda3d.core import PartSubset

app = Ursina()

# -----------------------------
# Texture generation
# -----------------------------

def generate_noise_texture(seed: str, width=512, height=512):
    data = seed.encode('utf-8')
    raw = list(hashlib.shake_256(data).digest(width * height))
    img = Image.fromarray(
        np.array(raw, dtype=np.uint8).reshape(width, height),
        'L'
    )
    return Texture(img)

# -----------------------------
# World
# -----------------------------

triplanar_shader = Shader(
    language=Shader.GLSL,
    vertex="""#version 150

in vec4 p3d_Vertex;

out vec4 world_pos;
out vec4 vertex_color;

uniform mat4 p3d_ModelMatrix;
uniform mat4 p3d_ViewProjectionMatrix;
uniform vec4 p3d_ColorScale;

void main() {
    world_pos = p3d_ModelMatrix * p3d_Vertex;
    vertex_color = p3d_ColorScale;

    gl_Position = p3d_ViewProjectionMatrix * world_pos;
}""",
    fragment="""#version 150

in vec4 world_pos;
in vec4 vertex_color;

out vec4 fragColor;

uniform sampler2D p3d_Texture0;

uniform float texture_scale;
uniform vec2 position;

void main() {

    vec2 uv = world_pos.xz;

    uv += position;
    uv *= texture_scale;

    vec4 tex = texture(p3d_Texture0, uv);

    fragColor = tex * vertex_color;
}""")

GROUND_NOISE_SCALE = 3.5

BOUNDARY_REGION = (-25, -25, 25, 25)
left, bottom, right, top = BOUNDARY_REGION

width = right - left
height = top - bottom

center_x = (right + left) / 2
center_y = (top + bottom) / 2

ground = Entity(
    model='cube',
    scale=(width, 0, height),
    shader=triplanar_shader,
    position=(center_x, center_y),
    texture=generate_noise_texture("world"),
    color=color.rgba(0.5,0.5,0.5,0),
    unlit=True,
)


void = Entity(
    model='plane',
    texture=generate_noise_texture("void"),
    scale=200,
    y=-0.1,
    texture_scale=(5, 5),
    color=color.rgb32(16, 16, 16),
    unlit=True
)

void_noise_timer = 0

ground.set_shader_input(
    "position", Vec2(0)
)

ground.set_shader_input(
    "texture_scale", Vec2(0.05)
)

app.setBackgroundColor(0, 0, 0, 1)
camera.position = (0, 25, 0)
camera.rotation = (90, 0, 0)
camera.orthographic = True
camera.fov = 16

# Tunables ---------------------------------------------------------------

SHOTGUN_PELLET_COUNT = 7        # bullets per shot
SHOTGUN_MAX_AMMO_COUNT = 8      # bullets per reload
SHOTGUN_SPREAD = 12             # half-cone spread in degrees
SHOTGUN_RANGE = 18              # max effective range

# Back-and-forth pump tuning
PUMP_TARGET = 0.75        # total stroke distance to fully pump
PUMP_MIN_STROKE = 0.15      # only here to filter literal pixel jitter
PUMP_STROKES_NEEDED = 2      # 2 reversals = 1 back-and-forths

# -----------------------------
# Player
# -----------------------------

class Player(Entity):
    def __init__(self, speed: int = 2.5, view_cone_range: int = 90, max_health: int = 100):
        super().__init__(
            model="models/player.glb",
            rotation=(0,0,0),
            y=0.3,
            unlit=True,
            shader=triplanar_shader
        )
    
        self.speed = speed
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

        self.shotgun_ammo_count = 0
        self.ammo_packets_count = 0
        self.reloading = False
        self.reload_step = 0

        self.shotgun_recoil = 0.0
        self.pump_back_amount = 0.0
        self.camera_shake = 0.0

        # Stroke tracking: which way the mouse is currently moving, and how far
        self.pump_stroke_dir = 0          # +1, -1, or 0 (no stroke in progress)
        self.pump_stroke_dist = 0.0       # distance traveled in the current stroke
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
        print("player initialized:")
        print("    model:", self.model)
        print("    available animation:")
        print("\n        "+"\n        ".join(self.anim_controls.keys()))
        print("    animation:", self.animation)
    
    def update_player(self, dt):
        self.update_shotgun(dt)
        
        # rotation always tracks the mouse so the crosshair lines up with the aim
        rad = -math.radians(self.rotation_y)
        if self.shotgun_ready:
            self.rotation_y = math.degrees(
                math.atan2(-mouse.y, mouse.x)
            )
            self.direction = Vec3(math.cos(rad), 0, math.sin(rad))
        
        # movement
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
                    Audio(Path("audio/step.mp3"))

                self.prev_frame_num = self.anim_controls[self.animation].getFrame()
                self.position += movement * (self.speed * (2 if held_keys["left shift"] else 1)) * dt
                self.position = Vec3(clamp(self.position.x, BOUNDARY_REGION[0], BOUNDARY_REGION[2]), 0.3, clamp(self.position.z, BOUNDARY_REGION[1], BOUNDARY_REGION[3]))
            elif not self.anim_controls["idle"].playing:
                self.animation = "idle"
                self.anim_controls["idle"].play()
                self.prev_frame_num = -1
            
            if self.animation != "idle":
                if held_keys["left shift"]:
                    self.anim_controls[self.animation].setPlayRate(2)
                else:
                    self.anim_controls[self.animation].setPlayRate(1)
            
        # Camera follow with shake
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
        Audio(Path("audio/shotgun/clink.mp3"))
        
        # ----- bullets hit detection with spread ----------------------------
        bullets_hit: dict[Enemy, float] = {}
        player_angle = - math.radians(self.rotation_y)
        player_dir = Vec3(math.cos(player_angle), 0, math.sin(player_angle))
        for _ in range(SHOTGUN_PELLET_COUNT):
            # random angle inside the spread cone
            spread = random.uniform(-SHOTGUN_SPREAD, SHOTGUN_SPREAD)/(1 + 0.5*(self.move_input.length() == 0 and not held_keys["left shift"]))
            bullets_angle = - math.radians(self.rotation_y+spread)

            # bullets direction in world space (matches the forward vector formula)
            dir_x =  math.cos(bullets_angle)
            dir_z =  math.sin(bullets_angle)

            hit = False
            for entity in enemies:
                # vector from this to enemies
                dx = entity.x - self.x
                dz = entity.z - self.z
                
                # project the entity onto the bullets ray -- t is the distance along the ray
                t = dx * dir_x + dz * dir_z-1
                
                if 0 < t < SHOTGUN_RANGE:
                    # closest point on the ray to the entity center
                    closest_x = self.x + t * dir_x
                    closest_z = self.z + t * dir_z
                    
                    # World-space offset from entity center
                    ox = closest_x - entity.x
                    oz = closest_z - entity.z

                    # Rotate into entity local space
                    angle = - math.radians(entity.rotation_y)
                    c = cos(angle)
                    s = sin(angle)
                    local_x = ox * c - oz * s
                    local_z = ox * s + oz * c

                    # Half extents of the hitbox
                    half_x = entity.scale.x * 2
                    half_z = entity.scale.z * 2

                    if abs(local_x) <= half_x and abs(local_z) <= half_z:
                        if (t <= 1.5):
                            rangeMultiplier = 1.0
                        else:
                            rangeMultiplier = max(0.0, 1.0 - ((t - 1.5) / 23.5))

                        bullets_hit[entity] = bullets_hit.get(entity, 0) + (25/SHOTGUN_PELLET_COUNT * rangeMultiplier * random.uniform(0.95, 1.05))
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

    def update_shotgun(self, dt):
        # --- Pump: each reversal is one "stroke", need 2 to strokes ---
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

            # Direction the shotgun is pointing
            aim_dir = Vec2(
                cos(angle),
                - sin(angle)
            )

            # How much mouse movement happened along the shotgun direction
            mouse_delta = (mouse.x - self.last_mouse_x) * aim_dir.x + (mouse.y - self.last_mouse_y) * aim_dir.y
            if abs(mouse_delta) > 0.0001:
                current_dir = 1 if mouse_delta > 0 else -1
                if self.pump_stroke_dir == 0 and current_dir == -1:
                    # First motion -- just start tracking
                    self.pump_stroke_dir = current_dir
                    self.pump_stroke_dist = abs(mouse_delta)
                if current_dir == self.pump_stroke_dir:
                    # Same direction, keep accumulating this stroke until it gets 
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

        # Apply recoil + pump to the model
        angle = math.radians(self.rotation_z)

        # Direction shotgun is pointing
        aim_dir = Vec2(
            cos(angle),
            sin(angle)
        )

        # Recoil pushes backward (opposite aim)
        self.shotgun_recoil = max(0, self.shotgun_recoil - dt * 6)
        recoil_offset = -aim_dir * self.shotgun_recoil * 0.12

        # Pump moves along the shotgun direction
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

        # Pump bar and crosshair
        if self.shotgun_pumping:
            if dialog_id > 3:
                crosshair.color = color.rgb32(255, 0, 0)
            crosshair_ring.color = color.rgb32(255, 0, 0)
            
            crosshair.position = (mouse.x, mouse.y, -2)
            
            fill = self.pump_progress
            pump_bar_fill.scale_x = (fill - 0.01) / 2
            pump_bar_fill.x = 0
            pump_bar_fill.color = color.rgba32(255, 200, 50, 220)
        elif self.shotgun_ready:
            if dialog_id > 3:
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

reload_image = Entity(
    parent=camera.ui,
    model='quad',
    texture='textures/reloading/get_bullet.png',
    scale=(87/100, 13/100),      # Adjust to your image size
    position=(0, 0),        # Center of the screen
    color=color.white,
    enabled=False
)

# Shotgun model -- parented to player, lies flat, points in +x (player forward)
shotgun = Entity(
    parent=player,
    model='quad',
    texture="textures/shotgun.png",
    scale=(1.125, 0.125),
    position=(0, 1.512, 0),    # 0.5 in front of player center
    rotation=(90, 0, 0),         # lay flat so it's visible from the top-down camera
    unlit=True,
    enabled=False
)

def reposition():
    shotgun_ammo_ui.x = -window.aspect_ratio / 2 + .02
    ammo_packets_count_ui.x = -window.aspect_ratio / 2 + .02
    tutorial.x = -window.aspect_ratio / 2 + .02

dialog_ui = Text(
    text="test",
    color=color.white,
    origin=(0, -0.5),
    position=(0, -0.475)
)

dialog_text = "where am I?..."
dialog_timer = 0
dialog_id = 0
player.can_move = False

tutorial = Text(
    text="",
    color=color.yellow,
    origin=(-0.5, -0.5),
    position=(-0.5, -0.475)
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

window.on_window_resize = reposition
reposition()

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

# Crosshair (center dot)
crosshair = Entity(
    parent=camera.ui,
    model='quad',
    texture="textures/crosshair.png",
    color=color.rgba32(255, 60, 60, 220),
    scale=(0.05, 0.05),
    z=-1,
    enabled=False
)

# Crosshair ring (slightly larger, dimmer)
crosshair_ring = Entity(
    parent=camera.ui,
    model='quad',
    texture="textures/crosshair_ring.png",
    color=color.rgba32(255, 60, 60, 80),
    scale=(0.05, 0.05),
    z=-2,
    enabled=False
)

# Pump progress bar background (bottom of screen)
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

# -----------------------------
# enemies
# -----------------------------

class Item(Entity):
    def __init__(self, item_name: str, position: tuple[int, int, int] = (0, 1.3, 0), gather_distance: float = 0.5, enabled: bool = True):
        super().__init__(
            model="sphere",
            scale=(0.75,0,0.75),
            unlit=True,
            rotation=(0,0,0),
            position=position,
            shader=triplanar_shader,
            texture=generate_noise_texture("item_"+item_name, 15, 15),
            enabled=enabled
        )
        
        self.label = Text(
            text=item_name.upper(),
            parent=self,
            rotation=(0,0,0),
            origin=(0, 0),
            z=1,
            billboard=True,
            world_scale=(9.5,0.01875)
        )

        self.item_name = item_name
        self.gather_distance = gather_distance
        self.fade_in_timer = 0

        self.set_shader_input(
            "position",
            Vec2(0)
        )
        
        self.set_shader_input(
            "texture_scale",
            Vec2(1/self.scale.x, 1/self.scale.y)
        )
        
        print(f"added items to the map:")
        print("    item name:", item_name.upper())
        print("    gathering distance:", gather_distance)
    
    def update_item(self, dt):
        global dialog_text, dialog_timer, dialog_id
        if self.fade_in_timer < 1:
            self.fade_in_timer += dt
            
        if random.random() > 0.5:
            itemColor = color.Color(color.random_color()*color.gray)
        else:
            itemColor = color.gray

        self.color = color.rgba(itemColor.r,itemColor.b,itemColor.g,self.fade_in_timer)
        self.label.color = color.rgba(1,1,1,self.fade_in_timer)
        
        self.texture = generate_noise_texture("item_"+self.item_name+str(dt*100), 10, 10)
        if distance_xz(self.position, player.position - player.direction/2) <= self.gather_distance*self.scale.length():
            if dialog_id == 3:
                dialog_timer = 0
                tutorial.text = ""
                dialog_text = "it seems there are items here that pulse fast in random colors, weird."
                player.can_move = False

            self.give(distance_xz(self.position, player.position - player.direction), dt)
            items.remove(self)
            destroy(self)

    def give(self, distance, dt):
        pass

class ammoBox(Item):
    def __init__(self, position = (0, 1.3, 0)):
        super().__init__("ammo box", position, 0.5)

    def give(self, distance, dt):
        player.ammo_packets_count += 8

class medicine(Item):
    def __init__(self, position = (0, 1.3, 0)):
        super().__init__("medicine", position, 0.25)

    def give(self, distance, dt):
        player.health = min(player.health + player.max_health/10, player.max_health)

class fullMedicineKit(Item):
    def __init__(self, position = (0, 1.3, 0)):
        super().__init__("full medicine kit", position, 0.5)

    def give(self, distance, dt):
        player.health = player.max_health

class Enemy(Entity):
    def __init__(self, model: str, position: tuple[int, int, int] = (0, 1.3, 0), scale: float | Vec2 | Vec3 = 1, max_health: int = 100, color: color.Color = color.white, enabled: bool = True):
        super().__init__(
            model=model,
            scale=scale,
            unlit=True,
            rotation=(0,0,0),
            position=position,
            shader=triplanar_shader,
            color=color,
            enabled=enabled
        )

        self.set_shader_input(
            "position",
            Vec2(0)
        )
        
        self.health = self.max_health = max_health
        self.damage_flash = 0
        self.death_flash = 0
        
        if not hasattr(self, "texture_scale"):
            self.texture_scale = Vec2(scale) if isinstance(scale, (float, int)) else Vec2(scale.x, scale.z)
        
        self.set_shader_input(
            "texture_scale",
            self.texture_scale
        )

    def update_entity(self, dt):
        pass
    
    def damage(self, damage: int):
        if self.health == 0:
            return

        self.health = max(0, self.health - damage)

        if self.health == 0:
            self.death_flash = 1
            return True
        else:
            self.damage_flash = 0.5
        return False
    
    def attack(self, damage: int):
        damage_mul = self.scale.length()*(1-(self.max_health/self.health if self.health > 0 else 0))
        player.health = max(player.health - damage_mul*damage, 0)
        if player.health > 0:
            trigger_screen_shift()
        else:
            trigger_screen_fade()

class Staticon(Enemy):
    def __init__(self, position: tuple[int, int, int] = (0, 1.3, 0), speed: float = 4, size: int = 1, attack_range: int = 1, awareness_range: int = 10, max_health: int = 100, base_color: color.Color = color.gray, ai_active: bool = True, enabled: bool = False):
        super().__init__(
            model="models/staticon.glb",
            scale=size,
            position=position,
            max_health=max_health,
            color=base_color,
            enabled=enabled
        )
        
        self.speed=speed
        self.ai_active = ai_active
        self.base_color = base_color
        self.texture = generate_noise_texture("hidden_entity_"+str(random.randint(0,1000000)))

        self.set_shader_input(
            "texture_scale",
            Vec2(
                GROUND_NOISE_SCALE/64,
                GROUND_NOISE_SCALE/64,
            )
        )
        
        self.is_moving = False

        self.attack_range = attack_range
        self.awareness_range = awareness_range

        char = self.model.find("**/+Character").node()
        part_bundle = char.getBundle(0)

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
    
        self.anim_controls["attack"].setPlayRate(0.75)
        self.anim_controls["walking"].setPlayRate(2)
        self.anim_controls["idle"].play()
        
        print("a staticon has been summoned:")
        print("    model:", self.model)
        print("    available animation:")
        print("\n        "+"\n        ".join(self.anim_controls.keys()).upper())
        print("    animation:", "idle")
        print("    stats:")
        print("        SPEED:", self.speed)
        print("        SIZE:", self.scale.length())
        print("        HEALTH/MAX_HEALTH:", self.health)
        print("        ATTACK_RANGE:", self.attack_range)
        print("        AWARENESS_RANGE:", self.awareness_range)
        print("    game ai:", self.ai_active)

    def damage(self, damage: int):
        damaged = super().damage(damage)
        if damaged == "":
            return
        player_dist = Vec3(
            self.x - player.x,
            0,
            self.z - player.z
        ).length()

        vol = (20 / player_dist) if player_dist > 0 else 0

        if damaged:
            Audio("audio/spider/death.mp3", volume=vol/2)
            self.update_texture_offset()
        else:
            Audio("audio/spider/hit.mp3", volume=vol)
    
    def update_texture_offset(self):
        self.set_shader_input(
            "position",
            Vec2(
                self.x + (not self.is_moving)*0.015*random.uniform(0, 1 - self.health/self.max_health),
                self.z + (not self.is_moving)*0.015*random.uniform(0, 1 - self.health/self.max_health)
            )
        )

    def update_entity(self, dt):
        # Entity death visuals
        if self.death_flash > 0:
            self.death_flash -= dt
            self.color = color.hsv(
                0,
                self.death_flash,
                self.death_flash
            )
        elif self.health != 0 and self.damage_flash > 0:
            self.damage_flash -= dt
            self.color = color.hsv(
                random.randint(0,360),
                lerp(0.75, self.base_color.s, 1-self.damage_flash),
                lerp(self.health/self.max_health, self.base_color.v, 1-self.damage_flash),
            )
            
            self.texture = generate_noise_texture("hidden_entity_"+str(random.randint(0,1000000)))
        elif self.health != 0:
            self.damage_flash = 0
            self.color = self.base_color

        # Entity AI
        if self.health != 0 and self.ai_active:
            to_self = Vec3(
                self.x - player.x,
                0,
                self.z - player.z
            )
            self.is_moving = False
            dist = max(to_self.length() - self.scale.length() / 2, 0)
            if self.awareness_range > dist:
                direction = to_self.normalized()
                forward = Vec3(
                    math.cos(-math.radians(player.rotation_y)),
                    0,
                    math.sin(-math.radians(player.rotation_y))
                )
                angle = math.degrees(
                    math.acos(
                        clamp(forward.dot(direction), -1, 1)
                    )
                )
                if angle > player.view_cone_half_angle or self.awareness_range > dist > self.awareness_range/1.5:
                    target_rotation_y = math.degrees(math.atan2(direction.x, direction.z))
                    self.rotation_y = lerp_angle(self.rotation_y, target_rotation_y, time.dt * 5)
                    
                    if dist <= self.attack_range*self.scale.length():
                        if not self.anim_controls["attack"].is_playing():
                            self.anim_controls["attack"].play()
                    else:
                        self.position -= direction * min(
                            self.speed * dt * self.scale.length(),
                            dist
                        )
                        self.is_moving = True
                        if not self.anim_controls["walking"].is_playing():
                            self.anim_controls["walking"].play()
            elif self.anim_controls["attack"].get_frame() < 15:
                self.anim_controls["attack"].stop()

            if self.anim_controls["attack"].get_frame() == 15:
                self.attack(16)
            if dist <= 1 and not self.anim_controls["attack"].is_playing():
                self.anim_controls["idle"].play()

        if self.health != 0:
            self.update_texture_offset()

class Obeliskus(Enemy):
    def __init__(self, position: tuple[int, int, int] = (0, 1.3, 0), speed: float = 4.5, size: int = 1, attack_range: int = 1, awareness_range: int = 10, max_health: int = 100, ai_active: bool = True, enabled: bool = False):
        super().__init__(
            model="models/obeliskus.glb",
            position=position,
            scale=size,
            max_health=max_health,
            enabled=enabled
        )
        
        char = self.model.find("**/+Character").node()
        part_bundle = char.getBundle(0)

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

        self.ai_active = ai_active
        self.speed=speed
        self.attack_range = attack_range
        self.awareness_range = awareness_range
        self.attacked_timer = 0
        self.anim_controls["hit"].setPlayRate(0.5)
        self.anim_controls["idle"].play()
        
        print("a obeliskus has been summoned:")
        print("    model:", self.model)
        print("    available animation:")
        print("\n        "+"\n        ".join(self.anim_controls.keys()).upper())
        print("    animation:", "idle")
        print("    stats:")
        print("        SPEED:", self.speed)
        print("        SIZE:", self.scale.length())
        print("        HEALTH/MAX_HEALTH:", self.health)
        print("        ATTACK_RANGE:", self.attack_range)
        print("        AWARENESS_RANGE:", self.awareness_range)
        print("    game ai:", self.ai_active)

    def update_entity(self, dt):
        # Entity death visuals
        if self.death_flash > 0:
            self.death_flash -= dt
            self.color = color.hsv(
                0,
                1,
                self.death_flash
            )
        elif self.health != 0 and self.attacked_timer > 0:
            self.attacked_timer -= dt
            self.color = color.hsv(
                0,
                0,
                lerp(1, 0, 1-1/(self.attacked_timer)),
            )
    
        elif self.health != 0:
            self.attacked_timer = 0
            self.color = color.white

        # Entity AI
        if self.health != 0 and self.ai_active:
            to_self = Vec3(
                self.x - player.x,
                0,
                self.z - player.z
            )
            dist = max(to_self.length() - self.scale.length() / 2, 0)
            if self.awareness_range > dist:
                direction = to_self.normalized()
                if self.attacked_timer <= 0:
                    target_rotation_y = math.degrees(math.atan2(to_self.x, to_self.z))
                    angle_diff = abs(((target_rotation_y % 360) - (self.rotation_y % 360) + 180) % 360 - 180)
                    if angle_diff > 4:
                        print(angle_diff)
                        self.rotation_y = lerp_angle(self.rotation_y, target_rotation_y, time.dt * 5)
                    else:
                        if dist <= self.attack_range*self.scale.length():
                            if not self.anim_controls["bite"].is_playing():
                                self.anim_controls["bite"].play()
                        else:
                            self.position -= direction * min(
                                self.speed * dt * self.scale.length() * (self.health/self.max_health),
                                dist
                            )

                            if not self.anim_controls["move"].is_playing():
                                self.anim_controls["move"].play()

            if self.attack_range*self.scale.length() < dist:
                if self.anim_controls["bite"].get_frame() < 15:
                    self.anim_controls["bite"].stop()
                
                elif 15 < self.anim_controls["bite"].get_frame() < 27:
                    self.anim_controls["bite"].stop()

                elif 27 < self.anim_controls["bite"].get_frame() < 41:
                    self.anim_controls["bite"].stop()

                if self.anim_controls["bite"].get_frame() in [15, 27, 41]:
                    self.attack(5)

            dx = player.x - self.x
            dz = player.z - self.z

            target_rotation_y = math.degrees(math.atan2(dx, dz))
            angle_diff = ((target_rotation_y % 360) - (self.rotation_y % 360) + 180) % 360 - 180

            if (dist <= 1 or self.attacked_timer > 0) and not self.anim_controls["bite"].is_playing() or angle_diff > 4:
                self.anim_controls["idle"].play()

    def damage(self, damage):
        if super().damage(damage) != "":
            self.attacked_timer = 6 + self.attacked_timer/3
            self.anim_controls["hit"].setPlayRate(0.5*self.health/self.max_health)

class Maime(Enemy):
    def __init__(self, item: Item, speed: float = 4, size: int = 1, attack_range: int = 1, awareness_range: int = 10, max_health: int = 100, ai_active: bool = True, exposed: bool = False, enabled: bool = False):
        self.texture_scale = Vec2(15/item.scale.x, 15/item.scale.y)
        super().__init__(
            item.model,
            position=item.position,
            scale=item.scale,
            max_health=max_health,
            enabled=enabled
        )
        
        self.health = max_health
        self.awareness_range = awareness_range
        self.size = size
        self.attack_range = attack_range
        self.speed = speed
        self.exposed = exposed
        self.timer = 0
        self.itemData = (item.model, item.scale)
        self.fade_in_timer = 0
        self.ai_active = ai_active
        self.itemColor = self.color = color.random_color()*color.gray
        self.texture = generate_noise_texture("maime_0", 15, 15)

        if not self.exposed:
            item.label.parent = self
            self.label = item.label

        destroy(item)
        
        print("a maime has been summoned:")
        print("    item disguised:", self.model)
        print("        MODEL:", self.itemData[0])
        print("        SCALE:", self.itemData[1])
        # print("    available animation:")
        # print("\n        ".join(self.anim_controls.keys()).upper())
        # print("    animation:", "idle")
        print("    stats:")
        print("        SPEED:", self.speed)
        print("        SIZE:", self.scale.length())
        print("        HEALTH/MAX_HEALTH:", self.health)
        print("        ATTACK_RANGE:", self.attack_range)
        print("        AWARENESS_RANGE:", self.awareness_range)
        print("    game ai:", self.ai_active)
    
    def update_entity(self, dt):
        if self.fade_in_timer < 1:
            self.fade_in_timer += dt
            
        if self.health != 0 and self.ai_active:
            if not self.exposed:
                self.color = color.rgba(self.itemColor.r,self.itemColor.b,self.itemColor.g,self.fade_in_timer)
                self.timer += dt
                if self.timer >= 1:
                    if random.random() > 0.5:
                        self.itemColor = color.Color(color.random_color()*color.gray)
                    else:
                        self.itemColor = color.gray
                                    
                    self.texture = generate_noise_texture("maime_"+str(dt*100), 15, 15)
                    self.timer = 0

                if distance_xz(self, player) <= self.awareness_range/2*self.scale.length():
                    self.model = "cube"
                    self.texture = ""
                    self.color = color.rgba(color.gray.r,color.gray.b,color.gray.g,self.fade_in_timer)
                    self.exposed = True
                    self.label.disable()
            elif distance_xz(self, player) > self.awareness_range/2*self.scale.length():
                self.exposed = False
                self.model = self.itemData[0]
                self.scale = self.itemData[1]
                self.label.enable()
            else:
                to_self = Vec3(
                    self.x - player.x,
                    0,
                    self.z - player.z
                )
                dist = max(to_self.length() - self.scale.length() / 2, 0)
                print(dist)
                direction = to_self.normalized()
                if dist > 0.05:
                    if dist <= self.attack_range*self.scale.length():
                        pass
                    else:
                        self.position -= direction * min(
                            self.speed * dt * self.scale.length(),
                            dist
                        )

#? other enemy ideas:
# - Diatom: if you look at him he will slowly born you
# health: 20



# -----------------------------
# Rune statues
# -----------------------------
class Rune(Entity):
    def __init__(self, rune_name: str, position: tuple[int, int, int] = (0,0.3,0), activation_distance: int = 1, uses: int = -1, enabled: bool = True):
        super().__init__(
            model= "quad",
            scale=(1, 0, 1),
            position=position,
            color=color.white,
            enabled=enabled
        )
        self.uses = uses
        self.used = False
        self.activation_distance = activation_distance
        self.rune_name = rune_name
        
        self.label = Text(
            text=rune_name.upper(),
            parent=self,
            rotation=(0,0,0),
            origin=(0, 0),
            billboard=True,
            world_scale=(9.5,0.01875),
            enabled=False
        )
    
    def update_rune(self, dt):
        self.rotation_y += dt*10
        if distance_xz(self.position, player.position - player.direction/2) <= self.activation_distance*self.scale.length() and not self.used:
            self.used = True
            self.action(dt)
            if self.uses > 0:
                self.uses -= 1
            if self.uses == 0:
                runes.remove(self)
                destroy(self)

        self.label.color = color.orange if self.used else color.white
        if distance_xz(self.position, player.position - player.direction/2) <= self.activation_distance*2*self.scale.length():
            self.label.enable()
        else:
            self.label.disable()

    def action(self, dt):
        pass

class WhisperRune(Rune):
    def __init__(self, position = (0, 0.3, 0), uses = -1):
        super().__init__("Whisper Rune", position, uses=uses)

    def action(self, dt):
        global dialog_id, dialog_text, dialog_timer
        dialog_timer = 0
        dialog_text = "there are {0} whispers still alive".format(len(enemies))
        dialog_id = 5

class HarmRune(Rune):
    def __init__(self, position = (0, 0.3, 0), uses = 2):
        super().__init__("Harm Rune", position, uses=uses)

    def action(self, dt):
        for enemy in enemies:
            enemy.damage(8*self.uses)

# -----------------------------
# Attack effect
# -----------------------------

screen_shift_strength = 0
screen_fade_animation = 0
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

def trigger_screen_shift():
    global screen_shift_strength
    screen_shift_strength = 0.5

def trigger_screen_fade():
    global screen_fade_timer, game_over
    game_over = True
    screen_fade_timer = 1

# -----------------------------
# Input
# -----------------------------

skip_to_dialog_id = -1

def input(key):
    global skip_to_dialog_id, enemies, dialog_text, dialog_timer, dialog_id
    if not player.reloading and player.enabled:
        if key == "enter":
            skip_to_dialog_id = dialog_id
        if key == 'left mouse down' and player.shotgun_ammo_count > 0:
            player.shoot()
        elif key == "left mouse down" and player.shotgun_ammo_count == 0:
            Audio("audio/shotgun/empty_clink.mp3")
        elif key == 'r' and player.shotgun_ammo_count < SHOTGUN_MAX_AMMO_COUNT and dialog_id == 4 and dialog_text == "":
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
        elif key == 'c' and dialog_id == 4 and not tutorial.enabled:
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

    if (player.reload_step == 3 or (player.reload_step == 1 and not tutorial.enabled)) and (key == 'up arrow up' or key == "w up"):
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
        if tutorial.enabled:
            enemies.append(Obeliskus((15, 0.3, 15)))
            enemies[0].enable()
            tutorial.disable()
        dialog_id = 4
        dialog_text = ""
        dialog_timer = 0

# -----------------------------
# Main update
# -----------------------------

def power_lerp(x, a=1):
    return 1-math.log(math.cosh((1-2*x)/a))+math.log(math.cosh(1/a))-1

enemies: list[Enemy] = []
items: list[Item] = []
runes: list[Rune] = []

waves: list[dict[str, list[Item] | list[Enemy]]] = []
wave_num = 0

for wave_num in range(5):
    waves.append({"items": [], "enemies": [], "runes": []})
    for _ in range(2*wave_num):
        if wave_num == 0:
            runes.append(WhisperRune((random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[0])/2, 5), 0.3, random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[1])/2, 5))))
        if wave_num >= 3:
            for _ in range(wave_num-1):
                runes.append(HarmRune((random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[0])-1, 12), 0.3, random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[1])-1, 12))))
        waves[-1]["enemies"].append(Staticon((random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[0])-1, 12), 0.3, random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[1])-1, 12))))
        if random.random() < 0.25:
            waves[-1]["items"].append(fullMedicineKit((random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[0])-1, 14), 0.3, random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[0])-1, 14))))
        else:
            waves[-1]["items"].append(medicine((random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[0])-1, 14), 0.3, random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[0])-1, 14))))        
    waves[-1]["items"].append(medicine((random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[0])-1, 14), 0.3, random.choice([-1, 1])*random.uniform(abs(BOUNDARY_REGION[0])-1, 14))))        

game_over = game_won = False
ground.fade_in(1, duration=3)

def update():
    global items, enemies, runes, wave_num
    global screen_shift_strength, screen_fade_animation, void_noise_timer
    global game_won, dialog_timer, dialog_text, dialog_id, skip_to_dialog_id

    dt = time.dt

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

    # Screen effect
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
    if dialog_timer >= len(dialog_text) + 5*(dialog_text.count(" ") + 1) and dialog_text != "" or ((skip_to_dialog_id not in [3, 4] or (skip_to_dialog_id == 3 and player.ammo_packets_count > 0)) and skip_to_dialog_id == dialog_id):
        dialog_id += 1
        dialog_text = ""
        if dialog_id == 1:
            player.can_move = False
            dialog_timer = 0
            dialog_ui.text = ""
            dialog_text = "and why do I have a shotgun?!"
            shotgun_pump.enabled=True
            shotgun.enabled=True
            ground.color = color.gray
            shotgun_pump.color = color.rgba(0,0,0,0)
            shotgun.color = color.rgba(0,0,0,0)
            shotgun_pump.animate_color(color.white, 0.5)
            shotgun.animate_color(color.white, 0.5)
        elif dialog_id == 2:
            player.can_move = False
            dialog_timer = 0
            dialog_ui.text = ""
            dialog_text = "I cant wake up too."
            crosshair.enabled=True
            crosshair_ring.enabled=True
            shotgun_pump.color = color.white
            shotgun.color = color.white
            
            crosshair.fade_in()
            crosshair_ring.color = color.rgba(255, 60, 60, 0)
            crosshair_ring.animate_color(color.rgba32(255, 60, 60, 80), 2)
        elif dialog_id == 3:
            crosshair_ring.color = color.rgb(crosshair_ring.color.r, crosshair_ring.color.g, crosshair_ring.color.b, 1)
            crosshair.color = color.rgb(crosshair.color.r, crosshair.color.g, crosshair.color.b, 1)
            player.can_move = False
            tutorial.text = "TUTORIAL: GO TOUCH THE ITEM"
            items.append(ammoBox((random.uniform(1, 3), 0.3, random.uniform(0, 5))))
            items[0].enable()
            
        elif dialog_id == 4:
            tutorial.text = "TUTORIAL: PRESS R TO LOAD SHOTGUN"
    skip_to_dialog_id = -1
    
    if dialog_text != "":
        if dialog_id == 3:
            tutorial.text = ""
        dialog_timer += dt*15
        dialog_ui.text = dialog_text[:int(min(dialog_timer, len(dialog_text)))]
    else:
        dialog_timer = 0
        dialog_ui.text = ""
        player.can_move = True

    # Void
    void.position = (
        player.x,
        -0.1,
        player.z
    )

    void_noise_timer += dt
    if void_noise_timer > 1.5:
        void_noise_timer = 0
        void.texture = generate_noise_texture("void_"+ str(int(random.random()*10)))

    alive_enemies = 0
    for entity in enemies:
        entity.update_entity(dt)
        if entity.health > 0:
            alive_enemies += 1

    for item in items:
        item.update_item(dt)
        
    for rune in runes:
        rune.update_rune(dt)

    if alive_enemies == 0 and dialog_id > 4:
        wave_num += 1
        if wave_num-1 < len(waves):
            for item in waves[wave_num-1]["items"]:
                items.append(duplicate(item, enabled=True))

            for enemy in waves[wave_num-1]["enemies"]:
                enemies.append(duplicate(enemy, enabled=True))

            for rune in waves[wave_num-1]["runes"]:
                runes.append(duplicate(rune, enabled=True))
        else:
            game_won = True
            screen_fade_animation = 1

app.run()