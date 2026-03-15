# -*- coding: utf-8 -*-
"""
单日发布脚本 - 每天发布一个视频到4个平台
使用: python daily_upload.py <day_index>
  day_index: 0-6，表示第几天（0=第1天）
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
    print(f"发布第 {day_index + 1} 天视频: {video_file.name}")
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


async def main():
    """主函数"""
    # 获取命令行参数
    if len(sys.argv) < 2:
        print("用法: python daily_upload.py <day_index>")
        print("  day_index: 0-6，表示第几天（0=第1天，1=第2天，以此类推）")
        sys.exit(1)
    
    try:
        day_index = int(sys.argv[1])
        if day_index < 0 or day_index > 6:
            print("错误: day_index 必须在 0-6 之间")
            sys.exit(1)
    except ValueError:
        print("错误: day_index 必须是整数")
        sys.exit(1)
    
    print("="*60)
    print(f"社交媒体定时发布 - 第 {day_index + 1} 天")
    print("="*60)
    
    # 获取视频列表
    videos = get_video_list()
    if not videos:
        print("错误: videos 目录中没有找到 .mp4 文件")
        sys.exit(1)
    
    # 检查是否有对应的视频
    if day_index >= len(videos):
        print(f"错误: 第 {day_index + 1} 天的视频不存在（只有 {len(videos)} 个视频）")
        sys.exit(1)
    
    video_file = videos[day_index]
    print(f"\n准备发布: {video_file.name}")
    
    # 执行发布
    success_count = await upload_video_to_all_platforms(video_file, day_index)
    
    print("\n" + "="*60)
    if success_count == 4:
        print(f"✅ 第 {day_index + 1} 天发布任务全部成功!")
    else:
        print(f"⚠️ 第 {day_index + 1} 天发布任务部分成功 ({success_count}/4)")
    print("="*60)
    
    return success_count


if __name__ == '__main__':
    try:
        result = asyncio.run(main())
        sys.exit(0 if result == 4 else 1)
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)
