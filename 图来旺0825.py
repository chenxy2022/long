import os
import re
import time
from io import BytesIO

# import aiofiles
import aiohttp
import asyncio
# import pandas as pd
from PIL import Image
from lxml import etree


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, cookie: str, down_path='', ):

        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
            'Cookie': cookie,
        }

        self.num = 0
        if down_path == "":
            if 'downpic' not in os.listdir('.'):  # 当前目录下的downpic目录
                os.mkdir('downpic')
            self.path = os.path.join(os.path.abspath('.'), 'downpic')
            os.chdir(self.path)  # 进入文件下载路径

        self.down_path = down_path
        self.url = 'http://tulaiwang.com/index.php?do={do}&page={page}'
        self.limit = 20  # tcp连接数
        self.page = 0
        self.sleep = 5  # 每页抓取间隔时间
        self.CONCURRENCY = 20  # 同时下载图片的个数
        self.origin = True  # 是否下载原图

    async def run(self, startpage, endpage, q):
        print(f'开始下载:"{q}"')
        async with aiohttp.TCPConnector(limit=self.limit, ssl=False, ) as conn:  # 限制tcp连接数

            async with aiohttp.ClientSession(connector=conn, headers=self.headers, trust_env=True, ) as session:
                if endpage == 0:
                    endpage = await self._get_img_links(1, q, session, get_totalpage=True)
                    if endpage is None:
                        endpage = 1
                    print(f'总页数：{endpage}')
                # return
                for pagen in range(startpage, endpage + 1):
                    await self._get_img_links(pagen, q, session)
                    await asyncio.sleep(self.sleep)  # 每页间隔时间，太快了，服务器不让抓
                print(f'下载:"{q}" 结束')
                print(f'一共下载成功{self.num}张图片')

    async def filerun(self, startpage, endpage, q=''):
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

            pic_path = '/html/body/div[3]/div[3]/div[1]/div/div[1]/img/@src'
            pic_url = el.xpath(pic_path)[0]
            # pic_url = turls.split(',')[-1].split()[0]  # 图片网址(最大的图)
            urltoname = url.split('/')[-1].split('.')[-2]
            # print(urltoname,pic_url)
            await self._get_content(pic_url, price=urltoname)

    async def trans_url(self, page, q, session):
        '''网址转换'''
        url = self.url.format(q)
        async with session.get(url=url, ) as respone:
            r = await respone.text()
            tran_url = re.search(r'location\.href = "([^"]+)"', r)
            if not tran_url:
                return
            else:
                tran_url = tran_url.group(1)
            tran_url = tran_url if tran_url.startswith(self.base_url) else f'{self.base_url}{tran_url}'
            # 加入页数参数
            tran_url = re.sub(r'_\d+\.html', f'_{page}.html', tran_url, 0)
            return tran_url

    async def _get_img_links(self, page, q, session, get_totalpage=False):  # 获取图片连接
        # url = await self.trans_url(page, q, session)
        # if not url: return
        params = {'do': 'goodslist', 'page': page}
        url = (self.url.format(**params))
        # print(url)
        # try:
        async with session.get(url=url, ) as respone:
            # print(respone.url)
            r = await respone.text()
            el = etree.HTML(r)
            # print(r)

            if get_totalpage:  # 获取总页数
                totalpagepath = '/html/body/div[8]/div[2]/div/text()'
                totalpage = el.xpath(totalpagepath)
                if totalpage:
                    total_num = int(re.search(r'共 (\d+) 个商品', totalpage[0]).group(1))
                    d, m = divmod(total_num, 28)
                    totalpage = d + bool(m)
                    return totalpage
            path = '//*[@id="container_putu"]/div/div[1]/a/img/@data-original'
            page_urls = el.xpath(path)
            # print(page_urls)

            idpath = '//*[@id="container_putu"]/div/div[1]/a/@href'
            ids = [x.split('=')[-1] for x in el.xpath(idpath)]

            # print(ids)
            # return

            # semaphore = asyncio.Semaphore(self.CONCURRENCY)
            # 直接下载图片
            getpictasks_large = [self._get_content(ehurl, price=id) for ehurl, id in zip(page_urls, ids)]
            await asyncio.gather(*getpictasks_large, return_exceptions=True)

            self.page += 1
            print(f'下载成功{self.page}页')

        # except Exception as e:
        #     print(e)

    async def _get_content(self, link, price=False):  # 传入的是图片连接
        if link.startswith('//'): link = f'https:{link}'
        conn = aiohttp.TCPConnector(limit=self.limit, ssl=False, )
        async with aiohttp.ClientSession(connector=conn, headers=self.headers) as session:
            try:
                async with session.get(url=link, ) as response:
                    content = await response.read()
                lastname = link.split('/')[-1].split('?')[0].split('.')[-1]
                # firstname = re.search(r'/id/(\d+)/', link).group(1)
                # filename = f'{firstname}.{lastname}'
                if price:
                    filename = f'图来旺{price}.{lastname}'

                await self._write_img(filename, content)
            except Exception as e:
                print(e)

    async def _write_img(self, file_name, content):
        if self.origin:  # 是否下载原图
            file_name_origin = os.path.join(self.down_path, '原图', file_name)
            ckpath = os.path.dirname(file_name_origin)
            if not os.path.exists(ckpath):
                os.makedirs(ckpath)
            with open(file_name_origin, 'wb') as f:
                f.write(content)
        # file_name_resize = os.path.join(self.down_path, '略缩图', file_name)
        # self._resize_image(BytesIO(content), outfile=file_name_resize)

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

        img = Image.open(input_fullname)
        img_size = img.size
        ratio = img_size[0] / img_size[1]
        img_width = img_size[0]
        img_high = img_size[1]
        total_length = (((img_width / 2) + (img_high / 2)) * 2) / 4

        # 横形图片矩形高=图片高*0.8v
        x1 = x2 = y1 = y2 = 0
        if 0.7 <= ratio <= 1.4:
            x1 = img_width * 0.1
            y1 = img_high - (total_length + img_high * 0.1)
            x2 = x1 + total_length
            y2 = img_high - (img_high * 0.1)
        elif ratio < 0.7:  # 竖的
            x1 = img_width * 0.05
            y1 = img_high - (total_length + img_high * 0.02)
            x2 = x1 + total_length
            y2 = img_high - (img_high * 0.02)
        elif ratio > 1.4:  # 横的
            x1 = img_width * 0.02
            y1 = img_high * 0.02
            x2 = x1 + total_length
            y2 = y1 + total_length

        cropped = img.crop((x1, y1, x2, y2))

        trans = cropped.convert('RGB')
        # 转换.save(output_fullname)
        self._resize_image(trans, outfile=output_fullname, is_file=False)


if __name__ == '__main__':
    start_time = time.perf_counter()

    # q = r'd:\download\1.txt'  # 要查询的内容，如果含有.号，那么就按照文件按行查询,否则就按照内容下载
    # q = ''

    down_path = r'd:\download'
    startpage = 1
    endpage = 0  # 0 表示全爬
    # cookie必须手动更新
    cookie = "PHPSESSID=bq713id8ll8olcmc2dmhktupdq; keke_auto_login=a%3A3%3A%7Bi%3A0%3Bs%3A8%3A%22MjYwOTU%3D%22%3Bi%3A1%3Bs%3A16%3A%22MTUzMDU3Nzg4MzE%3D%22%3Bi%3A2%3Bs%3A68%3A%22MjYwOTV8M2MxNzU5NGJmMGIzNjE4ZWNkY2QzNTExMWIxYTMyMDR8MTUzMDU3Nzg4MzE%3D%22%3B%7D"
    spider = Spider(cookie, down_path)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.filerun(startpage, endpage))
    print(f'总用时：{time.perf_counter() - start_time:.0f}秒')
