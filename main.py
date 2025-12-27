import pygame
import random
import math
import asyncio

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Screen settings
SCREEN_WIDTH = 900
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Cat Adventure")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 50, 50)
ORANGE = (255, 140, 0)
YELLOW = (255, 220, 0)
GREEN = (50, 200, 50)
BLUE = (70, 130, 200)
CYAN = (100, 200, 255)
PURPLE = (150, 80, 200)
PINK = (255, 150, 200)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)
LIGHT_BLUE = (150, 200, 255)
BROWN = (139, 90, 43)

# Fonts
font_large = pygame.font.Font(None, 72)
font_medium = pygame.font.Font(None, 48)
font_small = pygame.font.Font(None, 32)
font_tiny = pygame.font.Font(None, 24)

# Clock
clock = pygame.time.Clock()
FPS = 60


class TouchButton:
    def __init__(self, x, y, width, height, label, color, text_color=WHITE):
        self.rect = pygame.Rect(x, y, width, height)
        self.label = label
        self.color = color
        self.text_color = text_color
        self.pressed = False
        self.alpha = 150

    def check_press(self, pos):
        return self.rect.collidepoint(pos)

    def draw(self, surface):
        button_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        if self.pressed:
            color = (*self.color, 220)
        else:
            color = (*self.color, self.alpha)
        pygame.draw.rect(button_surface, color, (0, 0, self.rect.width, self.rect.height), border_radius=10)
        pygame.draw.rect(button_surface, (*WHITE, 180), (0, 0, self.rect.width, self.rect.height), 3, border_radius=10)
        text = font_small.render(self.label, True, self.text_color)
        text_x = (self.rect.width - text.get_width()) // 2
        text_y = (self.rect.height - text.get_height()) // 2
        button_surface.blit(text, (text_x, text_y))
        surface.blit(button_surface, (self.rect.x, self.rect.y))


class TouchControls:
    def __init__(self):
        button_size = 60
        spacing = 10
        bottom_margin = 80
        base_y = SCREEN_HEIGHT - bottom_margin - button_size

        self.left = TouchButton(20, base_y, button_size, button_size, "<", CYAN)
        self.right = TouchButton(20 + button_size + spacing, base_y, button_size, button_size, ">", CYAN)
        self.jump = TouchButton(20 + (button_size + spacing) // 2, base_y - button_size - spacing, button_size, button_size, "^", CYAN)
        self.attack = TouchButton(SCREEN_WIDTH - 100, base_y, 80, button_size, "ZAP", YELLOW)

        self.all_buttons = [self.left, self.right, self.jump, self.attack]
        self.active_touches = {}

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            for button in self.all_buttons:
                if button.check_press(pos):
                    button.pressed = True
            self.active_touches[0] = pos
        elif event.type == pygame.MOUSEBUTTONUP:
            for button in self.all_buttons:
                button.pressed = False
            self.active_touches.clear()
        elif event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
            pos = event.pos
            for button in self.all_buttons:
                button.pressed = button.check_press(pos)
        elif event.type == pygame.FINGERDOWN:
            pos = (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT))
            for button in self.all_buttons:
                if button.check_press(pos):
                    button.pressed = True
            self.active_touches[event.finger_id] = pos
        elif event.type == pygame.FINGERUP:
            if event.finger_id in self.active_touches:
                del self.active_touches[event.finger_id]
            if not self.active_touches:
                for button in self.all_buttons:
                    button.pressed = False
            else:
                self.update_button_states()
        elif event.type == pygame.FINGERMOTION:
            pos = (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT))
            self.active_touches[event.finger_id] = pos
            self.update_button_states()

    def update_button_states(self):
        for button in self.all_buttons:
            button.pressed = False
            for touch_pos in self.active_touches.values():
                if button.check_press(touch_pos):
                    button.pressed = True
                    break

    def get_input(self):
        return {
            'left': self.left.pressed,
            'right': self.right.pressed,
            'jump': self.jump.pressed,
            'attack': self.attack.pressed
        }

    def draw(self, surface):
        for button in self.all_buttons:
            button.draw(surface)
        label = font_tiny.render("SPACE CAT", True, CYAN)
        surface.blit(label, (40, SCREEN_HEIGHT - 160))


