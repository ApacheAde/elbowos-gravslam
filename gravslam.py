#!/usr/bin/env python3
"""GravSlam — original ElbowOS neon gravity-basketball arcade (Python 3 + pygame)."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys
from pathlib import Path

W, H = 1080, 1920
FPS = 30
SECONDS = 15
FRAMES = FPS * SECONDS
TITLE = "GRAVSLAM"
OUT = Path("/home/workdir/artifacts/GRAVSLAM_ElbowOS.mp4")

if "--play" not in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

COURT_L, COURT_R = 80, W - 80
COURT_T, COURT_B = 240, H - 180
GRAV = 0.62
BALL_R = 28
PAD_W, PAD_H = 168, 28


def lerp(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


class Game:
    def __init__(self, seed=7):
        self.rng = random.Random(seed)
        self.score = 0
        self.shots = 0
        self.t = 0
        self.flash = 0
        self.combo = 0
        self.sparks = []
        self.pad_x = W * 0.5
        self.pad_v = 0.0
        self.hoop_x = W * 0.5
        self.hoop_v = 4.2
        self.held = True
        self.charge = 0.0
        self.charging = False
        self.aim = -math.pi / 2
        self.reset_ball(held=True)
        self.orbs = [
            [280, 820, 36, 1.4, (70, 255, 210)],
            [800, 980, 42, -1.1, (255, 140, 70)],
            [540, 640, 30, 1.8, (180, 120, 255)],
        ]

    def reset_ball(self, held=True):
        self.held = held
        self.bx = self.pad_x
        self.by = COURT_B - 70
        self.vx = 0.0
        self.vy = 0.0
        self.scored = False

    def launch(self, power=None, ang=None):
        if not self.held:
            return
        a = self.aim if ang is None else ang
        p = 34.0 + 14.0 * (self.charge if power is None else power)
        self.vx = math.cos(a) * p
        self.vy = math.sin(a) * p
        self.held = False
        self.charging = False
        self.charge = 0.0
        self.shots += 1
        self.scored = False

    def autoplay(self):
        lead = self.hoop_x + self.hoop_v * 22
        err = lead - self.pad_x
        self.pad_v += max(-2.0, min(2.0, err * 0.018))
        self.pad_v *= 0.84
        want = -math.pi / 2 + max(-0.42, min(0.42, (lead - self.pad_x) * 0.0011))
        self.aim += (want - self.aim) * 0.22
        if self.held:
            if not self.charging and self.t % 18 == 0:
                self.charging = True
            if self.charging:
                self.charge = min(1.0, self.charge + 0.06)
                if self.charge > 0.72 + 0.12 * math.sin(self.t * 0.17):
                    self.launch()
        elif self.by > COURT_B - 90 and self.vy > 2:
            if abs(self.bx - self.pad_x) < PAD_W * 0.55:
                self.reset_ball(held=True)

    def tick(self, human=None):
        self.t += 1
        if self.flash:
            self.flash -= 1
        self.hoop_x += self.hoop_v
        if self.hoop_x < COURT_L + 140 or self.hoop_x > COURT_R - 140:
            self.hoop_v *= -1
            self.hoop_x = max(COURT_L + 140, min(COURT_R - 140, self.hoop_x))

        if human is None:
            self.autoplay()
        else:
            mx, charge, fire, aim_d = human
            self.pad_v += mx * 1.4
            self.pad_v *= 0.82
            self.aim += aim_d
            self.aim = max(-math.pi + 0.35, min(-0.35, self.aim))
            if charge and self.held:
                self.charging = True
                self.charge = min(1.0, self.charge + 0.05)
            if fire and self.held:
                self.launch()

        self.pad_x += self.pad_v
        self.pad_x = max(COURT_L + PAD_W * 0.5, min(COURT_R - PAD_W * 0.5, self.pad_x))

        for o in self.orbs:
            o[0] += o[3]
            if o[0] < COURT_L + 80 or o[0] > COURT_R - 80:
                o[3] *= -1

        if self.held:
            self.bx = self.pad_x
            self.by = COURT_B - 62
        else:
            self.vy += GRAV
            self.vx *= 0.998
            self.bx += self.vx
            self.by += self.vy
            if self.bx < COURT_L + BALL_R:
                self.bx = COURT_L + BALL_R
                self.vx = abs(self.vx) * 0.78
            if self.bx > COURT_R - BALL_R:
                self.bx = COURT_R - BALL_R
                self.vx = -abs(self.vx) * 0.78
            if self.by < COURT_T + BALL_R:
                self.by = COURT_T + BALL_R
                self.vy = abs(self.vy) * 0.55
            for o in self.orbs:
                dx, dy = self.bx - o[0], self.by - o[1]
                dist = math.hypot(dx, dy) or 0.001
                if dist < o[2] + BALL_R:
                    nx, ny = dx / dist, dy / dist
                    overlap = o[2] + BALL_R - dist
                    self.bx += nx * overlap
                    self.by += ny * overlap
                    vn = self.vx * nx + self.vy * ny
                    if vn < 0:
                        self.vx -= 1.75 * vn * nx
                        self.vy -= 1.75 * vn * ny
                        self.vx += nx * 3.2
                        self.vy += ny * 3.2
            rim_y = COURT_T + 210
            if not self.scored and self.vy > 0 and abs(self.bx - self.hoop_x) < 68 and rim_y - 28 < self.by < rim_y + 48:
                self.scored = True
                self.combo += 1
                pts = 100 + self.combo * 25
                self.score += pts
                self.flash = 10
                for _ in range(22):
                    a = self.rng.random() * 6.28
                    s = self.rng.uniform(2, 10)
                    self.sparks.append([self.hoop_x, rim_y, math.cos(a) * s, math.sin(a) * s, 16, (255, 200, 70)])
            if self.by > COURT_B - 48:
                if abs(self.bx - self.pad_x) < PAD_W * 0.55 and self.vy > 0:
                    self.reset_ball(held=True)
                    self.combo = max(0, self.combo - 1)
                elif self.by > COURT_B + 20:
                    self.combo = 0
                    self.reset_ball(held=True)

        keep = []
        for s in self.sparks:
            s[0] += s[2]
            s[1] += s[3]
            s[3] += 0.2
            s[4] -= 1
            if s[4] > 0:
                keep.append(s)
        self.sparks = keep
        if self.t % 20 == 0:
            self.score += 1


def draw(surf, g, fonts):
    font_lg, font_md, font_sm = fonts
    t = g.t
    for y in range(0, H, 8):
        pygame.draw.rect(surf, lerp((6, 18, 28), (18, 8, 40), y / H), (0, y, W, 8))
    for i in range(10):
        yy = int((t * 7 + i * 210) % H)
        pygame.draw.line(surf, (20, 70, 80), (0, yy), (W, yy), 2)

    pygame.draw.rect(surf, (10, 28, 38), (COURT_L, COURT_T, COURT_R - COURT_L, COURT_B - COURT_T), border_radius=28)
    pygame.draw.rect(surf, (40, 230, 210), (COURT_L, COURT_T, COURT_R - COURT_L, COURT_B - COURT_T), 5, border_radius=28)
    mid = (COURT_L + COURT_R) // 2
    pygame.draw.line(surf, (30, 90, 100), (mid, COURT_T + 20), (mid, COURT_B - 20), 3)
    pygame.draw.circle(surf, (30, 90, 100), (mid, (COURT_T + COURT_B) // 2), 120, 3)

    rim_y = COURT_T + 210
    hx = int(g.hoop_x)
    pygame.draw.rect(surf, (255, 150, 40), (hx - 8, COURT_T + 40, 16, rim_y - COURT_T - 40))
    back = pygame.Rect(hx - 110, COURT_T + 70, 220, 150)
    pygame.draw.rect(surf, (230, 250, 255), back, 6, border_radius=6)
    pygame.draw.rect(surf, (90, 200, 255), (hx - 48, COURT_T + 110, 96, 70), 5)
    pygame.draw.ellipse(surf, (255, 90, 40), (hx - 70, rim_y - 14, 140, 28), 8)
    pygame.draw.ellipse(surf, (255, 220, 80), (hx - 62, rim_y - 8, 124, 18), 3)
    for i in range(6):
        nx = hx - 50 + i * 20
        pygame.draw.line(surf, (255, 170, 70), (nx, rim_y + 6), (hx + (nx - hx) * 0.2, rim_y + 70), 2)

    for o in g.orbs:
        glow = pygame.Surface((int(o[2] * 4), int(o[2] * 4)), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*o[4], 60), (int(o[2] * 2), int(o[2] * 2)), int(o[2] * 2))
        surf.blit(glow, (int(o[0] - o[2] * 2), int(o[1] - o[2] * 2)))
        pygame.draw.circle(surf, o[4], (int(o[0]), int(o[1])), int(o[2]))
        pygame.draw.circle(surf, (255, 255, 240), (int(o[0]), int(o[1])), int(o[2]), 3)

    px, py = int(g.pad_x), COURT_B - 28
    pygame.draw.rect(surf, (40, 255, 190), (px - PAD_W // 2, py, PAD_W, PAD_H), border_radius=12)
    pygame.draw.rect(surf, (200, 255, 240), (px - PAD_W // 2, py, PAD_W, PAD_H), 3, border_radius=12)
    if g.held:
        ax = g.pad_x + math.cos(g.aim) * (90 + 80 * g.charge)
        ay = (COURT_B - 62) + math.sin(g.aim) * (90 + 80 * g.charge)
        col = lerp((80, 255, 210), (255, 200, 60), g.charge)
        pygame.draw.line(surf, col, (g.pad_x, COURT_B - 62), (ax, ay), 6)
        pygame.draw.circle(surf, col, (int(ax), int(ay)), 8)

    pygame.draw.circle(surf, (255, 160, 50), (int(g.bx), int(g.by)), BALL_R + 5)
    pygame.draw.circle(surf, (255, 120, 30), (int(g.bx), int(g.by)), BALL_R)
    pygame.draw.circle(surf, (40, 20, 10), (int(g.bx), int(g.by)), BALL_R, 3)
    pygame.draw.arc(surf, (40, 20, 10), (int(g.bx - 18), int(g.by - 18), 36, 36), 0.4, 2.6, 2)
    pygame.draw.line(surf, (40, 20, 10), (int(g.bx), int(g.by - BALL_R + 2)), (int(g.bx), int(g.by + BALL_R - 2)), 2)

    for s in g.sparks:
        pygame.draw.circle(surf, s[5], (int(s[0]), int(s[1])), max(2, s[4] // 3))
    if g.flash:
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((255, 180, 40, 36))
        surf.blit(veil, (0, 0))

    bar = pygame.Surface((W, 160), pygame.SRCALPHA)
    bar.fill((6, 16, 24, 230))
    surf.blit(bar, (0, 0))
    surf.blit(font_lg.render(TITLE, True, (255, 150, 40)), (36, 16))
    surf.blit(font_sm.render("ElbowOS  ·  Python 3 gravity basketball  ·  autoplay reel", True, (140, 230, 220)), (40, 100))
    sc = font_md.render(f"SLAM  {g.score:05d}", True, (255, 220, 80))
    surf.blit(sc, (W - sc.get_width() - 36, 26))
    cmb = font_sm.render(f"combo x{g.combo}   shots {g.shots}", True, (80, 255, 200))
    surf.blit(cmb, (W - cmb.get_width() - 36, 88))

    foot = pygame.Surface((W, 110), pygame.SRCALPHA)
    foot.fill((6, 16, 24, 230))
    surf.blit(foot, (0, H - 110))
    tag = font_sm.render("x.com/ElbowOS", True, (255, 150, 40))
    surf.blit(tag, (W - tag.get_width() - 36, H - 68))
    hint = font_sm.render("A/D move  ·  arrows aim  ·  SPACE charge/launch", True, (160, 210, 210))
    surf.blit(hint, (36, H - 68))


def fonts():
    try:
        return (
            pygame.font.SysFont("dejavusans", 68, bold=True),
            pygame.font.SysFont("dejavusans", 40, bold=True),
            pygame.font.SysFont("dejavusans", 28),
        )
    except Exception:
        return pygame.font.Font(None, 76), pygame.font.Font(None, 46), pygame.font.Font(None, 32)


def record(out: Path = OUT) -> Path:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    surf = pygame.Surface((W, H))
    g = Game()
    fnt = fonts()
    tmp = out.with_suffix(".tmp.mp4")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "veryfast", "-movflags", "+faststart", str(tmp),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    for _ in range(FRAMES):
        g.tick()
        draw(surf, g, fnt)
        proc.stdin.write(pygame.image.tostring(surf, "RGB"))
    proc.stdin.close()
    err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    rc = proc.wait()
    pygame.quit()
    if rc != 0 or not tmp.exists():
        raise RuntimeError(f"ffmpeg failed ({rc}): {err[-800:]}")
    tmp.replace(out)
    return out


def play():
    os.environ.pop("SDL_VIDEODRIVER", None)
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((W // 2, H // 2))
    pygame.display.set_caption("GravSlam — ElbowOS")
    canvas = pygame.Surface((W, H))
    clock = pygame.time.Clock()
    g = Game()
    fnt = fonts()
    running = True
    while running:
        keys = pygame.key.get_pressed()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif ev.key == pygame.K_r:
                    g = Game()
                elif ev.key in (pygame.K_SPACE, pygame.K_UP) and g.held and g.charge > 0.15:
                    g.launch()
        mx = (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0) - (1 if keys[pygame.K_a] or keys[pygame.K_LEFT] else 0)
        aim_d = (-0.04 if keys[pygame.K_w] else 0) + (0.04 if keys[pygame.K_s] else 0)
        charge = keys[pygame.K_SPACE] or keys[pygame.K_UP]
        fire = False
        g.tick((mx, charge, fire, aim_d))
        draw(canvas, g, fnt)
        pygame.transform.smoothscale(canvas, screen.get_size(), screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


if __name__ == "__main__":
    if "--play" in sys.argv:
        play()
    else:
        path = record()
        print(path)
        print("bytes", path.stat().st_size)
        sys.exit(0)
