"""背景音乐播放（Windows MCI，无需第三方依赖）。

用系统自带的 MCI 播放 MP3 等音频并循环。找不到音频文件时静默跳过。
"""
import ctypes
import glob
import os

_ALIAS = 'ddz_bgm'
_playing = False


def _mci(cmd):
    """执行一条 MCI 命令，成功返回 True。"""
    try:
        return ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None) == 0
    except Exception:
        return False


def find_bgm():
    """在常见位置找一个音频文件，返回绝对路径；没有则返回 None。"""
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = [
        os.getcwd(),            # 运行目录（一般把音乐放这里）
        here,                   # game 包目录
        os.path.dirname(here),  # game 的上级目录
    ]
    seen = set()
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for pattern in ('*.mp3', '*.MP3', '*.wav', '*.m4a', '*.flac'):
            for path in glob.glob(os.path.join(d, pattern)):
                ap = os.path.abspath(path)
                if ap not in seen:
                    seen.add(ap)
                    return ap
    return None


def play_bgm(path=None):
    """开始循环播放背景音乐。"""
    global _playing
    stop_bgm()
    path = path or find_bgm()
    if not path or not os.path.exists(path):
        return
    q = os.path.abspath(path).replace('"', '""')
    if _mci(f'open "{q}" type mpegvideo alias {_ALIAS}'):
        _mci(f'play {_ALIAS} repeat')
        _playing = True


def stop_bgm():
    """停止并关闭背景音乐。"""
    global _playing
    _mci(f'close {_ALIAS}')
    _playing = False


def is_playing():
    return _playing


def _mode():
    """查询 MCI 当前播放模式，返回如 'playing'/'stopped' 或空串。"""
    try:
        buf = ctypes.create_unicode_buffer(64)
        r = ctypes.windll.winmm.mciSendStringW(
            f'status {_ALIAS} mode', buf, 64, None)
        if r == 0:
            return buf.value.lower()
    except Exception:
        pass
    return ''


def keep_alive():
    """期望播放但系统已停止时（个别驱动不支持 repeat），重新开始播放。"""
    global _playing
    if _playing and _mode() == 'stopped':
        _mci(f'play {_ALIAS} repeat')
    return _playing
