import sys, math, os
import pygame

WIN_W, WIN_H = 1200, 700
BG = (236, 236, 236)
FPS = 60

MAX_SPEED = 170.0      
EASE = 6.0             
SMOOTH = 10.0          


MAX_TOTAL_TILT_DEG = 18
SPEED_TILT_FACTOR = 0.07 
MOUSE_TILT_GAIN   = 0.18 

# волна по телу 
SLICE_W = 2
WAVE_AMP = 10
WAVE_TAIL_GAIN = 2.2
WAVE_FREQ = 2.0
PROP_DELAY_TOTAL = 0.14
TAIL_BOOST = 1.9
TAIL_CURVE = 1.7
HEAD_NOD_PIX = 6
HEAD_NOD_SMOOTH = 0.33  

# ---------- УТИЛИТЫ ----------
def clamp(a, lo, hi): return max(lo, min(hi, a))

def clamp_vec(vx, vy, m):
    L = (vx*vx + vy*vy) ** 0.5
    if L == 0: return 0.0, 0.0
    if L > m:
        k = m / L
        return vx*k, vy*k
    return vx, vy

def _first_existing(path_list):
    """Вернёт первый существующий путь из списка или None."""
    for p in path_list:
        if p and os.path.exists(p): return p
    return None

def _load_and_scale(path, target_w):
    s = pygame.image.load(path).convert_alpha()
    scale = target_w / s.get_width()
    return pygame.transform.rotozoom(s, 0, scale)

def load_sprite_pair_for_set(color_set:str):
    """
    Возвращает (left, right) для выбранного набора.
    Поддерживает несколько вариантов имён файлов — как у тебя в папке.
    """
    target_w = WIN_W // 3

    if color_set == "blue":
        left  = _first_existing(["whale_pixel_1.png", "whale_pixel_1 (1).png"])
        right = _first_existing(["whale_pixel_2.png"])
        # если одного не хватает — зеркалим второй
        if not left and not right:
            raise SystemExit("Нет файлов голубого кита: whale_pixel_1*.png и whale_pixel_2.png")
        if left  and right:
            L = _load_and_scale(left,  target_w)
            R = _load_and_scale(right, target_w)
            return L, R
        if right:
            R = _load_and_scale(right, target_w)
            return pygame.transform.flip(R, True, False), R
        if left:
            L = _load_and_scale(left, target_w)
            return L, pygame.transform.flip(L, True, False)

    if color_set == "gray":
        left  = _first_existing(["whale_gray_left.png"])
        right = _first_existing(["whale_gray_right.png"])
        if not left and not right:
            raise SystemExit("Нет файлов серого кита: whale_gray_left.png / whale_gray_right.png")
        if left and right:
            return _load_and_scale(left, target_w), _load_and_scale(right, target_w)
        if right:
            R = _load_and_scale(right, target_w)
            return pygame.transform.flip(R, True, False), R
        if left:
            L = _load_and_scale(left, target_w)
            return L, pygame.transform.flip(L, True, False)

    if color_set == "dark":
    
        left  = _first_existing(["whale_darkblue_left.png", "whale_darkblue_2.png"])
        right = _first_existing(["whale_darkblue_right.png", "whale_darkblue.png"])
        if not left and not right:
            raise SystemExit("Нет файлов тёмно-синего кита: whale_darkblue_(left/right).png или whale_darkblue(.png/_2.png)")
        if left and right:
            return _load_and_scale(left, target_w), _load_and_scale(right, target_w)
        if right:
            R = _load_and_scale(right, target_w)
            return pygame.transform.flip(R, True, False), R
        if left:
            L = _load_and_scale(left, target_w)
            return L, pygame.transform.flip(L, True, False)

    raise SystemExit("Неизвестный набор цвета: " + color_set)

def undulate_whole_sprite_sine(src, t, head_on_right, head_nod_norm):
    """Плавная синусоида по Y с пропагацией; усиленный хвост; кивок головы."""
    w, h = src.get_width(), src.get_height()
    margin = int(WAVE_AMP * WAVE_TAIL_GAIN * max(1.0, TAIL_BOOST)) + HEAD_NOD_PIX + 8
    out = pygame.Surface((w, h + 2*margin), pygame.SRCALPHA)

    for x0 in range(0, w, SLICE_W):
        cw = min(SLICE_W, w - x0)
        col = src.subsurface(pygame.Rect(x0, 0, cw, h))

        tail_factor  = (1.0 - x0/(w-1)) if head_on_right else (x0/(w-1))
        tail_profile = tail_factor ** TAIL_CURVE

        delay = tail_factor * PROP_DELAY_TOTAL
        phase = 2.0 * math.pi * WAVE_FREQ * max(0.0, t - delay)

        base_amp = WAVE_AMP * (1.0 + tail_profile * (WAVE_TAIL_GAIN - 1.0))
        amp      = base_amp * (1.0 + tail_profile * (TAIL_BOOST - 1.0))

        dy_wave = amp * tail_profile * math.sin(phase)

        # кивок головы 
        head_weight = (1.0 - tail_profile)
        dy_head = HEAD_NOD_PIX * head_nod_norm * head_weight

        dy = int(dy_wave + dy_head)
        out.blit(col, (x0, margin + dy))

    return out.subsurface(pygame.Rect(0, margin, w, h)).copy()