class SpaceCat:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 50
        self.height = 50
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 6
        self.jump_power = -16
        self.on_ground = False
        self.on_ufo = None  # Reference to UFO cat is riding
        self.health = 100
        self.max_health = 100
        self.lives = 9
        self.facing_right = True
        self.is_attacking = False
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.invincible = False
        self.invincible_timer = 0
        self.animation_frame = 0
        self.animation_timer = 0
        self.jump_pressed_last = False
        self.laser_shots = []

    def move(self, input_dict):
        self.vel_x = 0
        if input_dict['left']:
            self.vel_x = -self.speed
            self.facing_right = False
        if input_dict['right']:
            self.vel_x = self.speed
            self.facing_right = True

        jump_pressed = input_dict['jump']
        if jump_pressed and not self.jump_pressed_last and (self.on_ground or self.on_ufo):
            self.vel_y = self.jump_power
            self.on_ground = False
            self.on_ufo = None  # Jump off UFO
        self.jump_pressed_last = jump_pressed

        if input_dict['attack']:
            self.attack()

    def attack(self):
        if not self.is_attacking and self.attack_cooldown <= 0:
            self.is_attacking = True
            self.attack_timer = 15
            self.attack_cooldown = 25
            laser_x = self.x + self.width if self.facing_right else self.x - 20
            self.laser_shots.append({
                'x': laser_x,
                'y': self.y + self.height // 2 - 5,
                'dir': 1 if self.facing_right else -1
            })

    def apply_gravity(self, gravity=0.7):
        if not self.on_ufo:
            self.vel_y += gravity
            if self.vel_y > 15:
                self.vel_y = 15

    def update(self, platforms, ufos):
        self.apply_gravity()

        # If riding UFO, move with it
        if self.on_ufo:
            self.x = self.on_ufo.x + self.on_ufo.width // 2 - self.width // 2
            self.y = self.on_ufo.y - self.height
            self.vel_y = 0

        self.x += self.vel_x

        if self.x < 0:
            self.x = 0
        if self.x > SCREEN_WIDTH - self.width:
            self.x = SCREEN_WIDTH - self.width

        self.y += self.vel_y

        # Check platform collisions
        self.on_ground = False
        for platform in platforms:
            if self.check_collision(platform):
                if self.vel_y > 0:
                    self.y = platform.y - self.height
                    self.vel_y = 0
                    self.on_ground = True
                    self.on_ufo = None

        # Check UFO landings (only if falling)
        if self.vel_y > 0 and not self.on_ufo:
            for ufo in ufos:
                cat_bottom = self.y + self.height
                ufo_top = ufo.y
                if (self.x + self.width > ufo.x and
                    self.x < ufo.x + ufo.width and
                    cat_bottom >= ufo_top and
                    cat_bottom <= ufo_top + 20 and
                    self.vel_y > 0):
                    self.on_ufo = ufo
                    self.y = ufo.y - self.height
                    self.vel_y = 0

        # Ground check
        if self.y > SCREEN_HEIGHT - self.height - 50:
            self.y = SCREEN_HEIGHT - self.height - 50
            self.vel_y = 0
            self.on_ground = True
            self.on_ufo = None

        if self.is_attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.is_attacking = False

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False

        for laser in self.laser_shots[:]:
            laser['x'] += laser['dir'] * 12
            if laser['x'] < -20 or laser['x'] > SCREEN_WIDTH + 20:
                self.laser_shots.remove(laser)

        self.animation_timer += 1
        if self.animation_timer >= 8:
            self.animation_timer = 0
            self.animation_frame = (self.animation_frame + 1) % 4

    def check_collision(self, obj):
        return (self.x < obj.x + obj.width and
                self.x + self.width > obj.x and
                self.y < obj.y + obj.height and
                self.y + self.height > obj.y)

    def take_damage(self, amount):
        if not self.invincible:
            self.health -= amount
            self.invincible = True
            self.invincible_timer = 90
            if self.health <= 0:
                self.lives -= 1
                if self.lives > 0:
                    self.health = self.max_health
                else:
                    self.health = 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, surface):
        if self.invincible and self.invincible_timer % 6 < 3:
            return

        x, y = int(self.x), int(self.y)

        # Space helmet
        pygame.draw.circle(surface, (200, 220, 255), (x + 25, y + 20), 22)
        pygame.draw.circle(surface, LIGHT_BLUE, (x + 25, y + 20), 22, 2)

        # Cat face
        pygame.draw.circle(surface, ORANGE, (x + 25, y + 22), 16)

        # Ears
        pygame.draw.polygon(surface, ORANGE, [(x + 12, y + 12), (x + 8, y + 2), (x + 18, y + 10)])
        pygame.draw.polygon(surface, ORANGE, [(x + 38, y + 12), (x + 42, y + 2), (x + 32, y + 10)])
        pygame.draw.polygon(surface, PINK, [(x + 13, y + 11), (x + 10, y + 5), (x + 17, y + 10)])
        pygame.draw.polygon(surface, PINK, [(x + 37, y + 11), (x + 40, y + 5), (x + 33, y + 10)])

        # Eyes
        eye_x_offset = 3 if self.facing_right else -3
        pygame.draw.ellipse(surface, WHITE, (x + 16 + eye_x_offset, y + 18, 8, 10))
        pygame.draw.ellipse(surface, WHITE, (x + 28 + eye_x_offset, y + 18, 8, 10))
        pygame.draw.ellipse(surface, GREEN, (x + 18 + eye_x_offset, y + 20, 5, 7))
        pygame.draw.ellipse(surface, GREEN, (x + 30 + eye_x_offset, y + 20, 5, 7))
        pygame.draw.circle(surface, BLACK, (x + 20 + eye_x_offset, y + 23), 2)
        pygame.draw.circle(surface, BLACK, (x + 32 + eye_x_offset, y + 23), 2)

        # Nose
        pygame.draw.polygon(surface, PINK, [(x + 25, y + 28), (x + 22, y + 32), (x + 28, y + 32)])

        # Whiskers
        pygame.draw.line(surface, WHITE, (x + 15, y + 30), (x + 5, y + 28), 1)
        pygame.draw.line(surface, WHITE, (x + 15, y + 32), (x + 5, y + 32), 1)
        pygame.draw.line(surface, WHITE, (x + 35, y + 30), (x + 45, y + 28), 1)
        pygame.draw.line(surface, WHITE, (x + 35, y + 32), (x + 45, y + 32), 1)

        # Space suit
        pygame.draw.ellipse(surface, LIGHT_BLUE, (x + 8, y + 38, 34, 20))
        pygame.draw.ellipse(surface, CYAN, (x + 8, y + 38, 34, 20), 2)

        # Jetpack
        pygame.draw.rect(surface, GRAY, (x + 5, y + 40, 8, 15))
        pygame.draw.rect(surface, GRAY, (x + 37, y + 40, 8, 15))

        if not self.on_ground and not self.on_ufo:
            flame_len = 8 + math.sin(self.animation_timer) * 4
            pygame.draw.polygon(surface, YELLOW, [(x + 9, y + 55), (x + 5, y + 55 + flame_len), (x + 13, y + 55)])
            pygame.draw.polygon(surface, ORANGE, [(x + 9, y + 55), (x + 7, y + 55 + flame_len - 3), (x + 11, y + 55)])
            pygame.draw.polygon(surface, YELLOW, [(x + 41, y + 55), (x + 37, y + 55 + flame_len), (x + 45, y + 55)])
            pygame.draw.polygon(surface, ORANGE, [(x + 41, y + 55), (x + 39, y + 55 + flame_len - 3), (x + 43, y + 55)])

        # Laser shots
        for laser in self.laser_shots:
            pygame.draw.rect(surface, YELLOW, (laser['x'], laser['y'], 20, 6))
            pygame.draw.rect(surface, WHITE, (laser['x'] + 2, laser['y'] + 2, 16, 2))


