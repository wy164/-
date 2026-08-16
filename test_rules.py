"""规则自测：牌型识别、比较、出牌枚举。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.cards import rank, name, LITTLE_JOKER, BIG_JOKER  # noqa: E402
from game.rules import (  # noqa: E402
    analyze, can_beat, generate_plays, TYPE_NAMES,
    SINGLE, PAIR, TRIPLE, TRIPLE_SINGLE, TRIPLE_PAIR, STRAIGHT,
    STRAIGHT_PAIR, AIRPLANE, AIRPLANE_SINGLE, AIRPLANE_PAIR,
    FOUR_TWO, BOMB, ROCKET,
)

FAIL = []


def C(*spec):
    """按 (点数, 数量) 构造牌，点数 3..17（16=小王 17=大王）。"""
    out = []
    for v, n in spec:
        if v >= 16:
            out += [LITTLE_JOKER, BIG_JOKER][:1] if v == 16 else [BIG_JOKER]
            out += [LITTLE_JOKER] * (n - 1) if v == 16 else [BIG_JOKER] * (n - 1)
            continue
        for i in range(n):
            out.append((v - 3) * 4 + i % 4)
    return out


def check(label, got, want):
    if got != want:
        FAIL.append((label, got, want))
        print(f'✗ {label}: 期望 {want}，实际 {got}')
    else:
        print(f'✓ {label}')


# 单张 / 对子 / 三张 / 炸弹 / 王炸
check('单张', analyze(C((3, 1))), (SINGLE, 3, 1))
check('对子', analyze(C((7, 2))), (PAIR, 7, 2))
check('三张', analyze(C((9, 3))), (TRIPLE, 9, 3))
check('炸弹', analyze(C((5, 4))), (BOMB, 5, 4))
check('王炸', analyze(C((16, 1), (17, 1))), (ROCKET, 17, 2))
check('杂牌', analyze(C((3, 1), (4, 1), (7, 1), (8, 1))), None)

# 三带一 / 三带二
check('三带一', analyze(C((6, 3), (10, 1))), (TRIPLE_SINGLE, 6, 4))
check('三带二', analyze(C((8, 3), (2, 2))), (TRIPLE_PAIR, 8, 5))
check('三带单加单', analyze(C((8, 3), (3, 1), (4, 1))), None)

# 顺子
check('顺子', analyze(C((3, 1), (4, 1), (5, 1), (6, 1), (7, 1))), (STRAIGHT, 7, 5))
check('含2顺子', analyze(C((10, 1), (11, 1), (12, 1), (13, 1), (14, 1), (15, 1))), None)
check('短顺子', analyze(C((3, 1), (4, 1), (5, 1), (6, 1))), None)

# 连对
check('连对', analyze(C((3, 2), (4, 2), (5, 2))), (STRAIGHT_PAIR, 5, 6))
check('连对含2', analyze(C((12, 2), (13, 2), (14, 2), (15, 2))), None)

# 飞机
check('飞机', analyze(C((3, 3), (4, 3), (5, 3), (6, 3))), (AIRPLANE, 6, 12))
check('飞机带单', analyze(C((3, 3), (4, 3), (5, 1), (6, 1))), (AIRPLANE_SINGLE, 4, 8))
check('飞机带对', analyze(C((3, 3), (4, 3), (5, 2), (6, 2))), (AIRPLANE_PAIR, 4, 10))

# 四带二
check('四带二(单)', analyze(C((7, 4), (3, 1), (4, 1))), (FOUR_TWO, 7, 6))
check('四带二(对)', analyze(C((7, 4), (3, 2), (4, 2))), (FOUR_TWO, 7, 8))

# 比较
def A(*spec):
    return analyze(C(*spec))

check('3管不上7', can_beat(A((3, 1)), A((7, 1))), False)
check('8管7', can_beat(A((8, 1)), A((7, 1))), True)
check('王炸最大', can_beat(A((16, 1), (17, 1)), A((15, 4))), True)
check('炸弹压单', can_beat(A((5, 4)), A((14, 1))), True)
check('小炸弹压不了大炸弹', can_beat(A((5, 4)), A((9, 4))), False)
check('顺子不压顺子(不同长)', can_beat(
    A((5, 1), (6, 1), (7, 1), (8, 1), (9, 1)),
    A((4, 1), (5, 1), (6, 1), (7, 1), (8, 1), (9, 1))), False)
check('同长顺子可压', can_beat(
    A((4, 1), (5, 1), (6, 1), (7, 1), (8, 1)),
    A((3, 1), (4, 1), (5, 1), (6, 1), (7, 1))), True)

# 枚举出的每个组合都能被 analyze 正确识别，且与目标一致
import random
random.seed(1)
deck = list(range(54))
random.shuffle(deck)
for hand in (deck[:17], deck[17:34], deck[34:51]):
    for t, k, cards in generate_plays(hand):
        a = analyze(cards)
        if a is None or a[0] != t or a[1] != k:
            FAIL.append(('generate 与 analyze 不一致',
                         (t, k, [name(x) for x in cards]), a))
            print('✗ generate 不一致:', [name(x) for x in cards], '->', a)
            break
print('✓ 枚举结果全部与 analyze 一致')

# 随机模拟若干局，确保流程能跑完不出错
from game.game_logic import Game  # noqa: E402
from game.ai import choose_bid, choose_play  # noqa: E402

# 逆时针出牌顺序：你(0) -> 右家(2) -> 左家(1) -> 你(0)
g0 = Game()
check('逆时针顺序', (g0.next_player(0), g0.next_player(1), g0.next_player(2)),
      (2, 0, 1))

games_done = 0
for seed in range(30):
    random.seed(seed)
    g = Game()
    for _ in range(200):  # 防止死循环
        if g.phase == Game.PHASE_END:
            break
        pid = g.current
        if g.phase == Game.PHASE_BID:
            score = choose_bid(g.hands[pid], g.bid, pid)
            r = g.submit_bid(pid, score)
            if r == 'redeal':
                g = Game()
        else:
            play = choose_play(g.hands[pid], g.last_play, g.last_play_player,
                               pid, g.landlord)
            if play is None:
                g.pass_turn(pid)
            else:
                g.play(pid, play)
    if g.phase == Game.PHASE_END:
        games_done += 1
        s = g.scores()
        if sum(s.values()) != 0:
            FAIL.append(('计分和为 0', s, 0))
            print('✗ 计分和不为 0:', s)
    else:
        print('✗ 对局未结束:', seed)
print(f'✓ 30 局随机模拟完成，结束 {games_done} 局')

if FAIL:
    print(f'\n共 {len(FAIL)} 个失败')
    sys.exit(1)
print('\n全部通过')
