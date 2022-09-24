import os, time, json
import pandas as pd
import re
import aiohttp, asyncio, aiofiles


class Spider(object):
    """
    下载路径在实例化时候指定，比如:r'd:\test\\'，这个目录如果不存在，会出错。
    如果想给文件名加前缀，只要在目录下加前缀就行，比如:r'd:\test\abc',那么生成的文件前面都有abc
    默认路径为当前文件下的downpic目录，此目录如果不存在会自动生成
    """

    def __init__(self, down_path=''):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36 Edg/105.0.1343.42'
        }
        self.num = 1
        if down_path == "":
            if 'downpic' not in os.listdir('.'):  # 当前目录下的downpic目录
                os.mkdir('downpic')
            self.path = os.path.join(os.path.abspath('.'), 'downpic')
            os.chdir(self.path)  # 进入文件下载路径

        self.down_path = down_path
        self.url = 'http://www.defuv.com/ajax/index/get-index-list.html'
        self.params = {'A': '', 'B': '', 'C': '', 'D': '', 'E': '',
                       'search_key': '', 'type': 'open', 'limit': 35, 'order_by': 'id',
                       'p': 1,
                       }

    async def _get_content(self, link, filename, session):  # 传入的是图片连接
        response = await session.get(link)
        content = await response.read()
        await self._write_img(filename, content)

    async def _get_img_links(self, page, session):  # 获取图片连接
        self.params['p'] = page

        # print(page)
        try:
            async with session.post(url=self.url, data=self.params) as respone:
                d = await respone.json(content_type='text/html')
                # print(page)
                return d
        except Exception as e:
            print(e)

    async def _write_img(self, file_name, content):
        file_name = os.path.join(self.down_path, file_name)
        async with aiofiles.open(file_name, 'wb') as f:
            await f.write(content)
        print('下载第%s张图片成功' % self.num)
        self.num += 1

    async def _get_total_page(self):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(url=self.url, data=self.params) as respone:
                d = await respone.json(content_type='text/html')
                return d

    async def _group_process(self, startpage, endpage, session):
        pagetasks = [asyncio.create_task(self._get_img_links(page, session))
                     for page in range(startpage, endpage + 1)]
        imgurls = await asyncio.gather(*pagetasks)  # 获取page下的json，json包含图片信息
        # -----------处理返回的数据
        df_imgurls = pd.json_normalize(sum(map(lambda x: x['data']['list'] if x else [], imgurls), []))
        df_imgurls['pic_id'] = ('DVF编号' +
                                df_imgurls['pic_id'] +
                                df_imgurls['pic_url'].str.extract(r'\d+(\.\w+)\?version=')[0]
                                )
        df_imgurls = df_imgurls[['pic_url', 'pic_id']]
        # ------------图片的网址和地址都已经获取

        imgtasks = [asyncio.create_task(
            self._get_content(row['pic_url'], row['pic_id'], session=session))
            for _, row in df_imgurls.iterrows()]
        await asyncio.gather(*imgtasks)

    async def run(self, startpage=1, endpage=1):
        """
        startpange:开始爬取的页面，默认为1
        endpage:结束页数，默认为1,如果此参数为0，那么就会下载全部页面的图片
        """
        start = time.time()
        if endpage == 0:
            [d] = await asyncio.gather(self._get_total_page())
            endpage = d['data']['page_total']
            print(f'总页数:{endpage}')
        se = pd.Series(range(1, endpage + 1))
        n = 400  # 下载多少页后存储图片，然后继续下一组下载，数值越大，整体下载速度越快。
        gdf = se.groupby(se.index // n).agg(['first', 'last'])
        async with aiohttp.ClientSession(headers=self.headers) as session:
            for x in gdf.itertuples(index=False):
                await self._group_process(*x, session)

        end = time.time()
        print('共运行了%s秒' % (end - start))


def main():
    down_path = r'E:\Download'
    spider = Spider(down_path)
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(spider.run(startpage=1, endpage=2))  # 这里填写开始页数和结束页数，如果结束页数写0，那么会全量下载。


if __name__ == '__main__':
    main()
