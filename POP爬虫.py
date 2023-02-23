import os
import time

import aiofiles
import aiohttp
import asyncio


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, down_path='', ):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Content-Length': '11',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            # 'Cookie': 'POP_UID=c5860a3aa88ca23b82b133115e8a5cd5; POP_USE_NEW_SITE_TIME=2022-11-8; Hm_lvt_ec1d5de03c39d652adb3b5432ece711d=1667867710; Hm_lpvt_ec1d5de03c39d652adb3b5432ece711d=1667867710; Hm_lvt_b923605182afd71b09f73febdc965591=1667867710; Hm_lpvt_b923605182afd71b09f73febdc965591=1667867710; gr_user_id=be8e8965-266c-4ca6-9637-86f7f7ff1e61; 8de2f524d49e13e1_gr_session_id=eb45044d-4af9-401f-9f12-3b55c453f007; 8de2f524d49e13e1_gr_session_id_eb45044d-4af9-401f-9f12-3b55c453f007=true',
            'Host': 'www.pop-fashion.com',
            'Origin': 'https://www.pop-fashion.com',
            'Referer': 'https://www.pop-fashion.com/patterns/graphics/',
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest', }
        self.data = {"pageSize": "20"}
        self.num = 0
        if down_path == "":
            if 'downpic' not in os.listdir('.'):  # 当前目录下的downpic目录
                os.mkdir('downpic')
            self.path = os.path.join(os.path.abspath('.'), 'downpic')
            os.chdir(self.path)  # 进入文件下载路径

        self.down_path = down_path
        self.url = 'https://www.pop-fashion.com/patterns/graphics/?page={}'
        self.limit = 10  # tcp连接数
        self.page = 0
        self.sleep = 10  # 每页抓取间隔时间

    async def run(self, startpage, endpage):
        async with aiohttp.TCPConnector(limit=self.limit) as conn:  # 限制tcp连接数
            async with aiohttp.ClientSession(connector=conn, headers=self.headers, ) as session:
                for pagen in range(startpage, endpage + 1):
                    await self._get_img_links(self.url.format(pagen), session)
                    await asyncio.sleep(self.sleep)  # 每页间隔时间，太快了，服务器不让抓
                print(f'一共下载成功{self.num}张图片')

    async def _get_img_links(self, page, session):  # 获取图片连接

        # try:
        async with session.post(url=page, data=self.data) as respone:
            r = await respone.json()
            urls = r['data']
            CONCURRENCY = 20
            semaphore = asyncio.Semaphore(CONCURRENCY)
            getpictasks = [self._get_content(ehurl, semaphore) for ehurl in urls]
            await asyncio.gather(*getpictasks, return_exceptions=False)
            self.page += 1
            print(f'下载成功{self.page}页')

    # except Exception as e:
    #     print(e)

    async def _get_content(self, link, semaphore):  # 传入的是图片连接

        async with semaphore:
            async with aiohttp.ClientSession() as session:
                # try:
                newurl = link['list_cover'].replace(link['cover'], '') + link['sBigPath']
                # print(newurl)
                async with session.get(url=newurl) as response:
                    content = await response.read()
                await self._write_img(link['id'], content)
            # except (asyncio.TimeoutError, ClientPayloadError):
            #     pass

    async def _write_img(self, file_name, content):
        file_name = os.path.join(self.down_path, str(file_name))
        file_name += '.jpg'
        print(file_name)
        async with aiofiles.open(file_name, 'wb') as f:
            await f.write(content)
            # print('下载第%s张图片成功' % self.num)
            self.num += 1


if __name__ == '__main__':
    start_time = time.perf_counter()
    down_path = r'E:\下载\POP'
    # down_path = r'd:\download'
    startpage = 1
    endpage = 2
    spider = Spider(down_path)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.run(startpage, endpage, ))
    print(f'总用时：{time.perf_counter() - start_time}')
