from util import *
from entities import player

class Rune(Entity):
    def __init__(self, rune_name: str, position: tuple[int, int, int] = (0,1,0), size: int = 1, activation_distance: int = 1, uses: int = -1, enabled: bool = False):
        super().__init__(
            model="cube",
            scale=(size, 1, size),
            position=position,
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
            z=5,
            billboard=True,
            world_scale=(9.5,0.01875),
            enabled=False
        )
        self.label.scale *= 5
        self.size = size
        if self.enabled:
            self.scale = Vec3(0)
            self.animate_scale(Vec3(size,1,size), 1)
        
    def update_rune(self, dt):
        global runes
        self.rotation_y += dt*10
        if distance_xz(self.position, player.position - player.direction/2) <= self.activation_distance and not self.used and held_keys["space"]:
            self.used = True
            self.action(dt)
            if self.uses > 0:
                self.uses -= 1
            if self.uses == 0:
                if self in runes:
                    runes.remove(self)
                destroy(self)
                return False

        if distance_xz(self.position, player.position - player.direction/2) <= self.activation_distance*2:
            self.label.enable()
        else:
            self.label.disable()
        
        return True

    def action(self, dt):
        pass

class WhisperRune(Rune):
    def __init__(self, position = (0, 1, 0), uses = 3, enabled: bool = False):
        super().__init__("Whisper Rune", position, uses=uses, enabled=enabled)

    def action(self, dt):
        global dialog_id, dialog_text, dialog_timer
        dialog_timer = 0
        dialog_text = "there are {0} whispers still alive".format(len(enemies))
        dialog_id = 5

class HarmRune(Rune):
    def __init__(self, position = (0, 1, 0), uses = 2, enabled: bool = False):
        super().__init__("Harm Rune", position, uses=uses, enabled=enabled)
        
    def action(self, dt):
        for enemy in enemies:
            enemy.damage(8*self.uses)

class AdvancingRune(Rune):
    def __init__(self, position = (0, 1, 0), uses = -1, enabled = False):
        super().__init__("Advancing Rune", position, uses=uses, enabled=enabled)
        self.color = color.hsv(0, 1, 0.5)

        if self.enabled:
            self.sound = Audio('audio/runes/advancing_rune.mp3', autoplay=True, loop=True)

    def action(self, dt):
        global wave_num, items, enemies, runes, game_won, screen_fade_animation
        
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

        self.uses = 0
        self.sound.stop()

    def update_rune(self, dt):
        if super().update_rune(dt):
            # Dynamically pan left or right based on x-position relative to camera
            # Clamp the balance between -1 (left) and 1 (right)
            panning = (self.x - camera.x) / 10
            self.sound.balance = clamp(panning, -1, 1)

            # reduce volume with distance
            distance = distance_xz(self.position, camera.position)
            self.color = color.hsv(0, 1, 0.5*(1-1/distance))
            self.sound.volume = clamp(1 / (1 + distance * 0.1), 0, 1)