from imports import *

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

        # Random RGB color
        color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )
        draw.polygon([p1, p2, p3], fill=color)
    
    return Texture(draw)


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

# Tunables ---------------------------------------------------------------

SHOTGUN_PELLET_COUNT = 7        # bullets per shot
SHOTGUN_MAX_AMMO_COUNT = 8      # bullets per reload
SHOTGUN_SPREAD = 12             # half-cone spread in degrees
SHOTGUN_RANGE = 18              # max effective range

# Back-and-forth pump tuning
PUMP_TARGET = 0.75        # total stroke distance to fully pump
PUMP_MIN_STROKE = 0.15      # only here to filter literal pixel jitter
PUMP_STROKES_NEEDED = 2      # 2 reversals = 1 back-and-forths

waves: list[dict[str, list]] = []
waiting_to_advance = False

wave_num = 0
game_over = game_won = tutorial_ended = False

enemies: list = []
items: list = []
runes: list = []

main_menu = True