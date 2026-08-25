from imports import *

title = "One Lucid Night"
app = Ursina(title)

paused_audio: set[int] = set()

def pauseAllAudio(pause: bool):
    if pause:
        for entity in scene.entities:
            if isinstance(entity, Audio) and entity.playing:
                entity.pause()
                paused_audio.add(id(entity))
    else:
        for entity in scene.entities:
            if isinstance(entity, Audio) and id(entity) in paused_audio:
                entity.resume()

        paused_audio.clear()

def pauseAllSequences(pause: bool):
    for entity in scene.entities:
        if isinstance(entity, Entity):
            for animation in entity.animations:
                if isinstance(entity, Sequence):
                    if pause:
                        animation.pause()
                    else:
                        animation.resume()

def generate_noise_texture(seed: str, width: int = 512, height: int = 512, min_value: int = 0, max_value: int = 255):
    data = seed.encode('utf-8')
    mat = np.array(list(hashlib.shake_256(data).digest(width * height)), dtype=np.uint8)

    scaled = (
        mat.astype(np.float32)
        * (max_value - min_value)
        / 255
        + min_value
    ).astype(np.uint8)

    img = Image.fromarray(
        scaled.reshape(height, width),
        'L'
    )
    return Texture(img)

def generate_triangle_texture(seed: str, width=512, height=512, min_value: int = 0, max_value: int = 255):
    data = seed.encode("utf-8")
    seed_int = int.from_bytes(hashlib.sha512(data).digest(), byteorder="big")
    random = np.random.RandomState(seed_int % (2**32))

    num_points = 150
    points = random.rand(num_points, 2) * [width - 24, height - 24]
    corners = np.array([[0, 0], [width, 0], [0, height], [width, height]])
    all_points = np.vstack([points, corners])

    tri = Delaunay(all_points)

    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)

    for simplex in tri.simplices:
        p1 = tuple(all_points[simplex[0]])
        p2 = tuple(all_points[simplex[1]])
        p3 = tuple(all_points[simplex[2]])

        color = random.randint(min_value, max_value)
        draw.polygon([p1, p2, p3], fill=(color, color, color))

    return Texture(image)

def generate_eye_blob(
        eye_seed: int,
        resolution: int = 256,
        radius_x: float = 0.30,
        radius_y: float = 0.16,
        randomness: float = 0.18,
        num_points: int = 24,
        scale: tuple[float, float] = (1.0, 0.5)
    ):

    np.random.seed(eye_seed)
    lin = np.linspace(-1.0, 1.0, resolution)
    X, Y = np.meshgrid(lin, lin)

    Angle = np.arctan2(Y, X)

    angles = np.linspace(-np.pi, np.pi, num_points, endpoint=False)

    random_radius = np.random.uniform(
        1.0 - randomness,
        1.0 + randomness,
        num_points
    )

    extended_angles = np.r_[angles - 2*np.pi, angles, angles + 2*np.pi]
    extended_radius = np.tile(random_radius, 3)

    radius_random = np.interp(
        Angle.ravel(),
        extended_angles,
        extended_radius
    ).reshape(Angle.shape)

    base_radius = (
        np.abs(np.sin(Angle)) ** 0.55
        + 0.12
    )

    boundary_x = radius_x * radius_random
    boundary_y = boundary_x * base_radius

    normalized_x = (X / boundary_x) / scale[0]
    normalized_y = (Y / boundary_y) / scale[1]

    blob = (normalized_x ** 2 + normalized_y ** 2) <= 1.0

    alpha = blob.astype(np.uint8) * 255
    black = np.full(
        (resolution, resolution),
        0,
        dtype=np.uint8
    )

    return Image.fromarray(
        np.dstack((black, black, black, alpha))
    )


