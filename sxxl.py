import os
import time

import aiofiles
import aiohttp
import asyncio
from lxml import etree


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, down_path='', ):
        self.headers = {
            'Host': 'www.sxxl.com',
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
            # 'Cookie': 'loginInfo=71236369f18a4e030621331449; CAU1233DC1FFZ=bGFnaJuVm57JZJ2aaspnlGRtZ5KWZGeVbJ0=; lastViewCategory=6; screenWidth=1920; Hm_lvt_1=1667887500; Hm_flag=1667887500063147638; Hm_flagall=1667887500063147638; Hm_session=16678875000630.14763826423156656; Hm_lvt_a3b242930672e1d3dd7781c8cd80b09a=1667887500; lastViewChannel=2085; __ad_view=5; __ad_date=1667891357; Hm_lpvt_1=1667891358; Hm_lpvt_a3b242930672e1d3dd7781c8cd80b09a=1667891359'
        }

        self.data = {"p": "1"}
        self.num = 0
        if down_path == "":
            if 'downpic' not in os.listdir('.'):  # 当前目录下的downpic目录
                os.mkdir('downpic')
            self.path = os.path.join(os.path.abspath('.'), 'downpic')
            os.chdir(self.path)  # 进入文件下载路径

        self.down_path = down_path

        self.urls = {
            'https://www.sxxl.com/BigPatter-index-cid-6-channel-2085.html': '女装_大牌图案',
            'https://www.sxxl.com/VectorGallery-index-cid-6-channel-2085-sex-32940.html': '女装_矢量图库',
            'https://www.sxxl.com/PatternGallery-index-cid-6-channel-2085.html': '女装_图案图库',
            'https://www.sxxl.com/PatternBook-index-cid-6-channel-2085.html': '女装_图案书刊',
            'https://www.sxxl.com/CowboyAccessories-index-cid-6-channel-2085.html': '女装_牛仔辅料',
            'https://www.sxxl.com/BigPatter-index-cid-6-channel-2084.html': '男装_大牌图案',
            'https://www.sxxl.com/VectorGallery-index-cid-6-channel-2084-sex-32939.html': '男装_矢量图库',
            'https://www.sxxl.com/PatternGallery-index-cid-6-channel-2084.html': '男装_图案图库',
            'https://www.sxxl.com/PatternBook-index-cid-6-channel-2084.html': '男装_图案书刊',
            'https://www.sxxl.com/CowboyAccessories-index-cid-6-channel-2084.html': '男装_牛仔辅料',
            'https://www.sxxl.com/BigPatter-index-cid-6-channel-2086.html': '童装_大牌图案',
            'https://www.sxxl.com/VectorGallery-index-cid-6-channel-2086-sex-109697.html': '童装_矢量图库',
            'https://www.sxxl.com/PatternGallery-index-cid-6-channel-2086.html': '童装_图案图库',
            'https://www.sxxl.com/PatternBook-index-cid-6-channel-2086.html': '童装_图案书刊',
        }

        self.url = [*self.urls][0]
        self.limit = 10  # tcp连接数
        self.page = 0
        self.sleep = 2  # 每页抓取间隔时间
        self.headers['Cookie'] = (self.getcookie(self.url))

    def getcookie(self, url):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url)
            cookie = context.cookies()
            # ---------------------
            context.close()
            browser.close()
            cookie = ';'.join([f'{eh["name"]}={eh["value"]}' for eh in cookie])
            return cookie

    async def run(self, startpage, endpage):
        org_endpage = endpage
        async with aiohttp.TCPConnector(limit=self.limit) as conn:  # 限制tcp连接数
            async with aiohttp.ClientSession(connector=conn, headers=self.headers, ) as session:
                for eh_url, pictype in self.urls.items():  # 对每个网址进行爬取
                    self.url = eh_url
                    self.page = 0
                    if org_endpage == 0:  # 如果是0那么全爬取
                        async with session.get(f'{self.url}?&p=1') as respone:
                            r = await respone.text()
                            el = etree.HTML(r)
                            totalpagep = '//*[@id="page"]/div/a[@class="page-item"]'
                            totalpage = el.xpath(totalpagep)[-1].xpath('./text()')[0]
                            endpage = int(totalpage)
                            print(f'总页数：{endpage}页  类型:{pictype} 网址：{self.url}')

                    for pagen in range(startpage, endpage + 1):
                        async with session.get(f'{self.url}?&p={pagen}') as respone:
                            r = await respone.text()
                            el = etree.HTML(r)
                            xpath = '//*[@id="js-list"]/li/div/div[1]/a/img/@src'
                            urls = (el.xpath(xpath))
                            tasks = [self._get_content(ehurl) for ehurl in urls]
                            await asyncio.gather(*tasks, return_exceptions=True)
                            self.page += 1
                            print(f'已下载第{self.page}页。 类型:{pictype} ')
        print(f'共下载{self.num}张图片')

    async def _get_content(self, link, ):  # 传入的是图片连接

        # async with semaphore:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url=link) as response:
                    content = await response.read()
                await self._write_img(link.split('/')[-1], content)
            except (asyncio.TimeoutError, ClientPayloadError):
                pass

    async def _write_img(self, file_name, content):
        file_name = os.path.join(self.down_path, file_name)
        async with aiofiles.open(file_name, 'wb') as f:
            await f.write(content)
            # print('下载第%s张图片成功' % self.num)
            self.num += 1


if __name__ == '__main__':
    start_time = time.perf_counter()
    down_path = r'D:\Download'
    startpage = 1
    endpage = 0  # 如果是0，那么全爬取
    spider = Spider(down_path)
    # print(spider.urls)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.run(startpage, endpage, ))
    print(f'总用时：{time.perf_counter() - start_time:.0f}秒')
