from imports import *

title = "One Lucid Night"
app = Ursina(title, fullscreen=True)

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

def generate_triangle_texture(seed: str, width=512, height=512):
    data = seed.encode('utf-8')
    seed = hashlib.sha512(data).digest().decode()
    random = np.random.RandomState(seed)

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

        color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )
        draw.polygon([p1, p2, p3], fill=color)

    return Texture(draw)

@dataclass
class GameState:
    enemies: list
    items: list
    runes: list

    wave_num: int
    game_over: bool
    game_won: bool
    tutorial_ended: bool

    main_menu: bool

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
        return cls([], [], [], 0, False, False, False, True, [], False, False, 0, 0, 0, 0, 0)

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