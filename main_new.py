# -*- coding: utf-8 -*-
"""
小红书上传器 - 完全重写版
基于实际页面结构
"""
from datetime import datetime
from playwright.async_api import Playwright, async_playwright
import os
import asyncio

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.log import xiaohongshu_logger


class XiaoHongShuVideoNew(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, thumbnail_path=None):
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        self.thumbnail_path = thumbnail_path

    async def upload(self, playwright: Playwright) -> None:
        # 启动浏览器
        if self.local_executable_path:
            browser = await playwright.chromium.launch(headless=self.headless, executable_path=self.local_executable_path)
        else:
            browser = await playwright.chromium.launch(headless=self.headless)
        
        context = await browser.new_context(
            viewport={"width": 1600, "height": 900},
            storage_state=f"{self.account_file}"
        )
        context = await set_init_script(context)
        page = await context.new_page()
        
        # 1. 打开发布页面
        await page.goto("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video")
        xiaohongshu_logger.info(f'[+]正在上传-------{self.title}.mp4')
        await page.wait_for_url("https://creator.xiaohongshu.com/publish/publish?from=homepage&target=video")
        
        # 2. 上传视频
        xiaohongshu_logger.info('[-] 正在上传视频...')
        await page.locator("div[class^='upload-content'] input[class='upload-input']").set_input_files(self.file_path)
        
        # 等待上传完成
        while True:
            try:
                video = await page.wait_for_selector('video', timeout=3000)
                if video:
                    xiaohongshu_logger.info('[+] 视频上传完成')
                    break
            except:
                pass
            await asyncio.sleep(1)
        
        await asyncio.sleep(2)  # 等待页面稳定
        
        # 3. 填写标题（只填写标题，不添加标签）
        xiaohongshu_logger.info('[-] 正在填写标题...')
        title_filled = await self.fill_title_only(page)
        if not title_filled:
            xiaohongshu_logger.error('[-] 标题填写失败')
        
        await asyncio.sleep(1)
        
        # 4. 添加标签（在标题下方的专门区域）
        xiaohongshu_logger.info('[-] 正在添加标签...')
        tags_added = await self.add_tags_separate(page)
        if not tags_added:
            xiaohongshu_logger.warning('[-] 标签添加失败，跳过')
        
        await asyncio.sleep(1)
        
        # 5. 设置定时发布
        if self.publish_date != 0:
            xiaohongshu_logger.info('[-] 正在设置定时发布...')
            schedule_set = await self.set_schedule(page, self.publish_date)
            if not schedule_set:
                xiaohongshu_logger.warning('[-] 定时发布设置失败')
        
        # 6. 点击发布
        xiaohongshu_logger.info('[-] 正在点击发布按钮...')
        publish_success = await self.click_publish(page)
        
        if publish_success:
            xiaohongshu_logger.success('[-] 视频发布成功')
        else:
            xiaohongshu_logger.error('[-] 视频发布失败')
        
        # 保存cookie
        await context.storage_state(path=self.account_file)
        await asyncio.sleep(2)
        await context.close()
        await browser.close()
    
    async def fill_title_only(self, page):
        """只填写标题，不添加标签"""
        try:
            # 查找标题输入框（通常是第一个 contenteditable 或特定class）
            # 方法1: 查找标题输入区域
            title_input = page.locator('div.plugin.title-container input.d-text, div[data-placeholder*="标题"] [contenteditable="true"], .title-container [contenteditable="true"]')
            if await title_input.count() > 0:
                await title_input.first.click()
                await page.keyboard.press("Control+KeyA")
                await page.keyboard.press("Delete")
                await page.keyboard.type(self.title[:30])
                xiaohongshu_logger.info('  [-] 标题填写成功(方式1)')
                return True
        except Exception as e:
            xiaohongshu_logger.info(f'  [-] 标题方式1失败: {e}')
        
        try:
            # 方法2: 查找所有 contenteditable，找最上面的一个（通常是标题）
            editables = await page.query_selector_all('[contenteditable="true"]')
            if editables:
                # 使用第一个（最上面的）作为标题
                await editables[0].click()
                await page.keyboard.press("Control+KeyA")
                await page.keyboard.press("Delete")
                await page.keyboard.type(self.title[:30])
                # 按Enter移出焦点
                await page.keyboard.press("Enter")
                xiaohongshu_logger.info('  [-] 标题填写成功(方式2)')
                return True
        except Exception as e:
            xiaohongshu_logger.info(f'  [-] 标题方式2失败: {e}')
        
        return False
    
    async def add_tags_separate(self, page):
        """在专门的标签区域添加标签"""
        try:
            # 先点击页面空白处，确保不在标题输入框
            await page.mouse.click(200, 400)
            await asyncio.sleep(0.5)
            
            # 查找"添加话题"按钮或话题输入区域
            # 方法1: 查找话题按钮
            topic_btn = page.locator('button:has-text("添加话题"), span:has-text("添加话题"), div:has-text("#添加话题")')
            if await topic_btn.count() > 0:
                await topic_btn.first.click()
                await asyncio.sleep(0.5)
                for tag in self.tags[:3]:
                    await page.keyboard.type(f"#{tag}")
                    await page.keyboard.press("Space")
                    await asyncio.sleep(0.3)
                xiaohongshu_logger.info(f'  [-] 添加{len(self.tags[:3])}个标签成功(方式1)')
                return True
        except Exception as e:
            xiaohongshu_logger.info(f'  [-] 标签方式1失败: {e}')
        
        try:
            # 方法2: 查找标签输入框（通常在标题下方）
            # 查找包含"话题"或"标签"的输入区域
            tag_inputs = await page.locator('input[placeholder*="话题"], input[placeholder*="标签"], .tag-input, [class*="tag"] input').all()
            for inp in tag_inputs:
                visible = await inp.is_visible()
                if visible:
                    await inp.click()
                    for tag in self.tags[:3]:
                        await page.keyboard.type(f"#{tag}")
                        await page.keyboard.press("Space")
                        await asyncio.sleep(0.3)
                    xiaohongshu_logger.info(f'  [-] 添加{len(self.tags[:3])}个标签成功(方式2)')
                    return True
        except Exception as e:
            xiaohongshu_logger.info(f'  [-] 标签方式2失败: {e}')
        
        return False
    
    async def set_schedule(self, page, publish_date):
        """设置定时发布"""
        try:
            # 等待页面稳定
            await asyncio.sleep(2)
            
            # 查找"定时发布"switch（排除"声明原创"）
            # 方法：查找包含"定时发布"文本的元素，然后点击其旁边的switch
            result = await page.evaluate('''() => {
                // 查找所有包含文本的元素
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                let node;
                while (node = walker.nextNode()) {
                    if (node.textContent.includes('定时发布') && !node.textContent.includes('原创')) {
                        // 找到父元素
                        let parent = node.parentElement;
                        while (parent && parent !== document.body) {
                            // 查找switch
                            const switchEl = parent.querySelector('.d-switch-simulator, .d-switch, input[type="checkbox"]');
                            if (switchEl) {
                                // 如果switch未选中，点击它
                                if (switchEl.tagName === 'INPUT' && !switchEl.checked) {
                                    switchEl.click();
                                    return 'clicked checkbox';
                                } else if (!switchEl.classList.contains('checked')) {
                                    switchEl.click();
                                    return 'clicked switch';
                                }
                                return 'already checked';
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
                return 'not found';
            }''')
            xiaohongshu_logger.info(f'  [-] 定时发布switch: {result}')
            
            if result in ['clicked checkbox', 'clicked switch', 'already checked']:
                # 等待时间选择器出现
                await asyncio.sleep(2)
                
                # 设置时间
                publish_date_str = publish_date.strftime("%Y-%m-%d %H:%M")
                
                # 方法1: 使用用户提供的精确选择器
                try:
                    time_input = page.locator('#publish-container > div.publish-page-container > div.style-override-container.red-theme-override-container > div > div.publish-page-content > div.publish-page-content-settings > div.publish-page-content-settings-content > div.post-time-wrapper > div.date-picker-container > div > div > div > div.d-datepicker-content > div > input')
                    if await time_input.count() > 0:
                        visible = await time_input.is_visible()
                        if visible:
                            await time_input.click()
                            await asyncio.sleep(0.5)
                            await page.keyboard.press("Control+KeyA")
                            await page.keyboard.type(publish_date_str)
                            await page.keyboard.press("Enter")
                            await asyncio.sleep(0.5)
                            
                            # 验证
                            new_value = await time_input.input_value()
                            if publish_date_str[:10] in new_value:
                                xiaohongshu_logger.info(f'  [-] 设置发布时间成功(精确选择器): {new_value}')
                                return True
                except Exception as e:
                    xiaohongshu_logger.info(f'  [-] 精确选择器失败: {e}')
                
                # 方法2: 查找时间输入框（备用）
                try:
                    time_inputs = await page.locator('input.d-text').all()
                    for inp in time_inputs:
                        visible = await inp.is_visible()
                        if visible:
                            # 检查当前值是否包含日期
                            current = await inp.input_value()
                            if current and ('2026' in current or '2025' in current or current == ''):
                                await inp.click()
                                await asyncio.sleep(0.5)
                                await page.keyboard.press("Control+KeyA")
                                await page.keyboard.type(publish_date_str)
                                await page.keyboard.press("Enter")
                                await asyncio.sleep(0.5)
                                
                                # 验证
                                new_value = await inp.input_value()
                                if publish_date_str[:10] in new_value:
                                    xiaohongshu_logger.info(f'  [-] 设置发布时间成功(备用方式): {new_value}')
                                    return True
                except Exception as e:
                    xiaohongshu_logger.info(f'  [-] 备用方式失败: {e}')
                
                # 方法3: 使用JS设置
                js_result = await page.evaluate(f'''() => {{
                    // 尝试使用精确选择器
                    const preciseInput = document.querySelector('#publish-container > div.publish-page-container > div.style-override-container.red-theme-override-container > div > div.publish-page-content > div.publish-page-content-settings > div.publish-page-content-settings-content > div.post-time-wrapper > div.date-picker-container > div > div > div > div.d-datepicker-content > div > input');
                    if (preciseInput) {{
                        preciseInput.value = '{publish_date_str}';
                        preciseInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        preciseInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return 'set precise: ' + preciseInput.value;
                    }}
                    // 备用：查找所有d-text输入框
                    const inputs = document.querySelectorAll('input.d-text');
                    for (let inp of inputs) {{
                        if (inp.offsetParent !== null) {{
                            inp.value = '{publish_date_str}';
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return 'set d-text: ' + inp.value;
                        }}
                    }}
                    return 'not found';
                }}''')
                xiaohongshu_logger.info(f'  [-] JS设置时间: {js_result}')
                return 'set' in js_result
            
            return False
        except Exception as e:
            xiaohongshu_logger.error(f'  [-] 设置定时发布失败: {e}')
            return False
    
    async def click_publish(self, page):
        """点击发布按钮"""
        try:
            # 方法1: 查找发布按钮
            publish_btn = page.locator('button:has-text("发布")')
            if await publish_btn.count() > 0:
                await publish_btn.first.click()
            else:
                # 方法2: JS点击
                await page.evaluate('''() => {
                    const buttons = document.querySelectorAll('button');
                    for (let btn of buttons) {
                        if (btn.innerText.trim() === '发布' && btn.offsetParent !== null) {
                            btn.click();
                            return 'clicked';
                        }
                    }
                    return 'not found';
                }''')
            
            # 等待发布成功
            for i in range(30):
                await asyncio.sleep(2)
                url = page.url
                if 'success' in url or 'content' in url:
                    return True
            
            return False
        except Exception as e:
            xiaohongshu_logger.error(f'  [-] 点击发布失败: {e}')
            return False
    
    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
