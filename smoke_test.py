"""GUI 冒烟测试：创建窗口，自动打完整局，验证绘制与流程无异常。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk  # noqa: E402

from game.gui import DouDiZhuApp  # noqa: E402
from game.ai import choose_play  # noqa: E402


def main():
    # 冒烟测试中禁用音乐保活，避免 after 立即执行造成递归
    DouDiZhuApp._bgm_tick = lambda self: None

    root = tk.Tk()
    root.after = lambda ms, fn=None: (fn() if callable(fn) else 0)
    app = DouDiZhuApp(root)

    safety = 0
    while app.game.phase != app.game.PHASE_END and safety < 2000:
        safety += 1
        g = app.game
        if g.current == 0:
            if g.phase == g.PHASE_BID:
                app.on_bid(0)
            else:
                play = choose_play(g.hands[0], g.last_play, g.last_play_player,
                                   0, g.landlord)
                if play is None and g.last_play is not None:
                    app.on_pass()
                else:
                    if play is None:
                        play = [g.hands[0][0]]
                    app.selected = set(play)
                    app.on_play()
        else:
            app.ai_turn()
        root.update()

    print(f'最终状态: phase={app.game.phase}, '
          f'winner={app.game.winner}, 步数={safety}')
    if app.game.phase != app.game.PHASE_END:
        sys.exit(1)
    root.destroy()
    print('GUI 冒烟测试通过')


if __name__ == '__main__':
    main()
