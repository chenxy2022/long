import os
import time
from io import BytesIO

import aiohttp
import asyncio
import requests
from PIL import Image
from lxml import etree


# import pandas as pd


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    如果想给文件名加前缀，只要在目录下加前缀就行，比如:r'd:\test\abc',那么生成的文件前面都有abc
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, down_path=''):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
        }
        self.num = 0
        if down_path == "":
            if 'downpic' not in os.listdir('.'):  # 当前目录下的downpic目录
                os.mkdir('downpic')
            self.path = os.path.join(os.path.abspath('.'), 'downpic')
            os.chdir(self.path)  # 进入文件下载路径

        self.down_path = down_path
        self.url = 'https://apps.wow-trend.com/api/trend/picture/get-list'
        self.params = {'nav_id': '35', 'gender_id': '72105', 'size': '60', 'page': '1', 'attrs': '[]'}

    def get_img_links(self, page, get_total_page=False):  # 获取图片连接
        self.params['page'] = str(page)
        # try:
        print('正在爬取页数：', page)
        r = requests.get(url=self.url, headers=self.headers, params=self.params)
        result = r.json()
        if get_total_page: return result['data']['totalPage']  # 获取总页数
        urls_info = result['data']['list']
        print('本页{}张图片'.format(len(urls_info)))
        return urls_info
        # except Exception as e:
        #     print(e)

    async def get_sub_img_links(self, url):  # 获取大图图片连接
        # print(url)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            r = await session.get(url)
            rtext = await r.text()
            el = etree.HTML(rtext)
            # 获取作者信息
            author_path = '//*[@id="__next"]/div/main/div[1]/div/div[3]/div[1]/div[1]/span[2]/a'
            author = el.xpath(author_path)[0]
            author_name = author.xpath('./text()')[0]
            author_code = author.xpath('./@href')[0].split('/')[-1]
            author_info = f'{author_name}_{author_code}'
            # print(author_info)
            # 获取作者信息结束

            pic_xpath = '//*[@id="__next"]/div/main/div[1]/div/div[2]/div/div[1]/figure/img/@data-src'
            await self.__download_img(el.xpath(pic_xpath)[0], crop=True, prefix=author_info)

    def _write_img(self, file_name, content):
        # if not crop:
        file_name_resize = os.path.join(self.down_path, '略缩图', file_name)
        self._resize_image(BytesIO(content), outfile=file_name_resize)
        # else:
        file_name_crop = os.path.join(self.down_path, '裁剪图', file_name)
        self._img_crop(BytesIO(content), output_fullname=file_name_crop)
        self.num += 1

    async def _get_content(self, link, filename=False):  # 传入的是图片连接
        if link.startswith('//'): link = f'https:{link}'
        async with aiohttp.ClientSession() as session:
            # try:
            async with session.get(url=link) as response:
                content = await response.read()
            extend = link.split('.')[-1]

            if filename:
                filename = f'{filename}.{extend}'
            else:
                filename = f'{self.num}.{extend}'
            self._write_img(filename, content)
        # except (asyncio.TimeoutError, ClientPayloadError):
        #     pass

    def run(self, startpage=1, endpage=1):
        """
        q:要查询的内容
        startpange:开始爬取的页面，默认为1
        endpage:结束页数，默认为1,如果此参数为0，那么就会下载全部页面的图片
        """
        start = time.time()
        if endpage == 0:
            endpage = self.get_img_links(1, get_total_page=True)
            print(f'总页数:{endpage}')

        for page in range(startpage, endpage + 1):  # 下载一百页的图片就能够了，或者本身更改页数
            picurls = self.get_img_links(page)  # 把那一页须要爬图片的连接传进去
            # print(picurls)
            if picurls:
                # tasks = [asyncio.ensure_future(self.__download_img(picurl)) for picurl in picurls]
                tasks_crop = [asyncio.ensure_future(self._get_content(d['big_path'], d['id'])) for d in picurls]
                loop = asyncio.get_event_loop()
                loop.run_until_complete(asyncio.gather(*tasks_crop, return_exceptions=False))
            end = time.time()
            print(f"共运行了{(end - start):.0f}秒")

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

        self._resize_image(转换, outfile=output_fullname, is_file=False)


def main():
    down_path = r'd:\download'
    spider = Spider(down_path)
    spider.run(startpage=1, endpage=0)
    print(f'共下载图片：{spider.num}')


if __name__ == '__main__':
    main()
