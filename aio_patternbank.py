import os
import re
import time
from multiprocessing.dummy import Process
from time import sleep

import aiofiles
import aiohttp
import asyncio
import pandas as pd
from aiohttp import ClientPayloadError
from lxml import etree
from tqdm import tqdm


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, down_path='', date=False):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
        }

        self.num = 0
        if down_path == "":
            if 'downpic' not in os.listdir('.'):  # 当前目录下的downpic目录
                os.mkdir('downpic')
            self.path = os.path.join(os.path.abspath('.'), 'downpic')
            os.chdir(self.path)  # 进入文件下载路径

        self.down_path = down_path
        self.url = 'https://patternbank.com/studio'
        self.base_url = 'https://patternbank.com'
        self.params = {'licence': 'all',
                       'page': '1',
                       'per_page': '100', }
        self.limit = 35  # tcp连接数
        self.done = False
        self.page = 0
        self.sub_path = {'-preview-small': '小图',
                         '-preview-large': '大图',
                         '-preview-cropped_large': '超大图'}
        for dir in self.sub_path.values():
            if not os.path.exists(filepath := os.path.join(self.down_path, dir)):
                os.mkdir(filepath)
        self.regex = re.compile('|'.join(self.sub_path.keys()))

    def writecsv(self, filename, colname, value):
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                f.write(colname + '\n')
        with open(filename, 'a') as f:
            f.write(value + '\n')

    async def _get_content(self, link, session):  # 传入的是图片网页(处理单个图片)

        try:
            async with session.get(url=link) as response:
                r = await response.text()
            el = etree.HTML(r)
            if el is not None:
                # # 将编号对应网址写入csv
                #
                bh = re.search(r'https://patternbank.com/([^/]+/designs/\d+)-', link).group(1).replace('/designs/', '-')
                # self.writecsv(os.path.join(self.down_path, '编号对应网址.csv'), '编号,网址',
                #               f"{bh},{link}")

                regex = 'https://[^"]+/uploads/uploaded_files/attachments/[\d/]+original[^"]+-preview-(?:large|cropped_large)\.jpg'
                plist = (re.findall(regex, r))
                if plist:
                    async with aiohttp.ClientSession(headers=self.headers) as session:
                        tasks = []
                        for picsrc in set(plist):
                            bh_name = bh + picsrc.split('/')[-1].lstrip('0123456789')
                            tasks.append(self.downloadone(picsrc, bh_name, session))

                        # tasks = [self.downloadone(picsrc,
                        #                           re.search(r'/(\d+)-', link).group(1) + picsrc.split('/')[-1].lstrip(
                        #                               '0123456789'), session) for picsrc in set(plist)]
                        await asyncio.gather(*tasks, return_exceptions=True)

        except (asyncio.TimeoutError, ClientPayloadError):
            pass

    async def downloadone(self, url, filename, session):
        async with session.get(url=url) as response:
            content = await response.read()
        await self._write_img(filename, content)

    async def _get_img_links(self, page, session):  # 获取图片连接
        self.params['page'] = page

        # print(page)
        try:
            async with session.get(url=self.url, data=self.params) as respone:
                r = await respone.text()
                el = etree.HTML(r)
                path = '//*[@id="main"]/section[1]/div/div[2]/div[3]/div/div/div/a/@href'
                smallpath = '//*[@id="main"]/section[1]/div/div[2]/div[3]/div/div/div/a/img/@src'

                urls = (list(map(lambda x: self.base_url + x, el.xpath(path))))
                getpictasks = [self._get_content(ehurl, session) for ehurl in urls]

                picurls = el.xpath(smallpath)  # 直接获取小图
                picurls = [x.split('?')[0] for x in picurls]
                async with aiohttp.ClientSession(headers=self.headers) as session1:
                    dirctdowns = [
                        self.downloadone(url, url.split('/')[-1], session1) for url in picurls]
                    await asyncio.gather(*dirctdowns, return_exceptions=True)

                await asyncio.gather(*getpictasks, return_exceptions=True)
                self.page += 1

        except Exception as e:
            print(e)

    async def _write_img(self, file_name, content):
        subpath = self.sub_path[self.regex.search(file_name).group()]
        # bh_name = file_name.split('-')[0] + '.' + file_name.split('.')[-1]
        bh_name = self.regex.sub('', file_name, 0)
        file_name = os.path.join(self.down_path, subpath, bh_name)
        async with aiofiles.open(file_name, 'wb') as f:
            await f.write(content)
        # print('下载第%s张图片成功' % self.num)
        # self.que.put(f'下载第{self.num}张图片成功')  # 进度条
        self.num += 1

    async def _get_total_page(self, session):
        async with session.get(url=self.url, params=self.params) as respone:
            r = await respone.text()

            el = etree.HTML(r)
            endpagepath = '//*[@id="main"]//span[@class="last"]/a/@data-linked-page'
            apages = el.xpath(endpagepath)
            if apages:
                self.total_page = int(apages[0])
            else:
                self.total_page = 0
            print(self.total_page)

    async def _group_process(self, urlpagelist, session):
        pagetasks = [asyncio.create_task(self._get_img_links(page, session))
                     for page in urlpagelist]
        # print(urlpagelist)
        await asyncio.gather(*pagetasks, return_exceptions=True)

    # @retry(stop_max_attempt_number=5, wait_fixed=10000)  # 如果出错10秒后重试，最多重试5次
    async def run(self, startpage=1, endpage=1):
        """
        q:要查询的内容
        startpange:开始爬取的页面，默认为1
        endpage:结束页数，默认为1,如果此参数为0，那么就会下载全部页面的图片
        """
        start = time.time()
        self.done = False
        self.num = 0
        self.page = 0
        # self.params['kw'] = q

        async with aiohttp.TCPConnector(limit=self.limit) as conn:  # 限制tcp连接数
            async with aiohttp.ClientSession(connector=conn, headers=self.headers) as session:
                if endpage == 0:
                    await self._get_total_page(session)  # 获得总页数
                    if self.total_page == 0:
                        print('无数据')
                        return
                    endpage = self.total_page

                t = Process(target=self.jdt, args=(startpage, endpage))  # 进度条
                t.daemon = True
                t.start()

                se = pd.Series(list(range(startpage, endpage + 1)))
                n = 5  # 按照多少页进行一组，异步并发操作
                gdf = se.groupby(se.index // n)
                for _, df in gdf:
                    await self._group_process(df.values, session)

        end = time.time()
        self.done = True
        t.join()
        print('共运行了%.2f秒' % (end - start))

    def jdt(self, startpage, endpage):
        bar = tqdm(total=endpage - startpage + 1)
        bar.clear()
        while 1:
            sleep(.1)
            bar.set_description(f'下载第{self.page}页，{self.num}张成功')
            bar.update(self.page - bar.last_print_n)
            if self.done:
                bar.clear()
                bar.set_description(f'下载{self.num}张图片成功')
                bar.update(self.page - bar.last_print_n)
                return


def main():
    down_path = r'D:\Download'
    startpage = 1
    endpage = 1  # 如果填写0，那么全部都下载
    spider = Spider(down_path)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.run(startpage, endpage, ))


if __name__ == '__main__':
    start_time = time.perf_counter()
    main()
    print(f'总用时：{time.perf_counter() - start_time}')
