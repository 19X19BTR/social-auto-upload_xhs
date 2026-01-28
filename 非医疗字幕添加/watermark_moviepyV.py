#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竖排中文水印 + 保留原音轨 + 页码选择 + q/y/n 退出
纯 Python 方案（moviepy + PIL），不依赖 ffmpeg 可执行文件
"""
import os, sys, threading, queue
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2   # 仅用来捕获键盘，不处理视频
from moviepy.editor import VideoFileClip
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip

# ------------------ 用户可调 ------------------
SRC_DIR = Path(r'D:\SMB\Vscodeproject\非医疗字幕添加\Videos')
OUT_DIR = Path(r'D:\SMB\Vscodeproject\非医疗字幕添加\output')
TEXT = '护肤品研发师非医疗'
TTF_FONT = r'C:\Windows\Fonts\simhei.ttf'
FONT_SIZE = 60
LEFT_M = 30
TOP_M = 100
TEXT_RGB = (255, 255, 255)
SHADOW_RGB = (0, 0, 0)
STROKE_WIDTH = 3
# ----------------------------------------------

VIDEO_EXTS = {'.mp4', '.mov', '.mkv', '.avi', '.flv', '.wmv', '.m4v', '.3gp'}

# ============ 键盘监听（同你原来） ============
if os.name == 'nt':
    import msvcrt
    def kb_hit(): return msvcrt.kbhit()
    def get_ch(): return msvcrt.getwch()
else:
    try:
        from pynput import keyboard
        _abort_flag, _listener = False, None
        def _on_press(key):
            global _abort_flag
            try:
                if key.char and key.char.lower() == 'q': _abort_flag = True
            except: pass
        _listener = keyboard.Listener(on_press=_on_press); _listener.start()
        def kb_hit(): return _abort_flag
        def get_ch(): return 'q' if _abort_flag else ''
    except ImportError:
        def kb_hit(): return False
        def get_ch(): return ''

# ============ 单帧画水印 ============
font = ImageFont.truetype(TTF_FONT, FONT_SIZE)
line_h = FONT_SIZE + 8

def add_text_to_frame(frame: np.ndarray) -> np.ndarray:
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    chars = list(TEXT)
    for idx, ch in enumerate(chars):
        y = TOP_M + idx * line_h
        for dx in range(-STROKE_WIDTH, STROKE_WIDTH + 1):
            for dy in range(-STROKE_WIDTH, STROKE_WIDTH + 1):
                if dx == 0 and dy == 0: continue
                draw.text((LEFT_M + dx, y + dy), ch, font=font, fill=SHADOW_RGB)
        draw.text((LEFT_M, y), ch, font=font, fill=TEXT_RGB)
    return np.asarray(img)

# ============ 单文件处理 ============
def process_video(src_path: Path, dst_path: Path) -> bool:
    print(f'[INFO] 开始处理：{src_path.name}')
    print('     按 q 可随时暂停，确认后退出将删除半成品...')
    # 读入
    clip = VideoFileClip(str(src_path))
    # 逐帧加水印
    def process_frame(get_frame, t):
        frame = get_frame(t)
        if kb_hit() and get_ch().lower() == 'q':
            raise KeyboardInterrupt   # 抛到外层去处理
        return add_text_to_frame(frame)
    try:
        processed = clip.fl(process_frame, apply_to=['video'])
        # 写文件；codec='libx264' 用机器自带的 x264，不需要外部 ffmpeg
        processed.write_videofile(str(dst_path),
                                  codec='libx264',
                                  audio_codec='aac',  # 会同时把原音轨写进去
                                  verbose=False, logger=None)
    except KeyboardInterrupt:
        print('\n>>> 检测到 q，暂停...')
        while True:
            yn = input('>>> 确认退出?(y/n) ').strip().lower()
            if yn == 'y':
                if dst_path.exists(): dst_path.unlink()
                print('[EXIT] 已删除半成品')
                return False
            elif yn == 'n':
                print('>>> 继续处理...')
                break
            else:
                print('请输入 y 或 n')
        # 继续，重新启动写入
        processed.write_videofile(str(dst_path),
                                  codec='libx264',
                                  audio_codec='aac',
                                  verbose=False, logger=None)
    print(f'[DONE] 已保存（含音频）：{dst_path.name}')
    return True

# ============ 页码选择（同你原来） ============
def parse_choice(raw: str, max_n: int) -> list[int]:
    raw = raw.strip()
    if not raw: return []
    idx_set = set()
    for part in raw.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            start = int(start) - 1
            end = max_n - 1 if end == '' else int(end) - 1
            if start < 0 or start >= max_n or end < start or end >= max_n:
                raise ValueError(f'区间 {part} 超出范围')
            idx_set.update(range(start, end + 1))
        else:
            idx = int(part) - 1
            if idx < 0 or idx >= max_n: raise ValueError(f'序号 {part} 超出范围')
            idx_set.add(idx)
    return sorted(idx_set)

# ============ 主入口 ============
def main():
    OUT_DIR.mkdir(exist_ok=True)
    videos = sorted([p for p in SRC_DIR.iterdir() if p.suffix.lower() in VIDEO_EXTS])
    if not videos:
        print(f'[WARN] 在 {SRC_DIR.resolve()} 未找到任何视频文件'); return
    for idx, v in enumerate(videos, 1):
        print(f'[{idx:>3}]  {v.name}')
    while True:
        raw = input('\n>>> 请选择要处理的视频（支持  2  5-  1-3  1,3,5-8,10- ）：').strip()
        try:
            choices = parse_choice(raw, len(videos))
            if not choices: print('未选中任何视频，请重新输入！'); continue
            break
        except ValueError as e:
            print('输入错误：', e, ' 请重新输入！')
    for c in choices:
        target = videos[c]
        out_file = OUT_DIR / f'{target.stem}_watermark.mp4'
        ok = process_video(target, out_file)
        if not ok:
            print('[All Abort] 用户主动退出，程序结束。')
            sys.exit(0)
    print(f'\n[All Done] 共处理 {len(choices)} 个视频。')

if __name__ == '__main__':
    main()