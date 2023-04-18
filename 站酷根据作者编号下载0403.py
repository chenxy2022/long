import os
import re
import time
from io import BytesIO

import aiohttp
import asyncio
import requests
from PIL import Image
from lxml import etree


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    如果想给文件名加前缀，只要在目录下加前缀就行，比如:r'd:\test\abc',那么生成的文件前面都有abc
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, down_path='', black=None):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
        }
        self.num = 1
        if down_path == "":
            if 'downpic' not in os.listdir('.'):  # 当前目录下的downpic目录
                os.mkdir('downpic')
            self.path = os.path.join(os.path.abspath('.'), 'downpic')
            os.chdir(self.path)  # 进入文件下载路径
        self.url = 'https://www.hellorf.com/image/contributor/{}'
        self.down_path = down_path
        self.black: list = self.black(black)

    def black(self, black):
        if black is None:
            return []
        with open(black, 'r') as f:
            return [re.search(r'\d+', x).group() for x in f.readlines() if re.search(r'\d+', x)]

    async def __get_content(self, link):  # 传入的是图片连接

        filename = re.findall(r'(\w*\d+\.\w{3,})', link.lower())[0]
        if re.search(r'\d+', filename).group() in self.black:
            print('过滤编号:', re.search(r'\d+', filename).group())
            return

        async with aiohttp.ClientSession(headers=self.headers) as session:
            response = await session.get(link)
            content = await response.read()
            return content, filename

    def get_img_links(self, page, q):  # 获取图片连接
        url_b = 'https://www.hellorf.com'
        url = self.url.format(q)

        params = {'page': str(page), 'tabIndex': '0'}
        try:
            print('正在爬取页数：', page)
            # params['page'] = str(page)
            r = requests.get(url=url, headers=self.headers, params=params)
            # el = etree.HTML(r.text)

            regex = re.compile(
                r'<figure class="sc-8c73fa21-1 kGnrlF"><a title="" href="([^"]+)" target="_blank"><img data-src="([^"]+)" class="lazyload" alt="" title=""/></a></figure>')
            urls_all = regex.findall(r.text)
            urls = [x[1] for x in urls_all]  # 小图的网址
            urls_crop = [f'{url_b}{x[0]}' for x in urls_all]  # 大图的链接
            print('本页{}张图片'.format(len(urls)))
            return urls, urls_crop
        except Exception as e:
            print(e)

    async def get_sub_img_links(self, url, smallurl=''):  # 获取大图图片连接
        '''
        url:获取图片信息具体内容
        smallurl:这是小图的网址，如果没有这个数据，那么就下载大图crop图
        '''
        # print(url)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            r = await session.get(url)
            rtext = await r.text()
            el = etree.HTML(rtext)
            # # 获取作者信息
            # author_path = '//*[@id="__next"]/div/main/div[1]/div/div[3]/div[1]/div[1]/span[2]/a'
            # author = el.xpath(author_path)[0]
            # # author_name = author.xpath('./text()')[0]
            # author_code = author.xpath('./@href')[0].split('/')[-1]
            # author_info = author_code
            # 获取作者信息结束

            # if smallurl:  # 是否下载小图
            await self.__download_img(smallurl, crop=False, )
            # else:
            pic_xpath = '//*[@id="__next"]/div/main/div[1]/div/div[2]/div/div[1]/figure/img/@data-src'

            await self.__download_img(el.xpath(pic_xpath)[0], crop=True, )

    async def __download_img(self, img, crop=False, prefix=''):
        content, file_name = await self.__get_content(img)  # 获取图片的进制文件
        if prefix:  # 文件名是否加前缀
            file_name = f'{prefix}_{file_name}'
        if not crop:
            file_name_orgin = os.path.join(self.down_path, '略缩图', file_name)
            if not os.path.exists(os.path.dirname(file_name_orgin)):
                os.makedirs(os.path.dirname(file_name_orgin))
            with open(file_name_orgin, 'wb') as f:
                f.write(content)
        else:
            file_name_crop = os.path.join(self.down_path, '裁剪图', f'{file_name}')
            # file_name_crop = os.path.join(self.down_path, file_name)
            self._img_crop(BytesIO(content), output_fullname=file_name_crop)
        # print('下载第%s张图片成功' % self.num)
        self.num += 1

    def get_total_page(self, q):
        url = self.url.format(q, )
        pamams = {'page': '1', 'tabIndex': '0'}

        r = requests.get(url=url, headers=self.headers, params=pamams)
        el = etree.HTML(r.text)
        path = '//*[@id="__next"]/div/main/div[2]/div[1]/ul/li[4]/span/text()'
        pages = el.xpath(path)
        if pages:
            pages = pages[0]  # 全部页面
        else:
            pages = '1'
        return int(pages.replace(',', ''))

    def run(self, q, startpage=1, endpage=1):
        """
        q:要查询的用户的额代码
        startpange:开始爬取的页面，默认为1
        endpage:结束页数，默认为1,如果此参数为0，那么就会下载全部页面的图片
        """
        start = time.time()
        if endpage == 0:
            endpage = self.get_total_page(q)
            print(f'总页数:{endpage}')

        for page in range(startpage, endpage + 1):  # 下载一百页的图片就能够了，或者本身更改页数
            # picurls, suburls = self.__get_img_links(page, q)  # 把那一页须要爬图片的连接传进去
            allurls = self.get_img_links(page, q)

            # print(allurls)
            if allurls:
                allurls = list(zip(*allurls))
                # tasks = [asyncio.ensure_future(self.__download_img(picurl)) for picurl in picurls]
                tasks_crop = [asyncio.ensure_future(self.get_sub_img_links(url[1], url[0])) for url in allurls]
                loop = asyncio.get_event_loop()
                loop.run_until_complete(asyncio.gather(*tasks_crop, return_exceptions=True))
            # if self.num >= 10:  # 测试速度使用，如须要下载多张图片能够注释这段代码
            #     break
            end = time.time()
            print('共运行了%s秒' % (end - start))

    def _resize_image(self, infile, outfile='', minsize=240, is_file=True):  # 把图片像素改成308
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
        # ckpath = os.path.dirname(output_fullname)
        # if not os.path.exists(ckpath):
        #     os.makedirs(ckpath)
        # 转换.save(output_fullname)  # 保存


# 关键词 = '圣诞花型'


def main():
    # down_path = r'E:\下载\站酷\{}\站酷编号'.format(关键词)
    down_path = r'd:\download'
    author_code = r'd:\download\站酷作者内部编号.txt'
    # author_code='95a2b3s3968582c'
    black = r'd:\download\过滤.txt'  # 如果不需要过滤这里写None

    spider = Spider(down_path, black=black)

    if '.' not in author_code:
        spider.run(author_code, startpage=1, endpage=0)
    else:
        with open(author_code, 'r', encoding='utf-8') as f:
            codes = [x.strip() for x in f.readlines()]
        for code in codes:
            print(code)
            spider.run(code, startpage=1, endpage=0)


if __name__ == '__main__':
    main()
