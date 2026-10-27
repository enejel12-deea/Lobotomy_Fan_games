import heapq
import os
import random
from collections import deque
import pygame

# 맵마다 창 크기가 달라서, 창을 만들거나 크기를 바꿀 때마다 화면 가운데에 오게 함
# (pygame._sdl2의 Window로 창을 옮기면 일반 pygame에서는 게임이 갑자기 꺼지는 문제가 있어서 이 방법을 씀)
os.environ["SDL_VIDEO_CENTERED"] = "1"
pygame.init()

screen_width = 800
screen_height = 800
screen = pygame.display.set_mode((screen_width, screen_height))

pygame.display.set_caption("게임")

# 방향별 캐릭터 이미지 (서 있는 모습, 걷는 모습들)
character_width = 56
character_height = 93

# you Now.png 스프라이트 시트: 4열 x 5행
# 1행: 서 있기 (아래, 왼쪽, 오른쪽, 위) / 2~5행: 아래, 왼쪽, 오른쪽, 위로 걷기 4장씩
sprite_sheet = pygame.image.load("D:/hjh/VScode/Movement test/you Now.png").convert_alpha()
# 칸 간격이 일정하지 않아서 칸 경계를 직접 지정
column_edges = [300, 530, 770, 1000, 1236]
row_edges = [0, 235, 441, 629, 816, 1024]

def cut_frame(column, row):
    cell = sprite_sheet.subsurface((column_edges[column], row_edges[row],
                                    column_edges[column + 1] - column_edges[column],
                                    row_edges[row + 1] - row_edges[row]))
    return clean_frame(cell)

def fill_edge_colors(image):
    # 투명한 칸은 색이 검은색이라 줄일 때 캐릭터 가장자리에 검은 테두리가 생김
    # 그래서 투명한 칸에 바로 옆 캐릭터 색을 채워 둠 (투명한 건 그대로)
    colors = image.copy()
    for _ in range(3):
        spread = pygame.Surface(colors.get_size(), pygame.SRCALPHA)
        for offset in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            spread.blit(colors, offset)
        spread.blit(colors, (0, 0))
        colors = spread
    colors.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MULT)
    colors.blit(image, (0, 0))
    return colors

def clean_frame(cell, biggest_only=False):
    # 캐릭터 주변의 반투명한 빛은 지우고 캐릭터만 남김
    mask = pygame.mask.from_surface(cell, 200)
    if biggest_only:
        # 옆 칸 캐릭터의 머리카락이 넘어온 조각은 버리고 가장 큰 덩어리(캐릭터)만 남김
        mask = mask.connected_component()
    clean = mask.to_surface(setsurface=cell, unsetcolor=(0, 0, 0, 0))
    clean = fill_edge_colors(clean.subsurface(clean.get_bounding_rect()))
    # 키를 character_height에 맞춰 줄임
    width = round(clean.get_width() * character_height / clean.get_height())
    return pygame.transform.smoothscale(clean, (width, character_height))

directions = ["down", "left", "right", "up"]
sprites = {}
for index, name in enumerate(directions):
    sprites[name] = {"idle": cut_frame(index, 0), "walk": [cut_frame(column, index + 1) for column in range(4)]}
direction = "down"
walk_timer = 0
walk_frame_time = 6  # 걷는 그림이 바뀌는 간격 (프레임 수)

# NPC 스프라이트 시트: 4줄(앞, 뒤, 왼쪽, 오른쪽) x 5칸(서 있기 1칸 + 걷기 4칸), 배경은 이미 투명함
# 그림마다 캐릭터 위치가 조금씩 달라서 칸 위치는 불투명한 부분을 보고 알아서 찾음
npc_files = ["Character image/NPC/npc_nn-%d.png" % number for number in range(1, 8)]
npc_row_directions = ["down", "up", "left", "right"]

def opaque_count(mask, rect):
    # rect 안에 있는 불투명한 픽셀 수
    area = pygame.mask.Mask(rect.size, fill=True)
    return mask.overlap_area(area, rect.topleft)

def find_columns(mask):
    # 세로로 한 줄씩 보면서 캐릭터가 하나도 없는 틈으로 5칸을 나눔 (캐릭터 폭보다 좁은 덩어리는 무시)
    width, height = mask.get_size()
    columns, left = [], None
    for x in range(width + 1):
        filled = x < width and opaque_count(mask, pygame.Rect(x, 0, 1, height)) > 0
        if filled and left is None:
            left = x
        elif not filled and left is not None:
            if x - left >= 60:
                columns.append((left, x))
            left = None
    return columns

def find_row_lines(mask, left, right):
    # 위아래 캐릭터는 머리카락 끝이 아래 줄 캐릭터의 발에 닿기도 해서,
    # 높이를 4등분한 선 근처에서 불투명한 픽셀이 가장 적은 가로줄을 경계로 씀
    height = mask.get_size()[1]
    lines = [0]
    for number in range(1, 4):
        guess = height * number // 4
        candidates = range(guess - 60, guess + 61)
        lines.append(min(candidates, key=lambda y: (opaque_count(mask, pygame.Rect(left, y, right - left, 1)), abs(y - guess))))
    return lines + [height]

def load_npc(file):
    sheet = pygame.image.load("D:/hjh/VScode/Movement test/" + file).convert_alpha()
    mask = pygame.mask.from_surface(sheet, 200)
    columns = find_columns(mask)
    cells = {name: [] for name in npc_row_directions}
    for left, right in columns:
        lines = find_row_lines(mask, left, right)
        for index, name in enumerate(npc_row_directions):
            cell = sheet.subsurface((left, lines[index], right - left, lines[index + 1] - lines[index]))
            cells[name].append(clean_frame(cell, biggest_only=True))
    sprites = {}
    for name, images in cells.items():
        # 한 발 내딛을 때마다 서 있는 모습을 잠깐 넣어서 걸음이 자연스럽게 이어지게 함
        idle, walk = images[0], images[1:]
        sprites[name] = {"idle": idle, "walk": [walk[0], walk[1], idle, walk[2], walk[3], idle]}
    return sprites

npc_sprites = [load_npc(file) for file in npc_files]

def direction_from_speed():
    # 움직이는 방향이 있으면 그쪽을 보고, 멈추면 마지막 방향 유지
    if to_x < 0:
        return "left"
    if to_x > 0:
        return "right"
    if to_y < 0:
        return "up"
    if to_y > 0:
        return "down"
    return direction