BTN_W, BTN_H = 120, 34
BTN_GAP = 10
BTN_Y = 8
def make_buttons():
    x = 10
    rect_gray = pygame.Rect(x, BTN_Y, BTN_W, BTN_H);   x += BTN_W + BTN_GAP
    rect_dark = pygame.Rect(x, BTN_Y, BTN_W, BTN_H);   x += BTN_W + BTN_GAP
    rect_blue = pygame.Rect(x, BTN_Y, BTN_W, BTN_H)
    return rect_gray, rect_dark, rect_blue

def draw_button(screen, rect, text, active, font):
    pygame.draw.rect(screen, (220,220,220) if not active else (190,190,190), rect, border_radius=8)
    pygame.draw.rect(screen, (160,160,160), rect, 2, border_radius=8)
    label = font.render(text, True, (30,30,30))
    screen.blit(label, (rect.centerx - label.get_width()//2, rect.centery - label.get_height()//2))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Whale — smooth wave + smoothed head nod & diagonal tilt")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 20)
    font_info = pygame.font.SysFont(None, 22)

    active_set = "blue"   # при старте голубой
    sprite_left, sprite_right = load_sprite_pair_for_set(active_set)

    posx, posy = WIN_W*0.35, WIN_H*0.55
    velx = vely = 0.0
    t = 0.0

    facing_right = True
    head_nod_norm = 0.0  

    btn_gray, btn_dark, btn_blue = make_buttons()

    while True:
        dt = clock.tick(FPS) / 1000.0
        t += dt

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                # нажатие по кнопкам
                if btn_gray.collidepoint(mx, my) and active_set != "gray":
                    active_set = "gray"
                    sprite_left, sprite_right = load_sprite_pair_for_set(active_set)
                elif btn_dark.collidepoint(mx, my) and active_set != "dark":
                    active_set = "dark"
                    sprite_left, sprite_right = load_sprite_pair_for_set(active_set)
                elif btn_blue.collidepoint(mx, my) and active_set != "blue":
                    active_set = "blue"
                    sprite_left, sprite_right = load_sprite_pair_for_set(active_set)

        mx, my = pygame.mouse.get_pos()

        # следование к курсору
        want_vx, want_vy = (mx - posx) * EASE, (my - posy) * EASE
        want_vx, want_vy = clamp_vec(want_vx, want_vy, MAX_SPEED)
        velx += (want_vx - velx) * min(1.0, SMOOTH * dt)
        vely += (want_vy - vely) * min(1.0, SMOOTH * dt)
        posx += velx * dt; posy += vely * dt

        if abs(mx - posx) > 2.0:
            facing_right = mx > posx

        base = sprite_right if facing_right else sprite_left
        head_on_right = facing_right

        # кивок головы 
        target_nod = clamp((posy - my) / (WIN_H * 0.35), -1.0, 1.0)
        alpha = 1.0 - math.exp(-dt / HEAD_NOD_SMOOTH)   # ~63% за 0.33с
        head_nod_norm += (target_nod - head_nod_norm) * alpha
        waved = undulate_whole_sprite_sine(base, t, head_on_right, head_nod_norm)

        # диагональный наклон 
        desired_angle_deg = math.degrees(math.atan2(my - posy, mx - posx))
        mouse_tilt_deg = desired_angle_deg * MOUSE_TILT_GAIN
        speed_tilt_deg = -vely * SPEED_TILT_FACTOR
        mouse_tilt_deg += head_nod_norm * 4.0
        angle_deg = clamp(mouse_tilt_deg + speed_tilt_deg,
                          -MAX_TOTAL_TILT_DEG, MAX_TOTAL_TILT_DEG)
        rotated = pygame.transform.rotozoom(waved, angle_deg, 1.0)
        rect = rotated.get_rect(center=(posx, posy))

        # тень 
        sh_w = int(base.get_width() * 0.7)
        sh_h = max(12, int(base.get_height() * 0.14))
        shadow = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 45), shadow.get_rect())

        screen.fill(BG)
        
        # кнопки
        draw_button(screen, btn_gray, "Gray", active_set=="gray", font)
        draw_button(screen, btn_dark, "Dark", active_set=="dark", font)
        draw_button(screen, btn_blue, "Blue", active_set=="blue", font)

        screen.blit(shadow, (posx - sh_w*0.45, posy + base.get_height()*0.25))
        screen.blit(rotated, rect)

        # текст
        screen.blit(font_info.render(
            "Press the buttons to change the whale’s color",
            True, (70,70,70)), (16, 14 + BTN_H + 6))

        pygame.display.flip()

if __name__ == "__main__":
    main()
