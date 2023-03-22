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

            # 'Cookie': self.getcookie(),
            # 'Cookie': 'HMACCOUNT_BFESS=4B87A02A9018F5B8;Hm_lvt_b923605182afd71b09f73febdc965591=1677459556;gr_user_id=912a6cd2-7494-4ec8-943d-80ed7ee54d62;9a62fc0377c54c0d_gr_session_id=101422eb-3373-47ff-a1e5-7cd610b0e6ad;9a62fc0377c54c0d_gr_session_id_101422eb-3373-47ff-a1e5-7cd610b0e6ad=true;Hm_lvt_ec1d5de03c39d652adb3b5432ece711d=1677459556;request_id=r63fc0063ec7614.08090117;client_id=c63fc0063eca240.05183479;client_token=c6653e0349bdfb04b07fe4a0d2cd7e12;NO_REFRESH_JWT=1;POP_USER=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ3ZWJzaXRlIjoiMSIsImp3dFR5cGUiOiJvZmZpY2lhbCIsImRldmljZV90eXBlIjoid2ViIiwiZXhwIjoxNjc3NTQ1OTU1LCJ1c2VyIjp7ImNsaWVudElkIjoiYzYzZmMwMDYzZWNhMjQwLjA1MTgzNDc5IiwicmVxdWVzdElkIjoicjYzZmMwMDYzZWM3NjE0LjA4MDkwMTE3IiwidXNlcklkIjoxNjUxMTI2LCJjaGlsZElkIjoiIiwibW9iaWxlIjoiIiwiYWNjb3VudCI6Ilx1NjY2OFx1OTQ2Ylx1NWUwM1x1ODI3YSIsImlwIjoiNjEuMTY0Ljk4LjIwIiwidXNlcl9mcm9tIjoiMSIsImNsaWVudF9udW1iZXIiOiIiLCJsb2dpbl9hdCI6MTY3NzQ1OTU1NSwicHdkX3RpcCI6dHJ1ZSwiY2hlY2tJcE51bSI6dHJ1ZX19.kBzk_MhhlPgVYukyhzg11AwrNc165shQIqPMsGpx2FY;POP_SSID=5pmWZdPpKOwdKgRl;userinfo_id=1651126;9a62fc0377c54c0d_gr_last_sent_sid_with_cs1=101422eb-3373-47ff-a1e5-7cd610b0e6ad;9a62fc0377c54c0d_gr_last_sent_cs1=1651126;9a62fc0377c54c0d_gr_cs1=1651126;Hm_lpvt_b923605182afd71b09f73febdc965591=1677459557;Hm_lpvt_ec1d5de03c39d652adb3b5432ece711d=1677459557;XSRF-TOKEN=eyJpdiI6IkhDaG8wZm9hU29mWTE2aXpHMFFHVGc9PSIsInZhbHVlIjoid0htbW1mQ1loT1pFdnJpdkNrS2Ixd2ZJV3BBU2l1Z0FiQzJOcXdIb2RzUlBTRFhiZTZBaWlcL0ZKbDU4bWZMU2VMZEhQdFcwUDBrZ2xxenVBK1NBNzRSc3dham8xZzNKUXBTcUh2d2E0UFhMS3htNVN0NHl6Q2JoTUVUa2VGVlV0IiwibWFjIjoiNGE2YmQ0YTdmZWQ0ZjE0OGI2YzJjNWI4NmIwYzFiZmUzODAwY2E0OTA2YWQ2MGY2MDU1OTFlZDZhNWM2ZTc5MyJ9;pop_fashion_session=8FlOvh6zx6paz3lECDFbTqc0UmKxypeUVOgWua7A',

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
        self.getcookie()
        # print(self.headers['Cookie'])
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
        self.sleep = 15  # 每页抓取间隔时间

    def getcookie(self):
        from playwright.sync_api import Playwright, sync_playwright
        def run(playwright: Playwright) -> None:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://www.pop-fashion.com/member/pagelogin/")
            page.locator(
                "text=用户名 登录密码 点击按钮完成图形验证 为保证你的账户安全，请先完成图形验证 换一换 向右滑动完成拼图 >> [placeholder=\"请输入用户名\"]").fill(
                "晨鑫布艺")
            page.locator(
                "text=用户名 登录密码 点击按钮完成图形验证 为保证你的账户安全，请先完成图形验证 换一换 向右滑动完成拼图 >> [placeholder=\"请输入密码\"]").fill(
                "cxby1234")
            # Click text=立即登录 >> nth=0
            page.locator("text=立即登录").first.click()
            page.wait_for_url("https://www.pop-fashion.com/")
            cookie = context.cookies()
            cookie = ';'.join([f'{eh["name"]}={eh["value"]}' for eh in cookie])
            self.headers['Cookie'] = cookie
            # ---------------------
            context.close()
            browser.close()
            # print(cookie)
            # return cookie

        with sync_playwright() as playwright:
            run(playwright)

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
            print(f'下载成功{self.page}页,累计{self.num}张图片。')

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
        # print(file_name)
        async with aiofiles.open(file_name, 'wb') as f:
            await f.write(content)
            # print('下载第%s张图片成功' % self.num)
            self.num += 1


if __name__ == '__main__':
    start_time = time.perf_counter()
    # down_path = r'E:\下载\POP'
    down_path = r'd:\download'
    startpage = 1
    endpage = 5
    spider = Spider(down_path)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(spider.run(startpage, endpage, ))
    print(f'总用时：{time.perf_counter() - start_time}')
