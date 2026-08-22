from util import *
from entities import tutorial, player, ShowDialog

class Item(Entity):
    def __init__(self, item_name: str, position: tuple[int, int, int] = (0, 1.3, 0), gather_distance: float = 0.5, enabled: bool = True):
        model = "models/items/"+item_name.lower().replace(" ", "_")+".glb"
        if not (application.asset_folder / model).exists():
            print(f"model path for item {model} does not exist falling back to a sphere model")
            model = "sphere"

        super().__init__(
            model=model,
            scale=(0.75,0,0.75),
            unlit=True,
            rotation=(0,0,0),
            position=position,
            shader=triplanar_shader,
            texture=generate_noise_texture("item_"+item_name.lower().replace(" ", "_"), 15, 15),
            enabled=enabled
        )

        self.label = Text(
            text=item_name.upper(),
            parent=self,
            rotation=(0,0,0),
            origin=(0, 0),
            z=1,
            billboard=True
        )
        self.label.world_scale *= 16

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
        if self.enabled:
            print(f"added items to the map:")
            print("    item name:", item_name.upper())
            print("    gathering distance:", gather_distance)

    def update_item(self, dt):
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
            if tutorial.text == "TUTORIAL: TOUCH THE ITEM" and not gameState.tutorial_ended:
                player.can_move = False
                ShowDialog("it seems there are items here that pulse fast in random colors, weird.").dialog_callback = dialogCallback4

            self.give(distance_xz(self.position, player.position - player.direction), dt)
            gameState.items.remove(self)
            destroy(self)

    def give(self, distance, dt):
        pass

def dialogCallback4():
    player.can_move = True
    tutorial.text = "TUTORIAL: PRESS R TO LOAD SHOTGUN"

class AmmoBoxItem(Item):
    def __init__(self, position = (0, 1.3, 0), ammo: int = 8):
        super().__init__("ammo box", position, 0.5)
        self.ammo = ammo

    def give(self, distance, dt):
        player.ammo_packets_count += self.ammo

class MedicineItem(Item):
    def __init__(self, position = (0, 1.3, 0)):
        super().__init__("medicine", position, 0.25)

    def give(self, distance, dt):
        player.health = min(player.health + player.max_health/10, player.max_health)

class FullMedicineKitItem(Item):
    def __init__(self, position = (0, 1.3, 0)):
        super().__init__("full medicine kit", position, 0.5)

    def give(self, distance, dt):
        player.health = player.max_health
