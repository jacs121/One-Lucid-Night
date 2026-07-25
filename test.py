from ursina import *

app = Ursina()

# 1. Create the full-screen background
background = Entity(
    parent=camera.ui,          # Attaches the entity to the 2D UI camera
    model='quad',              # Uses a flat plane shape
    texture='shore',           # Replace with your image file name/path
    scale=(camera.ui.scale.x, camera.ui.scale.y), # Scales to match the exact screen size
    z=1                        # Pushes it backward (higher positive z = further back in 2D)
)

# 2. Test entities to prove the background stays behind them
test_button = Button(text='UI Element', scale=0.2, color=color.azure)
test_cube = Entity(model='cube', color=color.orange, scale=2, z=0)

app.run()