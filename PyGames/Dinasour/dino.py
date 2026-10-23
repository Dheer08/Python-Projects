"""
DINO RUN — a Pygame remake of the Chrome offline T-Rex game, with extras.

Install:  pip install pygame
Run:      python dino_run.py

Controls
  Space / Up / W / Left-click   Jump (hold for a higher jump)
  Down / S                      Duck (in the air: fast-fall)
  P or Esc                      Pause / resume
  M                             Mute / unmute sound
  N                             Toggle night mode manually
  A                             Autopilot (watch the dino play itself)
  F                             Fullscreen
  1 / 2 / 3 (on the menu)       Easy / Normal / Hard

Extras beyond the original
  * Difficulty levels, saved high score and a local top-5 leaderboard
  * Power-ups: Shield, Slow-mo, x2 Score, Coin Magnet
  * Coins to collect (a lifetime total is saved)
  * Variable jump height, fast-fall, day/night cycle with moon and stars
  * Pause, mute, autopilot demo, fullscreen, resizable window
  * Synthesised retro sounds (no asset files needed), landing dust particles
"""
import json
import math
import os
import random
import sys
import time
from array import array

import pygame

# ----------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------
W, H = 900, 320
GROUND_Y = 262            # y of the ground line (dino feet rest here)
FPS = 60
PX = 3                    # pixel-art scale
DINO_X = 60
GRAVITY = 3000.0
JUMP_V = 780.0
HOLD_TIME = 0.22          # seconds the jump key boosts the jump
SAVE_FILE = os.path.join(os.path.expanduser("~"), ".dino_run_save.json")

DAY_BG, DAY_FG = (247, 247, 247), (83, 83, 83)
NIGHT_BG, NIGHT_FG = (32, 33, 36), (225, 225, 225)
GOLD = (232, 176, 32)

DIFFICULTY = {
    "Easy":   dict(start=380, accel=6,  max=950,  gap=1.25, bird_at=450),
    "Normal": dict(start=440, accel=9,  max=1150, gap=1.0,  bird_at=300),
    "Hard":   dict(start=520, accel=13, max=1350, gap=0.85, bird_at=150),
}
DIFF_NAMES = list(DIFFICULTY)

POWERUPS = {
    # key: (label, colour, icon text, duration seconds)
    "shield": ("SHIELD",  (40, 140, 230), "S",  10.0),
    "slow":   ("SLOW-MO", (150, 80, 220), "T",  5.0),
    "double": ("x2 SCORE", (230, 150, 20), "2", 8.0),
    "magnet": ("MAGNET",  (220, 60, 60),  "M",  8.0),
}

# ----------------------------------------------------------------------------
# Pixel art ('#' = pixel, anything else = transparent)
# ----------------------------------------------------------------------------
HEAD = [
    "           ######## ",
    "          ##.#######",
    "          ##########",
    "          ##########",
    "          #####     ",
    "          ########  ",
]
HEAD_DEAD = [
    "           ######## ",
    "          #.#.######",
    "          ##.#######",
    "          #.#.######",
    "          #####     ",
    "          ########  ",
]
BODY = [
    "#        #####      ",
    "#       #######     ",
    "##     #########    ",
    "###   ##########    ",
    "###########   #     ",
    " #########          ",
    "  ########          ",
    "   ######           ",
    "    ####            ",
]
LEGS_STAND = ["    ##  ##          ", "    #    #          ", "    ##   ##         "]
LEGS_RUN1 = ["    ##  ##          ", "    #    ###        ", "    ##              "]
LEGS_RUN2 = ["    ##  ##          ", "    ###  #          ", "         ##         "]

DUCK_TOP = [
    "                   ######## ",
    "#     ##########  ##.#######",
    "## ################ ########",
    "############################",
    " #################  #####   ",
    "  ##############    #       ",
    "   ############             ",
]
DUCK_LEGS1 = ["    ##   ##                 ", "    #     ##                "]
DUCK_LEGS2 = ["    ##   ##                 ", "    ##    #                 "]

