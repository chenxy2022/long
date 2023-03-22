import os
import time

import aiofiles
import aiohttp
import asyncio
from retrying import retry


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, down_path='', ):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
        }

        self.data = {"type": "1", "choose_type": "", "page": "1", "size": "20"}
        self.num = 0
        if down_path == "":
            if 'downpic' not in os.listdir('.'):  # 当前目录下的downpic目录
                os.mkdir('downpic')
            self.path = os.path.join(os.path.abspath('.'), 'downpic')
            os.chdir(self.path)  # 进入文件下载路径

        self.down_path = down_path
        self.url = "https://www.yituhuitu.com/api/newapi/SourceMaterial/index"
        self.beforeurl = 'https://admin.yituhuitu.com/'
        self.limit = 10  # tcp连接数
        self.page = 0
        self.sleep = 0  # 每页抓取间隔时间
        # self.headers['Cookie']=(self.getcookie(self.url[:-6]))

    def getcookie(self, url):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url)
            cookie = context.cookies()
            # ---------------------
            context.close()
            browser.close()
            cookie = ';'.join([f'{eh["name"]}={eh["value"]}' for eh in cookie])
            return cookie

    @retry(stop_max_attempt_number=5, wait_fixed=10000)  # 如果出错10秒后重试，最多重试5次
    async def run(self, startpage, endpage):
        async with aiohttp.TCPConnector(limit=self.limit) as conn:  # 限制tcp连接数
            async with aiohttp.ClientSession(connector=conn, headers=self.headers, ) as session:
                if endpage == 0:
                    async with session.post(self.url, data=self.data) as respone:
                        r = await respone.json(content_type='text/html')
                        ncount = r["data"]["count"]
                        page_list = r["data"]["page_limit"]
                        total_page = ncount // int(page_list) + 1 if ncount % int(page_list) else 0
                        endpage = total_page
                        print(f'总页数：{total_page}')
                data = self.data
                for pagen in range(startpage, endpage + 1):
                    data.update({'page': str(pagen)})
                    async with session.post(self.url, data=data) as respone:
                        r = await respone.json(content_type='text/html')
                        # print(r)
                        urls = r['data']['archivesInfo']
                        # print((urls))
                        # 开始爬一页图片
                        tasks = [self._get_content(link) for link in urls]
                        await asyncio.gather(*tasks, return_exceptions=True)
                        await asyncio.sleep(self.sleep)  # 每页间隔时间，太快了，服务器不让抓
                        self.page += 1
                        print(f'爬取{self.page}页成功')

        print(f'一共下载成功{self.num}张图片')

    async def _get_img_links(self, page, session):  # 获取图片连接

        try:
            data = {'p': str(page)}
            async with session.get(url=self.url, data=data) as respone:
                r = await respone.text()
                print(r)
                # urls = r['data']
                # CONCURRENCY = 20
                # semaphore = asyncio.Semaphore(CONCURRENCY)
                # getpictasks = [self._get_content(ehurl, semaphore) for ehurl in urls]
                # await asyncio.gather(*getpictasks, return_exceptions=True)
                self.page += 1
                print(f'下载成功{self.page}页')

        except Exception as e:
            print(e)

    async def _get_content(self, link, ):  # 传入的是图片连接
        if link['litpic'].startswith('/'):
            link['litpic'] = self.beforeurl + link['litpic']
        # async with semaphore:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url=link['litpic']) as response:
                    content = await response.read()
                await self._write_img(f"{link['aid']}.{link['litpic'].split('.')[-1]}", content)
            except (asyncio.TimeoutError, ClientPayloadError):
                pass

    async def _write_img(self, file_name, content):
        file_name = os.path.join(self.down_path, file_name)
        # file_name += '.jpg'
        async with aiofiles.open(file_name, 'wb') as f:
            await f.write(content)
            # print('下载第%s张图片成功' % self.num)
            self.num += 1


if __name__ == '__main__':
    start_time = time.perf_counter()
    down_path = r'D:\Download'
    startpage = 1
    endpage = 0  # 0默认全部爬取
    spider = Spider(down_path)

    types = ['1', '2']  # 对应 新款图案浏览 满印图案浏览
    # 原创付费爆款 要vip，无法爬取
    for ehtype in types:
        spider.data['type'] = ehtype
        loop = asyncio.get_event_loop()
        loop.run_until_complete(spider.run(startpage, endpage, ))
    print(f'总用时：{time.perf_counter() - start_time:.0f}秒')
