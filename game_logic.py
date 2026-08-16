"""斗地主游戏流程控制（叫地主、出牌、胜负判定）。

玩家编号：0 = 真人（界面下方），1、2 = 电脑（界面左、右）。
出牌顺序 0 -> 2 -> 1 -> 0（逆时针）。
"""
import random

from .cards import make_deck, sort_cards
from .rules import analyze, can_beat, BOMB, ROCKET


class Game:
    PHASE_BID = 0   # 叫地主
    PHASE_PLAY = 1  # 出牌
    PHASE_END = 2   # 结束

    def __init__(self):
        self.reset()

    def reset(self):
        deck = make_deck()
        random.shuffle(deck)
        self.hands = [
            sort_cards(deck[0:17]),
            sort_cards(deck[17:34]),
            sort_cards(deck[34:51]),
        ]
        self.bottom = deck[51:54]            # 底牌 3 张
        self.landlord = None                 # 地主编号
        self.phase = self.PHASE_BID
        self.bid = 0                         # 当前最高叫分
        self.bidder = None                   # 当前最高叫分者
        self.bid_pass_count = 0              # 连续不叫人数
        self.current = random.randrange(3)   # 当前行动玩家（先叫地主的人）
        self.last_play = None                # 当前一轮最大牌型 analyze 结果
        self.last_play_player = None
        self.last_played_cards = [[], [], []]  # 各家当前这一轮出的牌（界面显示用）
        self.passed = [False, False, False]    # 各家本轮是否已过牌（界面显示「不出」用）
        self.pass_count = 0                  # 连续不出人数
        self.winner = None                   # 'landlord' 或 'farmer'
        self.history = []                    # (玩家, 动作, 参数)
        self.bomb_count = 0                  # 本局打出的炸弹/王炸数（计分倍数）
        self.plays_count = [0, 0, 0]         # 各家出牌手数（春天/反春判定用）
        self.spring = False                  # 春天：地主胜且农民一张没出
        self.anti_spring = False             # 反春：农民胜且地主只出了一手

    def next_player(self, p):
        return (p - 1) % 3

    # ---------- 叫地主 ----------

    def available_bids(self):
        """当前玩家可选的叫分，0 表示不叫。"""
        if self.bid >= 3:
            return [0]
        return [0] + list(range(self.bid + 1, 4))

    def submit_bid(self, player, score):
        """玩家叫分。score == 0 表示不叫。返回 'continue' / 'done' / 'redeal'。"""
        if self.phase != self.PHASE_BID or player != self.current:
            raise ValueError('现在不能叫地主')
        if score != 0 and score not in self.available_bids():
            raise ValueError('叫分不合法')
        if score == 0:
            self.bid_pass_count += 1
        else:
            self.bid = score
            self.bidder = player
            self.bid_pass_count = 0
        self.history.append((player, 'bid', score))

        if self.bid >= 3 or self.bid_pass_count >= 3:
            if self.bidder is None:
                return 'redeal'          # 三家都不叫，重新发牌
            self._set_landlord(self.bidder)
            return 'done'
        self.current = self.next_player(player)
        return 'continue'

    def _set_landlord(self, player):
        self.landlord = player
        self.hands[player].extend(self.bottom)
        self.hands[player] = sort_cards(self.hands[player])
        self.phase = self.PHASE_PLAY
        self.current = player
        self.last_play = None
        self.last_play_player = None
        self.pass_count = 0

    # ---------- 出牌 ----------

    def can_play(self, cards):
        """检查这组牌能不能出，返回 (ok, 提示消息)。"""
        if not cards:
            return False, '请选择要出的牌'
        combo = analyze(cards)
        if combo is None:
            return False, '无效的牌型'
        if self.last_play is not None and not can_beat(combo, self.last_play):
            return False, '管不上上家的牌'
        return True, ''

    def play(self, player, cards):
        """玩家出牌。不合法抛 ValueError。"""
        if self.phase != self.PHASE_PLAY or player != self.current:
            raise ValueError('现在不能出牌')
        ok, msg = self.can_play(cards)
        if not ok:
            raise ValueError(msg)
        combo = analyze(cards)
        for c in cards:
            self.hands[player].remove(c)
        self.hands[player] = sort_cards(self.hands[player])
        self.last_play = combo
        self.last_play_player = player
        if combo[0] in (BOMB, ROCKET):
            self.bomb_count += 1     # 炸弹/王炸翻倍
        self.plays_count[player] += 1
        self.last_played_cards[player] = list(cards)
        self.passed[player] = False   # 出牌后不再是「过牌」状态
        self.pass_count = 0
        self.history.append((player, 'play', list(cards)))
        if not self.hands[player]:
            self._end(player)
            return
        self.current = self.next_player(player)

    def pass_turn(self, player):
        """玩家不出。若其余两家都不出，则由最后出牌者重新出。"""
        if self.phase != self.PHASE_PLAY or player != self.current:
            raise ValueError('现在不能不出')
        self.pass_count += 1
        self.history.append((player, 'pass', []))
        # 过牌后撤下该家上一轮出的牌，改显「不出」
        self.passed[player] = True
        self.last_played_cards[player] = []
        if self.pass_count >= 2:
            leader = self.last_play_player
            self.last_play = None
            self.last_play_player = None
            self.pass_count = 0
            self.current = leader
            # 新的一轮开始，清空整桌上一轮的牌
            self.last_played_cards = [[], [], []]
            self.passed = [False, False, False]
        else:
            self.current = self.next_player(player)

    def _end(self, player):
        self.phase = self.PHASE_END
        self.current = None
        self.winner = 'landlord' if player == self.landlord else 'farmer'
        farmers = [p for p in range(3) if p != self.landlord]
        if self.winner == 'landlord':
            # 春天：农民一张牌都没出
            self.spring = all(self.plays_count[p] == 0 for p in farmers)
        else:
            # 反春：地主只出了一手牌
            self.anti_spring = self.plays_count[self.landlord] == 1

    # ---------- 计分 ----------

    def multiplier(self):
        """本局计分倍数：2^炸弹数，春天/反春再 ×2。"""
        m = 2 ** self.bomb_count
        if self.spring or self.anti_spring:
            m *= 2
        return m

    def scores(self):
        """本局各家得分增量，返回 {玩家: 分数}，和为 0。"""
        amount = self.bid * self.multiplier()
        farmers = [p for p in range(3) if p != self.landlord]
        if self.winner == 'landlord':
            return {self.landlord: 2 * amount,
                    farmers[0]: -amount, farmers[1]: -amount}
        return {self.landlord: -2 * amount,
                farmers[0]: amount, farmers[1]: amount}

    def score_detail(self):
        """本局计分明细文本，如 '底分2 × 炸弹×2倍 × 春天×2 = 16'。"""
        parts = [f'底分{self.bid}']
        if self.bomb_count:
            parts.append(f'炸弹×{2 ** self.bomb_count}倍')
        if self.spring:
            parts.append('春天×2')
        elif self.anti_spring:
            parts.append('反春×2')
        return ' × '.join(parts) + f' = {self.bid * self.multiplier()}'

    # ---------- 其它 ----------

    def all_played(self):
        """场上已打出的所有牌（用于 AI 记牌）。"""
        played = set()
        for p in range(3):
            played.update(self.hands[p])
        played.update(self.bottom)
        return set(range(54)) - played
