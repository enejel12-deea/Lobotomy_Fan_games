import warnings
import pygame

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
    # 캐릭터 주변의 반투명한 빛은 지우고 캐릭터만 남김
    mask = pygame.mask.from_surface(cell, 200)
    clean = mask.to_surface(setsurface=cell, unsetcolor=(0, 0, 0, 0))
    clean = clean.subsurface(clean.get_bounding_rect())
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
            (pygame.Rect(660, 0, 125, 80), "safety4", (156, 600)),  # 위 복도 끝
            (pygame.Rect(660, 720, 125, 30), "safety7", (238, 40)),  # 아래 복도 끝
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
        ],
    },
}
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
    screen = pygame.display.set_mode((screen_width, screen_height))
    center_window()
    character_x_pos, character_y_pos = position

def center_window():
    # 창 크기가 바뀌어도 위치는 그대로라서, 큰 맵에서 창이 모니터 밖으로 나가지 않게 가운데로 옮김
    # pygame-ce와 일반 pygame은 Window 위치가 달라서 둘 다 처리하고, 실패해도 게임은 계속 진행
    try:
        if hasattr(pygame, "Window"):  # pygame-ce
            window_module = pygame
        else:  # 일반 pygame
            import pygame._sdl2.video as window_module
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            window = window_module.Window.from_display_module()
        window.position = window_module.WINDOWPOS_CENTERED
    except Exception:
        pass

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
    # 그림마다 폭이 달라서 가로는 가운데, 세로는 발끝에 맞춰 그림
    draw_x = character_x_pos + (character_width - character.get_width()) / 2
    screen.blit(character, (draw_x, character_y_pos))
    pygame.display.update()
pygame.quit()