clock = pygame.time.Clock()

# 격리실 문으로 들어갔을 때 캐릭터 위치 (격리실 아래쪽 문 바로 위)
isolation_entry = (300, 507)
# 원본 1020x1195 이미지를 640x750으로 줄여서 사용 (모든 격리실이 같은 그림을 씀)
isolation_background = pygame.transform.smoothscale(
    pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy isolation.png"), (640, 750))

def make_isolation(back_map, back_position):
    # 모습은 같지만 격리실마다 따로 만들어서 각자 들어온 문으로 돌아가게 함
    return {
        "background": isolation_background,
        "size": (640, 750),
        "walls": [
            pygame.Rect(0, 0, 640, 175),      # 위쪽 벽 (머리 높이만큼 아래까지)
            pygame.Rect(0, 0, 205, 750),      # 왼쪽 벽 (기계들까지)
            pygame.Rect(432, 0, 208, 750),    # 오른쪽 벽 (기계들까지)
            pygame.Rect(0, 640, 640, 110),    # 아래쪽 벽 (파이프부터)
        ],
        "doors": [
            (pygame.Rect(290, 620, 76, 20), back_map, back_position),  # 아래 문 (복도로 돌아가기)
        ],
    }

# 맵 정보: 배경, 화면 크기, 지나갈 수 없는 영역(walls), 문(doors)
# 문은 (닿는 영역, 이동할 맵 이름, 이동한 맵에서 캐릭터 위치)
maps = {
    "lobby": {
        "background": pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Corporation.png"),
        "size": (800, 800),
        "walls": [
            pygame.Rect(0, 0, 800, 215),      # 위쪽 벽
            pygame.Rect(0, 0, 25, 800),       # 왼쪽 벽
            pygame.Rect(775, 0, 25, 800),     # 오른쪽 벽
            pygame.Rect(0, 465, 328, 335),    # 왼쪽 아래 바깥
            pygame.Rect(472, 465, 328, 335),  # 오른쪽 아래 바깥
            pygame.Rect(0, 760, 800, 40),     # 복도 끝
            pygame.Rect(275, 215, 250, 70),   # 데스크
            pygame.Rect(310, 285, 180, 45),   # 데스크 앞쪽 곡선 부분
        ],
        "doors": [
            (pygame.Rect(100, 200, 45, 25), "lobby2", (290, 130)),  # 왼쪽 문
            (pygame.Rect(655, 200, 45, 25), "lobby2", (857, 130)),  # 오른쪽 문
        ],
        "elevator": True,  # 이 맵의 문은 엘리베이터를 타고 이동
    },
    "lobby2": {
        # 원본 1536x1024 이미지를 1200x800으로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Corporation-1.png"), (1200, 800)),
        "size": (1200, 800),
        "walls": [
            pygame.Rect(0, 0, 1200, 190),     # 위쪽 벽
            pygame.Rect(0, 0, 262, 335),      # 왼쪽 위 벽
            pygame.Rect(938, 0, 262, 335),    # 오른쪽 위 벽
            pygame.Rect(184, 285, 70, 70),    # 왼쪽 화분
            pygame.Rect(945, 285, 70, 70),    # 오른쪽 화분
            pygame.Rect(420, 185, 50, 28),    # 간판 왼쪽 화분
            pygame.Rect(732, 185, 50, 28),    # 간판 오른쪽 화분
            pygame.Rect(0, 437, 445, 363),    # 왼쪽 아래 바깥
            pygame.Rect(734, 437, 466, 363),  # 오른쪽 아래 바깥
            pygame.Rect(0, 562, 516, 238),    # 왼쪽 좁은 복도 벽
            pygame.Rect(688, 562, 512, 238),  # 오른쪽 좁은 복도 벽
            pygame.Rect(516, 609, 25, 86),    # 복도 왼쪽 화분
            pygame.Rect(663, 609, 25, 86),    # 복도 오른쪽 화분
            pygame.Rect(0, 781, 1200, 19),    # 복도 끝
        ],
        "doors": [
            (pygame.Rect(541, 760, 122, 21), "safety", (572, 40)),  # 아래 복도 끝
            (pygame.Rect(0, 335, 30, 102), "safety4", (990, 134)),  # 왼쪽 복도 끝
            (pygame.Rect(1170, 335, 30, 102), "safety5", (40, 109)),  # 오른쪽 복도 끝
        ],
    },
    "safety": {
        # 원본 1536x1024 이미지를 1200x800으로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Safety Team-1.png"), (1200, 800)),
        "size": (1200, 800),
        "walls": [
            pygame.Rect(0, 0, 515, 185),      # 왼쪽 위 소파 줄과 위 복도 왼쪽 벽
            pygame.Rect(0, 0, 315, 225),      # 왼쪽 위 화분 기둥
            pygame.Rect(0, 0, 290, 272),      # 왼쪽 위 계단 벽
            pygame.Rect(0, 0, 180, 335),      # 왼쪽 문 있는 벽
            pygame.Rect(0, 450, 180, 350),    # 왼쪽 아래 소파 줄
            pygame.Rect(0, 520, 290, 280),    # 왼쪽 아래 계단 벽
            pygame.Rect(0, 560, 315, 240),    # 왼쪽 아래 화분 기둥
            pygame.Rect(0, 605, 480, 195),    # 왼쪽 아래 소파 줄
            pygame.Rect(0, 640, 515, 160),    # 아래 복도 왼쪽 벽
            pygame.Rect(685, 0, 515, 185),    # 오른쪽 위 소파 줄과 위 복도 오른쪽 벽
            pygame.Rect(885, 0, 315, 225),    # 오른쪽 위 화분 기둥
            pygame.Rect(910, 0, 290, 272),    # 오른쪽 위 계단 벽
            pygame.Rect(1020, 0, 180, 335),   # 오른쪽 문 있는 벽
            pygame.Rect(1020, 450, 180, 350), # 오른쪽 아래 소파 줄
            pygame.Rect(910, 520, 290, 280),  # 오른쪽 아래 계단 벽
            pygame.Rect(885, 560, 315, 240),  # 오른쪽 아래 화분 기둥
            pygame.Rect(720, 605, 480, 195),  # 오른쪽 아래 소파 줄
            pygame.Rect(685, 640, 515, 160),  # 아래 복도 오른쪽 벽
            # 화단은 계단 모양이라 사각형 2개씩으로 채움
            pygame.Rect(435, 210, 85, 75),    # 왼쪽 위 화단
            pygame.Rect(395, 250, 75, 85),
            pygame.Rect(680, 210, 85, 75),    # 오른쪽 위 화단
            pygame.Rect(730, 250, 75, 85),
            pygame.Rect(395, 455, 70, 60),    # 왼쪽 아래 화단
            pygame.Rect(440, 495, 80, 75),
            pygame.Rect(735, 455, 70, 60),    # 오른쪽 아래 화단
            pygame.Rect(680, 495, 80, 75),
            pygame.Rect(480, 375, 240, 40),   # 가운데 분수 (마름모를 사각형 3개로 채움)
            pygame.Rect(520, 335, 160, 120),
            pygame.Rect(560, 295, 80, 200),
        ],
        "doors": [
            # 발 판정이 캐릭터 아래쪽에만 있어서 문 영역을 넉넉히 잡아야 닿음
            (pygame.Rect(515, 0, 170, 80), "lobby2", (572, 657)),  # 위 복도 끝 (돌아가기)
            (pygame.Rect(0, 335, 30, 115), "safety2", (1300, 287)),  # 왼쪽 복도 끝
            (pygame.Rect(1170, 335, 30, 115), "safety3", (50, 276)),  # 오른쪽 복도 끝
            (pygame.Rect(515, 770, 170, 30), "safety11", (581, 40)),  # 아래 복도 끝
        ],
    },
    "safety2": {
        # 원본 1702x887 이미지를 1440x750으로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Safety Team-2.png"), (1440, 750)),
        "size": (1440, 750),
        "walls": [
            pygame.Rect(0, 0, 660, 300),      # 왼쪽 위 (복도 위쪽 화분 줄까지)
            pygame.Rect(785, 0, 655, 300),    # 오른쪽 위
            pygame.Rect(0, 425, 660, 325),    # 왼쪽 아래 (복도 아래쪽 화분 줄부터)
            pygame.Rect(785, 425, 655, 325),  # 오른쪽 아래
        ],
        "doors": [
            (pygame.Rect(1380, 300, 60, 125), "safety", (50, 317)),  # 오른쪽 복도 끝 (돌아가기)
            (pygame.Rect(0, 300, 30, 125), "safety12", (969, 296)),  # 왼쪽 복도 끝
            (pygame.Rect(660, 0, 125, 80), "safety4", (156, 600)),  # 위 복도 끝
            (pygame.Rect(660, 720, 125, 30), "safety7", (238, 40)),  # 아래 복도 끝
            (pygame.Rect(289, 290, 51, 20), "isolation-1", isolation_entry),  # 왼쪽 격리실 문
            (pygame.Rect(1100, 290, 51, 20), "isolation-2", isolation_entry),  # 오른쪽 격리실 문
        ],
    },
    "restroom1": {
        # 원본 1254x1254 이미지에서 검은 여백을 잘라낸 895x605 부분을 1110x750으로 키워서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy restroom-1.png").subsurface((180, 355, 895, 605)),
            (1110, 750)),
        "size": (1110, 750),
        # 캐릭터 몸 전체가 바닥 밖으로 나가지 않게 벽을 잡음
        # (발 판정 기준이라 위쪽 벽은 머리 높이만큼, 양옆 벽은 몸 폭만큼 더 안쪽으로)
        "walls": [
            pygame.Rect(0, 0, 1110, 134),     # 위쪽 벽 (세로 복도 위 끝)
            pygame.Rect(0, 0, 473, 565),      # 세로 복도 왼쪽
            pygame.Rect(633, 0, 477, 565),    # 세로 복도 오른쪽
            pygame.Rect(0, 0, 163, 750),      # 왼쪽 벽 (왼쪽 문 앞까지)
            pygame.Rect(947, 0, 163, 750),    # 오른쪽 벽 (오른쪽 문 앞까지)
            pygame.Rect(0, 686, 1110, 64),    # 아래쪽 벽
        ],
        "doors": [
            (pygame.Rect(927, 565, 20, 121), "safety12", (110, 296)),  # 오른쪽 문 (Team-12로 돌아가기)
            (pygame.Rect(473, 114, 160, 30), "restroom2", (560, 382)),  # 위쪽 문 (휴게실 아래 문으로)
        ],
    },
    "restroom2": {
        # 원본 1536x1024 이미지에서 검은 여백을 잘라낸 1320x870 부분을 플레이어 크기에 맞게 792x522로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy restroom-2.png").subsurface((110, 60, 1320, 870)),
            (792, 522)),
        "size": (792, 522),
        "walls": [
            pygame.Rect(0, 0, 792, 144),      # 위쪽 벽 (자판기와 주방 조리대까지)
            pygame.Rect(0, 0, 57, 522),       # 왼쪽 벽
            pygame.Rect(738, 0, 54, 522),     # 오른쪽 벽
            pygame.Rect(0, 438, 552, 84),     # 아래쪽 벽 (문 왼쪽)
            pygame.Rect(624, 438, 168, 84),   # 아래쪽 벽 (문 오른쪽)
            pygame.Rect(0, 519, 792, 3),      # 문 복도 끝
            pygame.Rect(51, 162, 144, 66),    # 소파 (ㄱ자라 사각형 2개)
            pygame.Rect(51, 162, 66, 174),
            pygame.Rect(138, 255, 64, 75),    # 소파 앞 탁자
            pygame.Rect(201, 303, 75, 87),    # 1인용 소파
            pygame.Rect(363, 171, 153, 108),  # 위쪽 식탁과 의자
            pygame.Rect(363, 300, 153, 111),  # 아래쪽 식탁과 의자
            pygame.Rect(693, 138, 48, 48),    # 쓰레기통
            pygame.Rect(678, 189, 63, 141),   # TV 받침대
            pygame.Rect(687, 336, 54, 60),    # 책장
            pygame.Rect(42, 378, 51, 60),     # 왼쪽 아래 화분
            pygame.Rect(693, 384, 48, 54),    # 오른쪽 아래 화분
        ],
        "doors": [
            (pygame.Rect(552, 492, 72, 27), "restroom1", (525, 90)),  # 아래 문 (화장실 위쪽 문으로)
        ],
    },
    "safety12": {
        # 원본 1775x724 이미지의 왼쪽은 검은 빈 공간이라 복도 부분(x 700부터)만 잘라서 사용
        "background": pygame.image.load(
            "D:/hjh/VScode/Movement test/Lobotomy Safety Team-12.png").subsurface((700, 0, 1075, 724)),
        "size": (1075, 724),
        "walls": [
            pygame.Rect(0, 0, 1075, 330),     # 위쪽 벽 (가로 복도 위쪽 화분 줄까지)
            pygame.Rect(0, 428, 1075, 296),   # 아래쪽 벽 (가로 복도 아래쪽 화분 줄부터)
            pygame.Rect(0, 0, 60, 724),       # 왼쪽 벽 (문 앞까지)
        ],
        "doors": [
            (pygame.Rect(60, 330, 30, 98), "restroom1", (870, 537)),  # 왼쪽 문 (화장실 오른쪽 문으로)
            (pygame.Rect(1045, 330, 30, 98), "safety2", (50, 287)),  # 오른쪽 복도 끝
        ],
    },
    "safety3": {
        # 원본 1489x1024 이미지를 1091x750으로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy safety Team-3.png"), (1091, 750)),
        "size": (1091, 750),
        "walls": [
            pygame.Rect(0, 0, 571, 315),      # 왼쪽 위 (복도 위쪽 화분 줄까지)
            pygame.Rect(0, 403, 571, 347),    # 왼쪽 아래 (복도 아래쪽 화분 줄부터)
            pygame.Rect(680, 0, 411, 750),    # 세로 복도 오른쪽 (전부 막힘)
        ],
        "doors": [
            (pygame.Rect(0, 315, 30, 88), "safety", (1094, 317)),  # 왼쪽 복도 끝 (돌아가기)
            (pygame.Rect(571, 0, 109, 80), "safety5", (904, 660)),  # 위 복도 끝 (발 판정이 아래쪽이라 넉넉히)
            (pygame.Rect(571, 720, 109, 30), "safety6", (580, 40)),  # 아래 복도 끝
            (pygame.Rect(232, 305, 44, 20), "isolation-3", isolation_entry),  # 격리실 문
        ],
    },
    "safety6": {
        # 원본 1103x869 이미지를 952x750으로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Safety Team-6.png"), (952, 750)),
        "size": (952, 750),
        "walls": [
            pygame.Rect(0, 0, 561, 341),      # 왼쪽 위 (복도 위쪽 화분 줄까지)
            pygame.Rect(0, 401, 561, 349),    # 왼쪽 아래 (복도 아래쪽 화분 줄부터)
            pygame.Rect(656, 0, 296, 750),    # 세로 복도 오른쪽 (전부 막힘)
        ],
        "doors": [
            (pygame.Rect(561, 0, 95, 80), "safety3", (597, 610)),  # 위 복도 끝 (발 판정이 아래쪽이라 넉넉히)
            (pygame.Rect(0, 341, 30, 60), "safety11", (1094, 413)),  # 왼쪽 복도 끝
            (pygame.Rect(561, 720, 95, 30), "safety9", (834, 40)),  # 아래 복도 끝
            (pygame.Rect(200, 331, 47, 20), "isolation-6", isolation_entry),  # 격리실 문
        ],
    },
    "safety9": {
        # 원본 1323x885 이미지를 1121x750으로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Safety Team-9.png"), (1121, 750)),
        "size": (1121, 750),
        "walls": [
            pygame.Rect(0, 0, 818, 603),      # 왼쪽 위 빈 공간 (ㄴ자 복도 안쪽)
            pygame.Rect(907, 0, 214, 750),    # 오른쪽 벽 (세로 복도 오른쪽 화분 줄부터)
            pygame.Rect(0, 665, 1121, 85),    # 아래쪽 벽 (가로 복도 아래쪽 화분 줄부터)
        ],
        "doors": [
            (pygame.Rect(818, 0, 89, 80), "safety6", (580, 610)),  # 위 복도 끝 (발 판정이 아래쪽이라 넉넉히)
            (pygame.Rect(0, 603, 30, 62), "safety10", (1334, 190)),  # 왼쪽 복도 끝
            (pygame.Rect(226, 593, 51, 20), "isolation-9", isolation_entry),  # 격리실 문
        ],
    },
    "safety4": {
        # 원본 1175x820 이미지를 1075x750으로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Safety Team-4.png"), (1075, 750)),
        "size": (1075, 750),
        "walls": [
            pygame.Rect(0, 0, 1075, 172),     # 위쪽 벽 (문과 화분 줄까지)
            pygame.Rect(0, 0, 128, 750),      # 왼쪽 벽 (세로 복도 왼쪽 화분 줄까지)
            pygame.Rect(240, 262, 835, 488),  # 가운데 빈 공간 (ㄱ자 복도 안쪽)
        ],
        "doors": [
            (pygame.Rect(128, 720, 112, 30), "safety2", (694, 30)),  # 아래 복도 끝
            (pygame.Rect(1045, 172, 30, 90), "lobby2", (50, 303)),   # 오른쪽 복도 끝
            (pygame.Rect(471, 162, 65, 20), "isolation-4", isolation_entry),  # 격리실 문
        ],
    },
    "safety5": {
        # 원본 1210x794 이미지를 그대로 사용
        "background": pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Safety Team-5.png"),
        "size": (1210, 794),
        "walls": [
            pygame.Rect(0, 0, 1210, 145),     # 위쪽 벽 (문과 화분 줄까지)
            pygame.Rect(0, 240, 875, 554),    # 가운데 빈 공간 (세로 복도 왼쪽 화분 줄까지)
            pygame.Rect(990, 0, 220, 794),    # 오른쪽 벽 (세로 복도 오른쪽 화분 줄부터)
        ],
        "doors": [
            (pygame.Rect(0, 145, 30, 95), "lobby2", (1094, 303)),  # 왼쪽 복도 끝
            (pygame.Rect(875, 764, 115, 30), "safety3", (597, 40)),  # 아래 복도 끝
            (pygame.Rect(580, 135, 68, 20), "isolation-5", isolation_entry),  # 격리실 문
        ],
    },
    "safety7": {
        # 원본 1105x853 이미지를 972x750으로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Safety Team-7.png"), (972, 750)),
        "size": (972, 750),
        "walls": [
            pygame.Rect(0, 0, 224, 750),      # 왼쪽 벽 (세로 복도 왼쪽 화분 줄까지)
            pygame.Rect(308, 0, 664, 332),    # 오른쪽 위 (가로 복도 위쪽 화분 줄까지)
            pygame.Rect(308, 400, 664, 350),  # 오른쪽 아래 (가로 복도 아래쪽 화분 줄부터)
        ],
        "doors": [
            (pygame.Rect(224, 0, 84, 80), "safety2", (694, 600)),  # 위 복도 끝 (발 판정이 아래쪽이라 넉넉히)
            (pygame.Rect(942, 332, 30, 68), "safety11", (50, 413)),  # 오른쪽 복도 끝
            (pygame.Rect(224, 720, 84, 30), "safety8", (266, 40)),  # 아래 복도 끝
            (pygame.Rect(640, 322, 55, 20), "isolation-7", isolation_entry),  # 격리실 문
        ],
    },
    "safety8": {
        # 원본 1216x884 이미지를 1032x750으로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Safety Team-8.png"), (1032, 750)),
        "size": (1032, 750),
        "walls": [
            pygame.Rect(0, 0, 251, 750),      # 왼쪽 벽 (세로 복도 왼쪽 화분 줄까지)
            pygame.Rect(338, 0, 694, 611),    # 오른쪽 위 빈 공간 (ㄴ자 복도 안쪽)
            pygame.Rect(0, 672, 1032, 78),    # 아래쪽 벽 (가로 복도 아래쪽 화분 줄부터)
        ],
        "doors": [
            (pygame.Rect(251, 0, 87, 80), "safety7", (238, 600)),  # 위 복도 끝 (발 판정이 아래쪽이라 넉넉히)
            (pygame.Rect(1002, 611, 30, 61), "safety10", (50, 190)),  # 오른쪽 복도 끝
            (pygame.Rect(743, 601, 60, 20), "isolation-8", isolation_entry),  # 격리실 문
        ],
    },
    "safety10": {
        # 원본 1880x724 이미지를 1440x555로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Safety Team-10.png"), (1440, 555)),
        "size": (1440, 555),
        "walls": [
            pygame.Rect(0, 0, 1440, 241),     # 위쪽 벽 (가로 복도 위쪽 화분 줄까지)
            pygame.Rect(0, 305, 1440, 250),   # 아래쪽 벽 (가로 복도 아래쪽 화분 줄부터)
        ],
        "doors": [
            (pygame.Rect(0, 241, 30, 64), "safety8", (926, 558)),  # 왼쪽 복도 끝
            (pygame.Rect(1410, 241, 30, 64), "safety9", (50, 551)),  # 오른쪽 복도 끝
        ],
    },
    "safety11": {
        # 원본 1536x1024 이미지를 1200x800으로 줄여서 사용
        "background": pygame.transform.smoothscale(
            pygame.image.load("D:/hjh/VScode/Movement test/Lobotomy Safety Team-11.png"), (1200, 800)),
        "size": (1200, 800),
        "walls": [
            pygame.Rect(0, 0, 531, 418),      # 왼쪽 위 벽 (가로 복도 위쪽 벽까지)
            pygame.Rect(688, 0, 512, 418),    # 오른쪽 위 벽
            pygame.Rect(0, 406, 51, 35),      # 위쪽 화분들
            pygame.Rect(414, 406, 51, 35),
            pygame.Rect(734, 406, 51, 35),
            pygame.Rect(1148, 406, 52, 35),
            pygame.Rect(0, 574, 422, 226),    # 왼쪽 아래 바깥
            pygame.Rect(422, 617, 359, 183),  # 가운데 아래 바깥 (복도가 조금 더 내려옴)
            pygame.Rect(781, 574, 419, 226),  # 오른쪽 아래 바깥
            pygame.Rect(422, 578, 51, 35),    # 아래쪽 화분들
            pygame.Rect(727, 578, 51, 35),
        ],
        "doors": [
            (pygame.Rect(0, 441, 30, 133), "safety7", (866, 283)),  # 왼쪽 복도 끝
            (pygame.Rect(531, 0, 157, 80), "safety", (572, 657)),  # 위 복도 끝 (발 판정이 아래쪽이라 넉넉히)
            (pygame.Rect(1170, 441, 30, 133), "safety6", (50, 288)),  # 오른쪽 복도 끝
            (pygame.Rect(159, 408, 62, 20), "isolation-10", isolation_entry),  # 왼쪽 격리실 문
            (pygame.Rect(980, 408, 62, 20), "isolation-11", isolation_entry),  # 오른쪽 격리실 문
        ],
    },
}
# 격리실: (이름, 돌아갈 맵, 돌아갔을 때 캐릭터 위치 = 그 맵의 격리실 문 바로 아래)
isolations = [
    ("isolation-1", "safety2", (286, 247)),
    ("isolation-2", "safety2", (1097, 247)),
    ("isolation-3", "safety3", (226, 262)),
    ("isolation-4", "safety4", (475, 119)),
    ("isolation-5", "safety5", (586, 92)),
    ("isolation-6", "safety6", (195, 288)),
    ("isolation-7", "safety7", (639, 279)),
    ("isolation-8", "safety8", (745, 558)),
    ("isolation-9", "safety9", (223, 550)),
    ("isolation-10", "safety11", (162, 365)),
    ("isolation-11", "safety11", (983, 365)),
]
for name, back_map, back_position in isolations:
    maps[name] = make_isolation(back_map, back_position)