class Alien:
    """Enemy alien - hurts the cat!"""
    def __init__(self, x, y, alien_type="green"):
        self.x = x
        self.y = y
        self.alien_type = alien_type
        self.width = 45
        self.height = 45
        self.speed = 2 + random.random()
        self.direction = random.choice([-1, 1])
        self.health = 30
        self.damage = 20
        self.animation_timer = 0
        self.float_offset = random.random() * 6.28
        self.patrol_start = max(0, x - 120)
        self.patrol_end = min(SCREEN_WIDTH - 50, x + 120)

    def update(self):
        self.x += self.speed * self.direction
        if self.x <= self.patrol_start or self.x >= self.patrol_end:
            self.direction *= -1
        if self.x < 0:
            self.x = 0
            self.direction = 1
        if self.x > SCREEN_WIDTH - self.width:
            self.x = SCREEN_WIDTH - self.width
            self.direction = -1
        self.animation_timer += 1

    def take_damage(self, amount):
        self.health -= amount

    def is_alive(self):
        return self.health > 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, surface):
        x, y = int(self.x), int(self.y)
        float_y = int(math.sin(self.animation_timer * 0.1 + self.float_offset) * 5)

        if self.alien_type == "green":
            pygame.draw.ellipse(surface, GREEN, (x + 5, y + float_y, 35, 30))
            pygame.draw.ellipse(surface, (100, 255, 100), (x + 8, y + 3 + float_y, 29, 24))
            pygame.draw.ellipse(surface, BLACK, (x + 10, y + 8 + float_y, 12, 15))
            pygame.draw.ellipse(surface, BLACK, (x + 25, y + 8 + float_y, 12, 15))
            pygame.draw.circle(surface, RED, (x + 16, y + 13 + float_y), 3)
            pygame.draw.circle(surface, RED, (x + 31, y + 13 + float_y), 3)
            pygame.draw.ellipse(surface, GREEN, (x + 12, y + 28 + float_y, 20, 18))
            pygame.draw.line(surface, GREEN, (x + 22, y + float_y), (x + 22, y - 8 + float_y), 2)
            pygame.draw.circle(surface, RED, (x + 22, y - 10 + float_y), 4)

        elif self.alien_type == "purple":
            pygame.draw.ellipse(surface, PURPLE, (x + 5, y + 5 + float_y, 35, 25))
            pygame.draw.circle(surface, YELLOW, (x + 15, y + 15 + float_y), 6)
            pygame.draw.circle(surface, YELLOW, (x + 30, y + 15 + float_y), 6)
            pygame.draw.circle(surface, RED, (x + 15, y + 15 + float_y), 3)
            pygame.draw.circle(surface, RED, (x + 30, y + 15 + float_y), 3)
            for i in range(4):
                wave = math.sin(self.animation_timer * 0.2 + i) * 5
                pygame.draw.line(surface, PURPLE, (x + 10 + i * 8, y + 28 + float_y),
                               (x + 10 + i * 8 + wave, y + 42 + float_y), 3)