def generate_spike_ball(
        seed: int,
        resolution: int = 256,
        base_radius: float = 0.25,
        num_spikes: int = 35,
        min_len: float = 0.25,
        max_len: float = 0.64,
        spike_sharpness: float = 4.5
    ):
    np.random.seed(seed)
    lin = np.linspace(-1.0, 1.0, resolution)
    X, Y = np.meshgrid(lin, lin)

    R = np.sqrt(X**2 + Y**2)
    Angle = np.arctan2(Y, X)

    spike_angles = np.linspace(-np.pi, np.pi, num_spikes, endpoint=False)
    spike_angles += np.random.uniform(-0.04, 0.04, num_spikes)
    spike_lengths = np.random.uniform(min_len, max_len, num_spikes)

    boundary_radius = np.zeros_like(Angle) + base_radius

    for angle, length in zip(spike_angles, spike_lengths):
        angular_distance = np.abs(Angle - angle)
        angular_distance = np.minimum(angular_distance, 2 * np.pi - angular_distance)

        max_width = (2 * np.pi / num_spikes) * 0.8

        normalized_dist = np.maximum(0, 1 - (angular_distance / max_width))
        spike_contour = (normalized_dist ** spike_sharpness) * length
        boundary_radius = np.maximum(boundary_radius, base_radius + spike_contour)

    bw_texture = (R <= boundary_radius).astype(np.uint8) * 255
    white_channel = np.full((resolution, resolution), 255, dtype=np.uint8)

    texture = Image.fromarray(np.dstack((white_channel, white_channel, white_channel, bw_texture)))
    return texture

def generate_sun_with_eye(eye_seed: int, sun_seed: int, resolution: int = 256, eye_size_ratio: float = 0.35, eye_open_ratio: float = 0.5):
    texture = generate_spike_ball(sun_seed, resolution)

    eye = generate_eye_blob(
        eye_seed,
        resolution=int(resolution*eye_size_ratio),
        radius_x=0.30,
        radius_y=0.16,
        randomness=0.25,
        scale=(max(1, eye_open_ratio),min(1, eye_open_ratio))
    )

    texture.paste(eye, (int(resolution/2-eye.width/2), int(resolution/2-eye.height/2), int(resolution/2+eye.width/2), int(resolution/2+eye.height/2)), eye)
    return Texture(texture)

class SceneTypes(StrEnum):
    MAIN_MENU = auto()
    GAME = auto()
    ESCAPE = auto()

@dataclass
class GameState:
    enemies: list
    items: list
    runes: list

    wave_num: int
    game_over: bool
    game_won: bool
    tutorial_ended: bool

    scene_type: SceneTypes

    waves: list[dict[str, list]]
    waiting_to_advance: bool
    update_crosshair: bool

    screen_fade_animation: float
    screen_shift_strength: float
    screen_fade_timer: float
    void_noise_timer: float

    alive_enemies: int

    @classmethod
    def default(cls):
        return cls([], [], [], 0, False, False, False, SceneTypes.MAIN_MENU, [], False, False, 0, 0, 0, 0, 0)

d_ctx = zstd.ZstdDecompressor()
c_ctx = zstd.ZstdCompressor(level=3)

@dataclass
class SaveStates:
    first_time: bool
    directional_movement: bool

    @classmethod
    def init(cls, **kwargs):
        kwargs.setdefault("first_time", True)
        kwargs.setdefault("directional_movement", True)
        return cls(**kwargs)

    @classmethod
    def load_file(cls, filename: str):
        return cls.init(**json.loads(d_ctx.decompress(open(filename, "rb").read()).decode()))

    def save_data(self, filename: str):
        compressed_data = c_ctx.compress(str(self).encode('utf-8'))
        open(filename, "wb").write(compressed_data)

    def __str__(self):
        return json.dumps(asdict(self))

gameState = GameState.default()

GROUND_NOISE_SCALE = 3.5

BOUNDARY_REGION = (-25, -25, 25, 25)
left, bottom, right, top = BOUNDARY_REGION

width = right - left
height = top - bottom

center_x = (right + left) / 2
center_y = (top + bottom) / 2

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

app.setBackgroundColor(0, 0, 0, 1)
camera.position = (0, 25, 0)
camera.rotation = (90, 0, 0)
camera.orthographic = True
camera.fov = 16

SHOTGUN_MAX_AMMO_COUNT = 8
SHOTGUN_SPREAD = 12
SHOTGUN_RANGE = 18
PUMP_TARGET = 0.75
PUMP_MIN_STROKE = 0.15
PUMP_STROKES_NEEDED = 2

HWND_BROADCAST = 0xffff
WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1

hwnd = ctypes.windll.user32.FindWindowW(None, title)

icon = ctypes.windll.user32.LoadImageW(
    None,
    application.asset_folder.as_posix() + "/icons/icon.ico",
    1,
    0,
    0,
    0x00000010
)

ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, icon)
ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, icon)

default_player_direction = -math.radians(-90)
