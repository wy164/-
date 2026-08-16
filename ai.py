"""简单的电脑玩家决策逻辑：叫分与出牌。"""
from collections import Counter

from .cards import rank
from .rules import (analyze, can_beat, generate_plays,
                    BOMB, ROCKET)


def hand_strength(hand):
    """按手牌大牌数量估算牌力（用于叫地主）。"""
    strength = 0
    cnt = Counter(rank(c) for c in hand)
    for v, c in cnt.items():
        if v >= 13:          # K、A、2、大小王
            strength += 1
        if v >= 15:          # 2、大小王 额外加分
            strength += 1
        if c == 4:           # 炸弹
            strength += 3
        if c == 2 and v >= 15:
            strength += 1
    return strength


def choose_bid(hand, current_bid, player_id):
    """根据牌力决定叫分，0 表示不叫。"""
    strength = hand_strength(hand)
    want = 0
    if strength >= 8:
        want = 3
    elif strength >= 6:
        want = 2
    elif strength >= 4:
        want = 1
    if want > current_bid:
        return want
    # 牌特别好而别人已经叫了时，可以再抢一手
    if current_bid > 0 and strength >= 9:
        return 3
    return 0


def _should_bomb(hand, target, is_farmer, target_player, landlord_id):
    """是否值得用炸弹/火箭抢回出牌权。"""
    hand_size = len(hand)
    key = target[1]
    if hand_size <= 4:
        return True                     # 快出完了，全力抢权
    if is_farmer:
        if target_player == landlord_id and key >= 14:
            return True                 # 压住地主的 A/2/王
    else:
        if key >= 13:
            return True                 # 地主压农民的大牌
    return False


def _leading_play(hand, plays, is_farmer, self_id, landlord_id):
    """自由出牌（新一轮或地主先出）：优先出最小点数的牌，尽量多甩牌。"""
    normal = [p for p in plays if p[0] not in (BOMB, ROCKET)]
    if normal:
        normal.sort(key=lambda p: (p[1], -len(p[2])))
        return normal[0][2]
    # 手里只剩炸弹/火箭
    plays.sort(key=lambda p: (p[0] == ROCKET, p[1]))
    return plays[0][2]


def choose_play(hand, target, target_player, self_id, landlord_id):
    """决定出什么牌。返回要出的牌列表；None 表示不出。

    参数：
      hand          当前手牌
      target        当前一轮最大牌型 analyze 结果（None 表示自由出牌）
      target_player 当前一轮最大牌是哪个玩家出的
      self_id       自己
      landlord_id   地主
    """
    plays = generate_plays(hand)
    is_farmer = self_id != landlord_id

    if target is None:
        # 自由出牌（新一轮或地主先出）
        for t, k, cards in plays:
            if not [c for c in hand if c not in cards]:
                return cards
        return _leading_play(hand, plays, is_farmer, self_id, landlord_id)

    # 跟牌：先筛出能管上的组合
    beats = [p for p in plays if can_beat((p[0], p[1], len(p[2])), target)]
    if not beats:
        return None

    # 1) 一出手就能走完（且必须能管上）
    for t, k, cards in beats:
        if not [c for c in hand if c not in cards]:
            return cards

    # 2) 农民队友正在管牌 → 让队友出
    if (is_farmer and target_player is not None
            and target_player != landlord_id and target_player != self_id):
        return None

    # 3) 用普通牌型压
    normal = [p for p in beats if p[0] not in (BOMB, ROCKET)]
    if normal:
        normal.sort(key=lambda p: p[1])
        return normal[0][2]

    # 4) 只有炸弹/火箭能压，视情况出
    if _should_bomb(hand, target, is_farmer, target_player, landlord_id):
        beats.sort(key=lambda p: (p[0] == ROCKET, p[1]))
        return beats[0][2]
    return None
