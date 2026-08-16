"""斗地主图形界面（tkinter）。

布局：下方为真人手牌（点击选牌），左/右为两家电脑（牌背朝下），
顶部中间显示底牌；出牌过程中显示各家在当前这一轮出的牌，
过牌时撤下该家上一轮的牌并提示「不出」，新一轮开始桌面清空；
牌局结束后在画布上方缩小、横向铺开公示电脑剩余手牌。
出牌按逆时针顺序（你 -> 右家 -> 左家），终局显示本局计分与跨局累计总分。
界面含木质外框、圆角牌面与阴影等美化，启动时自动播放背景音乐。
"""
import tkinter as tk

from .cards import rank, RANK_NAMES, SUITS, LITTLE_JOKER, BIG_JOKER
from .game_logic import Game
from .ai import choose_bid, choose_play
from .audio import play_bgm, stop_bgm, is_playing, keep_alive

W, H = 1000, 648          # 画布设计尺寸
BAR_H = 52                # 按钮条高度（画布 + 按钮条合计 700）
FULLSCREEN_START = False  # 设为 True 则启动时直接进入全屏
CARD_W, CARD_H = 46, 64
LEFT_X, RIGHT_X = 34, W - 34 - CARD_W
PLAYER_NAMES = {0: '你', 1: '左家', 2: '右家'}

FELT = '#0a7d33'        # 桌面绿
FELT_DARK = '#086527'   # 阴影/暗部
WOOD1 = '#6d4420'       # 外框外圈
WOOD2 = '#8a5a2b'       # 外框内圈
RED = '#d3222a'
BLACK = '#232323'


def _round_rect(c, x1, y1, x2, y2, r=8, **kw):
    """画一个圆角矩形（用平滑多边形近似）。"""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, splinesteps=24, **kw)


