"""扑克牌定义与基础工具。

每张牌用一个 0~53 的整数表示：
  0..51 为普通牌，card // 4 对应点数下标，card % 4 对应花色；
  52 = 小王，53 = 大王。
点数大小（比较用）：3 < 4 < ... < A < 2 < 小王 < 大王，
对应数值 3..17。
"""
import random

SUITS = ('♠', '♥', '♣', '♦')
RANK_NAMES = ('3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2')

LITTLE_JOKER = 52  # 小王
BIG_JOKER = 53     # 大王


def make_deck():
    """生成一副完整牌（54 张，未洗乱）。"""
    return list(range(54))


def rank(card):
    """返回牌的点数大小，3~17（越大越大）。"""
    if card == LITTLE_JOKER:
        return 16
    if card == BIG_JOKER:
        return 17
    return card // 4 + 3


def suit(card):
    """返回花色字符，大小王返回空串。"""
    if card >= 52:
        return ''
    return SUITS[card % 4]


def name(card):
    """返回牌的显示名，如 '10♠'、'小王'。"""
    if card == LITTLE_JOKER:
        return '小王'
    if card == BIG_JOKER:
        return '大王'
    return RANK_NAMES[card // 4] + SUITS[card % 4]


def sort_cards(cards):
    """按点数从大到小排序。"""
    return sorted(cards, key=rank, reverse=True)
