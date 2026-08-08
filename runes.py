from util import *
from entities import player, tutorial, ShowDialog

class Rune(Entity):
    def __init__(self, rune_name: str, position: tuple[int, int, int] = (0,1,0), size: int = 0.5, activation_distance: int = 1, required_experience: float = 0, uses: int = -1):
        super().__init__(
            model="cube",
            scale=(size, 0, size),
            position=position,
            unlit=True,
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
            y=1,
            billboard=True,
            color=color.gray
        )
        self.label.world_scale *= 10

        self.size = size
        if self.enabled:
            self.scale = Vec3(0)
            self.animate_scale(Vec3(size,1,size), 1, curve=curve.linear)

    def update_rune(self, dt):
        self.rotation_y += dt*10
        if distance_xz(self.position, player.position - player.direction/2) <= self.activation_distance and not self.used and held_keys["space"] and player.experience >= self.required_experience:
            self.used = True
            player.experience -= self.required_experience
            self.action(dt)
            if self.uses > 0:
                self.uses -= 1
            if self.uses == 0:
                if self in gameState.runes:
                    gameState.runes.remove(self)
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
    def __init__(self, position = (0, 1, 0), uses = 3, required_experience: float = 5):
        super().__init__("Whisper Rune", position, uses=uses, required_experience=required_experience)

    def action(self, dt):
        ShowDialog("*there are {0} whispers still alive*".format(len(gameState.enemies)))

class BloodRune(Rune):
    def __init__(self, position = (0, 1, 0), uses = 3, required_experience: float = 8):
        super().__init__("Blood Rune", position, uses=uses, required_experience=required_experience)

    def action(self, dt):
        ShowDialog("*you have {0} milliliters of blood left*".format(4500*player.health/player.max_health))

class SharpenRune(Rune):
    def __init__(self, position = (0, 1, 0), uses = 2, required_experience: float = 10):
        super().__init__("Sharpen Rune", position, uses=uses, required_experience=required_experience)

    def action(self, dt):
        player.attack_damage += player.attack_damage/5

class PelletRune(Rune):
    def __init__(self, position = (0, 1, 0), uses = 1, required_experience: float = 15):
        super().__init__("Pellet Rune", position, uses=uses, required_experience=required_experience)

    def action(self, dt):
        player.shotgun_pellet_count += 1

class HarmRune(Rune):
    def __init__(self, position = (0, 1, 0), uses = 2, required_experience: float = 6):
        super().__init__("Harm Rune", position, uses=uses, required_experience=required_experience)

    def action(self, dt):
        self.required_experience = 10/self.uses
        for enemy in gameState.enemies:
            enemy.damage(8*self.uses)

class AdvancingRune(Rune):
    def __init__(self, position = (0, 1, 0), uses = -1, required_experience: float = 0):
        super().__init__("Advancing Rune", position, 1, uses=uses, required_experience=required_experience)
        self.color = color.hsv(0, 1, 0.5)

        if self.enabled:
            self.sound = Audio('audio/runes/advancing_rune.mp3', autoplay=True, loop=True)

    def action(self, dt):
        gameState.wave_num += 1
        if gameState.wave_num-1 < len(gameState.waves):
            for itemData in gameState.waves[gameState.wave_num-1]["items"]:
                gameState.items.append(itemData.pop("item")(**itemData))

            for enemyData in gameState.waves[gameState.wave_num-1]["enemies"]:
                print(enemyData)
                if "item" in enemyData.keys():
                    enemyData["item"] = enemyData["item"].pop("entity")(**enemyData["item"])
                gameState.enemies.append(enemyData.pop("enemy")(**enemyData))

            for runeData in gameState.waves[gameState.wave_num-1]["runes"]:
                gameState.runes.append(runeData.pop("rune")(**runeData))
        else:
            gameState.screen_fade_animation = 1
            gameState.game_won = True
            return False

        gameState.waiting_to_advance = False
        print("advancing wave to #"+str(gameState.wave_num))

        self.uses = 0
        self.sound.stop()
        if not gameState.tutorial_ended:
            gameState.tutorial_ended = True
            tutorial.text = ""
        return True

    def update_rune(self, dt):
        if super().update_rune(dt):
            panning = (self.x - camera.x) / 10
            self.sound.balance = clamp(panning, -2, 2)

            distance = distance_xz(self.position, camera.position)
            self.color = color.hsv(0, 1-1/(distance + 1.5), 1)
            self.label.color = color.hsv(0, 1/(distance + 1.5), 1)
            self.sound.volume = 1 - clamp(distance / distance_2d(Vec2(BOUNDARY_REGION[0], BOUNDARY_REGION[1]), Vec2(BOUNDARY_REGION[2], BOUNDARY_REGION[3])), 0, 1)