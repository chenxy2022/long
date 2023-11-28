import os
import time
from io import BytesIO

import aiohttp
import asyncio
import piexif
import 文件操作大全
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
        self.url = 'https://www.freepik.com/search?format=search&page={}&query={}'
        self.limit = 25  # tcp连接数
        self.page = 0
        self.sleep = 2  # 每页抓取间隔时间
        self.CONCURRENCY = 20  # 同时下载图片的个数
        self.origin = True  # 是否下载原图
        self.prefix = 'freepik编号'  # 文件名的前缀
        self.addtag = True  # 是否将网址写入备注

    async def run(self, startpage, endpage, q):
        print(f'开始下载:"{q}"')
        async with aiohttp.TCPConnector(limit=self.limit, ssl=False, ) as conn:  # 限制tcp连接数

            async with aiohttp.ClientSession(connector=conn, headers=self.headers, trust_env=True) as session:
                if endpage == 0:
                    endpage = await self._get_img_links(1, q, session, get_totalpage=True)
                    if endpage is None:
                        endpage = 1
                    print(f'总页数：{endpage}')
                for pagen in range(startpage, endpage + 1):
                    await self._get_img_links(pagen, q, session)
                    await asyncio.sleep(self.sleep)  # 每页间隔时间，太快了，服务器不让抓
                print(f'下载:"{q}" 结束')
                print(f'一共下载成功{self.num}张图片')
                文件操作大全.txt操作.删除txt某一行_方法(r'D:\下载\freepik关键词\全类通用关键词-续.txt', 0)

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

            pic_path = '//*[@id="main"]/div/header/div/div[1]/div/img/@srcset'
            turls = el.xpath(pic_path)[0]
            pic_url = turls.split(',')[-1].split()[0]  # 图片网址(最大的图)
            # urltoname = url.split('/')[-1].split('.')[-2]
            # urltoname = url.replace('https://www.freepik.com', '').replace('/', '@')  # .split('.')[0]
            # print(urltoname,url)

            await self._get_content(pic_url, price=url)

    async def _get_img_links(self, page, q, session, get_totalpage=False):  # 获取图片连接
        url = self.url.format(page, q)

        try:
            async with session.get(url=url, ) as respone:
                r = await respone.text()
                el = etree.HTML(r)

                if get_totalpage:  # 获取总页数
                    totalpagepath = '//span[@class="pagination__pages"]/text()'
                    totalpage = el.xpath(totalpagepath)
                    total_page = int(totalpage[0].replace(',', '')) if totalpage else None
                    return total_page

                path = '//*[@id="main"]/div[3]/div/div[2]/section/figure/div/a/@href'
                page_urls = el.xpath(path)

                # return

                semaphore = asyncio.Semaphore(self.CONCURRENCY)

                getpictasks_large = [self.get_sub_img_links(ehurl, semaphore, session) for ehurl in page_urls]
                await asyncio.gather(*getpictasks_large, return_exceptions=True)

                self.page += 1
                # print(f'下载成功{self.page}页')

        except Exception as e:
            print(e)

    async def _get_content(self, link, price=''):  # 传入的是图片连接
        if link.startswith('//'): link = f'https:{link}'

        async with aiohttp.ClientSession() as session:
            # print(link, price)
            try:
                async with session.get(url=link, ssl=False) as response:
                    # print(link, price)
                    content = await response.read()
                filename = link.split('/')[-1].split('?')[0]
                # print(f'---{link}')

                if price:
                    nprice = price.split("_")[-1].split(".")[0]
                    nprice = f'{self.prefix}{nprice}'
                    filename = f'{nprice}.{filename.split(".")[-1]}'
                    # print(filename)

                await self._write_img(filename, content, tag=price)

            except (asyncio.TimeoutError):
                pass

    async def _write_img(self, file_name, content, tag=""):
        # file_name_old = file_name  # 保存原始文件名
        if self.origin:  # 是否下载原图
            file_name_origin = os.path.join(self.down_path, '原图', file_name)
            # print(file_name)
            ckpath = os.path.dirname(file_name_origin)
            if not os.path.exists(ckpath):
                os.makedirs(ckpath)
            with open(file_name_origin, 'wb') as f:
                f.write(content)
            if self.addtag and tag:
                addtag(file_name_origin, tag)
        # file_name_resize = os.path.join(self.down_path, '略缩图', file_name)                #    不保存缩略图
        # self._resize_image(BytesIO(content), outfile=file_name_resize)

        file_name_crop = os.path.join(self.down_path, '裁剪图', file_name)
        self._img_crop(BytesIO(content), output_fullname=file_name_crop)
        if self.addtag and tag:
            addtag(file_name_crop, tag)
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
            if x2 > 图片宽:
                x1 = 0
                x2 = 图片宽
                y1 = 图片高 - (图片宽 + 图片高 * 0.02)
                y2 = y1 + 图片宽
        elif 比率 > 1.4:  # 横的
            x1 = 图片宽 * 0.02
            y1 = 图片高 * 0.02
            x2 = x1 + 矩形边长
            y2 = y1 + 矩形边长
            if y2 > 图片高:
                y1 = 0
                y2 = 图片高
                x2 = x1 + 图片高

        cropped = img.crop((x1, y1, x2, y2))

        转换 = cropped.convert('RGB')
        self._resize_image(转换, outfile=output_fullname, is_file=False)
        # 转换.save(output_fullname)  # 保存


def addtag(image_path, tag: str):
    if image_path.split(".")[-1].lower() not in ["jpg", 'jpeg']:
        print("不是jpg格式")
        return
    img = Image.open(image_path)  # 读图
    info = img.info
    if info.get("exif") is not None:
        exif_dict = piexif.load(info["exif"])  # 提取exif信息
    else:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
    # 修改 标记信息
    exif_dict["0th"][40092] = tuple(tag.encode("utf-16le"))  # 40092：备注信息 40094：标记
    # 将修改后的Exif数据写回到图片中
    exif_bytes = piexif.dump(exif_dict)
    # outfile = image_path.split(".")[0] + "_new." + image_path.split(".")[1]
    outfile = image_path
    img.save(outfile, exif=exif_bytes, quality=100)
    # 关闭图片
    img.close()


if __name__ == '__main__':
    start_time = time.perf_counter()

    q = r'D:\下载\freepik\全类通用关键词 - 副本.txt'  # 要查询的内容，如果含有.号，那么就按照文件按行查询,否则就按照内容下载
    # q = '苹果'

    down_path = r'D:\下载\freepik\1'
    # down_path=r'd:\download'
    startpage = 1
    endpage = 0  # 如果填写0，那么全部下载
    # endpage = 1  # 如果填写0，那么全部下载
    spider = Spider(down_path)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.filerun(startpage, endpage, q))
    print(f'总用时：{time.perf_counter() - start_time:.0f}秒')
