import os
import re

import aiohttp
import asyncio
from lxml import etree


class Match:
    def __init__(self, filepath):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36'
        }
        self.files = self.get_files(filepath)
        self.filter_files = [x for x in self.files if os.path.basename(x).startswith('汇图')]
        self.pic_url = "https://www.huitu.com/photo/show/{}/{}.html"
        self.num = 0
        self.CONCURRENCY = 50

    @staticmethod
    def get_files(filepath):
        return [os.path.join(root, f)
                for root, _, files in os.walk(filepath)
                for f in files]

    def getno(self, filename: str):
        regex = re.compile(r'(\d+)\.[^.]+$')
        r = regex.search(filename)
        if r:
            return r.group(1)

    async def run(self):
        async with aiohttp.ClientSession(headers=self.headers, ) as session:
            semaphore = asyncio.Semaphore(self.CONCURRENCY)
            tasks = [self.subpage(file, semaphore, session) for file in self.filter_files]
            await asyncio.gather(*tasks)

    async def subpage(self, file, semaphore, session):
        no = self.getno(file)
        url = self.pic_url.format(no[:8], no[8:])
        async with semaphore:
            async with session.get(url=url, ) as respone:
                r = await respone.text()
                t = re.search(r'<label>编号：(\d+)', r)
                # print(t)
                if t:
                    # bh = t.group(1)
                    # path = '//*[@id="details"]/div[1]/div/div[1]/div[1]/div/div[1]/img/@src'
                    el = etree.HTML(r)
                    # jpgurl = f'https:{el.xpath(path)[0]}'
                    # bhregex = r'"OriginalPrice":(\d+)\.00'
                    # money = re.search(bhregex, r).group(1)
                    # filename = (f'汇图网{money}元{bh}.{jpgurl.split(".")[-1]}')

                    # 获取作者信息
                    path = '//a[@class="author-name"]'
                    author = el.xpath(path)[0]
                    author_name = author.xpath('./text()')[0]
                    author_code = author.xpath('./@href')[0].split('/')[-2]
                    # 获取作者信息结束

                    userinfo = f'{author_name}_{author_code}'
                    filename_new = os.path.join(os.path.dirname(file), f'{userinfo}_{os.path.basename(file)}')
                    os.rename(file, filename_new)
                    self.num += 1


if __name__ == '__main__':
    file_path = r'D:\汇图网'
    match = Match(file_path)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(match.run())
    print(f'修改了文件数:{match.num}')