current_map = "lobby"
walls = maps[current_map]["walls"]
background = maps[current_map]["background"]
show_walls = False  # F1 키로 벽 표시 켜기/끄기

# 엘리베이터: 문에 닿으면 이 그림을 잠시 보여준 뒤 다음 맵으로 이동
elevator_image = pygame.image.load("D:/hjh/VScode/Movement test/elevator.png")
elevator_wait = 3000  # 엘리베이터에서 기다리는 시간 (밀리초)
elevator_timer = 0    # 남은 대기 시간 (0이면 엘리베이터 안이 아님)
elevator_target = None  # 엘리베이터가 도착할 (맵 이름, 캐릭터 위치)
elevator_feet_pos = (400, 480)  # 엘리베이터 그림에서 캐릭터 발끝이 놓일 위치 (바닥 가운데)
elevator_exit_direction = "down"  # 엘리베이터에서 나온 뒤 바라볼 방향 (문 반대쪽)

def change_map(name, position):
    global current_map, walls, background, screen, screen_width, screen_height
    global character_x_pos, character_y_pos
    current_map = name
    walls = maps[name]["walls"]
    background = maps[name]["background"]
    screen_width, screen_height = maps[name]["size"]
    # 창 크기가 바뀌어도 SDL_VIDEO_CENTERED 덕분에 창이 화면 가운데로 다시 옮겨짐
    screen = pygame.display.set_mode((screen_width, screen_height))
    character_x_pos, character_y_pos = position

