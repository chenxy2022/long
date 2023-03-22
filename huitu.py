import os
import re
import time

import aiofiles
import aiohttp
import asyncio
from lxml import etree


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, down_path='', ):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
        }
        # self.params = dict()
        self.num = 0
        if down_path == "":
            if 'downpic' not in os.listdir('.'):  # 当前目录下的downpic目录
                os.mkdir('downpic')
            self.path = os.path.join(os.path.abspath('.'), 'downpic')
            os.chdir(self.path)  # 进入文件下载路径

        self.down_path = down_path
        self.url = 'https://soso.huitu.com/?kw={}&page={}'
        self.limit = 10  # tcp连接数
        self.page = 0
        self.sleep = 2  # 每页抓取间隔时间
        self.CONCURRENCY = 20  # 并发数

    async def run(self, startpage, endpage, q):
        print(f'开始下载:"{q}"')
        async with aiohttp.TCPConnector(limit=self.limit) as conn:  # 限制tcp连接数
            async with aiohttp.ClientSession(connector=conn, headers=self.headers, ) as session:
                for pagen in range(startpage, endpage + 1):
                    await self._get_img_links(self.url.format(q, pagen), session)
                    await asyncio.sleep(self.sleep)  # 每页间隔时间，太快了，服务器不让抓
                print(f'下载:"{q}" 结束')
                print(f'一共下载成功{self.num}张图片')

    async def filerun(self, startpage, endpage, q):
        if '.' in q:
            try:
                with open(q, 'r') as f:
                    keys = f.readlines()
            except:
                with open(q, 'r', encoding='utf-8') as f:
                    keys = f.readlines()
            for ehkey in keys:
                await self.run(startpage, endpage, ehkey.strip())
        else:
            await self.run(startpage, endpage, q)

    async def _get_img_links(self, page, session):  # 获取图片连接

        try:
            async with session.get(url=page, ) as respone:
                r = await respone.text()
                el = etree.HTML(r)
                path = '//*[@id="app"]/div/div[1]/div[3]/div/div[4]/div[1]/div[1]/div/div/a/@href'
                path += '|//*[@id="app"]/div/div[1]/div[2]/div/div[4]/div[1]/div[1]/div/div/a/@href'
                urls = [f'https:{x}' for x in el.xpath(path)]
                # print(urls)

                semaphore = asyncio.Semaphore(self.CONCURRENCY)
                # getpictasks = [self._get_content(ehurl, semaphore) for ehurl in urls]
                getpictasks = [self.subpage(ehurl, semaphore, session) for ehurl in urls]
                await asyncio.gather(*getpictasks, return_exceptions=True)
                self.page += 1
                print(f'下载成功{self.page}页')

        except Exception as e:
            print(e)

    async def subpage(self, url, semaphore, session):
        async with semaphore:
            async with session.get(url=url, ) as respone:
                r = await respone.text()
                t = re.search(r'<label>编号：(\d+)', r)
                # print(t)
                if t:
                    bh = t.group(1)
                    path = '//*[@id="details"]/div[1]/div/div[1]/div[1]/div/div[1]/img/@src'
                    el = etree.HTML(r)
                    jpgurl = f'https:{el.xpath(path)[0]}'
                    bhregex = r'"OriginalPrice":(\d+)\.00'
                    money = re.search(bhregex, r).group(1)
                    filename = (f'绘图网{money}元{bh}.{jpgurl.split(".")[-1]}')
                    await self._get_content(jpgurl, filename)

    async def _get_content(self, link, filename):  # 传入的是图片连接

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url=link) as response:
                    content = await response.read()
                await self._write_img(filename, content)
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
    q = 'keys.txt'  # 要查询的内容,如果含有.号，那么就按照文件按行查询,否则就按照关键字下载
    down_path = r'D:\Download'
    startpage = 1
    endpage = 2
    spider = Spider(down_path)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.filerun(startpage, endpage, q))
    print(f'总用时：{time.perf_counter() - start_time:.0f}秒')