BIRD_UP = [
    "      #          ",
    "      ##         ",
    "      ###        ",
    "   #  ####       ",
    "  ##  #####      ",
    "################ ",
    "    ############ ",
    "      #######    ",
    "                 ",
    "                 ",
    "                 ",
]
BIRD_DOWN = [
    "                 ",
    "                 ",
    "                 ",
    "   #             ",
    "  ##             ",
    "################ ",
    "    ############ ",
    "      ######     ",
    "      ###        ",
    "      ##         ",
    "      #          ",
]
CLOUD = [
    "         #####         ",
    "      ###     ###      ",
    "   ###           ##    ",
    " ##                 ## ",
    "#######################",
]


def make_sprite(rows, scale=PX):
    """Build a white sprite from ASCII rows; tint it at draw time."""
    w = max(len(r) for r in rows)
    surf = pygame.Surface((w * scale, len(rows) * scale), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                surf.fill((255, 255, 255, 255), (x * scale, y * scale, scale, scale))
    return surf


def cactus_rows(height):
    """Procedurally generate a cactus with random arms."""
    w = 9
    g = [[" "] * w for _ in range(height)]
    for y in range(height):
        for x in (3, 4, 5):
            g[y][x] = "#"
    g[0][3] = g[0][5] = " "
    for side in (0, 1):
        if random.random() < 0.85:
            join = random.randint(height // 3, height // 2 + 1)
            top = max(1, join - random.randint(2, max(3, height // 3)))
            cols = (0, 1) if side == 0 else (7, 8)
            for y in range(top, join + 1):
                g[y][cols[0]] = g[y][cols[1]] = "#"
            g[top][cols[0] if side == 0 else cols[1]] = " "
            g[join][2 if side == 0 else 6] = "#"
    return ["".join(r) for r in g]


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_col(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


# ----------------------------------------------------------------------------
# Sound (synthesised square waves, no files needed)
# ----------------------------------------------------------------------------
class Sounds:
    def __init__(self):
        self.ok = False
        self.muted = False
        self.cache = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.rate, _, self.channels = pygame.mixer.get_init()
            self.cache = {
                "jump":  self._tone([(520, 760, 0.07)]),
                "point": self._tone([(990, 990, 0.08), (1320, 1320, 0.12)]),
                "hit":   self._tone([(220, 90, 0.25)], vol=0.35),
                "coin":  self._tone([(1400, 1400, 0.04), (1900, 1900, 0.08)], vol=0.18),
                "power": self._tone([(500, 1200, 0.18)], vol=0.25),
                "shield": self._tone([(700, 300, 0.15)], vol=0.3),
            }
            self.ok = True
        except Exception:
            self.ok = False

    def _tone(self, parts, vol=0.22):
        buf = array("h")
        for f0, f1, dur in parts:
            n = int(self.rate * dur)
            phase = 0.0
            for i in range(n):
                f = f0 + (f1 - f0) * i / n
                phase += f / self.rate
                v = 1.0 if (phase % 1.0) < 0.5 else -1.0
                env = min(1.0, (n - i) / (n * 0.3))
                s = int(v * env * vol * 32767)
                for _ in range(self.channels):
                    buf.append(s)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if self.ok and not self.muted and name in self.cache:
            self.cache[name].play()


# ----------------------------------------------------------------------------
# Save data
# ----------------------------------------------------------------------------
def load_save():
    data = {"high": 0, "top": [], "coins": 0, "difficulty": "Normal", "muted": False}
    try:
        with open(SAVE_FILE) as f:
            data.update(json.load(f))
    except Exception:
        pass
    if data.get("difficulty") not in DIFFICULTY:
        data["difficulty"] = "Normal"
    return data


def write_save(data):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Game objects
# ----------------------------------------------------------------------------
class Dino:
    def __init__(self, art):
        self.art = art
        self.reset()

    def reset(self):
        self.y = float(GROUND_Y)     # feet position
        self.vy = 0.0
        self.on_ground = True
        self.ducking = False
        self.hold = 0.0
        self.anim = 0.0
        self.dead = False
        self.landed = False

    @property
    def image(self):
        a = self.art
        if self.dead:
            return a["dead"]
        if not self.on_ground:
            return a["stand"]
        frame = int(self.anim * 12) % 2
        if self.ducking:
            return a["duck1"] if frame == 0 else a["duck2"]
        return a["run1"] if frame == 0 else a["run2"]

    @property
    def mask(self):
        return self.art["masks"][id(self.image)]

    @property
    def top(self):
        return int(self.y) - self.image.get_height()

    def update(self, dt, jump_pressed, jump_held, duck_held, sounds):
        self.landed = False
        self.anim += dt
        if self.on_ground:
            self.ducking = duck_held
            if jump_pressed and not duck_held:
                self.vy = -JUMP_V
                self.on_ground = False
                self.hold = 0.0
                sounds.play("jump")
        if not self.on_ground:
            self.ducking = False
            g = GRAVITY
            if self.vy < 0 and jump_held and self.hold < HOLD_TIME:
                g *= 0.4
                self.hold += dt
            if duck_held:
                g *= 3.0                        # fast-fall
            self.vy += g * dt
            self.y += self.vy * dt
            if self.y >= GROUND_Y:
                self.y = float(GROUND_Y)
                self.vy = 0.0
                self.on_ground = True
                self.landed = True


class Obstacle:
    def __init__(self, kind, frames, masks, x, y_bottom, speed_bonus=0.0):
        self.kind = kind
        self.frames = frames
        self.masks = masks
        self.x = float(x)
        self.y_bottom = y_bottom
        self.speed_bonus = speed_bonus
        self.anim = 0.0
        self.passed = False

    @property
    def index(self):
        return int(self.anim * 6) % len(self.frames)

    @property
    def image(self):
        return self.frames[self.index]

    @property
    def mask(self):
        return self.masks[self.index]

    @property
    def top(self):
        return self.y_bottom - self.image.get_height()

    @property
    def width(self):
        return self.image.get_width()

    def update(self, dt, speed):
        self.anim += dt
        self.x -= (speed + self.speed_bonus) * dt


class Coin:
    R = 7

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.t = random.random() * 6

    def update(self, dt, speed, magnet_target=None):
        self.t += dt
        self.x -= speed * dt
        if magnet_target:
            tx, ty = magnet_target
            dx, dy = tx - self.x, ty - self.y
            d = math.hypot(dx, dy)
            if d < 260 and d > 1:
                pull = 900 * dt
                self.x += dx / d * pull
                self.y += dy / d * pull


class PowerUp:
    SIZE = 26

    def __init__(self, kind, x, y):
        self.kind, self.x, self.base_y = kind, float(x), float(y)
        self.t = 0.0

    @property
    def y(self):
        return self.base_y + math.sin(self.t * 4) * 5

    def update(self, dt, speed):
        self.t += dt
        self.x -= speed * dt


class Particle:
    def __init__(self, x, y, vx, vy, life, size):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.size = size

    def update(self, dt):
        self.life -= dt
        self.vy += 900 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt


# ----------------------------------------------------------------------------
# Main game
# ----------------------------------------------------------------------------
class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.Font(None, 48)
        self.font = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 22)
        self.save = load_save()
        self.sounds = Sounds()
        self.sounds.muted = bool(self.save.get("muted"))
        self.diff_name = self.save["difficulty"]
        self._build_art()
        self.dino = Dino(self.dino_art)
        self.tint_cache = {}
        self.state = "menu"
        self.autopilot = False
        self.night_override = False
        self.jump_held = False
        self.duck_held = False
        self.jump_pressed = False
        self.reset()

    # ----- setup ---------------------------------------------------------
    def _build_art(self):
        arts = {
            "stand": HEAD + BODY + LEGS_STAND,
            "run1": HEAD + BODY + LEGS_RUN1,
            "run2": HEAD + BODY + LEGS_RUN2,
            "dead": HEAD_DEAD + BODY + LEGS_STAND,
            "duck1": DUCK_TOP + DUCK_LEGS1,
            "duck2": DUCK_TOP + DUCK_LEGS2,
        }
        self.dino_art = {k: make_sprite(v) for k, v in arts.items()}
        self.dino_art["masks"] = {
            id(s): pygame.mask.from_surface(s) for k, s in self.dino_art.items() if k != "masks"
        }
        self.bird_frames = [make_sprite(BIRD_UP), make_sprite(BIRD_DOWN)]
        self.bird_masks = [pygame.mask.from_surface(s) for s in self.bird_frames]
        self.cloud_img = make_sprite(CLOUD, 2)
        # Pre-generate a pool of cactus designs for variety
        self.cacti = {"small": [], "large": []}
        for _ in range(6):
            self.cacti["small"].append(make_sprite(cactus_rows(12)))
            self.cacti["large"].append(make_sprite(cactus_rows(17)))

    def reset(self):
        cfg = DIFFICULTY[self.diff_name]
        self.cfg = cfg
        self.speed = float(cfg["start"])
        self.score = 0.0
        self.coins = 0
        self.next_milestone = 100
        self.flash = 0.0
        self.obstacles = []
        self.coin_list = []
        self.powerups = []
        self.particles = []
        self.active = {}             # power-up kind -> seconds left
        self.invincible = 0.0
        self.spawn_dist = 600.0
        self.clouds = [[random.uniform(0, W), random.uniform(40, 140)] for _ in range(4)]
        self.stars = [[random.uniform(0, W), random.uniform(20, 160), random.choice((1, 2))]
                      for _ in range(18)]
        self.moon_x = W * 0.75
        self.ground_bits = [[random.uniform(0, W), random.randint(2, 10), random.choice((1, 2, 3))]
                            for _ in range(40)]
        self.ground_off = 0.0
        self.night_t = 0.0
        self.new_high = False
        self.dino.reset()

    # ----- helpers -------------------------------------------------------
    def tinted(self, surf, color):
        key = (id(surf), color)
        img = self.tint_cache.get(key)
        if img is None:
            if len(self.tint_cache) > 400:
                self.tint_cache.clear()
            img = surf.copy()
            img.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.tint_cache[key] = img
        return img

    @property
    def time_scale(self):
        return 0.55 if "slow" in self.active else 1.0

    @property
    def is_night(self):
        cycle = (int(self.score) // 700) % 2 == 1
        return cycle != self.night_override

    def dust(self, x, y, n=6, spread=120):
        for _ in range(n):
            self.particles.append(Particle(x, y, random.uniform(-spread, spread * 0.3),
                                           random.uniform(-220, -60), random.uniform(0.25, 0.5),
                                           random.choice((2, 3))))

    # ----- spawning ------------------------------------------------------
    def spawn(self):
        x = W + 20
        r = random.random()
        can_bird = self.score >= self.cfg["bird_at"]
        if can_bird and r < 0.22:
            height = random.choice(("low", "mid", "high"))
            y_bottom = {"low": GROUND_Y - 6, "mid": GROUND_Y - 44, "high": GROUND_Y - 78}[height]
            ob = Obstacle("bird_" + height, self.bird_frames, self.bird_masks, x, y_bottom,
                          speed_bonus=random.choice((0, 40, -30)))
        else:
            large = self.score > 80 and random.random() < 0.45
            max_n = 1 if self.speed < 520 else (2 if self.speed < 750 else 3)
            n = random.randint(1, max_n)
            pool = self.cacti["large" if large else "small"]
            parts = [random.choice(pool) for _ in range(n)]
            gap = PX
            w = sum(p.get_width() for p in parts) + gap * (n - 1)
            h = max(p.get_height() for p in parts)
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            cx = 0
            for p in parts:
                surf.blit(p, (cx, h - p.get_height()))
                cx += p.get_width() + gap
            ob = Obstacle("cactus", [surf], [pygame.mask.from_surface(surf)], x, GROUND_Y)
        self.obstacles.append(ob)

        # coins arcing over the obstacle
        if random.random() < 0.35:
            n = random.randint(3, 5)
            mid = ob.x + ob.width / 2
            for i in range(n):
                f = (i / (n - 1)) * 2 - 1 if n > 1 else 0
                self.coin_list.append(Coin(mid + f * 70, ob.top - 30 - (1 - f * f) * 45))

        # occasional power-up floating between obstacles
        if self.score > 120 and random.random() < 0.09:
            kind = random.choice(list(POWERUPS))
            self.powerups.append(PowerUp(kind, x + self.speed * 0.45, GROUND_Y - 80))

        # distance to next obstacle grows with speed so jumps stay possible
        min_gap = self.speed * 0.62 + ob.width + 80
        self.spawn_dist = min_gap + random.uniform(0, self.speed * 0.75) * self.cfg["gap"]
        self.spawn_dist *= max(0.85, self.cfg["gap"])

    # ----- autopilot -----------------------------------------------------
    def autopilot_inputs(self):
        d = self.dino
        front = DINO_X + d.image.get_width()
        target = None
        for ob in self.obstacles:
            if ob.x + ob.width > DINO_X:
                target = ob
                break
        jump = duck = hold = False
        if target:
            dist = target.x - front
            lead = (self.speed + target.speed_bonus) * 0.15 + 18
            if target.kind == "bird_high":
                pass
            elif target.kind == "bird_mid":
                duck = dist < self.speed * 0.35
            elif dist < lead:
                jump = True
                hold = target.width > 60 or target.kind == "bird_low"
            if not d.on_ground and target.x + target.width < DINO_X:
                duck = True            # fast-fall once cleared
        return jump, hold or (not d.on_ground and d.vy < 0 and hold), duck

    # ----- update --------------------------------------------------------
    def update(self, dt):
        if self.state != "play":
            self.dino.anim += dt if self.state == "menu" else 0
            return
        dt *= self.time_scale

        jump_pressed, jump_held, duck_held = self.jump_pressed, self.jump_held, self.duck_held
        if self.autopilot:
            jump_pressed, jump_held, duck_held = self.autopilot_inputs()
        self.jump_pressed = False

        d = self.dino
        d.update(dt, jump_pressed, jump_held, duck_held, self.sounds)
        if d.landed:
            self.dust(DINO_X + 20, GROUND_Y)

        # speed & score
        self.speed = min(self.cfg["max"], self.speed + self.cfg["accel"] * dt)
        mult = 2 if "double" in self.active else 1
        self.score += self.speed * dt * 0.025 * mult
        if self.score >= self.next_milestone:
            self.next_milestone += 100
            self.flash = 0.9
            self.sounds.play("point")
        self.flash = max(0.0, self.flash - dt)

        # timers
        for k in list(self.active):
            self.active[k] -= dt / self.time_scale if k == "slow" else dt
            if self.active[k] <= 0:
                del self.active[k]
        self.invincible = max(0.0, self.invincible - dt)

        # night transition
        target = 1.0 if self.is_night else 0.0
        self.night_t += (target - self.night_t) * min(1.0, dt * 2.5)

        # world scroll
        sp = self.speed
        self.ground_off = (self.ground_off + sp * dt) % W
        for b in self.ground_bits:
            b[0] -= sp * dt
            if b[0] < -10:
                b[0] += W + 20
                b[1] = random.randint(2, 10)
        for c in self.clouds:
            c[0] -= sp * 0.12 * dt
            if c[0] < -60:
                c[0] = W + random.uniform(20, 200)
                c[1] = random.uniform(40, 140)
        for s in self.stars:
            s[0] -= 6 * dt
            if s[0] < 0:
                s[0] += W
        self.moon_x -= 4 * dt
        if self.moon_x < -40:
            self.moon_x = W + 40

        # spawn
        self.spawn_dist -= sp * dt
        if self.spawn_dist <= 0:
            self.spawn()

        # objects
        magnet = (DINO_X + 30, d.top + 25) if "magnet" in self.active else None
        for ob in self.obstacles:
            ob.update(dt, sp)
        for c in self.coin_list:
            c.update(dt, sp, magnet)
        for p in self.powerups:
            p.update(dt, sp)
        for p in self.particles:
            p.update(dt)
        self.obstacles = [o for o in self.obstacles if o.x + o.width > -20]
        self.coin_list = [c for c in self.coin_list if c.x > -20]
        self.powerups = [p for p in self.powerups if p.x > -40]
        self.particles = [p for p in self.particles if p.life > 0]

        self.collisions()

    def collisions(self):
        d = self.dino
        dimg = d.image
        dmask = d.mask
        dtop = d.top
        drect = pygame.Rect(DINO_X, dtop, dimg.get_width(), dimg.get_height())

        # coins
        for c in self.coin_list[:]:
            if drect.inflate(6, 6).collidepoint(c.x, c.y):
                self.coin_list.remove(c)
                self.coins += 1
                self.score += 10 * (2 if "double" in self.active else 1)
                self.sounds.play("coin")

        # power-ups
        for p in self.powerups[:]:
            prect = pygame.Rect(p.x, p.y, PowerUp.SIZE, PowerUp.SIZE)
            if drect.colliderect(prect):
                self.powerups.remove(p)
                self.active[p.kind] = POWERUPS[p.kind][3]
                self.sounds.play("power")

        # obstacles
        for ob in self.obstacles[:]:
            off = (int(ob.x) - DINO_X, ob.top - dtop)
            if dmask.overlap(ob.mask, off):
                if self.invincible > 0:
                    continue
                if "shield" in self.active:
                    del self.active["shield"]
                    self.invincible = 1.0
                    self.obstacles.remove(ob)
                    self.dust(ob.x + ob.width / 2, ob.top + 10, n=16, spread=260)
                    self.sounds.play("shield")
                    continue
                self.game_over()
                return

    def game_over(self):
        self.dino.dead = True
        self.state = "over"
        self.sounds.play("hit")
        score = int(self.score)
        s = self.save
        if score > s["high"]:
            s["high"] = score
            self.new_high = True
        s["coins"] = s.get("coins", 0) + self.coins
        s["top"].append({"score": score, "diff": self.diff_name,
                         "date": time.strftime("%d %b %Y")})
        s["top"] = sorted(s["top"], key=lambda e: -e["score"])[:5]
        write_save(s)

    # ----- drawing -------------------------------------------------------
    def draw(self):
        t = self.night_t
        bg = lerp_col(DAY_BG, NIGHT_BG, t)
        fg = lerp_col(DAY_FG, NIGHT_FG, t)
        faint = lerp_col(bg, fg, 0.3)
        scr = self.screen
        scr.fill(bg)

        # stars & moon
        if t > 0.05:
            sc = lerp_col(bg, (255, 255, 255), t)
            for x, y, s in self.stars:
                pygame.draw.rect(scr, sc, (int(x), int(y), s, s))
            mx, my = int(self.moon_x), 55
            pygame.draw.circle(scr, lerp_col(bg, (240, 240, 230), t), (mx, my), 18)
            pygame.draw.circle(scr, bg, (mx + 9, my - 4), 15)

        for x, y in self.clouds:
            scr.blit(self.tinted(self.cloud_img, faint), (int(x), int(y)))

        # ground
        pygame.draw.line(scr, fg, (0, GROUND_Y - 2), (W, GROUND_Y - 2), 2)
        for x, dy, w in self.ground_bits:
            pygame.draw.rect(scr, fg, (int(x), GROUND_Y + dy, w * 2, 2))

        # coins
        for c in self.coin_list:
            wscale = abs(math.cos(c.t * 4))
            rw = max(2, int(Coin.R * 2 * wscale))
            r = pygame.Rect(0, 0, rw, Coin.R * 2)
            r.center = (int(c.x), int(c.y))
            pygame.draw.ellipse(scr, GOLD, r)
            pygame.draw.ellipse(scr, lerp_col(GOLD, (255, 255, 255), 0.5), r.inflate(-rw // 2, -6))

        # power-ups
        for p in self.powerups:
            label, col, icon, _ = POWERUPS[p.kind]
            r = pygame.Rect(int(p.x), int(p.y), PowerUp.SIZE, PowerUp.SIZE)
            glow = int(3 + 2 * math.sin(p.t * 6))
            pygame.draw.rect(scr, lerp_col(col, bg, 0.6), r.inflate(glow * 2, glow * 2), border_radius=8)
            pygame.draw.rect(scr, col, r, border_radius=6)
            txt = self.font.render(icon, True, (255, 255, 255))
            scr.blit(txt, txt.get_rect(center=r.center))

        # obstacles
        for ob in self.obstacles:
            scr.blit(self.tinted(ob.image, fg), (int(ob.x), ob.top))

        # dino
        d = self.dino
        blink = self.invincible > 0 and int(self.invincible * 12) % 2 == 0
        if not blink:
            scr.blit(self.tinted(d.image, fg), (DINO_X, d.top))
        if "shield" in self.active:
            col = POWERUPS["shield"][1]
            cx, cy = DINO_X + d.image.get_width() // 2, d.top + d.image.get_height() // 2
            rad = max(d.image.get_width(), d.image.get_height()) // 2 + 8
            pygame.draw.circle(scr, col, (cx, cy), rad + int(math.sin(time.time() * 8) * 2), 2)

        for p in self.particles:
            col = lerp_col(bg, fg, max(0.0, p.life / p.max_life))
            pygame.draw.rect(scr, col, (int(p.x), int(p.y), p.size, p.size))

        self.draw_hud(fg, bg)

        if self.state == "menu":
            self.draw_menu(fg, bg)
        elif self.state == "paused":
            self.center_text("PAUSED", self.font_big, fg, H // 2 - 40)
            self.center_text("P / Esc to resume   ·   Q for menu", self.font_small, fg, H // 2)
        elif self.state == "over":
            self.draw_game_over(fg, bg)

    def center_text(self, text, font, color, y):
        img = font.render(text, True, color)
        self.screen.blit(img, img.get_rect(center=(W // 2, y)))

    def draw_hud(self, fg, bg):
        if self.state == "menu":
            return
        scr = self.screen
        score = int(self.score)
        show = not (self.flash > 0 and int(self.flash * 8) % 2 == 0)
        hi = max(self.save["high"], score)
        hi_img = self.font.render(f"HI {hi:05d}", True, lerp_col(fg, bg, 0.35))
        sc_img = self.font.render(f"{score:05d}", True, fg)
        scr.blit(sc_img, (W - 20 - sc_img.get_width(), 14))
        scr.blit(hi_img, (W - 36 - sc_img.get_width() - hi_img.get_width(), 14))

        coin_img = self.font_small.render(f"x {self.coins}", True, fg)
        pygame.draw.circle(scr, GOLD, (W - 30 - coin_img.get_width(), 46), 6)
        scr.blit(coin_img, (W - 20 - coin_img.get_width(), 39))

        x = 16
        for kind, left in self.active.items():
            label, col, icon, dur = POWERUPS[kind]
            pygame.draw.rect(scr, col, (x, 14, 120, 18), border_radius=4)
            pygame.draw.rect(scr, lerp_col(col, (255, 255, 255), 0.45),
                             (x, 14, int(120 * max(0, left) / dur), 18), border_radius=4)
            img = self.font_small.render(label, True, (255, 255, 255))
            scr.blit(img, (x + 6, 16))
            x += 130

        tags = []
        if self.autopilot:
            tags.append("AUTOPILOT")
        if self.sounds.muted:
            tags.append("MUTED")
        tags.append(self.diff_name.upper())
        img = self.font_small.render("   ".join(tags), True, lerp_col(fg, bg, 0.4))
        scr.blit(img, (16, H - 24))

    def draw_menu(self, fg, bg):
        scr = self.screen
        self.center_text("DINO RUN", self.font_big, fg, 60)
        self.center_text("Press SPACE to start", self.font, fg, 100)
        x0 = W // 2 - 165
        for i, name in enumerate(DIFF_NAMES):
            r = pygame.Rect(x0 + i * 115, 122, 100, 28)
            sel = name == self.diff_name
            pygame.draw.rect(scr, fg, r, 0 if sel else 2, border_radius=6)
            img = self.font_small.render(f"{i + 1}  {name}", True, bg if sel else fg)
            scr.blit(img, img.get_rect(center=r.center))
        top = self.save["top"]
        y = 168
        title = self.font_small.render(
            f"TOP SCORES        lifetime coins: {self.save.get('coins', 0)}", True, fg)
        scr.blit(title, (W // 2 - 140, y))
        for i, e in enumerate(top[:5]):
            img = self.font_small.render(
                f"{i + 1}.  {e['score']:05d}   {e['diff']:<6}  {e['date']}", True,
                lerp_col(fg, bg, 0.25))
            scr.blit(img, (W // 2 - 140, y + 20 + i * 17))
        if not top:
            img = self.font_small.render("No runs yet — be the first!", True, lerp_col(fg, bg, 0.3))
            scr.blit(img, (W // 2 - 140, y + 20))
        help_ = "Jump: Space/Up/Click (hold = higher)   Duck: Down   Pause: P   Mute: M   Auto: A   Night: N"
        img = self.font_small.render(help_, True, lerp_col(fg, bg, 0.45))
        scr.blit(img, img.get_rect(center=(W // 2, H - 12)))

    def draw_game_over(self, fg, bg):
        self.center_text("G A M E   O V E R", self.font_big, fg, 90)
        msg = f"Score {int(self.score)}   ·   Coins {self.coins}"
        if self.new_high:
            msg = "NEW HIGH SCORE!   " + msg
        self.center_text(msg, self.font, fg, 130)
        # restart icon
        cx, cy = W // 2, 175
        pygame.draw.arc(self.screen, fg, (cx - 16, cy - 16, 32, 32), 0.6, 5.9, 4)
        pygame.draw.polygon(self.screen, fg, [(cx + 10, cy - 18), (cx + 20, cy - 6), (cx + 6, cy - 4)])
        self.center_text("SPACE to play again   ·   Esc for menu", self.font_small, fg, 212)

    # ----- input & loop --------------------------------------------------
    def start(self):
        self.reset()
        self.state = "play"
        self.jump_pressed = False

    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.quit()
        jump_keys = (pygame.K_SPACE, pygame.K_UP, pygame.K_w)
        duck_keys = (pygame.K_DOWN, pygame.K_s)
        if e.type == pygame.KEYDOWN:
            k = e.key
            if k == pygame.K_m:
                self.sounds.muted = not self.sounds.muted
                self.save["muted"] = self.sounds.muted
                write_save(self.save)
            elif k == pygame.K_f:
                try:
                    pygame.display.toggle_fullscreen()
                except Exception:
                    pass
            elif k == pygame.K_n:
                self.night_override = not self.night_override
                if self.state != "play":
                    self.night_t = 1.0 if self.is_night else 0.0
            elif k == pygame.K_a:
                self.autopilot = not self.autopilot

            if self.state == "menu":
                if k in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.set_difficulty(DIFF_NAMES[k - pygame.K_1])
                elif k in (pygame.K_LEFT, pygame.K_RIGHT):
                    i = DIFF_NAMES.index(self.diff_name) + (1 if k == pygame.K_RIGHT else -1)
                    self.set_difficulty(DIFF_NAMES[i % 3])
                elif k in jump_keys or k == pygame.K_RETURN:
                    self.start()
                elif k == pygame.K_ESCAPE:
                    self.quit()
            elif self.state == "play":
                if k in jump_keys:
                    self.jump_pressed = True
                    self.jump_held = True
                elif k in duck_keys:
                    self.duck_held = True
                elif k in (pygame.K_p, pygame.K_ESCAPE):
                    self.state = "paused"
            elif self.state == "paused":
                if k in (pygame.K_p, pygame.K_ESCAPE):
                    self.state = "play"
                elif k == pygame.K_q:
                    self.state = "menu"
                    self.reset()
            elif self.state == "over":
                if k in jump_keys or k == pygame.K_RETURN:
                    self.start()
                elif k == pygame.K_ESCAPE:
                    self.state = "menu"
                    self.reset()
        elif e.type == pygame.KEYUP:
            if e.key in jump_keys:
                self.jump_held = False
            elif e.key in duck_keys:
                self.duck_held = False
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.state in ("menu", "over"):
                self.start()
            elif self.state == "play":
                self.jump_pressed = self.jump_held = True
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.jump_held = False
        elif e.type in (pygame.WINDOWFOCUSLOST,) and self.state == "play":
            self.state = "paused"          # auto-pause when you alt-tab

    def set_difficulty(self, name):
        self.diff_name = name
        self.save["difficulty"] = name
        write_save(self.save)
        self.reset()

    def quit(self):
        write_save(self.save)
        pygame.quit()
        sys.exit()

    def run(self):
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 30)
            for e in pygame.event.get():
                self.handle_event(e)
            self.update(dt)
            self.draw()
            pygame.display.flip()


def main():
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    pygame.display.set_caption("Dino Run")
    flags = pygame.SCALED | pygame.RESIZABLE
    try:
        screen = pygame.display.set_mode((W, H), flags)
    except Exception:
        screen = pygame.display.set_mode((W, H))
    Game(screen).run()


if __name__ == "__main__":
    main()