character_x_pos = (screen_width / 2) - (character_width / 2)
character_y_pos = 760 - character_height

# 충돌 판정은 캐릭터 발 부분만 사용 (탑다운 시점)
# 발 폭을 캐릭터 폭보다 좁게 잡아서 좁은 길에서도 걸리지 않게 함
feet_width = 28
feet_height = 20

def feet_rect(x, y):
    return pygame.Rect(int(x) + (character_width - feet_width) // 2,
                       int(y) + character_height - feet_height, feet_width, feet_height)

def hits_wall(x, y):
    rect = feet_rect(x, y)
    return any(rect.colliderect(wall) for wall in walls)

# NPC: Lobotomy Corporation-1(lobby2)과 Safety Team-1 ~ 11 맵을 돌아다니고, 문을 지나 서로 오감
# (엘리베이터가 있는 lobby에는 가지 않음)
# 지금 보고 있지 않은 맵의 NPC도 계속 움직이고, 화면에는 현재 맵에 있는 NPC만 그림
npc_maps = ["lobby2", "safety"] + ["safety%d" % number for number in range(2, 12)]
grid = 10       # NPC 길찾기 칸 크기 (픽셀)
npc_door_chance = 0.3  # 한 곳에 도착한 뒤 다른 맵으로 떠날 확률
npc_wall_cost = 4      # 벽 가까운 칸을 지날 때 드는 추가 비용 (클수록 복도 가운데로 걸음)
npc_target_clearance = 3  # 목적지는 벽에서 이만큼(칸) 이상 떨어진 곳만 고름
npc_neighbors = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]

