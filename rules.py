"""斗地主牌型识别与比较。

analyze(cards) 返回 (牌型, 比较值, 张数)，无法识别返回 None。
牌型常量说明：比较时同牌型同张数比较“比较值”，
炸弹可压一切非炸弹，火箭最大。
"""
from collections import Counter

from .cards import rank, LITTLE_JOKER, BIG_JOKER

# 牌型常量
SINGLE = 0            # 单张
PAIR = 1              # 对子
TRIPLE = 2            # 三张
TRIPLE_SINGLE = 3     # 三带一
TRIPLE_PAIR = 4       # 三带二
STRAIGHT = 5          # 顺子（>=5 张连续单张）
STRAIGHT_PAIR = 6     # 连对（>=3 个连续对子）
AIRPLANE = 7          # 飞机不带
AIRPLANE_SINGLE = 8   # 飞机带单
AIRPLANE_PAIR = 9     # 飞机带对
FOUR_TWO = 10         # 四带二
BOMB = 11             # 炸弹
ROCKET = 12           # 王炸（火箭）

TYPE_NAMES = {
    SINGLE: '单张', PAIR: '对子', TRIPLE: '三张', TRIPLE_SINGLE: '三带一',
    TRIPLE_PAIR: '三带二', STRAIGHT: '顺子', STRAIGHT_PAIR: '连对',
    AIRPLANE: '飞机', AIRPLANE_SINGLE: '飞机带单', AIRPLANE_PAIR: '飞机带对',
    FOUR_TWO: '四带二', BOMB: '炸弹', ROCKET: '王炸',
}


def _consecutive(vals):
    """vals 是否严格连续（每两个相差 1）。"""
    return all(vals[i + 1] == vals[i] + 1 for i in range(len(vals) - 1))


def _runs(values, min_len):
    """返回 values 中所有长度 >= min_len 的连续子序列（元组形式）。"""
    res = []
    values = sorted(set(values))
    n = len(values)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[j + 1] == values[j] + 1:
            j += 1
        seg = values[i:j + 1]
        if len(seg) >= min_len:
            for L in range(min_len, len(seg) + 1):
                for s in range(len(seg) - L + 1):
                    res.append(tuple(seg[s:s + L]))
        i = j + 1
    return res


def _find_airplane(cnt, n):
    """在点数字典中查找飞机牌型，返回 (牌型, 比较值, 张数) 或 None。"""
    trip_vals = [v for v in sorted(cnt) if cnt[v] == 3]
    # 枚举所有连续、长度 >= 2、最大点数 <= 14 的连续三张子序列
    windows = []
    for s in range(len(trip_vals)):
        for e in range(s + 1, len(trip_vals) + 1):
            w = trip_vals[s:e]
            if len(w) >= 2 and w[-1] <= 14 and _consecutive(w):
                windows.append(w)
    # 长的优先，点数大的优先
    windows.sort(key=lambda w: (-len(w), w[-1]))
    for w in windows:
        k = len(w)
        rem = n - 3 * k
        if rem == 0:
            return (AIRPLANE, w[-1], n)
        if rem == k:
            return (AIRPLANE_SINGLE, w[-1], n)
        if rem == 2 * k:
            remaining = []
            for v, c in cnt.items():
                c2 = c - (3 if v in w else 0)
                if c2:
                    remaining.extend([v] * c2)
            if len(remaining) == 2 * k and all(
                    remaining.count(v) == 2 for v in set(remaining)):
                return (AIRPLANE_PAIR, w[-1], n)
    return None


def analyze(cards):
    """识别一组牌的牌型，返回 (牌型, 比较值, 张数)；非法返回 None。"""
    n = len(cards)
    if n == 0:
        return None
    if n == 2:
        vals = sorted(rank(c) for c in cards)
        if vals == [16, 17]:
            return (ROCKET, 17, 2)
    cnt = Counter(rank(c) for c in cards)
    uniq = sorted(cnt)
    kinds = Counter(cnt.values())

    if n == 1:
        return (SINGLE, uniq[0], 1)
    if n == 2 and len(cnt) == 1:
        return (PAIR, uniq[0], 2)
    if n == 3 and len(cnt) == 1:
        return (TRIPLE, uniq[0], 3)

    if kinds.get(4):
        fours = [v for v in uniq if cnt[v] == 4]
        if len(fours) == 1 and n in (4, 6, 8):
            return (BOMB if n == 4 else FOUR_TWO, fours[0], n)
        return None

    if n == 4 and kinds.get(3) == 1 and kinds.get(1) == 1:
        return (TRIPLE_SINGLE, [v for v in uniq if cnt[v] == 3][0], 4)
    if n == 5 and kinds.get(3) == 1 and kinds.get(2) == 1:
        return (TRIPLE_PAIR, [v for v in uniq if cnt[v] == 3][0], 5)

    if n >= 5:
        # 顺子
        if all(c == 1 for c in cnt.values()) and uniq[-1] <= 14 and _consecutive(uniq):
            return (STRAIGHT, uniq[-1], n)
        # 连对
        if (n % 2 == 0 and len(uniq) >= 3 and all(c == 2 for c in cnt.values())
                and uniq[-1] <= 14 and _consecutive(uniq)):
            return (STRAIGHT_PAIR, uniq[-1], n)
        # 飞机
        ap = _find_airplane(cnt, n)
        if ap:
            return ap
    return None


