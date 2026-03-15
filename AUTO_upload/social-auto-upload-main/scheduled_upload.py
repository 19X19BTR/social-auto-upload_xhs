# -*- coding: utf-8 -*-
"""
定时发布任务脚本 - 每天7点发布一个视频到4个平台
使用: python scheduled_upload.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from conf import BASE_DIR as CONF_BASE_DIR
from utils.files_times import get_title_and_hashtags

# 导入各平台上传模块
from uploader.douyin_uploader.main import douyin_setup, DouYinVideo
from uploader.ks_uploader.main import ks_setup, KSVideo
from uploader.tencent_uploader.main import weixin_setup, TencentVideo
from uploader.xiaohongshu_uploader.main import xiaohongshu_setup, XiaoHongShuVideo
from utils.constant import TencentZoneTypes

# 配置
VIDEOS_DIR = Path(CONF_BASE_DIR) / "videos"
PUBLISH_HOUR = 7  # 每天7点发布

# Cookie 文件路径
COOKIE_PATHS = {
    "douyin": Path(CONF_BASE_DIR) / "cookies" / "douyin_uploader" / "account.json",
    "kuaishou": Path(CONF_BASE_DIR) / "cookies" / "ks_uploader" / "account.json",
    "tencent": Path(CONF_BASE_DIR) / "cookies" / "tencent_uploader" / "account.json",
    "xiaohongshu": Path(CONF_BASE_DIR) / "cookies" / "xiaohongshu_uploader" / "account.json"
}


def get_video_list():
    """获取视频列表（按文件名排序）"""
    files = sorted(VIDEOS_DIR.glob("*.mp4"))
    return files


def get_publish_date(day_offset: int) -> datetime:
    """计算发布时间（明天开始 + day_offset天，每天7点）"""
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    publish_date = tomorrow + timedelta(days=day_offset)
    return publish_date.replace(hour=PUBLISH_HOUR, minute=0)


async def upload_to_douyin(video_file: Path, title: str, tags: list, publish_date: datetime):
    """上传到抖音"""
    try:
        print(f"[抖音] 开始上传: {video_file.name}")
        account_file = COOKIE_PATHS["douyin"]
        app = DouYinVideo(title, video_file, tags, publish_date, account_file)
        await app.main()
        print(f"[抖音] 上传成功: {video_file.name}")
        return True
    except Exception as e:
        print(f"[抖音] 上传失败: {video_file.name}, 错误: {e}")
        return False


async def upload_to_kuaishou(video_file: Path, title: str, tags: list, publish_date: datetime):
    """上传到快手"""
    try:
        print(f"[快手] 开始上传: {video_file.name}")
        account_file = COOKIE_PATHS["kuaishou"]
        app = KSVideo(title, video_file, tags, publish_date, account_file)
        await app.main()
        print(f"[快手] 上传成功: {video_file.name}")
        return True
    except Exception as e:
        print(f"[快手] 上传失败: {video_file.name}, 错误: {e}")
        return False


async def upload_to_tencent(video_file: Path, title: str, tags: list, publish_date: datetime):
    """上传到视频号"""
    try:
        print(f"[视频号] 开始上传: {video_file.name}")
        account_file = COOKIE_PATHS["tencent"]
        category = TencentZoneTypes.LIFESTYLE.value
        app = TencentVideo(title, video_file, tags, publish_date, account_file, category)
        await app.main()
        print(f"[视频号] 上传成功: {video_file.name}")
        return True
    except Exception as e:
        print(f"[视频号] 上传失败: {video_file.name}, 错误: {e}")
        return False


async def upload_to_xiaohongshu(video_file: Path, title: str, tags: list, publish_date: datetime):
    """上传到小红书"""
    try:
        print(f"[小红书] 开始上传: {video_file.name}")
        account_file = COOKIE_PATHS["xiaohongshu"]
        # 小红书使用立即发布（0表示立即发布）
        app = XiaoHongShuVideo(title, video_file, tags, 0, account_file)
        await app.main()
        print(f"[小红书] 上传成功: {video_file.name}")
        return True
    except Exception as e:
        print(f"[小红书] 上传失败: {video_file.name}, 错误: {e}")
        return False


async def upload_video_to_all_platforms(video_file: Path, day_index: int):
    """上传一个视频到所有平台"""
    # 获取标题和标签
    title, tags = get_title_and_hashtags(str(video_file))
    publish_date = get_publish_date(day_index)
    
    print(f"\n{'='*60}")
    print(f"准备发布第 {day_index + 1} 天视频: {video_file.name}")
    print(f"发布时间: {publish_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"标题: {title}")
    print(f"标签: {tags}")
    print(f"{'='*60}\n")
    
    # 同时上传到4个平台
    tasks = [
        upload_to_douyin(video_file, title, tags, publish_date),
        upload_to_kuaishou(video_file, title, tags, publish_date),
        upload_to_tencent(video_file, title, tags, publish_date),
        upload_to_xiaohongshu(video_file, title, tags, publish_date)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 统计结果
    success_count = sum(1 for r in results if r is True)
    print(f"\n发布完成: {success_count}/4 个平台成功\n")
    
    return success_count


async def setup_all_cookies():
    """初始化所有平台的cookie"""
    print("正在初始化各平台登录状态...\n")
    
    setups = []
    
    # 抖音
    if COOKIE_PATHS["douyin"].exists():
        print("[抖音] 检查登录状态...")
        setups.append(douyin_setup(COOKIE_PATHS["douyin"], handle=False))
    
    # 快手
    if COOKIE_PATHS["kuaishou"].exists():
        print("[快手] 检查登录状态...")
        setups.append(ks_setup(COOKIE_PATHS["kuaishou"], handle=False))
    
    # 视频号
    if COOKIE_PATHS["tencent"].exists():
        print("[视频号] 检查登录状态...")
        setups.append(weixin_setup(COOKIE_PATHS["tencent"], handle=True))
    
    # 小红书
    if COOKIE_PATHS["xiaohongshu"].exists():
        print("[小红书] 检查登录状态...")
        setups.append(xiaohongshu_setup(COOKIE_PATHS["xiaohongshu"], handle=False))
    
    if setups:
        await asyncio.gather(*setups, return_exceptions=True)
    
    print("\n登录状态检查完成\n")


async def main():
    """主函数 - 执行7天发布计划"""
    print("="*60)
    print("社交媒体定时发布工具")
    print("="*60)
    
    # 获取视频列表
    videos = get_video_list()
    if not videos:
        print("错误: videos 目录中没有找到 .mp4 文件")
        return
    
    print(f"\n找到 {len(videos)} 个视频文件")
    for i, v in enumerate(videos, 1):
        print(f"  {i}. {v.name}")
    
    # 初始化cookie
    await setup_all_cookies()
    
    # 确认发布
    print("\n" + "="*60)
    print("发布计划:")
    print("="*60)
    for i, video in enumerate(videos[:7]):
        pub_date = get_publish_date(i)
        print(f"第 {i+1} 天 ({pub_date.strftime('%Y-%m-%d %H:%M')}): {video.name}")
    
    print("\n注意: 请确保已在Chrome浏览器登录各平台创作者中心")
    print("按 Ctrl+C 取消，或等待 5 秒后开始发布...")
    
    # 等待确认
    await asyncio.sleep(5)
    
    # 开始发布
    print("\n" + "="*60)
    print("开始执行发布任务")
    print("="*60 + "\n")
    
    for day_index, video_file in enumerate(videos[:7]):
        await upload_video_to_all_platforms(video_file, day_index)
        
        # 每个视频之间间隔一些时间，避免过于频繁
        if day_index < len(videos[:7]) - 1:
            print("等待 10 秒后发布下一个...\n")
            await asyncio.sleep(10)
    
    print("\n" + "="*60)
    print("所有视频发布任务已完成!")
    print("="*60)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)
