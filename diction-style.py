import time,os

import aiohttp
import asyncio

from playwright.async_api import Playwright, async_playwright


async def down_img(urls, session):
    global i
    try:
        async with session.get(url=urls) as respone:
            r = await respone.read()
            filename = urls.split('_-_-')[-1]
            downpath=r'd:\download' # 下载的路径
            filename= os.path.join(downpath,filename)
            with open(filename, 'wb') as f:
                f.write(r)
            i += 1
    except Exception:
        pass


async def run(playwright: Playwright, start_page, end_page) -> None:
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context()
    # Open new page
    page = await context.new_page()

    imgpath = '//*[@id="app"]/div[1]/div[2]/div[2]/div[1]/div/ul//a/img'
    url = "https://www.diction-style.com/list/pattern/channel/20850/column/141378/p/{}"

    imgurls = []

    async def pagep(pagenum):
        pageurl = url.format(pagenum)
        print('正在爬取:', pageurl)
        # page = await context.new_page()
        await page.goto(pageurl)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(1000)
        for _ in range(5):
            await page.keyboard.press('End')
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(1000)
        el = await page.query_selector_all(imgpath)
        imglinks = [await x.get_attribute('src') for x in el]
        # await page.close()
        imgurls.extend(imglinks)
        tasks = [down_img(links, session) for links in imglinks]
        await asyncio.gather(*tasks,return_exceptions=True)

    async with aiohttp.ClientSession() as session:
        # pagetasks=[]

        for pagenum in range(start_page, end_page + 1):
            # pagetasks.append(pagep(pagenum))
            # await asyncio.gather(*pagetasks)
            await pagep(pagenum)

    await context.close()
    await browser.close()
    return imgurls


async def main() -> None:
    async with async_playwright() as playwright:
        start_page = 1  # 开始页面
        end_page = 5  # 结束页面
        urls = await run(playwright, start_page, end_page)
        print('一共爬取：', len(urls))


if __name__ == '__main__':
    st = time.perf_counter()
    i = 1
    asyncio.run(main())
    print('用时：', time.perf_counter() - st)
