from util import *
from items import Item
from entities import player

class AnimStub:
    def __init__(self):
        self._playing = False
    def setPlayRate(self, r):
        pass
    def play(self):
        self._playing = True
    def stop(self):
        self._playing = False
    def is_playing(self):
        return getattr(self, "_playing", False)
    def get_frame(self):
        return 0

class Enemy(Entity):
    def __init__(self, model: str, position: tuple[int, int, int] = (0, 1.3, 0), scale: float | Vec2 | Vec3 = 1, max_health: int = 20, color: color.Color = color.white, enabled: bool = True):
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

        self.anim_controls = {}
        char_match = self.model.find("**/+Character")
        if not char_match.isEmpty():
            try:
                char = char_match.node()
                part_bundle = char.getBundle(0)

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
            except Exception:
                print("warning: failed to bind animations; using stub controls")
                self.anim_controls = {"idle": AnimStub()}
        else:
            print("warning: model has no Character node; using stub controls")
            self.anim_controls = {"idle": AnimStub()}

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
            gameState.screen_shift_strength = 0.5
            Audio("audio/hurt.mp3")
        else:
            gameState.game_over = True
            gameState.screen_fade_timer = 1
            Audio("audio/hurt.mp3", pitch=0.25)

    def update(self):
        self.position.x = clamp(self.position.x, BOUNDARY_REGION[0]+self.scale.x, BOUNDARY_REGION[2]-self.scale.x)
        self.position.z = clamp(self.position.z, BOUNDARY_REGION[1]+self.scale.z, BOUNDARY_REGION[3]-self.scale.z)

class StaticonEnemy(Enemy):
    def __init__(self, position: tuple[int, int, int] = (0, 1.3, 0), speed: float = 4, size: int = 1, attack_range: int = 1, awareness_range: int = 10, max_health: int = 20, base_color: color.Color = color.gray, ai_active: bool = True):
        super().__init__(
            model="models/staticon.glb",
            scale=size,
            position=position,
            max_health=max_health,
            color=base_color
        )
        
        self.speed=speed
        self.ai_active = ai_active
        self.base_color = base_color
        self.texture = generate_noise_texture("staticon_"+str(random.randint(0,1000000)))

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

        self.anim_controls["attack"].setPlayRate(0.75)
        self.anim_controls["walking"].setPlayRate(2)
        self.anim_controls["idle"].play()
        if self.enabled:
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
            Audio("audio/staticon/death.mp3", volume=vol/2)
            self.update_texture_offset()
        else:
            Audio("audio/staticon/hit.mp3", volume=vol)
    
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

            self.texture = generate_noise_texture("staticon_"+str(random.randint(0,1000000)))
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
                if angle > player.view_cone_half_angle or player.reloading or self.awareness_range > dist > self.awareness_range/1.5:
                    target_rotation_y = math.degrees(math.atan2(direction.x, direction.z))
                    self.rotation_y = lerp_angle(self.rotation_y, target_rotation_y, time.dt * 5)
                    
                    if dist <= self.attack_range*self.scale.length():
                        if not self.anim_controls["attack"].is_playing():
                            self.anim_controls["attack"].play()
                    else:
                        self.position -= direction * min(
                            self.speed * dt * self.scale.length() * (1 - 0.5 * int(player.reloading)),
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

class ObeliskusEnemy(Enemy):
    def __init__(self, position: tuple[int, int, int] = (0, 1.3, 0), speed: float = 4.5, size: int = 1, attack_range: int = 1, awareness_range: int = 10, max_health: int = 50, ai_active: bool = True):
        super().__init__(
            model="models/obeliskus.glb",
            position=position,
            scale=size,
            max_health=max_health
        )

        self.ai_active = ai_active
        self.speed=speed
        self.attack_range = attack_range
        self.awareness_range = awareness_range
        self.attacked_timer = 0
        self.attacking_timer = 0

        if self.enabled:
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

        self.anim_controls["idle"].play()

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

        if self.health != 0 and self.ai_active:
            to_self = Vec3(
                self.x - player.x,
                0,
                self.z - player.z
            )
            dist = max(to_self.length() - self.scale.length() / 2, 0)
            if self.awareness_range > dist:
                if self.attacked_timer <= 0:
                    target_rotation_y = math.degrees(math.atan2(to_self.x, to_self.z))
                    angle_diff = abs(((target_rotation_y % 360) - (self.rotation_y % 360) + 180) % 360 - 180)
                    if angle_diff > 4:
                        self.rotation_y = lerp_angle(self.rotation_y, target_rotation_y, time.dt * 5)
                    else:
                        if dist <= self.attack_range*self.scale.length():
                            if self.attacking_timer <= 0:
                                self.attacking_timer = 2.5
                            else:
                                self.attacking_timer -= dt
                        else:
                            forward = Vec3(
                                math.cos(-math.radians(self.rotation_y+90)),
                                0,
                                math.sin(-math.radians(self.rotation_y+90))
                            )
                            
                            self.position += forward * min(
                                self.speed * dt * self.scale.length() * (self.health/self.max_health) * (1 - 0.5 * int(player.reloading)),
                                dist
                            )
            dx = player.x - self.x
            dz = player.z - self.z

            target_rotation_y = math.degrees(math.atan2(dx, dz))
            angle_diff = ((target_rotation_y % 360) - (self.rotation_y % 360) + 180) % 360 - 180
            if not self.anim_controls["idle"].is_playing():
                self.anim_controls["idle"].play()

    def update_texture(self):
        self.texture = generate_triangle_texture("obeliskus_"+str(int(self.position.x))+"_"+str(int(self.position.z)))

    def damage(self, damage):
        if super().damage(damage) != "":
            self.attacked_timer += 4 - min(self.attacked_timer/4, 3)

class MaimeEnemy(Enemy):
    def __init__(self, item: Item, speed: float = 4, size: int = 1, attack_range: int = 1, awareness_range: int = 10, max_health: int = 100, ai_active: bool = True, exposed: bool = False):
        self.texture_scale = Vec2(15/item.scale.x, 15/item.scale.y)
        super().__init__(
            model="models/maime.glb",
            position=item.position,
            scale=item.scale,
            max_health=max_health
        )

        self.model = item.model
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
        
        if self.enabled:
            print("a maime has been summoned:")
            print("    item disguised:", self.model)
            print("        MODEL: item/", item.label.text.lower().replace(" ", "_"))
            print("        SCALE:", self.itemData[1])
            print("    available animation:")
            print("\n        ".join(self.anim_controls.keys()).upper())
            print("    animation:", "idle")
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
                direction = to_self.normalized()
                if dist > 0.05:
                    if dist <= self.attack_range*self.scale.length():
                        if not self.anim_controls["attack"].is_playing():
                            self.anim_controls["attack"].play()
                    else:
                        self.position -= direction * min(
                            self.speed * dt * self.scale.length() * (1 - 0.5 * int(player.reloading)),
                            dist
                        )

                        if not self.anim_controls["walk"].is_playing():
                            self.anim_controls["walk"].play()

            if self.anim_controls["attack"].get_frame() < 15:
                self.anim_controls["attack"].stop()

            if self.anim_controls["attack"].get_frame() == 15:
                self.attack(5)

            if dist <= 1 and not self.anim_controls["attack"].is_playing():
                self.anim_controls["idle"].play()
