import os
import re
import time
import winreg
from io import BytesIO

# import aiofiles
import aiohttp
import asyncio
import requests
# import pandas as pd
from PIL import Image
from lxml import etree


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, down_path='', ):
        proxy = self.get_proxy()
        if not proxy:
            print('请先开代理，然后再运行本程序！')
            return
        self.proxies = f'http://{proxy}'

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
        self.url = 'https://www.istockphoto.com/search/2/image'
        # self.url = 'https://www.istockphoto.com/hk/search/2/image'
        # self.base_url = 'https://www.16pic.com'
        self.limit = 20  # tcp连接数
        self.page = 0
        self.sleep = 10  # 每页抓取间隔时间
        self.CONCURRENCY = 20  # 同时下载图片的个数
        self.origin = True  # 是否下载原图

    @staticmethod
    def get_proxy():
        # 定义注册表路径
        internet_settings_path = r'Software\Microsoft\Windows\CurrentVersion\Internet Settings'
        # 打开 Internet 设置的注册表项
        internet_settings_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, internet_settings_path)
        try:
            # 读取局域网设置
            lan_settings = winreg.QueryValueEx(internet_settings_key, 'AutoConfigURL')[0]
            print('局域网设置:', lan_settings)
            r = requests.get(lan_settings)
            regex = re.compile(r'return "PROXY (\d+\.\d+.\d+\.\d+:\d+)";')
            return (regex.search(r.content.decode()).group(1))
        except Exception:
            pass
        # 关闭注册表项
        winreg.CloseKey(internet_settings_key)

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
        params = {'phrase': q, 'page': str(page)}
        # try:
        async with session.get(url=self.url, params=params, proxy=self.proxies) as respone:
            r = await respone.text()
            el = etree.HTML(r)
            # print(r)

            if get_totalpage:  # 获取总页数
                totalpagepath = '/html/body/div[2]/section/div/main/div/div/div[2]/div[2]/section/span/text()'
                totalpage = el.xpath(totalpagepath)
                total_page = int(totalpage[0].split()[-1].replace(',', '')) if totalpage else None
                return total_page

            path = '/html/body/div[2]/section/div/main/div/div/div[2]/div[2]/div[3]/div/article/a/figure/picture/source/@srcset'
            page_urls = el.xpath(path)
            # print(page_urls)
            # return

            # semaphore = asyncio.Semaphore(self.CONCURRENCY)
            # 直接下载图片
            getpictasks_large = [self._get_content(ehurl, ) for ehurl in page_urls]
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
                async with session.get(url=link, proxy=self.proxies) as response:
                    content = await response.read()
                lastname = link.split('/')[-1].split('?')[0].split('.')[-1]
                firstname = re.search(r'/id/(\d+)/', link).group(1)
                filename = f'{firstname}.{lastname}'
                if price:
                    filename = f'六图网{price.split("_")[-1]}.{filename.split(".")[-1]}'

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
    # 关键字请用英文,线路需要用美国的线路
    q = r'd:\download\1.txt'  # 要查询的内容，如果含有.号，那么就按照文件按行查询,否则就按照内容下载
    # q = 'apple'

    down_path = r'd:\download'
    startpage = 1
    endpage = 3  # 国外网址，访问很不稳定 不建议全爬取。
    spider = Spider(down_path)
    print(spider.proxies)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.filerun(startpage, endpage, q))
    print(f'总用时：{time.perf_counter() - start_time:.0f}秒')
