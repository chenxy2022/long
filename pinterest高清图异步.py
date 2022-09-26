import asyncio
import contextlib
import time, os

from playwright.async_api import async_playwright


class Play_get_pic:
    def __init__(self, url, picurl, down_path, sem=2, show=False):
        self.picurl = picurl  # 判断需要下载的图片网址链接
        self.num = 0
        self.sem = sem
        self.url = url
        self.start_t = time.perf_counter()
        self.down_path = down_path
        self.show = show

    async def pagegetpic(self, browser, url, sem):
        async with sem:
            async def handle_response(response):
                if (response.ok and response.request.resource_type == "image"  # it is of type image
                ):
                    # with contextlib.suppress(Exception):
                    # print(self.picurl)

                    if self.picurl in response.url:
                        # print(response.url)
                        firstname = url.split('/')[-2]
                        shortname = f'{firstname}.{response.url.split(".")[-1]}'
                        filename = os.path.join(self.down_path, shortname)
                        with open(filename, 'wb') as f:
                            f.write(await response.body())
                            # print(filename)
                            self.num += 1
                            print(f'已经下载:{self.num}张。耗时：{time.perf_counter() - self.start_t:.0f}秒')
                            await page.close()

            page = await browser.new_page()
            page.on("response", handle_response)
            with contextlib.suppress(Exception):
                await page.goto(url)
                await page.wait_for_selector(
                    '//*[@id="mweb-unauth-container"]/div/div/div[2]/div[3]/div/div/div/div/div[1]/div/div/div/div/div/div[2]/div/img')

    async def run(self):
        async with async_playwright() as playwright:
            driver = playwright.firefox  # or "firefox" or "webkit". not use chromium
            browser = await driver.launch(headless=not self.show)
            sem = asyncio.Semaphore(self.sem)
            await self.geturls(browser, sem)

    async def geturls(self, browser, sem):
        page = await browser.new_page()
        await page.goto(self.url)

        num = 0
        allurls = []
        for i in range(999):  # 翻页的次数
            await page.wait_for_load_state('networkidle', )
            await page.wait_for_timeout(1000)
            suburls = await page.query_selector_all('//a[contains(@href,"/pin/")]')
            base_url = '/'.join(self.url.split('/')[:3])
            suburls = [base_url + await x.get_attribute("href") for x in suburls]
            # oldlen = len(allurls)  # 保存原来的数量
            p_list = []  # 要处理的列表
            for eh in suburls:
                if eh in allurls: continue  # 网址重复那么取下一个网址
                allurls.append(eh)
                p_list.append(eh)
            # print(len(p_list))
            if p_list:
                num += len(p_list)
                print(f'图片张数：{num}')
                await page.keyboard.press('PageDown')
                tasks = (self.pagegetpic(browser, ehurl, sem) for ehurl in p_list)
                await asyncio.gather(*tasks)
            else:
                await page.keyboard.press('PageDown')


async def main(q, down_path):
    url = f'https://www.pinterest.ca/search/pins/?q={q}'
    picurl = 'https://i.pinimg.com/originals'
    myclass = Play_get_pic(url, picurl, down_path)
    myclass.sem = 3  # 开几个窗口同时爬图片，我网络不行只能开3个
    myclass.show = False  # 是否显示浏览器
    await myclass.run()


if __name__ == '__main__':
    '''
    程序是死循环，需要手工停止，如果长时间没有出现任何提示信息说明：
    1、网络断了
    2、数据爬完了
    '''
    q = "孔雀鱼"  # 要查询的关键字
    down_path = r'e:\download'
    asyncio.run(main(q, down_path))