class Meteor:
    """Falling meteor - dangerous enemy!"""
    def __init__(self, x):
        self.x = x
        self.y = -50
        self.width = 40
        self.height = 40
        self.speed = 4 + random.random() * 3
        self.rotation = 0
        self.rotation_speed = random.uniform(-5, 5)
        self.damage = 25
        self.health = 20

    def update(self):
        self.y += self.speed
        self.rotation += self.rotation_speed

    def is_on_screen(self):
        return self.y < SCREEN_HEIGHT + 50

    def take_damage(self, amount):
        self.health -= amount

    def is_alive(self):
        return self.health > 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, surface):
        x, y = int(self.x), int(self.y)

        # Meteor body
        pygame.draw.circle(surface, BROWN, (x + 20, y + 20), 20)
        pygame.draw.circle(surface, (100, 60, 30), (x + 15, y + 15), 8)
        pygame.draw.circle(surface, (80, 50, 25), (x + 28, y + 25), 6)
        pygame.draw.circle(surface, (90, 55, 28), (x + 18, y + 28), 5)

        # Fire trail
        trail_points = [
            (x + 20, y - 5),
            (x + 10, y - 20 - random.randint(0, 10)),
            (x + 20, y - 15),
            (x + 30, y - 20 - random.randint(0, 10)),
        ]
        pygame.draw.polygon(surface, ORANGE, [(x + 10, y), (x + 20, y - 25), (x + 30, y)])
        pygame.draw.polygon(surface, YELLOW, [(x + 15, y), (x + 20, y - 15), (x + 25, y)])


