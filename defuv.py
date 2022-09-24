import requests, os, time, re
import aiohttp, asyncio
from lxml import etree


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

    async def __get_content(self, link):  # 传入的是图片连接
        filename = re.findall(r'(\w*\d+\.\w{3,})', link.lower())[0]
        async with aiohttp.ClientSession(headers=self.headers) as session:
            response = await session.get(link)
            content = await response.read()
            return content, filename

    def __get_img_links(self, page, q):  # 获取图片连接
        # url_b = 'https://www.hellorf.com'
        url = 'https://www.hellorf.com/image/search'
        params = {'q': q,
                  'category': 'undefined',
                  'page': page,
                  }
        try:
            print('正在爬取页数：', page)
            params['page'] = str(page)
            r = requests.get(url=url, headers=self.headers, params=params)
            el = etree.HTML(r.text)
            if re.findall(r'发现精选素材', r.text):
                hrefpath = '//*[@id="__next"]/div/main/div/div[5]/div//figure/a/img/@data-src'
            else:
                hrefpath = '//*[@id="__next"]/div/main/div/div[3]/div//figure/a/img/@data-src'

            urls = el.xpath(hrefpath)
            print('本页{}张图片'.format(len(urls)))
            return urls
        except Exception as e:
            print(e)

    async def __download_img(self, img):
        content, file_name = await self.__get_content(img)  # 获取图片的进制文件
        file_name = self.down_path + file_name
        with open(file_name + '.jpg', 'wb') as f:
            f.write(content)
        print('下载第%s张图片成功' % self.num)
        self.num += 1

    def _get_total_page(self):
        url = 'http://www.defuv.com/ajax/index/get-index-list.html'
        params = {
            'A': '',
            'B': '',
            'C': '',
            'D': '',
            'E': '',
            'p': 1,
            'search_key': '',
            'type': 'open',
            'limit': 35,
            'order_by': 'id',
        }
        # self.headers.update\
        # myjson=json.dumps\
        # self.headers\
        # params.update(dict(Referer='http://www.defuv.com/index/index/open.html',
        #                          # Origin='http://www.defuv.com',
        #                          # Host='www.defuv.com',
        #                          ))

        r = requests.post(url=url, headers=self.headers, data=params)
        # print(r.json())
        # el = etree.HTML(r.text)
        # pages = el.xpath('//*[@id="vue"]/div[4]//text()')
        # # '//*[@id="vue"]/div[3]/div[3]/ul/li[8]/text()')
        return r.json()
        # return pages

    def run(self, q, startpage=1, endpage=1):
        """
        q:要查询的内容
        startpange:开始爬取的页面，默认为1
        endpage:结束页数，默认为1,如果此参数为0，那么就会下载全部页面的图片
        """
        start = time.time()
        if endpage == 0:
            endpage = self._get_total_page()
            print(f'总页数:{endpage}')
        for page in range(startpage, endpage + 1):  # 下载一百页的图片就能够了，或者本身更改页数
            links = self.__get_img_links(page, q)  # 把那一页须要爬图片的连接传进去
            if links:
                tasks = [asyncio.ensure_future(self.__download_img(link)) for link in links]
                loop = asyncio.get_event_loop()
                loop.run_until_complete(asyncio.wait(tasks))
            # if self.num >= 10:  # 测试速度使用，如须要下载多张图片能够注释这段代码
            #     break
            end = time.time()
            print('共运行了%s秒' % (end - start))


def main():
    down_path = r'E:\Download'
    spider = Spider(down_path)
    r=spider._get_total_page()
    print(r)
    # spider.run('苹果',startpage=1,endpage=5)


if __name__ == '__main__':
    main()
