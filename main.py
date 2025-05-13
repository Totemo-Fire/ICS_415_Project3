import pyglet
from pyglet.gl import *
from OpenGL.GL import *
from OpenGL.GLU import *
import noise
import math
from pyglet.window import key

window = pyglet.window.Window(800, 600, "Minecraft-like Engine, Mohammed Alghunaim, 202016140", resizable=True)
window.set_exclusive_mouse(True)  # Hide and lock mouse

# Load texture
texture = pyglet.image.load('terrain.png').get_texture()
glEnable(GL_TEXTURE_2D)
glBindTexture(GL_TEXTURE_2D, texture.id)
glEnable(GL_DEPTH_TEST)
glClearColor(0.5, 0.7, 1.0, 1.0)

# Fix blurry textures by using nearest-neighbor filtering
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

# Camera class to handle player view and movement
class Camera:
    def __init__(self):
        self.x, self.y, self.z = 0, 10, 0
        self.pitch = 0
        self.yaw = 0
        self.speed = 10
        self.mouse_sensitivity = 0.15

    def update(self, dt, keys):
        dx, dy, dz = 0, 0, 0
        speed = self.speed * dt
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)

        # Compute forward direction vector (includes pitch)
        forward_x = math.cos(pitch_rad) * math.sin(yaw_rad)
        forward_y = math.sin(pitch_rad)
        forward_z = math.cos(pitch_rad) * math.cos(yaw_rad)

        # Compute right direction vector (horizontal perpendicular to forward)
        right_x = math.cos(yaw_rad)
        right_z = -math.sin(yaw_rad)

        # Normalize vectors to ensure consistent speed
        forward_length = math.sqrt(forward_x**2 + forward_y**2 + forward_z**2)
        forward_x /= forward_length
        forward_y /= forward_length
        forward_z /= forward_length

        # Movement
        if keys[key.W]:
            dx += forward_x * speed
            dy += forward_y * speed
            dz += forward_z * speed
        if keys[key.S]:
            dx -= forward_x * speed
            dy -= forward_y * speed
            dz -= forward_z * speed
        if keys[key.D]:
            dx -= right_x * speed
            dz -= right_z * speed
        if keys[key.A]:
            dx += right_x * speed
            dz += right_z * speed

        self.x += dx
        self.y += dy
        self.z += dz

    def mouse_motion(self, dx, dy):
        self.yaw -= dx * self.mouse_sensitivity
        self.pitch += dy * self.mouse_sensitivity
        self.pitch = max(-89, min(89, self.pitch))

    def get_look_vector(self):
        # Get the look vector based on yaw and pitch
        pitch_rad = math.radians(self.pitch)
        yaw_rad = math.radians(self.yaw)
        dx = math.cos(pitch_rad) * math.sin(yaw_rad)
        dy = math.sin(pitch_rad)
        dz = math.cos(pitch_rad) * math.cos(yaw_rad)
        return (self.x + dx, self.y + dy, self.z + dz)

camera = Camera()
keys = key.KeyStateHandler()
window.push_handlers(keys)

# Initialize blocks (dictionary for easy deletion)
blocks = {}
for x in range(16):
    for z in range(16):
        y = int(noise.pnoise2(x / 10.0, z / 10.0, octaves=3) * 3 + 5)
        blocks[(x, y, z)] = ((3, 15), (3, 15), (3, 15), (3, 15), (0, 15), (2, 15))

@window.event
def on_mouse_motion(x, y, dx, dy):
    camera.mouse_motion(dx, dy)

@window.event
def on_resize(width, height):
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(65, width / float(height), 0.1, 1000)
    glMatrixMode(GL_MODELVIEW)
    return True

# UV from atlas
def get_tex_coords(tx, ty, tile_size=16, atlas_size=256):
    u = tx * tile_size / atlas_size
    v = ty * tile_size / atlas_size
    du = tile_size / atlas_size
    dv = tile_size / atlas_size
    return [(u, v), (u + du, v), (u + du, v + dv), (u, v + dv)]

def draw_face(verts, uvs):
    glBegin(GL_QUADS)
    glColor3f(1, 1, 1)
    for (x, y, z), (u, v) in zip(verts, uvs):
        glTexCoord2f(u, v)
        glVertex3f(x, y, z)
    glEnd()

