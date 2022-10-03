import asyncio
import contextlib
import time, os
from multiprocessing.dummy import Process
from playwright.async_api import async_playwright


class Play_get_pic:
    def __init__(self, down_path, sem=2, show=False):
        self.picurl = 'https://i.pinimg.com/originals'  # 判断需要下载的图片网址链接
        self.num = 0
        self.sem = sem
        self.url_format = 'https://www.pinterest.ca/search/pins/?q={}'
        self.start_t = time.perf_counter()
        self.down_path = down_path
        self.show = show
        self.next = False  # 是否应该中断标志符

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
                            print(f'{self.q}，已经下载:{self.num}张。耗时：{time.perf_counter() - self.start_t:.0f}秒')
                            await page.close()

            page = await browser.new_page()
            page.on("response", handle_response)
            with contextlib.suppress(Exception):
                await page.goto(url)
                await page.wait_for_selector(
                    '//*[@id="mweb-unauth-container"]/div/div/div[2]/div[3]/div/div/div/div/div[1]/div/div/div/div/div/div[2]/div/img')

    async def run(self, q, is_file=None):
        if ('.' in q) and (is_file is None):  # is_file 无参数传入，并且查询内容含有点，那么按照文件名处理
            is_file = True

        if is_file:  # 如果是文件
            with open(q, 'r', encoding='utf-8') as f:  # 获取关键字
                keys_list = f.readlines()
                keys_list = map(str.strip, keys_list)
        else:
            keys_list = [q]  # 如果不是文件也变成列表

        async with async_playwright() as playwright:
            driver = playwright.firefox  # or "firefox" or "webkit". not use chromium
            browser = await driver.launch(headless=not self.show)
            sem = asyncio.Semaphore(self.sem)
            for ehkey in keys_list:
                self.q = ehkey
                self.url = self.url_format.format(ehkey)
                self.next = False  # 重置中断标记
                await self.geturls(browser, sem)

    async def geturls(self, browser, sem):
        page = await browser.new_page()
        await page.goto(self.url)

        num = 0
        allurls = []
        for i in range(999):  # 翻页的次数
            if self.next: return  # 长时间没有数据，那么就退出循环
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
            if p_list:
                num += len(p_list)
                print(f'图片张数：{num}')
                await page.keyboard.press('PageDown')
                tasks = (self.pagegetpic(browser, ehurl, sem) for ehurl in p_list)
                await asyncio.gather(*tasks)
            else:
                await page.keyboard.press('PageDown')

    def dinshi(self, timev):
        time.sleep(30)  # 启动时间设定为20秒
        while 1:
            old = self.num
            time.sleep(timev)
            numadd = self.num - old
            # print(f'期间爬取：{numadd}')
            if numadd == 0:
                self.next = True  # 标记中断标记
                print(f'{timev}秒内无数据下载，爬取下一个')


async def main(q, down_path):
    myclass = Play_get_pic(down_path)
    myclass.sem = 3  # 开几个窗口同时爬图片，我网络不行只能开3个
    myclass.show = False  # 是否显示浏览器
    timev =  60 *5  # 监测间隔时间(秒)，如果超过这个时间间隔没有下载数据，那么就下载下一个或者结束。
    t = Process(target=myclass.dinshi, args=(timev,))
    t.daemon = True
    t.start()
    await myclass.run(q)


if __name__ == '__main__':
    '''
    查询内容如果包括.那么就按照文件处理，打开文件根据文件内容逐个下载
    根据时间间隔判断，时间间隔内如果无数据下载，那么就认为已经下载完了
    '''
    q = "keys.txt"  # 要查询的关键字，如果查询内容包含.那么就认为传入的是文件名
    down_path = r'e:\download'
    asyncio.run(main(q, down_path))
