import os, re
import chardet
import time
from lxml import etree
import aiofiles
import aiohttp
import asyncio
import pandas as pd
from tqdm import tqdm
from time import sleep
from multiprocessing.dummy import Process
# from queue import Queue
from aiohttp import ClientPayloadError


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, down_path='', date=False):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
            'referer': 'https://www.photophoto.cn/'}
        self.num = 0
        if down_path == "":
            if 'downpic' not in os.listdir('.'):  # 当前目录下的downpic目录
                os.mkdir('downpic')
            self.path = os.path.join(os.path.abspath('.'), 'downpic')
            os.chdir(self.path)  # 进入文件下载路径

        self.down_path = down_path
        self.url = 'https://www.photophoto.cn/search/getKeyWords'
        self.params = dict()
        self.limit = 35  # tcp连接数
        self.done = False
        self.date = date
        self.page = 0

    async def file_to_keysrun(self, q, startpage, endpage, date):
        self.date=date
        if ('.' in q):  # 如果是文件
            with open(q, 'rb', ) as f:  # 判断文本编码
                code=chardet.detect(f.read())['encoding']
            with open(q, 'r', encoding=code) as f:  # 获取关键字
                keys_list = f.readlines()
                keys_list = list(map(str.strip, keys_list))
        else:
            keys_list = [q]  # 如果不是文件也变成列表
        print('关键字:',keys_list)
        for ehq in keys_list:
            await self.run(ehq, startpage, endpage)

    async def _get_content(self, link, session):  # 传入的是图片连接
        try:
            async with session.get(url=link) as response:
                r = await response.text()
            el = etree.HTML(r)
            # print(url)
            # 判断是否jpg格式文档，如果是，那么就不下载
            pictypepath = '//div[@class="download-right-main mt20"]/div[2]/p/text()'
            pictype = el.xpath(pictypepath)[0]
            if 'JPG' in pictype.upper():
                # print(url)
                return 0
            # 判断图片结束
            # 判断上传时间
            uploaddatepath = '//div[@class="download-right-main mt20"]/div/p/text()'
            uploaddate = el.xpath(uploaddatepath)[-2]

            if bool(self.date) and (uploaddate < self.date):
                # print(uploaddate)
                return 0
            # 判断上传时间结束

            picsrc = el.xpath('//*[@id="pic-main"]/@src')[0]
            picsrc = 'https:' + picsrc.replace('https:', '')
            filename = picsrc.split('/')[-1]
            async with session.get(url=picsrc) as response:
                content = await response.read()
            await self._write_img(filename, content)
        except (asyncio.TimeoutError, ClientPayloadError):
            pass

    async def _get_img_links(self, page, session):  # 获取图片连接
        # self.params['p'] = page

        # print(page)
        try:
            async with session.get(url=page) as respone:
                r = await respone.text()
                el = etree.HTML(r)
                urls = el.xpath('//*[@id = "Masonry"]/div/div/div/a/@href')
                urls = ['https:' + x.replace('https:', '') for x in urls]
                # print(urls)
                getpictasks = [self._get_content(ehurl, session) for ehurl in urls]
                await asyncio.gather(*getpictasks)
                self.page += 1

        except Exception as e:
            print(e)

    async def _write_img(self, file_name, content):
        file_name = os.path.join(self.down_path, file_name)
        async with aiofiles.open(file_name, 'wb') as f:
            await f.write(content)
        # print('下载第%s张图片成功' % self.num)
        # self.que.put(f'下载第{self.num}张图片成功')  # 进度条
        self.num += 1

    async def _get_total_page(self, session):
        async with session.get(url=self.url_pase, params=self.params) as respone:
            r = await respone.text()

            apages = re.search(r'<input type="number" id="paging-mini-current".*data-count ="(\d+)"', r)
            if apages:
                self.total_page = int(apages.group(1))
                addstr = etree.HTML(r).xpath('//*[@id="page"]/div/a/@href')
                self.addstr = f'https:{addstr[0]}' if addstr else ''
            else:
                self.total_page = 0

    def set_urlpages(self, startpage, endpage):
        if self.addstr:
            addstr = re.search(r'(?:\-\d+){7}\-', self.addstr).group()
            urlpagelist = [
                f'{".".join(self.url_pase.split(".")[:-1])}{addstr}{page}.html' for page in
                range(startpage, int(endpage) + 1)]
        else:
            urlpagelist = [self.url_pase]
        self.urlpagelist = urlpagelist

    async def _group_process(self, urlpagelist, session):
        pagetasks = [asyncio.create_task(self._get_img_links(page, session))
                     for page in urlpagelist]
        # print(urlpagelist)
        imgurls = await asyncio.gather(*pagetasks)

    async def paseurl(self, session):
        # 解析网址，并更新self.url_pase
        async with session.get(url=self.url, params=self.params) as respone:
            d = await respone.json()
            self.url_pase = f'https://www.photophoto.cn/all/{d["pinyin"]}.html'

    async def run(self, q, startpage=1, endpage=1):
        """
        q:要查询的内容
        startpange:开始爬取的页面，默认为1
        endpage:结束页数，默认为1,如果此参数为0，那么就会下载全部页面的图片
        """
        start = time.time()
        self.done = False
        self.num = 0
        self.page = 0
        self.params['kw'] = q

        async with aiohttp.TCPConnector(limit=self.limit) as conn:  # 限制tcp连接数
            async with aiohttp.ClientSession(connector=conn, headers=self.headers) as session:
                await self.paseurl(session)  # 解析网址
                await self._get_total_page(session)  # 获得总页数
                if self.total_page == 0:
                    print('无数据')
                    return

                if endpage == 0:
                    endpage = self.total_page
                else:
                    endpage = min(endpage, self.total_page)

                t = Process(target=self.jdt, args=(startpage, endpage))  # 进度条
                t.daemon = True
                t.start()

                self.set_urlpages(startpage, endpage)  # 生成所有页的列表
                # print(self.urlpagelist)
                se = pd.Series(self.urlpagelist, index=range(len(self.urlpagelist)))
                n = 5  # 按照多少页进行一组，异步并发操作
                gdf = se.groupby(se.index // n)
                gtasks = [self._group_process(df.values, session) for _, df in gdf]
                await asyncio.gather(*gtasks)

        end = time.time()
        self.done = True
        t.join()
        print('共运行了%.2f秒' % (end - start))

    def jdt(self, startpage, endpage):
        bar = tqdm(total=endpage - startpage + 1)
        bar.clear()
        while 1:
            sleep(.1)
            bar.set_description(f'关键字：{self.params["kw"]}，下载第{self.page}页成功')
            bar.update(self.page - bar.last_print_n)
            if self.done:
                bar.clear()
                bar.set_description(f'下载{self.num}张图片成功')
                bar.update(self.page - bar.last_print_n)
                return


def main():
    down_path = r'E:\Download'
    q = '大牌' # 这里智能判断，如果含有点，那么就按照文件来每行读取，否则就按照单个名称爬取
    startpage = 1
    endpage = 10  # 如果填写0，那么全部都下载
    spider = Spider(down_path)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.file_to_keysrun(q, startpage, endpage,'2021-01-02'))


if __name__ == '__main__':
    main()
