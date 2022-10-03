import os, re
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

    def __init__(self, down_path=''):
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

    async def _get_content(self, link, filename, session):  # 传入的是图片连接
        try:
            response = await session.get(link)
            content = await response.read()
            await self._write_img(filename, content)
        except (asyncio.TimeoutError, ClientPayloadError):
            pass

    async def _get_img_links(self, page, session):  # 获取图片连接
        self.params['p'] = page

        # print(page)
        try:
            async with session.post(url=self.url, data=self.params) as respone:
                d = await respone.json(content_type='text/html')
                # print(page)
                return d
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
        async with session.get(url=self.url, params=self.params) as respone:
            r = await respone.text()
            if re.search('抱歉！没有找到符合条件的相关素材', r):
                print('查不到图片信息')
                self.total_page = None
                return
            apages = re.search(r'<input type="number" id="paging-mini-current".*data-count ="(\d+)"', r).group(1)
            self.total_page = int(apages)
            self.addstr = etree.HTML(r).xpath('//*[@id="page"]/div/a/@href')

    def set_urlpages(self, startpage, endpage):
        if self.addstr:
            addstr = re.search(r'(?:\-\d+){7}\-', self.addstr[0]).group()
            urlpagelist = [
                f'{".".join(url.split(".")[:-1])}{addstr}{page}.html' for page in range(startpage, int(endpage) + 1)]
        else:
            urlpagelist = [url]
        self.urlpagelist = urlpagelist

    async def _group_process(self, startpage, endpage, session):
        pagetasks = [asyncio.create_task(self._get_img_links(page, session))
                     for page in range(startpage, endpage + 1)]
        imgurls = await asyncio.gather(*pagetasks)  # 获取page下的json，json包含图片信息
        # -----------处理返回的数据
        df_imgurls = pd.json_normalize(sum(map(lambda x: x['data']['list'] if x else [], imgurls), []))
        df_imgurls['pic_id'] = ('DVF编号' +
                                df_imgurls['pic_id'] +
                                df_imgurls['pic_url'].str.extract(r'\d+(\.\w+)\?version=')[0]
                                )
        df_imgurls = df_imgurls[['pic_url', 'pic_id']]
        # ------------图片的网址和地址都已经获取

        imgtasks = [asyncio.create_task(
            self._get_content(row['pic_url'], row['pic_id'], session=session))
            for _, row in df_imgurls.iterrows()]
        await asyncio.gather(*imgtasks)

    async def paseurl(self, session):
        # 解析网址，并更新self.url
        async with session.get(url=self.url, params=self.params) as respone:
            d = await respone.json()
            self.url = f'https://www.photophoto.cn/all/{d["pinyin"]}.html'

    async def run(self, q, startpage=1, endpage=1):
        """
        q:要查询的内容
        startpange:开始爬取的页面，默认为1
        endpage:结束页数，默认为1,如果此参数为0，那么就会下载全部页面的图片
        """
        start = time.time()
        self.params['kw'] = q

        # totalnum = (endpage - startpage + 1) * 35
        # if endpage == 0:
        #     [d] = await asyncio.gather(self._get_total_page())
        #     endpage = d['data']['page_total']
        #     totalnum = d['data']['total']  # 总数量
        #     print(f'总页数:{endpage}')
        # t = Process(target=self.jdt, args=(totalnum,))  # 进度条
        # t.daemon = True
        # t.start()

        async with aiohttp.TCPConnector(limit=self.limit) as conn:  # 限制tcp连接数
            async with aiohttp.ClientSession(connector=conn, headers=self.headers) as session:
                await self.paseurl(session)  # 更新网址
                await self._get_total_page(session)  # 获得总页数
                if endpage == 0:
                    endpage = self.total_page
                else:
                    endpage = min(endpage, self.total_page)

                self.set_urlpages() # 生成所有页的列表
                se = pd.Series(range(startpage, endpage + 1))
                n = 10  # 按照多少页进行一组，异步并发操作
                gdf = se.groupby(se.index // n).agg(['first', 'last'])

                return

                # gtasks = [self._group_process(*x, session)
                #           for x in gdf.itertuples(index=False)]
                # await asyncio.gather(*gtasks)

        end = time.time()
        self.done = True
        # t.join()
        print('共运行了%.2f秒' % (end - start))

    def jdt(self, totalnum: int):
        bar = tqdm(total=totalnum)
        while 1:
            sleep(.1)
            bar.set_description(f'下载第{self.num - 1}张图片成功')
            bar.update(self.num - 1 - bar.last_print_n)
            if self.done or bar.last_print_n == totalnum:
                bar.clear()
                bar.set_description(f'下载第{self.num - 1}张图片成功')
                bar.update(self.num - 1 - bar.last_print_n)
                break


def main():
    down_path = r'E:\Download'
    spider = Spider(down_path)
    endpage = 1
    asyncio.run(spider.run(q='泰顺', startpage=1, endpage=endpage))  # 这里填写开始页数和结束页数，如果结束页数写0，那么会全量下载。


if __name__ == '__main__':
    main()