def draw_cube(x, y, z, front, back, left, right, top, bottom):
    uvFront = get_tex_coords(front[0], front[1])
    uvBack = get_tex_coords(back[0], back[1])
    uvLeft = get_tex_coords(right[0], left[1])
    uvRight = get_tex_coords(right[0], right[1])
    uvTop = get_tex_coords(top[0], top[1])
    uvBottom = get_tex_coords(bottom[0], bottom[1])
    draw_face([(x, y, z+1), (x+1, y, z+1), (x+1, y+1, z+1), (x, y+1, z+1)], uvFront)  # Front
    draw_face([(x+1, y, z), (x, y, z), (x, y+1, z), (x+1, y+1, z)], uvBack)          # Back
    draw_face([(x, y, z), (x, y, z+1), (x, y+1, z+1), (x, y+1, z)], uvLeft)          # Left
    draw_face([(x+1, y, z+1), (x+1, y, z), (x+1, y+1, z), (x+1, y+1, z+1)], uvRight)  # Right
    draw_face([(x, y+1, z+1), (x+1, y+1, z+1), (x+1, y+1, z), (x, y+1, z)], uvTop)  # Top
    draw_face([(x, y, z), (x+1, y, z), (x+1, y, z+1), (x, y, z+1)], uvBottom)          # Bottom

def raycast(camera, blocks, max_distance=10):
    # Get precise direction vector using camera's look angles
    pitch_rad = math.radians(camera.pitch)
    yaw_rad = math.radians(camera.yaw)
    dx = math.cos(pitch_rad) * math.sin(yaw_rad)
    dy = math.sin(pitch_rad)
    dz = math.cos(pitch_rad) * math.cos(yaw_rad)

    # Start at camera position
    x, y, z = camera.x, camera.y, camera.z
    
    # Track previous block coordinates
    prev_block = None
    for _ in range(int(max_distance * 10)):  # Higher precision steps
        prev_x, prev_y, prev_z = x, y, z
        x += dx * 0.1  # Smaller step size for accuracy
        y += dy * 0.1
        z += dz * 0.1
        
        current_block = (int(x), int(y), int(z))
        
        # Detect when we cross into a new block
        if current_block in blocks:
            # Calculate which face we entered through
            face = []
            if int(prev_x) != current_block[0]:
                face.append(('x', 1 if x > prev_x else -1))
            if int(prev_y) != current_block[1]:
                face.append(('y', 1 if y > prev_y else -1))
            if int(prev_z) != current_block[2]:
                face.append(('z', 1 if z > prev_z else -1))
            
            # Return both block and face normal
            return current_block, face
        
    return None, None

def place_block(camera, blocks):
    hit_block, face_normals = raycast(camera, blocks)
    if hit_block and face_normals:
        px, py, pz = hit_block
        
        # Use the primary face normal (first in list)
        axis, direction = face_normals[0]
        
        # Calculate new block position based on hit face
        if axis == 'x':
            new_pos = (px - direction, py, pz)
        elif axis == 'y':
            new_pos = (px, py - direction, pz)
        elif axis == 'z':
            new_pos = (px, py, pz - direction)
        blocks[new_pos] = ((3, 15), (3, 15), (3, 15), (3, 15), (0, 15), (2, 15))

def remove_block(camera, blocks):
    hit_block, _ = raycast(camera, blocks)
    if hit_block and hit_block in blocks:
        del blocks[hit_block]

@window.event
def on_mouse_press(x, y, button, modifiers):
    if button == 1:  # Left-click (place block)
        place_block(camera, blocks)
    elif button == 4:  # Right-click (destroy block)
        remove_block(camera, blocks)

@window.event
def on_draw():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    lx, ly, lz = camera.get_look_vector()
    gluLookAt(camera.x, camera.y, camera.z, lx, ly, lz, 0, 1, 0)

    glBindTexture(GL_TEXTURE_2D, texture.id)
    for (x, y, z), (front, back, left, right, top, bottom) in blocks.items():
        draw_cube(x, y, z, front, back, left, right, top, bottom)

def update(dt):
    camera.update(dt, keys)

pyglet.clock.schedule_interval(update, 1/60.0)
pyglet.app.run()