class FriendlyUFO:
    """Friendly UFO - ride it to escape enemies!"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 70
        self.height = 30
        self.speed = 2
        self.direction = random.choice([-1, 1])
        self.animation_timer = 0
        self.patrol_start = max(50, x - 150)
        self.patrol_end = min(SCREEN_WIDTH - 120, x + 150)

    def update(self):
        self.x += self.speed * self.direction
        if self.x <= self.patrol_start or self.x >= self.patrol_end:
            self.direction *= -1
        self.animation_timer += 1

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, surface):
        x, y = int(self.x), int(self.y)
        float_y = int(math.sin(self.animation_timer * 0.08) * 3)
        y += float_y

        # UFO body
        pygame.draw.ellipse(surface, (100, 200, 255), (x, y + 10, self.width, 20))
        pygame.draw.ellipse(surface, (150, 220, 255), (x + 5, y + 12, self.width - 10, 16))

        # Glass dome
        pygame.draw.ellipse(surface, (200, 230, 255), (x + 20, y - 5, 30, 20))
        pygame.draw.ellipse(surface, CYAN, (x + 20, y - 5, 30, 20), 2)

        # Friendly face inside
        pygame.draw.circle(surface, WHITE, (x + 30, y + 3), 4)
        pygame.draw.circle(surface, WHITE, (x + 40, y + 3), 4)
        pygame.draw.circle(surface, BLACK, (x + 31, y + 3), 2)
        pygame.draw.circle(surface, BLACK, (x + 41, y + 3), 2)
        pygame.draw.arc(surface, BLACK, (x + 30, y + 5, 12, 6), 3.14, 6.28, 1)

        # Glowing lights
        colors = [GREEN, CYAN, GREEN]
        for i, color in enumerate(colors):
            blink = (self.animation_timer + i * 5) % 15 < 10
            if blink:
                pygame.draw.circle(surface, color, (x + 15 + i * 20, y + 28), 4)

        # "FRIEND" indicator
        friend_text = font_tiny.render("RIDE ME!", True, GREEN)
        surface.blit(friend_text, (x + self.width // 2 - friend_text.get_width() // 2, y - 25))


class SpacePlatform:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def draw(self, surface):
        pygame.draw.rect(surface, GRAY, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(surface, (120, 120, 120), (self.x, self.y, self.width, 5))
        pygame.draw.rect(surface, CYAN, (self.x, self.y + self.height - 3, self.width, 3))
        for i in range(0, self.width, 30):
            pygame.draw.line(surface, DARK_GRAY, (self.x + i, self.y), (self.x + i, self.y + self.height), 1)


class Collectible:
    def __init__(self, x, y, collect_type="star"):
        self.x = x
        self.y = y
        self.collect_type = collect_type
        self.width = 30
        self.height = 30
        self.collected = False
        self.animation_frame = 0

    def update(self):
        self.animation_frame += 0.15

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, surface):
        if self.collected:
            return
        float_offset = int(math.sin(self.animation_frame) * 4)
        x, y = int(self.x), int(self.y + float_offset)

        if self.collect_type == "star":
            points = []
            for i in range(5):
                angle = i * 72 - 90
                px = x + 15 + math.cos(math.radians(angle)) * 12
                py = y + 15 + math.sin(math.radians(angle)) * 12
                points.append((px, py))
                angle2 = angle + 36
                px2 = x + 15 + math.cos(math.radians(angle2)) * 5
                py2 = y + 15 + math.sin(math.radians(angle2)) * 5
                points.append((px2, py2))
            pygame.draw.polygon(surface, YELLOW, points)
            pygame.draw.polygon(surface, WHITE, points, 1)

        elif self.collect_type == "fish":
            pygame.draw.circle(surface, (100, 200, 255), (x + 15, y + 15), 15, 2)
            pygame.draw.ellipse(surface, ORANGE, (x + 5, y + 10, 18, 10))
            pygame.draw.polygon(surface, ORANGE, [(x + 5, y + 15), (x - 2, y + 8), (x - 2, y + 22)])
            pygame.draw.circle(surface, WHITE, (x + 18, y + 13), 3)
            pygame.draw.circle(surface, BLACK, (x + 19, y + 13), 1)

        elif self.collect_type == "crystal":
            points = [(x + 15, y), (x + 25, y + 10), (x + 25, y + 20), (x + 15, y + 30), (x + 5, y + 20), (x + 5, y + 10)]
            pygame.draw.polygon(surface, PURPLE, points)
            pygame.draw.polygon(surface, (200, 150, 255), points, 2)


class Game:
    def __init__(self):
        self.state = "menu"
        self.level = 1
        self.score = 0
        self.cat = None
        self.platforms = []
        self.enemies = []
        self.meteors = []
        self.ufos = []
        self.collectibles = []
        self.stars = []
        self.planets = []
        self.meteor_timer = 0
        self.touch_controls = TouchControls()
        self.generate_background()

    def generate_background(self):
        self.stars = []
        for _ in range(150):
            self.stars.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'size': random.randint(1, 3),
                'twinkle': random.random() * 6.28
            })
        self.planets = []
        planet_colors = [(200, 100, 100), (100, 150, 200), (150, 200, 100)]
        for i in range(2):
            self.planets.append({
                'x': random.randint(100, SCREEN_WIDTH - 100),
                'y': random.randint(50, 150),
                'size': random.randint(40, 70),
                'color': random.choice(planet_colors),
                'ring': random.random() > 0.5
            })

    def setup_level(self):
        self.cat = SpaceCat(100, 400)

        self.platforms = [
            SpacePlatform(0, SCREEN_HEIGHT - 40, SCREEN_WIDTH, 40),
            SpacePlatform(80, 480, 120, 20),
            SpacePlatform(300, 420, 150, 20),
            SpacePlatform(550, 350, 140, 20),
            SpacePlatform(150, 280, 130, 20),
            SpacePlatform(400, 220, 150, 20),
            SpacePlatform(650, 160, 130, 20),
        ]

        # Enemies (aliens)
        self.enemies = []
        alien_types = ["green", "purple"]
        for i in range(2 + self.level):
            alien_type = alien_types[i % 2]
            ex = random.randint(200, 750)
            ey = random.choice([380, 300, 180, 520])
            self.enemies.append(Alien(ex, ey, alien_type))

        # Friendly UFOs
        self.ufos = []
        ufo_positions = [(150, 350), (450, 280), (700, 220)]
        for i in range(min(3, 1 + self.level // 2)):
            if i < len(ufo_positions):
                self.ufos.append(FriendlyUFO(ufo_positions[i][0], ufo_positions[i][1]))

        # Meteors start empty, spawn during gameplay
        self.meteors = []
        self.meteor_timer = 0

        # Collectibles
        self.collectibles = []
        for i in range(6):
            cx = random.randint(80, 820)
            cy = random.choice([440, 360, 240, 120])
            ctype = random.choice(["star", "star", "fish", "crystal"])
            self.collectibles.append(Collectible(cx, cy, ctype))

    def draw_background(self, surface):
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(10 + 15 * ratio)
            g = int(15 + 20 * ratio)
            b = int(40 + 30 * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        for planet in self.planets:
            pygame.draw.circle(surface, planet['color'], (planet['x'], planet['y']), planet['size'])
            pygame.draw.circle(surface, tuple(max(0, c - 40) for c in planet['color']),
                             (planet['x'] + planet['size']//4, planet['y']), planet['size'] - 8)
            if planet['ring']:
                pygame.draw.ellipse(surface, (200, 180, 150),
                    (planet['x'] - planet['size'] - 10, planet['y'] - 5, planet['size'] * 2 + 20, 12), 2)

        for star in self.stars:
            star['twinkle'] += 0.05
            brightness = int(150 + 100 * math.sin(star['twinkle']))
            pygame.draw.circle(surface, (brightness, brightness, min(255, brightness + 50)),
                             (star['x'], star['y']), star['size'])

    def draw_ui(self, surface):
        pygame.draw.rect(surface, DARK_GRAY, (10, 10, 204, 24))
        health_ratio = self.cat.health / self.cat.max_health
        health_color = GREEN if health_ratio > 0.5 else YELLOW if health_ratio > 0.25 else RED
        pygame.draw.rect(surface, health_color, (12, 12, 200 * health_ratio, 20))
        health_text = font_tiny.render("HEALTH", True, WHITE)
        surface.blit(health_text, (15, 14))

        lives_text = font_small.render(f"Lives: {self.cat.lives}", True, ORANGE)
        surface.blit(lives_text, (10, 40))

        score_text = font_medium.render(f"Score: {self.score}", True, YELLOW)
        surface.blit(score_text, (SCREEN_WIDTH - 200, 10))

        level_text = font_small.render(f"Level: {self.level}", True, CYAN)
        surface.blit(level_text, (SCREEN_WIDTH - 200, 50))

        # Riding indicator
        if self.cat.on_ufo:
            ride_text = font_small.render("Riding UFO!", True, GREEN)
            surface.blit(ride_text, (SCREEN_WIDTH // 2 - ride_text.get_width() // 2, 10))

    def draw_menu(self, surface):
        self.draw_background(surface)

        for offset in range(4, 0, -1):
            glow = font_large.render("SPACE CAT", True, (50 + offset * 20, 100 + offset * 20, 200 + offset * 10))
            surface.blit(glow, (SCREEN_WIDTH // 2 - glow.get_width() // 2 + offset, 80 + offset))
        title = font_large.render("SPACE CAT", True, CYAN)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 80))

        subtitle = font_medium.render("ADVENTURE", True, YELLOW)
        surface.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 150))

        preview_cat = SpaceCat(SCREEN_WIDTH // 2 - 25, 230)
        preview_cat.draw(surface)

        story = [
            "Aliens and Meteors are trying to get you!",
            "Ride friendly UFOs to escape danger!",
            "Collect stars, fish, and crystals!",
            "Zap the enemies with your laser!"
        ]
        for i, line in enumerate(story):
            text = font_small.render(line, True, WHITE)
            surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 340 + i * 32))

        # Legend
        legend_y = 480
        pygame.draw.circle(surface, GREEN, (200, legend_y), 8)
        surface.blit(font_tiny.render("= Enemy Alien", True, WHITE), (215, legend_y - 8))

        pygame.draw.circle(surface, BROWN, (400, legend_y), 8)
        surface.blit(font_tiny.render("= Meteor (Danger!)", True, WHITE), (415, legend_y - 8))

        pygame.draw.ellipse(surface, CYAN, (580, legend_y - 8, 30, 16))
        surface.blit(font_tiny.render("= Friendly UFO", True, WHITE), (615, legend_y - 8))

        blink = pygame.time.get_ticks() % 1000 < 500
        if blink:
            start = font_medium.render("Tap or Press ENTER!", True, YELLOW)
            surface.blit(start, (SCREEN_WIDTH // 2 - start.get_width() // 2, 540))

    def draw_game_over(self, surface, won=False):
        self.draw_background(surface)
        if won:
            title = font_large.render("LEVEL COMPLETE!", True, GREEN)
            msg = font_medium.render(f"Score: {self.score}", True, YELLOW)
        else:
            title = font_large.render("GAME OVER", True, RED)
            msg = font_medium.render("The aliens got you!", True, WHITE)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 200))
        surface.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, 280))
        cont = font_small.render("Tap or Press ENTER to continue", True, YELLOW)
        surface.blit(cont, (SCREEN_WIDTH // 2 - cont.get_width() // 2, 400))

    def update(self):
        keys = pygame.key.get_pressed()
        touch_input = self.touch_controls.get_input()

        combined_input = {
            'left': keys[pygame.K_LEFT] or keys[pygame.K_a] or touch_input['left'],
            'right': keys[pygame.K_RIGHT] or keys[pygame.K_d] or touch_input['right'],
            'jump': keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE] or touch_input['jump'],
            'attack': keys[pygame.K_z] or keys[pygame.K_x] or keys[pygame.K_RETURN] or touch_input['attack']
        }

        self.cat.move(combined_input)
        self.cat.update(self.platforms, self.ufos)

        # Update UFOs
        for ufo in self.ufos:
            ufo.update()

        # Spawn meteors
        self.meteor_timer += 1
        if self.meteor_timer >= 120 - self.level * 10:  # Faster with levels
            self.meteor_timer = 0
            if len(self.meteors) < 3 + self.level:
                self.meteors.append(Meteor(random.randint(50, SCREEN_WIDTH - 90)))

        # Update meteors
        for meteor in self.meteors[:]:
            meteor.update()
            if not meteor.is_on_screen():
                self.meteors.remove(meteor)
            elif meteor.get_rect().colliderect(self.cat.get_rect()):
                self.cat.take_damage(meteor.damage)
                self.meteors.remove(meteor)
            else:
                # Check laser hits on meteors
                for laser in self.cat.laser_shots[:]:
                    laser_rect = pygame.Rect(laser['x'], laser['y'], 20, 6)
                    if laser_rect.colliderect(meteor.get_rect()):
                        meteor.take_damage(15)
                        self.score += 5
                        if laser in self.cat.laser_shots:
                            self.cat.laser_shots.remove(laser)
                        if not meteor.is_alive():
                            if meteor in self.meteors:
                                self.meteors.remove(meteor)
                            self.score += 50

        # Update enemies
        for enemy in self.enemies[:]:
            enemy.update()
            if enemy.get_rect().colliderect(self.cat.get_rect()):
                self.cat.take_damage(enemy.damage)

            for laser in self.cat.laser_shots[:]:
                laser_rect = pygame.Rect(laser['x'], laser['y'], 20, 6)
                if laser_rect.colliderect(enemy.get_rect()):
                    enemy.take_damage(20)
                    self.score += 10
                    if laser in self.cat.laser_shots:
                        self.cat.laser_shots.remove(laser)

            if not enemy.is_alive():
                self.enemies.remove(enemy)
                self.score += 100

        # Update collectibles
        for c in self.collectibles:
            if c.collected:
                continue
            c.update()
            if c.get_rect().colliderect(self.cat.get_rect()):
                c.collected = True
                if c.collect_type == "star":
                    self.score += 50
                elif c.collect_type == "fish":
                    self.score += 75
                    self.cat.health = min(self.cat.health + 25, self.cat.max_health)
                elif c.collect_type == "crystal":
                    self.score += 100

        # Win/Lose
        if self.cat.lives <= 0 and self.cat.health <= 0:
            self.state = "game_over"
        if len(self.enemies) == 0 and all(c.collected for c in self.collectibles):
            self.state = "level_complete"

    def draw(self, surface):
        if self.state == "menu":
            self.draw_menu(surface)
        elif self.state == "playing":
            self.draw_background(surface)
            for p in self.platforms:
                p.draw(surface)
            for ufo in self.ufos:
                ufo.draw(surface)
            for c in self.collectibles:
                c.draw(surface)
            for meteor in self.meteors:
                meteor.draw(surface)
            for e in self.enemies:
                e.draw(surface)
            self.cat.draw(surface)
            self.draw_ui(surface)
            self.touch_controls.draw(surface)
        elif self.state == "game_over":
            self.draw_game_over(surface, won=False)
        elif self.state == "level_complete":
            self.draw_game_over(surface, won=True)


async def main():
    game = Game()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if game.state == "playing":
                game.touch_controls.handle_event(event)

            if event.type in [pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN]:
                if game.state == "menu":
                    game.setup_level()
                    game.state = "playing"
                elif game.state == "game_over":
                    game.level = 1
                    game.score = 0
                    game.state = "menu"
                elif game.state == "level_complete":
                    game.level += 1
                    game.setup_level()
                    game.state = "playing"

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if game.state == "playing":
                        game.state = "menu"
                    else:
                        running = False
                elif event.key == pygame.K_RETURN:
                    if game.state == "menu":
                        game.setup_level()
                        game.state = "playing"
                    elif game.state == "game_over":
                        game.level = 1
                        game.score = 0
                        game.state = "menu"
                    elif game.state == "level_complete":
                        game.level += 1
                        game.setup_level()
                        game.state = "playing"

        if game.state == "playing":
            game.update()

        game.draw(screen)
        pygame.display.flip()
        await asyncio.sleep(0)  # Required for web compatibility
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