def make_walkable(name):
    # 캐릭터가 설 수 있는 칸 (발이 벽에 안 닿고 화면 밖으로 안 나가는 칸)
    width, height = maps[name]["size"]
    cells = set()
    for gx in range((width - character_width) // grid + 1):
        for gy in range((height - character_height) // grid + 1):
            if feet_rect(gx * grid, gy * grid).collidelist(maps[name]["walls"]) == -1:
                cells.add((gx, gy))
    return cells

def make_clearance(name):
    # 칸마다 벽(또는 화면 끝)에서 몇 칸 떨어져 있는지 (벽 바로 옆이 1)
    cells = walkable[name]
    clearance = {}
    queue = deque()
    for x, y in cells:
        if any((x + dx, y + dy) not in cells for dx, dy in npc_neighbors):
            clearance[(x, y)] = 1
            queue.append((x, y))
    while queue:
        x, y = queue.popleft()
        for dx, dy in npc_neighbors:
            cell = (x + dx, y + dy)
            if cell in cells and cell not in clearance:
                clearance[cell] = clearance[(x, y)] + 1
                queue.append(cell)
    return clearance

walkable = {name: make_walkable(name) for name in npc_maps}
walkable_list = {name: list(cells) for name, cells in walkable.items()}
clearance = {name: make_clearance(name) for name in npc_maps}

def make_spots(name):
    # NPC가 걸어갈 목적지들: 벽에서 떨어진 칸 중에서 맵 곳곳에 고르게 퍼지도록 골라 둠
    least = min(npc_target_clearance, max(clearance[name].values()))
    cells = [cell for cell, space in clearance[name].items() if space >= least]
    count = max(8, len(cells) // 60)  # 넓은 맵일수록 목적지가 많음
    spots = [max(cells, key=lambda cell: clearance[name][cell])]  # 가장 넓은 곳에서 시작
    while len(spots) < count:
        # 이미 고른 목적지들에서 가장 멀리 떨어진 칸을 다음 목적지로
        spots.append(max(cells, key=lambda cell: min((cell[0] - x) ** 2 + (cell[1] - y) ** 2 for x, y in spots)))
    return spots

npc_spots = {name: make_spots(name) for name in npc_maps}

def make_npc_doors(name):
    # NPC가 쓸 수 있는 문 (npc_maps에 있는 맵으로 가는 문만): (도착할 맵, 도착 위치, 문 가운데 칸)
    doors = []
    for door, next_map, position in maps[name]["doors"]:
        if next_map not in npc_maps:
            continue
        cells = [cell for cell in walkable[name] if feet_rect(cell[0] * grid, cell[1] * grid).colliderect(door)]
        if cells:
            # 문 모서리가 아니라 문 한가운데로 걸어 들어가게 함
            def gap(cell):
                feet = feet_rect(cell[0] * grid, cell[1] * grid)
                return (feet.centerx - door.centerx) ** 2 + (feet.centery - door.centery) ** 2
            doors.append((next_map, position, min(cells, key=gap)))
    return doors

npc_doors = {name: make_npc_doors(name) for name in npc_maps}

routes = {}  # 목적지까지 가는 길 지도는 처음 쓸 때 한 번 만들고 계속 다시 씀

def route_map(name, target):
    # 목표 칸에서 거꾸로 퍼져 나가며, 각 칸에서 목표 쪽으로 가려면 다음에 어느 칸으로 가야 하는지 기록
    # 벽 가까운 칸일수록 비용이 커서 길이 복도 가운데로 나게 됨 (다익스트라)
    key = (name, target)
    if key in routes:
        return routes[key]
    cells, space = walkable[name], clearance[name]
    cost = {target: 0}
    next_cell = {target: None}
    queue = [(0, target)]
    while queue:
        here_cost, (x, y) = heapq.heappop(queue)
        if here_cost > cost[(x, y)]:
            continue
        for dx, dy in npc_neighbors:
            cell = (x + dx, y + dy)
            if cell not in cells:
                continue
            # 대각선은 양옆 칸이 다 비어 있을 때만 (벽 모서리를 깎고 지나가지 않게)
            if dx and dy and ((x + dx, y) not in cells or (x, y + dy) not in cells):
                continue
            step = (1.4 if dx and dy else 1) * (1 + npc_wall_cost / space[cell])
            if here_cost + step < cost.get(cell, float("inf")):
                cost[cell] = here_cost + step
                next_cell[cell] = (x, y)
                heapq.heappush(queue, (cost[cell], cell))
    routes[key] = next_cell
    return next_cell

# 아직 안 만든 길 지도들: NPC가 길을 찾지 않는 프레임마다 하나씩 미리 만들어 둠 (한 번에 다 만들면 게임 시작이 느려짐)
route_queue = [(name, spot) for name in npc_maps for spot in npc_spots[name]]
route_queue += [(name, door[2]) for name in npc_maps for door in npc_doors[name]]

def prepare_route():
    while route_queue:
        name, target = route_queue.pop()
        if (name, target) not in routes:
            route_map(name, target)
            return

def clear_line(name, start, end, least):
    # 두 칸 사이를 곧장 걸어가도 벽에 너무 붙지 않고, 벽 모서리에 발이 걸리지 않는지 확인 (2픽셀마다 검사)
    steps = max(abs(end[0] - start[0]), abs(end[1] - start[1])) * grid // 2
    for index in range(1, steps):
        x = (start[0] + (end[0] - start[0]) * index / steps) * grid
        y = (start[1] + (end[1] - start[1]) * index / steps) * grid
        if clearance[name].get((round(x / grid), round(y / grid)), 0) < least:
            return False
        # 발 판정을 조금 넓혀서 검사한 점 사이를 지날 때도 벽에 닿지 않게 함
        if feet_rect(x, y).inflate(4, 4).collidelist(maps[name]["walls"]) != -1:
            return False
    return True

def smooth_path(name, path):
    # 칸 단위로 지그재그인 길을, 곧게 걸어갈 수 있는 구간끼리 이어서 꺾이는 점 몇 개만 남김
    points = []
    start = 0
    while start < len(path) - 1:
        end = min(len(path) - 1, start + 30)
        while end > start + 1:
            least = min(clearance[name][cell] for cell in path[start:end + 1])
            if clear_line(name, path[start], path[end], least):
                break
            end -= 1
        points.append((path[end][0] * grid, path[end][1] * grid))
        start = end
    return points

def find_path(name, start, target):
    route = route_map(name, target)
    if start not in route or start == target:
        return None
    path = [start]
    while route[path[-1]] is not None:
        path.append(route[path[-1]])
    return smooth_path(name, path)

def nearest_cell(name, x, y):
    return min(walkable_list[name], key=lambda cell: (cell[0] * grid - x) ** 2 + (cell[1] * grid - y) ** 2)

def make_npc(index, name, taken):
    # 같은 맵에서 시작하는 NPC끼리 겹쳐 서 있지 않게 아직 아무도 없는 목적지에서 시작함
    cell = random.choice([spot for spot in npc_spots[name] if (name, spot) not in taken] or npc_spots[name])
    taken.append((name, cell))
    return {"sprites": npc_sprites[index % len(npc_sprites)], "map": name, "came_from": None,
            "x": float(cell[0] * grid), "y": float(cell[1] * grid),
            "speed": random.uniform(2.4, 3.2),  # NPC마다 걷는 속도가 조금씩 다름 (플레이어는 5)
            "pace": 0.0,  # 지금 속도 비율 (출발할 때 천천히 빨라지고 멈출 때 천천히 느려짐)
            "direction": random.choice(directions), "walk_timer": 0.0, "walking": False,
            "wait": random.randint(0, 60), "path": None, "door": None, "goal": cell}

def choose_npc_goal(npc):
    name = npc["map"]
    start = nearest_cell(name, npc["x"], npc["y"])
    # 들어온 문으로 바로 돌아가지 않게 함 (다른 문이 없으면 어쩔 수 없이 돌아감)
    doors = [door for door in npc_doors[name] if door[0] != npc["came_from"]] or npc_doors[name]
    if doors and random.random() < npc_door_chance:
        door = random.choice(doors)
        path = find_path(name, start, door[2])
        if path:
            npc["path"], npc["door"], npc["goal"] = path, door, None
            return
    # 아니면 같은 맵의 다른 목적지로 걸어감 (너무 가깝거나 다른 NPC가 가는 곳은 빼고)
    taken = [other["goal"] for other in npcs if other is not npc and other["map"] == name]
    spots = [spot for spot in npc_spots[name] if abs(spot[0] - start[0]) + abs(spot[1] - start[1]) >= 8]
    # 좁은 맵에 NPC가 몰려서 빈 목적지가 없으면 다른 NPC와 같은 곳이라도 감
    spots = [spot for spot in spots if spot not in taken] or spots
    random.shuffle(spots)
    for target in spots[:3]:
        path = find_path(name, start, target)
        if path:
            npc["path"], npc["door"], npc["goal"] = path, None, target
            return
    npc["wait"] = 30  # 갈 곳을 못 찾으면 잠깐 쉬었다가 다시 고름

def face_toward(npc, move_x, move_y):
    # 대각선으로 걸을 때 방향이 계속 바뀌어 깜빡이지 않게, 확실히 한쪽으로 기울었을 때만 돌아봄
    horizontal = "left" if move_x < 0 else "right"
    vertical = "up" if move_y < 0 else "down"
    if abs(move_x) > abs(move_y) * 1.3:
        npc["direction"] = horizontal
    elif abs(move_y) > abs(move_x) * 1.3:
        npc["direction"] = vertical
    elif npc["direction"] not in (horizontal, vertical):
        npc["direction"] = horizontal if abs(move_x) >= abs(move_y) else vertical

def update_npc(npc, can_plan):
    # 길 찾기는 시간이 걸려서 한 프레임에 NPC 한 명만 하게 함 (길을 찾았으면 True를 돌려줌)
    npc["walking"] = False
    if npc["wait"] > 0:
        npc["wait"] -= 1
        # 서 있는 동안 가끔 두리번거림
        if random.random() < 0.01:
            npc["direction"] = random.choice(directions)
        return False
    if npc["path"] is None:
        if not can_plan:
            return False
        choose_npc_goal(npc)
        return True
    path = npc["path"]
    # 출발할 때는 천천히 빨라지고, 멈출 곳에 가까워지면 천천히 느려짐
    npc["pace"] = min(1.0, npc["pace"] + 0.08)
    pace = npc["pace"]
    if len(path) == 1 and npc["door"] is None:
        left = ((path[0][0] - npc["x"]) ** 2 + (path[0][1] - npc["y"]) ** 2) ** 0.5
        pace = min(pace, max(0.35, left / 40))
    move = npc["speed"] * pace
    # 이번 프레임에 걸을 거리만큼 꺾이는 점들을 따라감
    moved_x = moved_y = 0.0
    while move > 0 and path:
        gap_x, gap_y = path[0][0] - npc["x"], path[0][1] - npc["y"]
        gap = (gap_x ** 2 + gap_y ** 2) ** 0.5
        if gap <= move:
            step_x, step_y = gap_x, gap_y
            path.pop(0)
        else:
            step_x, step_y = gap_x / gap * move, gap_y / gap * move
        npc["x"] += step_x
        npc["y"] += step_y
        moved_x += step_x
        moved_y += step_y
        move -= min(gap, move)
    if moved_x or moved_y:
        face_toward(npc, moved_x, moved_y)
        npc["walking"] = True
        # 걷는 속도에 맞춰 다리 움직임도 빨라지거나 느려짐
        npc["walk_timer"] += npc["speed"] * pace / 3
    if path:
        return False
    # 목표에 도착: 문이면 다음 맵으로, 아니면 잠깐 서 있기
    npc["path"] = None
    npc["pace"] = 0.0
    if npc["door"] is not None:
        next_map, position, _ = npc["door"]
        npc["came_from"] = npc["map"]
        npc["map"] = next_map
        npc["x"], npc["y"] = float(position[0]), float(position[1])
        npc["goal"] = None
        npc["pace"] = 1.0  # 문을 지나온 것이니 멈추지 않고 이어서 걸음
    else:
        npc["wait"] = random.randint(45, 150)
        npc["walk_timer"] = 0.0
    return False

# NPC 28명: 그림 7개를 4번씩 돌려 쓰고, Safety Team 맵마다 고르게 나눠서 시작시킴
npc_count = 28
start_maps = []
while len(start_maps) < npc_count:
    start_maps += random.sample(npc_maps, len(npc_maps))
start_taken = []
npcs = [make_npc(index, name, start_taken) for index, name in enumerate(start_maps[:npc_count])]

to_x = 0
to_y = 0

running = True
while running:
    dt = clock.tick(30)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                to_x -= 5
                direction = "left"
            if event.key == pygame.K_RIGHT:
                to_x += 5
                direction = "right"
            if event.key == pygame.K_UP:
                to_y -= 5
                direction = "up"
            if event.key == pygame.K_DOWN:
                to_y += 5
                direction = "down"
            if event.key == pygame.K_F1:
                show_walls = not show_walls
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                to_x =0
            elif event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                to_y = 0
            # 대각선 이동 중 키 하나를 떼면 남은 방향을 보게 함
            direction = direction_from_speed()
    # NPC는 플레이어가 어디 있든 계속 움직임
    planned = False
    for npc in npcs:
        planned = update_npc(npc, not planned) or planned
    if not planned:
        prepare_route()
    # 엘리베이터 안에서는 움직이지 않고 기다리기만 함
    if elevator_timer > 0:
        elevator_timer -= dt
        if elevator_timer > 0:
            # 엘리베이터 그림 위에 캐릭터를 문(위쪽)을 보고 서 있게 그린 뒤 화면 크기에 맞춤
            elevator_frame = elevator_image.copy()
            character = sprites["up"]["idle"]
            elevator_frame.blit(character, (elevator_feet_pos[0] - character.get_width() / 2,
                                            elevator_feet_pos[1] - character.get_height()))
            screen.blit(pygame.transform.smoothscale(elevator_frame, (screen_width, screen_height)), (0, 0))
            pygame.display.update()
            continue
        change_map(*elevator_target)
        direction = elevator_exit_direction
    screen.blit(background, (0, 0))
    # x, y를 따로 움직여서 벽에 닿으면 그 방향만 막기 (벽을 따라 미끄러짐)
    if not hits_wall(character_x_pos + to_x, character_y_pos):
        character_x_pos += to_x
    if not hits_wall(character_x_pos, character_y_pos + to_y):
        character_y_pos += to_y
    if character_x_pos < 0 :
        character_x_pos = 0
    elif character_x_pos > screen_width - character_width:
        character_x_pos = screen_width - character_width
    if character_y_pos < 0:
        character_y_pos = 0
    elif character_y_pos > screen_height - character_height:
        character_y_pos = screen_height - character_height
    # 문에 닿으면 다른 맵으로 이동 (엘리베이터 맵이면 먼저 엘리베이터에서 기다림)
    for door, next_map, position in maps[current_map]["doors"]:
        if feet_rect(character_x_pos, character_y_pos).colliderect(door):
            if maps[current_map].get("elevator"):
                elevator_timer = elevator_wait
                elevator_target = (next_map, position)
                to_x = 0
                to_y = 0
            else:
                change_map(next_map, position)
                screen.blit(background, (0, 0))
            break
    if elevator_timer > 0:
        continue
    if show_walls:
        for wall in walls:
            pygame.draw.rect(screen, (255, 0, 0), wall, 2)
        for door, next_map, position in maps[current_map]["doors"]:
            pygame.draw.rect(screen, (0, 0, 255), door, 2)
        pygame.draw.rect(screen, (0, 255, 0), feet_rect(character_x_pos, character_y_pos), 2)
    if to_x != 0 or to_y != 0:
        walk_timer += 1
        frames = sprites[direction]["walk"]
        character = frames[(walk_timer // walk_frame_time) % len(frames)]
    else:
        walk_timer = 0
        character = sprites[direction]["idle"]
    # 같은 맵의 NPC와 플레이어를 발 위치(y)가 위인 것부터 그려서 앞뒤가 맞게 겹치게 함
    drawings = [(character_y_pos, character_x_pos, character)]
    for npc in npcs:
        if npc["map"] != current_map:
            continue
        npc_sprite = npc["sprites"][npc["direction"]]
        if npc["walking"]:
            frames = npc_sprite["walk"]
            image = frames[int(npc["walk_timer"] / walk_frame_time) % len(frames)]
        else:
            image = npc_sprite["idle"]
        drawings.append((npc["y"], npc["x"], image))
    drawings.sort(key=lambda drawing: drawing[0])
    for y, x, image in drawings:
        # 그림마다 폭이 달라서 가로는 가운데, 세로는 발끝에 맞춰 그림
        screen.blit(image, (x + (character_width - image.get_width()) / 2, y))
    pygame.display.update()
pygame.quit()
