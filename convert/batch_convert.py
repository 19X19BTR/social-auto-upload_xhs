#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量选片转码器 —— 完整版
作者：Kimi
"""
import os
import sys
import shutil
import subprocess
import signal
from pathlib import Path
from typing import List
import threading

INPUT_DIR = Path(".\convert\input")
OUTPUT_DIR = Path(".\convert\output")
OUTPUT_DIR.mkdir(exist_ok=True)
PAGE_SIZE = 10

# ---------- 预设 ----------
PRESETS = {
    1: {"name": "mp4(H.264)", "ext": "mp4", "vcodec": "libx264", "acodec": "aac"},
    2: {"name": "mp4(H.265)", "ext": "mp4", "vcodec": "libx265", "acodec": "aac"},
    3: {"name": "mkv(H.264)", "ext": "mkv", "vcodec": "libx264", "acodec": "copy"},
    4: {"name": "avi(Xvid)",  "ext": "avi", "vcodec": "libxvid", "acodec": "mp3"},
    5: {"name": "mov(H.264)", "ext": "mov", "vcodec": "libx264", "acodec": "aac"},
    6: {"name": "gif",        "ext": "gif", "vcodec": "gif",     "acodec": "none"},
}

FFMPEG = shutil.which("ffmpeg")
if not FFMPEG:
    sys.exit("ffmpeg 不在 PATH！")

# ---------- 全局退出标志 ----------
STOP = threading.Event()
def handler(signum, frame):
    STOP.set()
signal.signal(signal.SIGINT, handler)

# ---------- 选片语法解析 ----------
def parse_choice(raw: str, max_n: int) -> List[int]:
    raw = raw.strip()
    if not raw:
        return []
    idx_set = set()
    for part in raw.split(','):
        part = part.strip()
        if '-' in part:
            # 前缀 -5
            if part.startswith('-') and part.count('-') == 1:
                end = int(part[1:])
                if end < 1 or end > max_n:
                    raise ValueError(f'前缀区间 {part} 超出范围')
                idx_set.update(range(0, end))
                continue
            # 后缀 5-
            if part.endswith('-') and part.count('-') == 1:
                start = int(part[:-1])
                if start < 1 or start > max_n:
                    raise ValueError(f'后缀区间 {part} 超出范围')
                idx_set.update(range(start - 1, max_n))
                continue
            # 普通范围 3-7
            start_str, end_str = part.split('-', 1)
            start = int(start_str)
            end = int(end_str)
            if start > end or start < 1 or end > max_n:
                raise ValueError(f'区间 {part} 超出范围')
            idx_set.update(range(start - 1, end))
        else:
            # 单点
            idx = int(part)
            if idx < 1 or idx > max_n:
                raise ValueError(f'序号 {part} 超出范围')
            idx_set.add(idx - 1)
    return sorted(idx_set)

# ---------- 分页 ----------
def paginate(files: List[Path]) -> List[Path]:
    total = len(files)
    page = 0
    while True:
        start = page * PAGE_SIZE
        end = min(start + PAGE_SIZE, total)
        print(f"\n===== 第 {page+1} 页 / 共 {(total+PAGE_SIZE-1)//PAGE_SIZE} 页 =====")
        for i in range(start, end):
            pos = i + 1
            print(f"{pos:>3}  {files[i].name}")   # ← 已去掉负数列
        print("[n] 下页  [p] 上页  [q] 退出选片  直接输入序号/范围")
        choice = input(">>> ").strip()
        if choice == "n":
            page = (page + 1) % ((total + PAGE_SIZE - 1) // PAGE_SIZE)
        elif choice == "p":
            page = (page - 1) % ((total + PAGE_SIZE - 1) // PAGE_SIZE)
        elif choice.lower() == "q":
            return []
        else:
            try:
                idxs = parse_choice(choice, total)
                return [files[i] for i in idxs]
            except ValueError as e:
                print(e)
    total = len(files)
    page = 0
    while True:
        start = page * PAGE_SIZE
        end = min(start + PAGE_SIZE, total)
        print(f"\n===== 第 {page+1} 页 / 共 {(total+PAGE_SIZE-1)//PAGE_SIZE} 页 =====")
        for i in range(start, end):
            pos = i + 1
            neg = i - total
            print(f"{pos:>3}  {files[i].name}")
        print("[n] 下页  [p] 上页  [q] 退出选片  直接输入序号/范围")
        choice = input(">>> ").strip()
        if choice == "n":
            page = (page + 1) % ((total + PAGE_SIZE - 1) // PAGE_SIZE)
        elif choice == "p":
            page = (page - 1) % ((total + PAGE_SIZE - 1) // PAGE_SIZE)
        elif choice.lower() == "q":
            return []
        else:
            try:
                idxs = parse_choice(choice, total)
                return [files[i] for i in idxs]
            except ValueError as e:
                print(e)

# ---------- 选格式 ----------
def choose_preset():
    print("\n===== 目标格式 =====")
    for k, v in PRESETS.items():
        print(f"{k}  {v['name']}")
    while True:
        try:
            fmt = int(input("请选择格式（1-{}）：".format(len(PRESETS))))
            if fmt in PRESETS:
                return PRESETS[fmt]
        except ValueError:
            pass

# ---------- 转码 ----------
def convert_one(src: Path, preset: dict) -> Path:
    dst = OUTPUT_DIR / f"{src.stem}.{preset['ext']}"
    cmd = [FFMPEG, "-i", str(src), "-vcodec", preset["vcodec"]]
    if preset["acodec"] != "none":
        cmd += ["-acodec", preset["acodec"]]
    cmd += ["-y", str(dst)]

    print(f"\n开始：{src.name}")
    print(" ".join(cmd), "\n")          # 可选：打印完整命令
    # 实时输出
    try:
        subprocess.run(cmd, check=True)
        print(f"完成：{dst}")
        return dst
    except subprocess.CalledProcessError:
        print(f"失败：{src.name}")
        return None

# ---------- 主流程 ----------
def main():
    files = [p for p in INPUT_DIR.iterdir() if p.is_file()]
    if not files:
        sys.exit("input 文件夹里没有文件！")
    chosen = paginate(files)
    if not chosen:
        print("未选择任何文件，拜拜！")
        return
    preset = choose_preset()
    print("\n转换中，随时 Ctrl+C 或 q 再确认 y 即可退出")
    done: List[Path] = []
    for src in chosen:
        if STOP.is_set():
            break
        dst = convert_one(src, preset)
        if dst:
            done.append(dst)
    if STOP.is_set():
        if input("\n已按退出，确认终止？ y/n ").lower() == 'y':
            print("用户终止，已转完的文件：")
        else:
            STOP.clear()
            for src in chosen[len(done):]:
                dst = convert_one(src, preset)
                if dst:
                    done.append(dst)
    print("\n========== 汇总 ==========")
    for d in done:
        print(d)

if __name__ == "__main__":
    main()