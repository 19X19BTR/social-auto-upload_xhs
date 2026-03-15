# -*- coding: utf-8 -*-
"""
小红书上传脚本 - 使用新版上传器
"""
import asyncio
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))

from conf import BASE_DIR as CONF_BASE_DIR
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags
from uploader.xiaohongshu_uploader.main_new import XiaoHongShuVideoNew


async def main():
    filepath = Path(CONF_BASE_DIR) / "videos"
    account_file = Path(CONF_BASE_DIR / "cookies" / "xiaohongshu_uploader" / "account.json")
    
    # 获取视频
    files = list(filepath.glob("*.mp4"))
    file_num = len(files)
    
    if file_num == 0:
        print("没有找到视频文件")
        return
    
    # 生成发布时间
    publish_datetimes = generate_schedule_time_next_day(file_num, 1, daily_times=[7])
    
    print(f"找到 {file_num} 个视频")
    print(f"发布时间计划:")
    for i, dt in enumerate(publish_datetimes):
        print(f"  视频{i+1}: {dt}")
    print()
    
    for index, file in enumerate(files):
        title, tags = get_title_and_hashtags(str(file))
        
        print(f"\n{'='*60}")
        print(f"上传视频 {index+1}/{file_num}: {file.name}")
        print(f"标题: {title}")
        print(f"标签: {tags}")
        print(f"发布时间: {publish_datetimes[index]}")
        print(f"{'='*60}\n")
        
        app = XiaoHongShuVideoNew(title, file, tags, publish_datetimes[index], account_file)
        await app.main()
        
        if index < file_num - 1:
            print(f"\n等待 5 秒后上传下一个视频...")
            await asyncio.sleep(5)
    
    print("\n" + "="*60)
    print("所有视频上传完成!")
    print("="*60)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n出错: {e}")
        import traceback
        traceback.print_exc()
