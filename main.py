"""斗地主游戏入口。

运行方式（在 game 的上级目录下）：
    python game/main.py
或：
    python -m game.main
"""
import ctypes
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.gui import DouDiZhuApp  # noqa: E402


def _enable_dpi_awareness():
    """开启系统级 DPI 感知，让高分辨率屏幕下文字和图案更清晰。"""
    try:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def main():
    _enable_dpi_awareness()
    import tkinter as tk
    root = tk.Tk()
    DouDiZhuApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
