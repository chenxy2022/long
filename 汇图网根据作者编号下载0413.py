import json
import math
import os
import re
import time
from io import BytesIO

# import aiofiles
import aiohttp
import asyncio
import pandas as pd
from PIL import Image
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
        self.url = 'https://hi.huitu.com/{}/photo/?pagenum={}'
        self.limit = 10  # tcp连接数
        self.page = 0
        self.sleep = 2  # 每页抓取间隔时间
        self.CONCURRENCY = 20  # 同时下载图片的个数

    async def run(self, startpage, endpage, q):
        print(f'开始下载:"{q}"')
        async with aiohttp.TCPConnector(limit=self.limit) as conn:  # 限制tcp连接数
            async with aiohttp.ClientSession(connector=conn, headers=self.headers, ) as session:
                if endpage == 0:
                    endpage = await self._get_img_links(self.url.format(q, 1), session, get_totalpage=True)
                    if endpage is None:
                        endpage = 1
                    print(f'总页数：{endpage}')
                for pagen in range(startpage, endpage + 1):
                    await self._get_img_links(self.url.format(q, pagen), session)
                    await asyncio.sleep(self.sleep)  # 每页间隔时间，太快了，服务器不让抓
                print(f'下载:"{q}" 结束')
                print(f'一共下载成功{self.num}张图片')

    async def filerun(self, startpage, endpage, q):
        if '.' in q:
            try:
                with open(q, 'r', encoding='utf-8') as f:
                    keys = f.readlines()
            except Exception as e:
                with open(q, 'r') as f:
                    keys = f.readlines()
            for ehkey in keys:
                await self.run(startpage, endpage, ehkey.strip())
        else:
            await self.run(startpage, endpage, q)

    async def get_sub_img_links(self, url, semaphore, session):  # 获取大图图片连接
        if not url.startswith('http'):
            url = 'https:' + url

        async with semaphore:
            r = await session.get(url)
            rtext = await r.text()
            el = etree.HTML(rtext)

            type_path = '//*[@class="pic-info-box"]//span/@title'
            pic_type = el.xpath(type_path)[0]  # 图片类型
            price_regex = r'"Price":(\d+).\d\d'
            price = re.search(price_regex, rtext).group(1)  # 价格
            pic_path = '//*[@id="details"]/div[1]/div/div[1]/div[1]/div/div[1]/img/@src'
            pic_url = el.xpath(pic_path)[0]  # 图片网址
            # print(pic_type, price,pic_url)
            await self._get_content(pic_url, price=f'{pic_type}\\汇图网{price}')

    async def _get_img_links(self, page, session, get_totalpage=False):  # 获取图片连接

        try:
            async with session.get(url=page, ) as respone:
                r = await respone.text()
                regex = r'\{.*\}\}'
                s = re.search(regex, r).group()
                d = json.loads(s)
                df = pd.DataFrame(d)
                dresult = df.loc["photo"]["hiStore"]["data"]["searchResult"]
                if get_totalpage:  # 获取总页数
                    totalcount = dresult["totalCount"]
                    total_page = math.ceil(int(totalcount) / 20)
                    return total_page
                df_result = pd.DataFrame(dresult["picList"])
                page_urls = df_result["pageUrl"]

                # 获取类型
                # print(df_small_price)

                semaphore = asyncio.Semaphore(self.CONCURRENCY)
                # getpictasks = [self._get_content(ehurl, semaphore,price=df_small_price[ehurl]) for ehurl in small_urls]
                getpictasks_large = [self.get_sub_img_links(ehurl, semaphore, session) for ehurl in page_urls]
                await asyncio.gather(*getpictasks_large, return_exceptions=True)
                # await asyncio.gather(*getpictasks_large, return_exceptions=True)
                self.page += 1
                print(f'下载成功{self.page}页')

        except Exception as e:
            print(e)

    async def _get_content(self, link, price=False):  # 传入的是图片连接
        if link.startswith('//'): link = f'https:{link}'
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url=link) as response:
                    content = await response.read()
                filename = link.split('_')[-2] + '.jpg'

                if price:
                    filename = f'{price}元{filename}'

                await self._write_img(filename, content)
            except (asyncio.TimeoutError, ClientPayloadError):
                pass

    async def _write_img(self, file_name, content):
        # if not crop:
        file_name_resize = os.path.join(self.down_path, '略缩图', file_name)
        self._resize_image(BytesIO(content), outfile=file_name_resize)
        # else:
        file_name_crop = os.path.join(self.down_path, '裁剪图', file_name)
        self._img_crop(BytesIO(content), output_fullname=file_name_crop)
        self.num += 1

    def _resize_image(self, infile, outfile='', minsize=300, is_file=True):  # 把图片像素改成308
        """修改图片尺寸
        :param infile: 图片源文件
        :param outfile: 输出文件名，如果为空，那么直接修改原图片
        :param minsize: min长宽
        :return:
        """
        im = Image.open(infile) if is_file else infile

        if min(im.size) > minsize:
            x, y = im.size
            if x < y:
                y = int(y * minsize / x)
                x = minsize
            else:
                x = int(x * minsize / y)
                y = minsize
            im = im.resize((x, y), 1)
        if not outfile:
            outfile = infile
        # 如果路径不存在，那么就创建
        ckpath = os.path.dirname(outfile)
        if not os.path.exists(ckpath):
            os.makedirs(ckpath)

        im.save(outfile)

    def _img_crop(self, input_fullname, output_fullname):
        print(output_fullname)
        img = Image.open(input_fullname)
        图片大小 = img.size
        比率 = 图片大小[0] / 图片大小[1]
        图片宽 = 图片大小[0]
        图片高 = 图片大小[1]
        矩形边长 = (((图片宽 / 2) + (图片高 / 2)) * 2) / 4

        # 横形图片矩形高=图片高*0.8v
        x1 = x2 = y1 = y2 = 0
        if 0.7 <= 比率 <= 1.4:
            x1 = 图片宽 * 0.1
            y1 = 图片高 - (矩形边长 + 图片高 * 0.1)
            x2 = x1 + 矩形边长
            y2 = 图片高 - (图片高 * 0.1)
        elif 比率 < 0.7:  # 竖的
            x1 = 图片宽 * 0.05
            y1 = 图片高 - (矩形边长 + 图片高 * 0.02)
            x2 = x1 + 矩形边长
            y2 = 图片高 - (图片高 * 0.02)
        elif 比率 > 1.4:  # 横的
            x1 = 图片宽 * 0.02
            y1 = 图片高 * 0.02
            x2 = x1 + 矩形边长
            y2 = y1 + 矩形边长

        cropped = img.crop((x1, y1, x2, y2))

        转换 = cropped.convert('RGB')
        # 转换.save(output_fullname)
        self._resize_image(转换, outfile=output_fullname, is_file=False)


if __name__ == '__main__':
    start_time = time.perf_counter()
    # q = r'E:\下载\呢图\txt原文件保存\汇图网关键词.txt'  # 要查询的内容,如果含有.号，那么就按照文件按行查询,否则就按照关键字下载
    q = r'd:\download\1.txt'  # 要查询的编号，如果含有.号，那么就按照文件按行查询,否则就按照编号下载
    # down_path = r'T:\汇图网'
    down_path = r'd:\download'
    startpage = 1
    endpage = 0  # 如果填写0，那么全部下载
    spider = Spider(down_path)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.filerun(startpage, endpage, q))
    print(f'总用时：{time.perf_counter() - start_time:.0f}秒')