def can_beat(new, old):
    """new / old 为 analyze 的结果元组；old 为 None 表示可以自由出牌。"""
    if old is None:
        return True
    nt, nk, nl = new
    ot, ok, ol = old
    if nt == ROCKET:
        return True
    if ot == ROCKET:
        return False
    if nt == BOMB:
        return nk > ok if ot == BOMB else True
    if nt == ot and nl == ol:
        return nk > ok
    return False


def generate_plays(hand):
    """枚举一手牌所有可能的出牌，返回 [(牌型, 比较值, 牌列表), ...]。

    生成的每个组合都会用 analyze 复核，保证与判定规则一致。
    """
    plays = []
    groups = {}
    for c in hand:
        v = rank(c)
        groups.setdefault(v, []).append(c)
    vals = sorted(groups)

    # 单张 / 对子 / 三张 / 炸弹
    for v in vals:
        cards = groups[v]
        plays.append((SINGLE, v, [cards[0]]))
        if len(cards) >= 2:
            plays.append((PAIR, v, cards[:2]))
        if len(cards) >= 3:
            plays.append((TRIPLE, v, cards[:3]))
        if len(cards) == 4:
            plays.append((BOMB, v, cards[:4]))

    # 王炸
    if LITTLE_JOKER in hand and BIG_JOKER in hand:
        plays.append((ROCKET, 17, [LITTLE_JOKER, BIG_JOKER]))

    # 三带一 / 三带二
    trip_vals = [v for v in vals if len(groups[v]) >= 3]
    for t in trip_vals:
        tc = groups[t][:3]
        for v in vals:
            if v == t:
                continue
            for c in groups[v]:
                plays.append((TRIPLE_SINGLE, t, tc + [c]))
        for v in vals:
            if v != t and len(groups[v]) >= 2:
                plays.append((TRIPLE_PAIR, t, tc + groups[v][:2]))

    # 顺子
    svals = [v for v in vals if v <= 14]
    for run in _runs(svals, 5):
        plays.append((STRAIGHT, run[-1], [groups[v][0] for v in run]))

    # 连对
    pvals = [v for v in vals if v <= 14 and len(groups[v]) >= 2]
    for run in _runs(pvals, 3):
        cards = []
        for v in run:
            cards.extend(groups[v][:2])
        plays.append((STRAIGHT_PAIR, run[-1], cards))

    # 飞机（不带 / 带单 / 带对）
    tv = [v for v in trip_vals if v <= 14]
    for run in _runs(tv, 2):
        k = len(run)
        trip_cards = []
        for v in run:
            trip_cards.extend(groups[v][:3])
        plays.append((AIRPLANE, run[-1], trip_cards))

        wing = []
        for v in vals:
            if v not in run:
                wing.extend(groups[v])
        if len(wing) >= k:
            plays.append((AIRPLANE_SINGLE, run[-1], trip_cards + wing[:k]))

        pw = []
        for v in vals:
            if v not in run and len(groups[v]) >= 2:
                pw.append(groups[v][:2])
        if len(pw) >= k:
            cards = trip_cards + [c for p in pw[:k] for c in p]
            plays.append((AIRPLANE_PAIR, run[-1], cards))

    # 四带二
    for v in vals:
        if len(groups[v]) == 4:
            fc = groups[v]
            rest = [c for u in vals for c in groups[u] if u != v]
            if len(rest) >= 2:
                plays.append((FOUR_TWO, v, fc + rest[:2]))

    # 复核，剔除与 analyze 判定不一致的组合
    out = []
    for t, k, cards in plays:
        a = analyze(cards)
        if a and a[0] == t and a[1] == k:
            out.append((t, k, cards))
    return out