class DouDiZhuApp:
    def __init__(self, root):
        self.root = root
        root.title('斗地主 · 人机对战')
        root.resizable(False, False)
        root.configure(bg=WOOD1)

        # 按系统 DPI 与屏幕大小计算缩放，保证高分屏下窗口既清晰又不显小
        self.fullscreen = False
        self.scale = self._compute_scale(root)
        root.tk.call('tk', 'scaling', self.scale * (96 / 72))

        vw, vh = self._px(W), self._px(H + BAR_H)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        windowed_geom = f'{vw}x{vh}+{max(0, (sw - vw) // 2)}+{max(0, (sh - vh) // 2)}'
        root.geometry(windowed_geom)
        # 记住启动时的窗口比例与位置，退出全屏时原样恢复。
        # 注意：此时窗口尚未真正显示，root.geometry() 读取到的是 1x1，必须用目标字符串本身。
        self._windowed_scale = self.scale
        self._windowed_geom = windowed_geom

        self.f_small = ('Microsoft YaHei', 10)
        self.f_mid = ('Microsoft YaHei', 13)
        self.f_big = ('Microsoft YaHei', 20, 'bold')

        self.selected = set()   # 已选中的手牌
        self.status = ''        # 状态提示
        self.hand_positions = []  # (牌, x0, y0, x1, y1)，用于点击命中
        self.music_on = False
        self.total_scores = [0, 0, 0]  # 跨局累计总分
        self._score_applied = False    # 本局得分是否已并入总分

        self._build_buttons()   # 先放底部按钮条，再放画布
        self.canvas = tk.Canvas(root, width=vw, height=self._px(H), bg=FELT,
                                highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self._cv_w, self._cv_h = vw, self._px(H)  # 画布目标尺寸，用于全屏时内容居中
        self._ox = self._oy = 0                   # 缩放后内容相对画布左上角的偏移

        root.bind('<F11>', lambda e: self.toggle_fullscreen())
        root.bind('<Escape>', lambda e: self.exit_fullscreen())

        self._start_music()
        root.protocol('WM_DELETE_WINDOW', self._on_close)

        self.new_game()
        if FULLSCREEN_START:
            self.toggle_fullscreen()

    # ---------- 缩放与控件 ----------

    def _compute_scale(self, root):
        """按系统 DPI 与屏幕尺寸计算整体缩放比例。"""
        try:
            dpi = root.winfo_fpixels('1i')
        except Exception:
            dpi = 96.0
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        if self.fullscreen:
            # 全屏：尽量铺满整个屏幕（保持长宽比，多出的一侧自然留边）
            return max(0.85, min(sw / W, sh / (H + BAR_H)))
        s = dpi / 96.0                       # 保持与系统缩放一致的观感
        s = min(s, sw / W, (sh - 60) / (H + BAR_H))  # 且不超出屏幕
        return max(0.85, s)

    def toggle_fullscreen(self):
        """全屏 / 窗口模式切换（可用 F11 或工具栏按钮触发）。

        注意：Windows 下 `-fullscreen` 直接切换会导致退出全屏时窗口尺寸损坏，
        必须在切换前后临时允许缩放（resizable True），退出后再恢复。
        """
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.root.resizable(True, True)
            self.root.attributes('-fullscreen', True)
        else:
            self.root.attributes('-fullscreen', False)
            self.root.resizable(True, True)
            self.root.geometry(self._windowed_geom)
            self.root.update_idletasks()
            self.root.resizable(False, False)
        self._relayout()
        self.btn_fullscreen.config(text='退出全屏' if self.fullscreen else '全屏')

    def exit_fullscreen(self):
        """退出全屏（Escape 键）。"""
        if self.fullscreen:
            self.toggle_fullscreen()

    def _relayout(self):
        """全屏 / 窗口切换后，按当前状态重算缩放并应用到按钮条与画布。"""
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        if self.fullscreen:
            self.scale = self._compute_scale(self.root)
            self.root.tk.call('tk', 'scaling', self.scale * (96 / 72))
            self.bar.configure(height=self._px(BAR_H))
            cw, ch = sw, sh - self._px(BAR_H)
            self.canvas.configure(width=cw, height=ch)
        else:
            # 退出全屏：恢复启动时的窗口比例与位置
            self.scale = self._windowed_scale
            self.root.tk.call('tk', 'scaling', self.scale * (96 / 72))
            self.bar.configure(height=self._px(BAR_H))
            cw, ch = self._px(W), self._px(H)
            self.canvas.configure(width=cw, height=ch)
        self._cv_w, self._cv_h = cw, ch
        self.refresh()

    def _px(self, v):
        return int(round(v * self.scale))

    def _make_btn(self, parent, text, cmd, bg, fg, width=8):
        return tk.Button(
            parent, text=text, command=cmd, width=width,
            font=('Microsoft YaHei', 11, 'bold'),
            bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
            relief='flat', bd=0, highlightthickness=0, pady=5,
            cursor='hand2', takefocus=0)

    def _build_buttons(self):
        # 按钮条：必须显式给高度（随 DPI 缩放），否则会被压缩到 1px、按钮全部不可见
        bar = tk.Frame(self.root, bg=WOOD2, height=self._px(BAR_H))
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)
        self.bar = bar

        self.btn_new = self._make_btn(bar, '新一局', self.new_game, '#2e6da4', 'white')
        self.btn_play = self._make_btn(bar, '出牌', self.on_play, '#e8a13c', '#4a2f00')
        self.btn_pass = self._make_btn(bar, '不出', self.on_pass, '#6b7a8f', 'white')
        self.btn_hint = self._make_btn(bar, '提示', self.on_hint, '#d9dde3', '#333')
        self.btn_bids = {}
        for s in (1, 2, 3):
            self.btn_bids[s] = self._make_btn(
                bar, f'叫{s}分', lambda s=s: self.on_bid(s), '#e8a13c', '#4a2f00')
        self.btn_no = self._make_btn(bar, '不叫', lambda: self.on_bid(0), '#6b7a8f', 'white')
        self.btn_music = self._make_btn(bar, '音乐', self.on_music, '#3f9d3f', 'white')
        self.btn_fullscreen = self._make_btn(
            bar, '全屏', self.toggle_fullscreen, '#7a5a2e', 'white', width=9)
        # 按钮位置按 DPI 缩放，保证在放大的按钮条上居中、不堆在左侧
        self.btn_new.place(x=self._px(10), y=self._px(8))
        self.btn_fullscreen.place(x=self._px(W - 156), y=self._px(8))
        self.btn_music.place(x=self._px(W - 76), y=self._px(8))

    def update_buttons(self):
        g = self.game
        for w in (self.btn_play, self.btn_pass, self.btn_hint,
                  self.btn_no, self.btn_new, self.btn_music,
                  self.btn_fullscreen):
            w.place_forget()
        for w in self.btn_bids.values():
            w.place_forget()

        self.btn_new.place(x=self._px(10), y=self._px(8))
        self.btn_fullscreen.place(x=self._px(W - 156), y=self._px(8))
        self.btn_music.place(x=self._px(W - 76), y=self._px(8))
        if g.phase == g.PHASE_BID and g.current == 0:
            self.btn_no.place(x=self._px(W // 2 - 190), y=self._px(8))
            idx = 0
            for s in (1, 2, 3):
                if s in g.available_bids():
                    self.btn_bids[s].place(
                        x=self._px(W // 2 - 100 + idx * 100), y=self._px(8))
                    idx += 1
        elif g.phase == g.PHASE_PLAY and g.current == 0:
            self.btn_play.place(x=self._px(W // 2 - 160), y=self._px(8))
            self.btn_pass.place(x=self._px(W // 2 - 60), y=self._px(8))
            self.btn_hint.place(x=self._px(W // 2 + 40), y=self._px(8))

    # ---------- 背景音乐 ----------

    def _start_music(self):
        play_bgm()
        self.music_on = is_playing()
        self._bgm_tick()

    def _bgm_tick(self):
        if self.music_on:
            keep_alive()
        self.root.after(4000, self._bgm_tick)

    def on_music(self):
        if self.music_on:
            stop_bgm()
            self.music_on = False
        else:
            play_bgm()
            self.music_on = is_playing()
        self.btn_music.config(text='音乐' if self.music_on else '静音')

    def _on_close(self):
        stop_bgm()
        self.root.destroy()

    # ---------- 绘制 ----------

    def _card(self, x, y, card, selected=False, scale=1.0, face=True):
        """在画布上画一张牌。face=False 为牌背。"""
        w, h = CARD_W * scale, CARD_H * scale
        r = 8 * scale
        yy = y - 18 * scale if selected else y
        c = self.canvas
        # 阴影
        _round_rect(c, x + 2 * scale, yy + 3 * scale, x + w + 2 * scale,
                    yy + h + 3 * scale, r, fill=FELT_DARK, outline='')
        if not face:
            # 牌背：蓝底 + 黄菱格
            _round_rect(c, x, yy, x + w, yy + h, r, fill='#1b5fb8',
                        outline='#0d3d80', width=1)
            _round_rect(c, x + 3 * scale, yy + 3 * scale, x + w - 3 * scale,
                        yy + h - 3 * scale, r * 0.8, outline='#ffd966',
                        width=1, fill='')
            cx, cy = x + w / 2, yy + h / 2
            c.create_polygon(cx, cy - 13 * scale, cx + 9 * scale, cy,
                             cx, cy + 13 * scale, cx - 9 * scale, cy,
                             fill='#ffd966', outline='')
            c.create_polygon(cx, cy - 8 * scale, cx + 5 * scale, cy,
                             cx, cy + 8 * scale, cx - 5 * scale, cy,
                             fill='#1b5fb8', outline='')
            return
        # 正面
        _round_rect(c, x, yy, x + w, yy + h, r, fill='#fffef7',
                    outline='#c9c2b0', width=1)
        _round_rect(c, x + 3 * scale, yy + 3 * scale, x + w - 3 * scale,
                    yy + h - 3 * scale, r * 0.8, outline='#e6ddc9',
                    width=1, fill='')
        if card == BIG_JOKER:
            color, label = RED, '大王'
        elif card == LITTLE_JOKER:
            color, label = '#1e5faa', '小王'
        else:
            rk, s = RANK_NAMES[card // 4], SUITS[card % 4]
            color = RED if s in '♥♦' else BLACK
            c.create_text(x + 5 * scale, yy + 3 * scale, text=rk, anchor='nw',
                          fill=color, font=('Microsoft YaHei', int(12 * scale), 'bold'))
            c.create_text(x + 5 * scale, yy + 17 * scale, text=s, anchor='nw',
                          fill=color, font=('Microsoft YaHei', int(9 * scale)))
            c.create_text(x + w / 2, yy + h / 2, text=s, fill=color,
                          font=('Microsoft YaHei', int(24 * scale)))
            c.create_text(x + w - 5 * scale, yy + h - 3 * scale, text=rk,
                          anchor='se', fill=color,
                          font=('Microsoft YaHei', int(12 * scale), 'bold'))
            c.create_text(x + w - 5 * scale, yy + h - 17 * scale, text=s,
                          anchor='se', fill=color,
                          font=('Microsoft YaHei', int(9 * scale)))
            return
        # 大小王：中央大字
        c.create_text(x + w / 2, yy + h / 2 - 5 * scale, text=label[0],
                      fill=color, font=('Microsoft YaHei', int(26 * scale), 'bold'))
        c.create_text(x + w / 2, yy + h / 2 + 13 * scale, text='王', fill=color,
                      font=('Microsoft YaHei', int(11 * scale), 'bold'))
        c.create_text(x + 5 * scale, yy + 3 * scale, text=label, anchor='nw',
                      fill=color, font=('Microsoft YaHei', int(11 * scale), 'bold'))

    def _draw_frame(self):
        c = self.canvas
        c.create_rectangle(0, 0, W, H, fill=WOOD1, outline='')
        c.create_rectangle(6, 6, W - 6, H - 6, fill=WOOD2, outline='')
        c.create_rectangle(14, 14, W - 14, H - 14, fill=FELT, outline='')
        c.create_rectangle(16, 16, W - 16, H - 16, outline='#095d25', width=1)

    def _draw_opponent(self, pid, x):
        g = self.game
        c = self.canvas
        n = len(g.hands[pid])
        start_y = 170
        for i in range(n):
            self._card(x, start_y + i * 13, 0, scale=0.9, face=False)
        # 名字小牌
        label = PLAYER_NAMES[pid]
        _round_rect(c, x + CARD_W / 2 - 30, start_y - 44, x + CARD_W / 2 + 30,
                    start_y - 16, 8, fill='#0b5a26', outline='#1c7a3a', width=1)
        c.create_text(x + CARD_W / 2, start_y - 30, text=label,
                      fill='#eaffea', font=self.f_mid)
        c.create_text(x + CARD_W / 2, start_y + n * 13 + 6,
                      text=f'{n} 张', fill='#eaffea', font=self.f_small)

    def _draw_reveal_fan(self, pid, y, scale, step, x_start=None, x_end=None):
        """终局公示：把一家电脑的剩余手牌横向铺开（缩小比例）。"""
        g = self.game
        c = self.canvas
        hand = sorted(g.hands[pid], key=rank)
        n = len(hand)
        card_w = CARD_W * scale
        label = PLAYER_NAMES[pid]
        if g.landlord == pid:
            label += '·地主'
        label += f'·{n} 张'
        if n == 0:
            cx = x_start if x_start is not None else x_end
            c.create_text(cx, y - 9, text=label, fill='#eaffea', font=self.f_small)
            return
        if x_start is not None:
            x = x_start
            center = x_start + (step * (n - 1) + card_w) / 2
        else:
            width = step * (n - 1) + card_w
            x = x_end - width
            center = x_end - width / 2
        for card in hand:
            self._card(x, y, card, scale=scale)
            x += step
        c.create_text(center, y - 9, text=label, fill='#eaffea', font=self.f_small)

    def _draw_end_reveal(self):
        """牌局结束后，把两家电脑的剩余手牌在画布上方缩小、横向铺开公示。"""
        scale = 0.5
        card_w = CARD_W * scale
        step = card_w * 0.78
        y = 102
        self._draw_reveal_fan(1, y, scale, step, x_start=66)
        self._draw_reveal_fan(2, y, scale, step, x_end=W - 66)

    def _draw_landlord_marker(self):
        g = self.game
        # 终局由上方公示标签标注「·地主」，不再画侧边浮标
        if g.landlord is None or g.phase == g.PHASE_END:
            return
        c = self.canvas
        pid = g.landlord
        if pid == 0:
            bx, by = W // 2 + 132, 542
        elif pid == 1:
            bx, by = LEFT_X + CARD_W + 24, 138
        else:
            bx, by = RIGHT_X - 24, 138
        c.create_oval(bx - 16, by - 16, bx + 16, by + 16, fill='#ffd700',
                      outline='#8a6d00', width=1)
        c.create_text(bx, by, text='地', fill='#5a3e00',
                      font=('Microsoft YaHei', 14, 'bold'))

    def _draw_turn_indicator(self):
        g = self.game
        if g.current is None or g.phase == g.PHASE_END:
            return
        c = self.canvas
        pos = {0: (W // 2, 544), 1: (150, 200), 2: (W - 150, 200)}
        x, y = pos[g.current]
        label = f'{PLAYER_NAMES[g.current]} 出牌中'
        w = 26 + len(label) * 14
        _round_rect(c, x - w / 2, y - 14, x + w / 2, y + 14, 14,
                    fill='#ffcc00', outline='#c99700')
        c.create_text(x, y + 1, text=label, fill='#5a3e00',
                      font=('Microsoft YaHei', 12, 'bold'))

    def _draw_last_play(self, pid, x, y, right_align=False):
        """显示各家在『当前这一轮』出的牌：出牌→亮出；
        过牌→撤下该家上一轮的牌、提示「不出」；新一轮开始桌面清空。"""
        g = self.game
        c = self.canvas
        cards = g.last_played_cards[pid]
        if cards:
            cards = sorted(cards, key=rank)
            scale = 0.72
            step = CARD_W * scale * 0.72
            x0 = x - step * (len(cards) - 1) if right_align else x
            for card in cards:
                self._card(x0, y, card, scale=scale)
                x0 += step
        elif g.passed[pid]:
            c.create_text(x, y + CARD_H * 0.72 / 2, text='不出', fill='#ffdddd',
                          font=self.f_mid)

    def _draw_hand(self):
        g = self.game
        hand = sorted(g.hands[0], key=rank)  # 升序显示
        n = len(hand)
        y = 560
        spacing = min(34, (W - 240 - CARD_W) / max(1, n - 1)) if n > 1 else 0
        x = (W - (n - 1) * spacing - CARD_W) / 2
        for card in hand:
            sel = card in self.selected
            yy = y - 18 if sel else y
            self._card(x, y, card, selected=sel)
            # 命中区用放大后 + 居中偏移的坐标，与画布实际像素一致，保证点击选牌准确
            self.hand_positions.append(
                (card, self._px(x) + self._ox, self._px(yy) + self._oy,
                 self._px(x + CARD_W) + self._ox,
                 self._px(yy + CARD_H) + self._oy))
            x += spacing

    def _draw_status(self):
        """居中的状态横幅（避开牌面，不被遮挡）。"""
        c = self.canvas
        if not self.status or self.game.phase == self.game.PHASE_END:
            return
        w = max(230, min(640, 36 + len(self.status) * 15))
        x1, x2 = W // 2 - w / 2, W // 2 + w / 2
        _round_rect(c, x1, 106, x2, 148, 12, fill='#0b5a26',
                    outline='#1c7a3a', width=1)
        c.create_text(W // 2, 127, text=self.status, fill='white', font=self.f_mid)

    def _result_text(self):
        g = self.game
        if g.winner == 'landlord':
            return '地主获胜！' if g.landlord == 0 else '地主获胜（电脑）'
        return '农民获胜！' if g.landlord != 0 else '农民获胜（电脑）'

    def _draw_end_score(self):
        """终局计分面板：本局明细 + 各家本局得分 + 累计总分。"""
        g = self.game
        c = self.canvas
        bx = W // 2
        s = g.scores()
        n = PLAYER_NAMES
        lines = [
            g.score_detail(),
            f'本局  {n[0]} {s[0]:+d}   {n[1]} {s[1]:+d}   {n[2]} {s[2]:+d}',
            f'累计  {n[0]} {self.total_scores[0]:+d}   '
            f'{n[1]} {self.total_scores[1]:+d}   {n[2]} {self.total_scores[2]:+d}',
        ]
        w = min(760, max(400, 44 + max(len(l) * 15 for l in lines)))
        y0, h = 232, 3 * 24 + 16
        _round_rect(c, bx - w / 2, y0, bx + w / 2, y0 + h, 12,
                    fill='#0b5a26', outline='#1c7a3a', width=1)
        for i, line in enumerate(lines):
            c.create_text(bx, y0 + 22 + i * 24, text=line, fill='#eaffea',
                          font=self.f_small if i else self.f_mid)

    def _draw(self):
        g = self.game
        c = self.canvas
        bx = W // 2

        self._draw_frame()

        # 标题（带投影）
        c.create_text(31, 23, text='斗地主', anchor='nw', fill=FELT_DARK,
                      font=('Microsoft YaHei', 22, 'bold'))
        c.create_text(30, 22, text='斗地主', anchor='nw', fill='white',
                      font=('Microsoft YaHei', 22, 'bold'))
        c.create_text(31, 54, text='人机对战 · 你 VS 左家 · 右家', anchor='nw',
                      fill='#cdeacd', font=self.f_small)

        # 右上角跨局累计总分（逆时针 你 -> 右家 -> 左家）
        c.create_text(W - 20, 24, anchor='ne',
                      text=f'总分  你 {self.total_scores[0]:+d}   '
                           f'右家 {self.total_scores[2]:+d}   '
                           f'左家 {self.total_scores[1]:+d}',
                      fill='#eaffea', font=self.f_small)

        # 底牌
        c.create_text(bx, 22, text='底牌', fill='#e8ffe8', font=self.f_mid)
        if g.landlord is not None:
            for i, card in enumerate(g.bottom):
                self._card(bx - 76 + i * 52, 38, card, scale=0.85)
        else:
            for i in range(3):
                self._card(bx - 76 + i * 52, 38, 0, scale=0.85, face=False)

        if g.phase == g.PHASE_END:
            # 终局：电脑剩余手牌在上方缩小横向公示，不再画侧边竖排牌背
            self._draw_end_reveal()
        else:
            self._draw_opponent(1, LEFT_X)
            self._draw_opponent(2, RIGHT_X)

        self._draw_last_play(0, bx, 468)
        self._draw_last_play(1, 168, 250)
        self._draw_last_play(2, W - 168, 250, right_align=True)

        self._draw_hand()
        self._draw_status()

        if g.phase == g.PHASE_END:
            msg = self._result_text()
            _round_rect(c, bx - 220, 150, bx + 220, 218, 16, fill='#fffdf4',
                        outline='#ffd700', width=3)
            c.create_text(bx, 176, text=msg,
                          fill=RED if '你' in msg else '#555', font=self.f_big)
            c.create_text(bx, 203, text='点击「新一局」再来一局（计分继续累计）',
                          fill='#999', font=self.f_small)
            self._draw_end_score()

        self._draw_landlord_marker()
        self._draw_turn_indicator()

    def refresh(self):
        self.canvas.delete('all')
        self.hand_positions = []
        c = self.canvas
        # 画布按 1000x648 设计坐标绘制，最后统一放大。缩放后内容尺寸
        # 可能比画布小（全屏时留边），把内容平移到画布中央，避免空白偏在一侧
        self._ox = int(round((self._cv_w - W * self.scale) / 2))
        self._oy = int(round((self._cv_h - H * self.scale) / 2))
        self._draw()
        if self.scale != 1.0:
            c.scale('all', 0, 0, self.scale, self.scale)
        if self._ox or self._oy:
            c.move('all', self._ox, self._oy)

    # ---------- 交互 ----------

    def on_canvas_click(self, event):
        g = self.game
        if g.phase != g.PHASE_PLAY or g.current != 0:
            return
        for card, x0, y0, x1, y1 in reversed(self.hand_positions):
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                if card in self.selected:
                    self.selected.discard(card)
                else:
                    self.selected.add(card)
                self.refresh()
                return

    def on_play(self):
        g = self.game
        if g.phase != g.PHASE_PLAY or g.current != 0:
            return
        cards = [c for c in g.hands[0] if c in self.selected]
        if not cards:
            self.status = '请先点击选择要出的牌'
            self.refresh()
            return
        ok, msg = g.can_play(cards)
        if not ok:
            self.status = msg
            self.refresh()
            return
        g.play(0, cards)
        self.selected.clear()
        self.status = '你出牌了'
        self.refresh()
        self.advance()

    def on_pass(self):
        g = self.game
        if g.phase != g.PHASE_PLAY or g.current != 0:
            return
        if g.last_play is None:
            self.status = '新一轮必须出牌'
            self.refresh()
            return
        g.pass_turn(0)
        self.selected.clear()
        self.status = '你不出'
        self.refresh()
        self.advance()

    def on_hint(self):
        g = self.game
        if g.phase != g.PHASE_PLAY or g.current != 0:
            return
        play = choose_play(g.hands[0], g.last_play, g.last_play_player,
                           0, g.landlord)
        if play is None:
            self.status = '提示：不出'
        else:
            self.selected = set(play)
            self.status = f'提示：出 {len(play)} 张牌'
        self.refresh()

    def on_bid(self, score):
        g = self.game
        if g.phase != g.PHASE_BID or g.current != 0:
            return
        try:
            res = g.submit_bid(0, score)
        except ValueError as e:
            self.status = str(e)
            self.refresh()
            return
        if res == 'redeal':
            self.new_game()
            return
        self.selected.clear()
        if g.phase == g.PHASE_PLAY:
            self.status = ('你是地主，先出牌！'
                           if g.landlord == 0
                           else f'{PLAYER_NAMES[g.landlord]} 是地主')
        else:
            self.status = '你不叫' if score == 0 else f'你叫了 {score} 分'
        self.refresh()
        self.advance()

    # ---------- 流程 ----------

    def new_game(self):
        self.game = Game()
        self.selected = set()
        self._score_applied = False
        self.status = '发牌完成，叫地主开始'
        self.refresh()
        self.advance()

    def advance(self):
        g = self.game
        self.update_buttons()
        if g.phase == g.PHASE_END:
            if not self._score_applied:
                self._score_applied = True
                delta = g.scores()
                for pid in range(3):
                    self.total_scores[pid] += delta[pid]
            return
        if g.current != 0:   # 轮到电脑
            self.root.after(650, self.ai_turn)

    def ai_turn(self):
        g = self.game
        if g.phase == g.PHASE_END:
            self.refresh()
            self.advance()
            return
        pid = g.current
        if g.phase == g.PHASE_BID:
            score = choose_bid(g.hands[pid], g.bid, pid)
            res = g.submit_bid(pid, score)
            if res == 'redeal':
                self.new_game()
                return
            if g.phase == g.PHASE_PLAY:
                self.status = f'{PLAYER_NAMES[g.landlord]} 成为地主'
            else:
                self.status = (f'{PLAYER_NAMES[pid]} 不叫'
                               if score == 0 else f'{PLAYER_NAMES[pid]} 叫 {score} 分')
        else:
            play = choose_play(g.hands[pid], g.last_play, g.last_play_player,
                               pid, g.landlord)
            if play is None:
                g.pass_turn(pid)
                self.status = f'{PLAYER_NAMES[pid]} 不出'
            else:
                g.play(pid, play)
                self.status = f'{PLAYER_NAMES[pid]} 出了 {len(play)} 张牌'
        self.refresh()
        self.advance()
