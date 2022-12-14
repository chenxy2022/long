import json
import os
import time
from time import sleep

import aiofiles
import aiohttp
import asyncio
import pandas as pd
from aiohttp import ClientPayloadError
from retrying import retry
from tqdm import tqdm


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, userdata, down_path='', date=False):
        self.headers = {'Host': 'www.mihuiai.com',
                        'Origin': 'http://www.mihuiai.com',
                        'Referer': 'http://www.mihuiai.com/mall',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
                        }
        self.img_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
        }
        self.token = ""
        self.json = {'orderBy': "random", 'isHot': 0, 'sort': "gmtShowHome", 'start': 0, 'isTop': 'false',
                     'limit': 10000,
                     }
        self.num = 0
        if down_path == "":
            if 'downpic' not in os.listdir('.'):  # 当前目录下的downpic目录
                os.mkdir('downpic')
            self.path = os.path.join(os.path.abspath('.'), 'downpic')
            os.chdir(self.path)  # 进入文件下载路径

        self.down_path = down_path
        self.url = "http://www.mihuiai.com/api/resourceManage/queryPattern?_dt={}"
        self.limit = 35  # tcp连接数
        self.done = False
        self.date = date
        self.page = 0
        self.userdata = userdata

    async def get_token(self):
        json = {
            "userType": 4,
            "userTypeExt": 0
        }
        json.update(self.userdata)
        url = 'http://www.mihuiai.com/api/user-login/login'
        headers = {
            "Host": "www.mihuiai.com",
            "Origin": "http://www.mihuiai.com",
            "Referer": "http://www.mihuiai.com/login",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
        }
        async with aiohttp.ClientSession(headers=headers, ) as session:
            async with session.post(url, json=json) as respone:
                r = await respone.json()
                self.token = r['data']['token']
                self.headers['token'] = self.token
                # print(self.token)

    async def _get_content(self, link, session):  # 传入的是图片连接
        try:
            async with session.get(url=link[1]) as response:
                content = await response.read()
            await self._write_img(link[0], content)
        except (asyncio.TimeoutError, ClientPayloadError):
            pass

    async def _get_img_links(self, start, session):  # 获取图片连接
        myjson = self.json
        myjson['start'] = str(start)
        sjc = str(time.time()).replace('.', '')[:13]

        try:
            async with session.post(url=self.url.format(sjc), json=myjson) as respone:
                d = await respone.json()
                df = pd.DataFrame(d['data']['list'])[['serial', 'thumbnailOssPath']]
                df['serial'] = df['serial'] + '.' + df['thumbnailOssPath'].str.split('.').str[-1]
                if df.shape[0] != self.json['limit']: self.done = True  # 判断是否已经爬完
                async with aiohttp.ClientSession(headers=self.img_headers) as session_no_head:
                    getpictasks = [self._get_content(ehurl, session_no_head) for ehurl in
                                   df.itertuples(index=False)]
                    await asyncio.gather(*getpictasks, return_exceptions=True)
                self.page += 1

        except Exception as e:
            print(e)

    async def _write_img(self, file_name, content):
        file_name = os.path.join(self.down_path, file_name)
        async with aiofiles.open(file_name, 'wb') as f:
            await f.write(content)
            # print('下载第%s张图片成功' % self.num)
            self.num += 1

    @retry(stop_max_attempt_number=5, wait_fixed=10000)  # 如果出错10秒后重试，最多重试5次
    async def run(self, startpage=1):
        """
        startpange:开始爬取的页面，默认为1
        """
        print('开始爬数据，请耐心等待！单页爬取模式，无进度条。')
        self.done = False
        self.num = 0
        self.page = 0
        if not self.token: await self.get_token()  # 设置token值
        async with aiohttp.TCPConnector(limit=self.limit) as conn:  # 限制tcp连接数
            async with aiohttp.ClientSession(connector=conn, headers=self.headers) as session:
                # t = Process(target=self.jdt, )  # 进度条
                # t.daemon = True
                # t.start()

                start = (startpage - 1) * self.json['limit']

                while self.done == False:  # 如果完成就不继续
                    gtasks = [self._get_img_links(start, session)]
                    await asyncio.gather(*gtasks, return_exceptions=True)
                    start += self.json['limit']

                    # if self.page>4:break # 测试用的

        self.done = True
        # t.join()
        print(f'一共爬取{self.page}页，{self.num}张图片')

    def jdt(self, ):
        # sleep(1)
        bar = tqdm()
        bar.clear()
        while 1:
            sleep(.1)
            bar.set_description(f'下载成功{self.page}页，{self.num}张图片')
            bar.update(self.page - bar.last_print_n)
            if self.done:
                bar.clear()
                bar.set_description(f'共下载成功{self.page}页，{self.num}张图片')
                bar.update(self.page - bar.last_print_n)
                return


def main():
    down_path = r'D:\Download'
    startpage = 1
    with open('user.json', 'r', encoding='utf-8') as fp:  # 用户名密码，直接写程序不安全，从json文件中读取
        userdata = json.load(fp)
    spider = Spider(userdata, down_path, )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.run(startpage))


if __name__ == '__main__':
    start_time = time.perf_counter()
    main()
    print(f'总用时：{time.perf_counter() - start_time}')
