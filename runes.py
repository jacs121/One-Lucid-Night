from util import *
from entities import player

class Rune(Entity):
    def __init__(self, rune_name: str, position: tuple[int, int, int] = (0,1,0), size: int = 1, activation_distance: int = 1, required_experience: float = 0, uses: int = -1, enabled: bool = False):
        super().__init__(
            model="cube",
            scale=(size, 1, size),
            position=position,
            enabled=enabled
        )

        self.uses = uses
        self.used = False
        self.activation_distance = activation_distance
        self.required_experience = required_experience
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
        if distance_xz(self.position, player.position - player.direction/2) <= self.activation_distance and not self.used and held_keys["space"] and player.experience >= self.required_experience:
            self.used = True
            player.experience -= self.required_experience
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
    def __init__(self, position = (0, 1, 0), uses = 3, enabled: bool = False, required_experience: float = 5):
        super().__init__("Whisper Rune", position, uses=uses, enabled=enabled, required_experience=required_experience)

    def action(self, dt):
        global dialog_id, dialog_text, dialog_timer
        dialog_timer = 0
        dialog_text = "there are {0} whispers still alive".format(len(enemies))
        dialog_id = 5

class sharpenRune(Rune):
    def __init__(self, position = (0, 1, 0), uses = 3, enabled: bool = False, required_experience: float = 10):
        super().__init__("Sharpen Rune", position, uses=uses, enabled=enabled, required_experience=required_experience)

    def action(self, dt):
        player.attack_damage += player.attack_damage/5

class HarmRune(Rune):
    def __init__(self, position = (0, 1, 0), uses = 2, enabled: bool = False, required_experience: float = 6):
        super().__init__("Harm Rune", position, uses=uses, enabled=enabled, required_experience=required_experience)

    def action(self, dt):
        self.required_experience = 10/self.uses
        for enemy in enemies:
            enemy.damage(8*self.uses)

class AdvancingRune(Rune):
    def __init__(self, position = (0, 1, 0), uses = -1, enabled = False, required_experience: float = 0):
        super().__init__("Advancing Rune", position, uses=uses, enabled=enabled, required_experience=required_experience)
        self.color = color.hsv(0, 1, 0.5)

        if self.enabled:
            self.sound = Audio('audio/runes/advancing_rune.mp3', autoplay=True, loop=True)

    def action(self, dt):
        global wave_num, items, enemies, runes, game_won, screen_fade_animation, tutorial_ended
        
        wave_num += 1
        if wave_num-1 < len(waves):
            for itemData in waves[wave_num-1]["items"]:
                items.append(duplicate(itemData.pop("item")(**itemData), enabled=True))

            for enemyData in waves[wave_num-1]["enemies"]:
                if "item" in enemyData.keys():
                    enemyData["item"] = enemyData["item"].pop("entity")(**enemyData["item"])
                enemies.append(duplicate(enemyData.pop("enemy")(**enemyData), enabled=True))

            for runeData in waves[wave_num-1]["runes"]:
                runes.append(duplicate(runeData.pop("runes")(**runeData), enabled=True))
        else:
            game_won = True
            screen_fade_animation = 1

        self.uses = 0
        self.sound.stop()
        if not tutorial_ended:
            tutorial_ended = True

    def update_rune(self, dt):
        if super().update_rune(dt):
            panning = (self.x - camera.x) / 10
            self.sound.balance = clamp(panning, -1, 1)

            distance = distance_xz(self.position, camera.position)
            self.color = color.hsv(0, 1, 0.5*(1-1/distance) if distance > 0 else 0)
            self.sound.volume = clamp(1 / (1 + distance * 0.1), 0, 1)