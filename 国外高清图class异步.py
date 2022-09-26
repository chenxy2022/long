import time, asyncio
from playwright.async_api import async_playwright
import re
import contextlib


class Play_get_pic:
    def __init__(self, picurl, sem=6):
        self.picurl = picurl  # 判断需要下载的图片网址链接
        self.num = 0
        self.sem = sem

    async def pageon(self, browser, url, sem):
        async with sem:
            async def handle_response(response):
                if (response.ok and response.request.resource_type == "image"  # it is of type image
                ):
                    with contextlib.suppress(Exception):
                        if self.picurl in response.url:
                            filename = re.findall(r'\w+.jpg', response.url)[0]
                            self.num += 1
                            filename = f'./picdown/{self.num}_{filename}'
                            with open(filename, 'wb') as f:
                                f.write(await response.body())
                                # print(filename)
                                await page.close()

            page = await browser.new_page()
            page.on("response", handle_response)
            with contextlib.suppress(Exception):
                await page.goto(url)

    async def run(self, urls):
        async with async_playwright() as playwright:
            driver = playwright.firefox  # or "firefox" or "webkit". not use chromium
            browser = await driver.launch(headless=False)
            sem = asyncio.Semaphore(self.sem)
            if isinstance(urls, str):
                urls = [urls]
            tasks = (asyncio.create_task(self.pageon(browser, ehurl, sem)) for ehurl in urls)
            await asyncio.gather(*tasks)


async def main(urls, picurl):
    myclass = Play_get_pic(picurl)
    start_t = time.perf_counter()
    await myclass.run(urls)
    print(f'共下载{myclass.num}张图片，耗时：{time.perf_counter() - start_t:.0f}秒。')


if __name__ == '__main__':
    '''只要把需要下载图片的网页的网址组成列表，传入main就行'''
    picurl = 'https://i.pinimg.com/originals' # 判断需要下载的图片网址验证
    urls = 'https://www.pinterest.ca/pin/140806230194462/' # 可以传递列表

    asyncio.run(main(urls, picurl))
