import os
import time
from io import BytesIO

# import aiofiles
import aiohttp
import asyncio
from PIL import Image
from lxml import etree


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(
        self,
        down_path="",
    ):
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36"
        }
        # self.params = dict()
        self.num = 0
        if down_path == "":
            if "downpic" not in os.listdir("."):  # 当前目录下的downpic目录
                os.mkdir("downpic")
            self.path = os.path.join(os.path.abspath("."), "downpic")
            os.chdir(self.path)  # 进入文件下载路径

        self.down_path = down_path
        self.url = "https://www.sucai999.com/default/search/lists?keyword={}"
        self.base_url = "https://www.sucai999.com"
        self.limit = 25  # tcp连接数
        self.page = 0
        self.sleep = 2  # 每页抓取间隔时间
        self.CONCURRENCY = 20  # 同时下载图片的个数
        self.origin = True  # 是否下载原图
        self.url_transed = False  # 是否需要解析网址
        self.true_url = ""
        self.end = False

    async def run(self, startpage, endpage, q):
        print(f'开始下载:"{q}"')
        async with aiohttp.TCPConnector(
            limit=self.limit,
            ssl=False,
        ) as conn:  # 限制tcp连接数

            async with aiohttp.ClientSession(
                connector=conn, headers=self.headers, trust_env=True
            ) as session:
                if endpage == 0:
                    endpage = 99999
                # return
                for pagen in range(startpage, endpage + 1):
                    if self.end:
                        return  # 如果没有数据了就返回
                    await self._get_img_links(pagen, q, session)
                    await asyncio.sleep(self.sleep)  # 每页间隔时间，太快了，服务器不让抓
                print(f'下载:"{q}" 结束')
                print(f"一共下载成功{self.num}张图片")

    async def filerun(self, startpage, endpage, q):
        if "." in q:
            try:
                with open(q, "r", encoding="utf-8") as f:
                    keys = f.readlines()
            except Exception as e:
                with open(q, "r") as f:
                    keys = f.readlines()
            for ehkey in keys:
                self.url_transed = False  # 重置url解析
                self.end = False  # 初始化是否结束
                await self.run(startpage, endpage, ehkey.strip())
        else:
            await self.run(startpage, endpage, q)

    async def get_sub_img_links(self, url, semaphore, session):  # 获取大图图片连接
        if not url.startswith("http"):
            url = "https:" + url
        # print(url,'getsub')
        async with semaphore:
            r = await session.get(url)
            rtext = await r.text()
            el = etree.HTML(rtext)

            # 图片的网址存在不同的xpath
            pic_path = (
                '//*[@class="imgbox"]/a/img/@src|//*[@class="detail_img"]/img/@src'
            )

            pic_url = el.xpath(pic_path)
            # print(url,pic_url)

            # pic_url = turls.split(',')[-1].split()[0]  # 图片网址(最大的图)
            urltoname = url.split("/")[-1].split(".")[-2]
            if pic_url:
                pic_url = pic_url[0]
                await self._get_content(pic_url, price=urltoname)

    async def trans_url(self, page, q, session):
        """网址转换"""
        url = self.url.format(q)
        async with session.get(
            url=url,
        ) as respone:
            tran_url = respone.url
            return tran_url

    async def _get_img_links(self, page, q, session, get_totalpage=False):  # 获取图片连接
        if not self.url_transed:
            self.true_url = await self.trans_url(page, q, session)
            if not self.true_url:
                return
            self.url_transed = True
            url = self.true_url
        else:
            url = str(self.true_url).replace(".html", f"-{page}.html")

        try:
            async with session.get(
                url=url,
            ) as respone:
                r = await respone.text()
                el = etree.HTML(r)

                if get_totalpage:  # 获取总页数
                    totalpagepath = '//*[@id="top_page"]/../text()'
                    totalpage = el.xpath(totalpagepath)
                    total_page = (
                        int(totalpage[0].split()[-1].replace(",", ""))
                        if totalpage
                        else None
                    )
                    return total_page

                path = '//*[@id="flow"]/li/figure/a/@href'
                page_urls = [
                    x if x.startswith(self.base_url) else f"{self.base_url}{x}"
                    for x in el.xpath(path)
                ]
                if not page_urls:
                    self.end = True  # 如果获取不到数据那么就将结束标志为True
                    print(f"累计爬取{self.page}页，{self.num}张图")
                    return
                # print(page_urls,'aaa')
                # return

                semaphore = asyncio.Semaphore(self.CONCURRENCY)

                getpictasks_large = [
                    self.get_sub_img_links(ehurl, semaphore, session)
                    for ehurl in page_urls
                ]
                await asyncio.gather(*getpictasks_large, return_exceptions=True)

                self.page += 1
                print(f"下载成功{self.page}页")

        except Exception as e:
            print(e)

    async def _get_content(self, link, price=""):  # 传入的是图片连接
        if link.startswith("//"):
            link = f"https:{link}"
        # print(link)
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url=link) as response:
                    content = await response.read()
                filename = link.split("/")[-1].split("?")[0]

                if price:
                    filename = f'六图网{price}.{filename.split(".")[-1]}'

                await self._write_img(filename, content)
            except (asyncio.TimeoutError,):
                pass

    async def _write_img(self, file_name, content):
        if self.origin:  # 是否下载原图
            file_name_origin = os.path.join(self.down_path, "原图", file_name)
            ckpath = os.path.dirname(file_name_origin)
            if not os.path.exists(ckpath):
                os.makedirs(ckpath)
            with open(file_name_origin, "wb") as f:
                f.write(content)
        # file_name_resize = os.path.join(self.down_path, '略缩图', file_name)
        # self._resize_image(BytesIO(content), outfile=file_name_resize)

        file_name_crop = os.path.join(self.down_path, "裁剪图", file_name)
        self._img_crop(BytesIO(content), output_fullname=file_name_crop)
        self.num += 1

    def _resize_image(
        self, infile, outfile="", minsize=300, is_file=True
    ):  # 把图片像素改成308
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

        转换 = cropped.convert("RGB")
        # 转换.save(output_fullname)
        self._resize_image(转换, outfile=output_fullname, is_file=False)


if __name__ == "__main__":
    start_time = time.perf_counter()

    q = r"d:\download\1.txt"  # 要查询的内容，如果含有.号，那么就按照文件按行查询,否则就按照内容下载
    # q = '小龙虾'

    down_path = r"d:\download"
    startpage = 1
    endpage = 0  # 如果填写0，那么全部下载
    spider = Spider(down_path)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.filerun(startpage, endpage, q))
    print(f"总用时：{time.perf_counter() - start_time:.0f}秒")
