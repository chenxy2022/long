"""
用requests同步方式爬取每页的图片链接；
用aiohttp异步方式爬取图片；
用multiprocessing的多进程，主进程为计时器，按照设定的间隔时间判断是否断网，
如果断网重新在断网页重新开始下载。用manager().dict()进行进程间传输数据。
需要安装 pip install retrying
"""
import json
import os
import re
import time
from datetime import datetime
from io import BytesIO
import math
from multiprocessing import Process, Manager

import aiohttp
import asyncio
import chardet
import requests
from PIL import Image
from lxml import etree
from retrying import retry
import pandas as pd
import charset_normalizer as cn

关键词数 = 0


class Spider(object):
    """
    """

    def __init__(self, para: dict):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/93.0.4577.82 Safari/537.36 '
        }
        self.num = 1
        self.sem = para.get('sem', 100)
        self.update_date = para.get('update_date', False)
        self.delay = para.get('delay', 0.5)
        self.url = 'https://soso.nipic.com/'
        # --------------建目录
        self.down_path = para.get('down_path', '')
        self.resize_path = os.path.join(self.down_path, para.get('resize_path', 'resize'))
        self.crop_path = os.path.join(self.down_path, para.get('crop_path', 'crop'))
        for f_path in [self.down_path, self.resize_path, self.crop_path]:
            if not os.path.exists(f_path):
                os.makedirs(f_path)
        self.black = self._black(para.get('black'))

        self.huitu_url = 'https://hi.huitu.com/{}/photo/'
        self.nipic_url = 'https://hi.nipic.com/people/{}/ni'
        self.dateout = False  # 判断日期是否，如果是True,那么后面的页面就不爬了
        self.original = para.get('original')

    def _black(self, filename):
        if not filename: return set()
        text = str(cn.from_path(para.get('black')).best())
        return {x.split("_")[-1].strip() for x in text.splitlines()}


    def _resize_image(self, infile, outfile='', minsize=260, is_file=True):  # 把图片像素改成308
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
        # print('保存路径:{}'.format(outfile))

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

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    async def get_content(self, url, ):  # 传入的是图片连接
        async with aiohttp.ClientSession(headers=self.headers) as session:

            r = await session.get(url)
            el = etree.HTML(await r.text())
            if '//www.nipic.com/' in url:

                # 判断图片类型
                pictypepath = '//*[@id="J_detailMain"]/div[2]/div[1]/p[2]/span[2]/span/text()'
                try:
                    pictype = el.xpath(pictypepath)[0].strip()
                except Exception:
                    pictype = ''

                # if 'JPG' in pictype.upper():
                #     return 0
                # 判断图片类型结束

                # 判断上传日期
                uploaddatepath = '//*[@id="J_detailMain"]/div[2]/div[1]/p[1]/span[2]/span/text()'
                uploaddate = el.xpath(uploaddatepath)[0].strip()
                uploaddate = datetime.strptime(
                    uploaddate, '%Y/%m/%d').strftime('%Y-%m-%d')
                if bool(self.update_date) and uploaddate < self.update_date:
                    self.dateout = True  # 设置标识位为True，后续页面不再爬取
                    return 0
                # 判断上传日期结束

                # 获取上传者
                upload_user_path = '//*[@id="contextBox"]/div[3]/dl/dd/div[1]/div/a'
                try:
                    upload_user = el.xpath(upload_user_path)[0]
                    # print(upload_user.xpath('./@title'), upload_user.xpath('./@href'))
                    username = upload_user.xpath('./@title')[0]
                    usercode = re.search(r'\d{3,}', upload_user.xpath('./@href')[0]).group()
                    if usercode in self.black:return
                    userinfo = usercode # (f"{username}_{usercode}")
                except Exception:
                    print('no upload_user')
                # 获取上传者结束

                try:
                    picsrc = el.xpath('//*[@id="J_worksImg"]//@src')[0]
                except Exception:
                    return 0
                bhpath = '//*[@id = "J_detailMain"]/div[2]/div[1]/p[1]/span[1]/span/text()'
                filebh = el.xpath(bhpath)[0]

                # if filebh in self.black: return  # 剔除黑名单编号

                file_format_ph = '//*[@id="J_detailMain"]/div[2]/div[1]/p[2]/span[2]/span/text()'
                file_format = el.xpath(file_format_ph)[0]
                file_format = re.sub(r'\(.*\)', '', file_format).strip()
                # print(file_fomat)
                # 判断是否存在共享分
                shareph = '//*[@id="J_detailMain"]/div[2]/div[2]/span/b/text/text()'
                if (share := el.xpath(shareph)):
                    filebh = f'昵图{share[0]}共享分{filebh}'
                elif (mh := re.search(r'var price = \((\d+)\).toString\(\);', await r.text())):
                    filebh = f'昵图{mh.group(1)}元{filebh}'
                # print(filebh)
            else:  # 汇图网
                # 判断图片类型

                pictypepath = '//*[@id = "details"]/div[1]/div/div[2]/div//span/@title'
                try:
                    pictype = el.xpath(pictypepath)[0].strip()
                except Exception:
                    return 0
                # if 'JPG' in pictype.upper():
                #     return 0
                # 判断图片类型结束

                # 获取上传者
                upload_user_path = '//*[@class="author-name"]'

                try:
                    upload_user = el.xpath(upload_user_path)[0]
                    username = upload_user.xpath('./text()')[0]
                    usercode = re.search(r'\d{3,}', upload_user.xpath('./@href')[0]).group()
                    if usercode in self.black: return
                    userinfo = usercode # (f"{username}_{usercode}")
                except Exception:
                    print('no upload_user')
                # 获取上传者结束

                try:
                    picsrc = el.xpath(
                        '//*[@id="details"]/div[1]/div/div[1]/div[1]/div/div[1]/img/@src')[0]
                except Exception:
                    return 0

                bhpath = '//*[@id="details"]/div[1]/div/div[2]/div/div[3]/label[1]/text()'
                filebh = el.xpath(bhpath)
                file_format_ph = '//*[@id="details"]/div[1]/div/div[2]/div//text()'
                # '//*[@id="details"]/div[1]/div/div[2]/div/div[3]'

                file_format = el.xpath(file_format_ph)
                file_format = file_format[[i for i, x in enumerate(file_format) if '格式' in x][0] + 1].strip()
                file_format = re.sub(r'\(.*\)', '', file_format).strip()

                if filebh:
                    if filebh in self.black: return  # 剔除黑名单编号
                    filebh = filebh[0].split("：")[1]
                    ht = "汇图网编号"
                    if (mh := re.search(r'"OriginalPrice":(\d+)\.\d\d', await r.text())):  # Price 是折扣后价格
                        ht = f'汇图网{mh.group(1)}元编号'
                    filebh = ht + filebh
                    # print(userinfo)
                else:
                    return 0  # 如果获取不到图片，直接忽略。

            picsrc = 'https:' + picsrc

            filebh = userinfo + '_' + filebh  # --------------------------加作者和内部编号    userinfo + '_' + filebh
            # print('我是')
            # print(filebh)

            filename = filebh + '.jpg'
            filename = os.path.join(file_format, filename)

            response = await session.get(picsrc)  # 图片网址
            content = await response.read()
            if content and filename:
                return content, filename  # 结果包括图片内容和文件名

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def _get_img_links(self, page, q):  # 获取图片连接
        url = q
        if 'nipic.com' in url:  # 昵图网
            params = {'page': str(page)}
            try:
                print('正在爬取 {} 页数：{}'.format(q, page))

                r = requests.get(url=url, headers=self.headers, params=params)
                el = etree.HTML(r.text)
                path = '/html/body/div[2]/div[2]/div[2]/div[1]/div/div[1]/a/@href'
                s = el.xpath(path)

                if s:
                    urls = s
                    urls = ['https:' + x if x[:2] == '//' else x for x in urls]
                    # print(urls)
                    return urls
            except Exception as e:
                print(e)
        else:
            params = {'pagenum': str(page)}
            try:
                print('正在爬取 {} 页数：{}'.format(q, page))
                r = requests.get(url=url, headers=self.headers, params=params)
                s = re.findall(r'\[{"picId":.+"picDiscountType":\d+}\]', r.text)
                if s:
                    urls = pd.DataFrame(json.loads(s[0]))['pageUrl'].values
                    urls = ['https:' + x.replace('https:', '') for x in urls]
                    return urls
            except Exception as e:
                print(e)

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    async def _download_img(self, img, share_dict, mysem):

        async with mysem:
            resu = await self.get_content(img)  # 获取图片的进制文件
            await asyncio.sleep(self.delay)

        if not resu:  # 如果没有返回值
            return

        content, short_name = resu

        # file_name_resize = os.path.join(self.resize_path, short_name)                                             # 不下载缩略图注释行
        file_name_crop = os.path.join(self.crop_path, short_name)
        file_name_crop = os.path.join(os.path.split(file_name_crop)[0],  os.path.split(file_name_crop)[1])

        if self.original:  # 下载原图
            file_name_original = os.path.join(self.down_path,'原图', short_name)
            ckpath = os.path.dirname(file_name_original)
            if not os.path.exists(ckpath):
                os.makedirs(ckpath)
            with open(file_name_original, 'wb') as f:
                f.write(content)

        # self._resize_image(BytesIO(content), outfile=file_name_resize)                                             # 不下载缩略图注释行

        self._img_crop(BytesIO(content), output_fullname=file_name_crop)
        share_dict['num'] += 1
        self.num += 1

    def _get_total_page(self, q):
        url = q
        r = requests.get(url=url, headers=self.headers, )
        if 'nipic.com' in url:  # 昵图网
            totalpage = re.findall(r'page=(\d+)', r.text)
            if totalpage:
                return int(totalpage[-1])
        else:
            totalpage = re.findall(r'"totalCount":"(\d+)"', r.text)
            if totalpage:
                return math.ceil(int(totalpage[0]) / 20)

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def run(self, q, startpage=1, endpage=1, share_dict=None):

        """
        q:要查询的内容
        startpange:开始爬取的页面，默认为1
        endpage:结束页数，默认为1，如果参数为0,会全部爬取
        share_dict:这个多进程时候，共享信息用。重新启动进程时候，保存信息的。
        """
        q = self.nipic_url.format(q.split('_')[-1])  # 将数据转换为网址
        if share_dict is None:
            share_dict = {}
        if not share_dict.get('starttime'):  # 保存初始时间
            share_dict['starttime'] = time.time()
        if not share_dict.get('num'):  # 更新下载的数量
            share_dict['num'] = self.num
        share_dict['q'] = q

        start = share_dict['starttime']
        if endpage == 0:
            endpage = self._get_total_page(q)
            if endpage is None: endpage = 1
            print(f'总页数:{endpage}')

        self.endpage = endpage
        for page in range(startpage, endpage + 1):  # 下载的页数范围
            self.dateout = False  # 每页开始前重置日期标识

            # 保存开始页数和结束页数
            share_dict['startpage'], share_dict['endpage'] = page, endpage
            links = self._get_img_links(page, q)  # 把那一页须要爬图片的连接传进去
            # print(links)
            if links:
                mysem = asyncio.Semaphore(self.sem)  # 并发数，一定要在生成task前定义并传入
                tasks = [asyncio.ensure_future(
                    self._download_img(link, share_dict, mysem, )) for link in links]
                loop = asyncio.get_event_loop()
                loop.run_until_complete(asyncio.wait(tasks))

            end = time.time()
            print('共运行了{:.2f}秒'.format(end - start))
            print('下载第{}张图片成功'.format(share_dict['num'] - 1))
            if self.dateout: break  # 如果本页有设置这个标识，那么后续不不爬了。
class Spider_keys(object):
    """
    """

    def __init__(self, para: dict):
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/93.0.4577.82 Safari/537.36 '
        }
        self.num = 1
        self.sem = para.get('sem', 100)
        self.update_date = para.get('update_date', False)
        self.delay = para.get('delay', 0.5)
        self.url = 'https://soso.nipic.com/'
        # --------------建目录
        self.down_path = para.get('down_path', '')
        self.resize_path = os.path.join(self.down_path, para.get('resize_path', 'resize'))
        self.crop_path = os.path.join(self.down_path, para.get('crop_path', 'crop'))
        for f_path in [self.down_path, self.resize_path, self.crop_path]:
            if not os.path.exists(f_path):
                os.makedirs(f_path)
        self.black = self._black(para.get('black'))
        self.original = para.get('original')

    def _black(self, filename):
        if not filename: return set()
        text = str(cn.from_path(para.get('black')).best())
        return {x.split("_")[-1].strip() for x in text.splitlines()}

    def _resize_image(self, infile, outfile='', maxsize=308, is_file=True):
        """修改图片尺寸
        :param infile: 图片源文件
        :param outfile: 输出文件名，如果为空，那么直接修改原图片
        :param maxsize: 最大长宽
        :return:
        """
        im = Image.open(infile) if is_file else infile
        immax = max(im.size)
        if immax > maxsize:
            x, y = im.size
            x = int(x * maxsize / immax)
            y = int(y * maxsize / immax)
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
        # 转换.save(output_fullname)  # 保存

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    async def get_content(self, url, ):  # 传入的是图片连接
        async with aiohttp.ClientSession(headers=self.headers) as session:

            r = await session.get(url)
            el = etree.HTML(await r.text())
            if '//www.nipic.com/' in url:

                # 判断图片类型
                pictypepath = '//*[@id="J_detailMain"]/div[2]/div[1]/p[2]/span[2]/span/text()'
                try:
                    pictype = el.xpath(pictypepath)[0].strip()
                except Exception:
                    pictype = ''

                # if 'JPG' in pictype.upper():
                #     return 0
                # 判断图片类型结束

                # 判断上传日期
                uploaddatepath = '//*[@id="J_detailMain"]/div[2]/div[1]/p[1]/span[2]/span/text()'
                uploaddate = el.xpath(uploaddatepath)[0].strip()
                uploaddate = datetime.strptime(
                    uploaddate, '%Y/%m/%d').strftime('%Y-%m-%d')
                if bool(self.update_date) and uploaddate < self.update_date:
                    self.dateout = True  # 设置标识位为True，后续页面不再爬取
                    return 0
                # 判断上传日期结束

                # 获取上传者
                upload_user_path = '//*[@id="contextBox"]/div[3]/dl/dd/div[1]/div/a'
                try:
                    upload_user = el.xpath(upload_user_path)[0]
                    # print(upload_user.xpath('./@title'), upload_user.xpath('./@href'))
                    username = upload_user.xpath('./@title')[0]
                    usercode = re.search(r'\d{3,}', upload_user.xpath('./@href')[0]).group()
                    if usercode in self.black: return
                    userinfo = usercode  # (f"{username}_{usercode}")
                except Exception:
                    print('no upload_user')
                # 获取上传者结束

                try:
                    picsrc = el.xpath('//*[@id="J_worksImg"]//@src')[0]
                except Exception:
                    return 0
                bhpath = '//*[@id = "J_detailMain"]/div[2]/div[1]/p[1]/span[1]/span/text()'
                filebh = el.xpath(bhpath)[0]

                # if filebh in self.black: return  # 剔除黑名单编号

                file_format_ph = '//*[@id="J_detailMain"]/div[2]/div[1]/p[2]/span[2]/span/text()'
                file_format = el.xpath(file_format_ph)[0]
                file_format = re.sub(r'\(.*\)', '', file_format).strip()
                # print(file_fomat)
                # 判断是否存在共享分
                shareph = '//*[@id="J_detailMain"]/div[2]/div[2]/span/b/text/text()'
                if (share := el.xpath(shareph)):
                    filebh = f'昵图{share[0]}共享分{filebh}'
                elif (mh := re.search(r'var price = \((\d+)\).toString\(\);', await r.text())):
                    filebh = f'昵图{mh.group(1)}元{filebh}'
                # print(filebh)
            else:  # 汇图网
                # 判断图片类型

                pictypepath = '//*[@id = "details"]/div[1]/div/div[2]/div//span/@title'
                try:
                    pictype = el.xpath(pictypepath)[0].strip()
                except Exception:
                    return 0
                # if 'JPG' in pictype.upper():
                #     return 0
                # 判断图片类型结束

                # 获取上传者
                upload_user_path = '//*[@class="author-name"]'

                try:
                    upload_user = el.xpath(upload_user_path)[0]
                    username = upload_user.xpath('./text()')[0]
                    usercode = re.search(r'\d{3,}', upload_user.xpath('./@href')[0]).group()
                    if usercode in self.black: return
                    userinfo = usercode  # (f"{username}_{usercode}")
                except Exception:
                    print('no upload_user')
                # 获取上传者结束

                try:
                    picsrc = el.xpath(
                        '//*[@id="details"]/div[1]/div/div[1]/div[1]/div/div[1]/img/@src')[0]
                except Exception:
                    return 0

                bhpath = '//*[@id="details"]/div[1]/div/div[2]/div/div[3]/label[1]/text()'
                filebh = el.xpath(bhpath)
                file_format_ph = '//*[@id="details"]/div[1]/div/div[2]/div//text()'
                # '//*[@id="details"]/div[1]/div/div[2]/div/div[3]'

                file_format = el.xpath(file_format_ph)
                file_format = file_format[[i for i, x in enumerate(file_format) if '格式' in x][0] + 1].strip()
                file_format = re.sub(r'\(.*\)', '', file_format).strip()

                if filebh:
                    if filebh in self.black: return  # 剔除黑名单编号
                    filebh = filebh[0].split("：")[1]
                    ht = "汇图网编号"
                    if (mh := re.search(r'"OriginalPrice":(\d+)\.\d\d', await r.text())):  # Price 是折扣后价格
                        ht = f'汇图网{mh.group(1)}元编号'
                    filebh = ht + filebh
                    # print(userinfo)
                else:
                    return 0  # 如果获取不到图片，直接忽略。

            picsrc = 'https:' + picsrc

            filebh = userinfo + '_' + filebh  # --------------------------加作者和内部编号    userinfo + '_' + filebh
            # print('我是')
            # print(filebh)

            filename = filebh + '.jpg'
            filename = os.path.join(file_format, filename)

            response = await session.get(picsrc)  # 图片网址
            content = await response.read()
            if content and filename:
                return content, filename  # 结果包括图片内容和文件名

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def _get_img_links(self, page, q):  # 获取图片连接
        url = self.url
        params = {'q': q,
                  'page': str(page),
                  }
        try:
            print('正在爬取 {} 页数：{}'.format(q, page))
            r = requests.get(url=url, headers=self.headers, params=params)
            el = etree.HTML(r.text)
            urls = el.xpath('//*[@id="img-list-outer"]/li/a/@href')
            urls = ['https:' + x.replace('https:', '') for x in urls]
            # print('本页{}张图片'.format(len(urls)))
            return urls
        except Exception as e:
            print(e)

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    async def _download_img(self, img, share_dict, mysem):

        async with mysem:
            resu = await self.get_content(img)  # 获取图片的进制文件
            await asyncio.sleep(self.delay)

        if not resu:  # 如果没有返回值
            return

        content, short_name = resu

        # file_name_resize = os.path.join(self.resize_path, short_name)                                             # 不下载缩略图注释行
        file_name_crop = os.path.join(self.crop_path, short_name)
        file_name_crop = os.path.join(os.path.split(file_name_crop)[0], os.path.split(file_name_crop)[1])

        if self.original:  # 下载原图
            file_name_original = os.path.join(self.down_path, '原图', short_name)
            ckpath = os.path.dirname(file_name_original)
            if not os.path.exists(ckpath):
                os.makedirs(ckpath)
            with open(file_name_original, 'wb') as f:
                f.write(content)

        # self._resize_image(BytesIO(content), outfile=file_name_resize)                                             # 不下载缩略图注释行

        self._img_crop(BytesIO(content), output_fullname=file_name_crop)
        share_dict['num'] += 1
        self.num += 1

    def _get_total_page(self, q):
        url = self.url
        params = {'q': q,
                  'page': '1',
                  }
        r = requests.get(url=url, headers=self.headers, params=params)
        el = etree.HTML(r.text)
        pages = el.xpath('/html/body/div[5]/a//@title')

        if pages:
            pages = list(filter(lambda x: x.startswith('第'), pages))
            pages = pages[-1].strip('第页')  # 全部页面
        else:
            pages = 0
        return int(pages)

    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def run(self, q, startpage=1, endpage=1, share_dict=None):
        """
        q:要查询的内容
        startpange:开始爬取的页面，默认为1
        endpage:结束页数，默认为1，如果参数为0,会全部爬取
        share_dict:这个多进程时候，共享信息用。重新启动进程时候，保存信息的。
        """

        if share_dict is None:
            share_dict = {}
        if not share_dict.get('starttime'):  # 保存初始时间
            share_dict['starttime'] = time.time()
        if not share_dict.get('num'):  # 更新下载的数量
            share_dict['num'] = self.num
        share_dict['q'] = q

        start = share_dict['starttime']
        if endpage == 0:
            endpage = self._get_total_page(q)
            print(f'总页数:{endpage}')
        self.endpage = endpage
        for page in range(startpage, endpage + 1):  # 下载的页数范围
            # 保存开始页数和结束页数
            share_dict['startpage'], share_dict['endpage'] = page, endpage
            links = self._get_img_links(page, q)  # 把那一页须要爬图片的连接传进去
            # print(len(links))
            if links:
                mysem = asyncio.Semaphore(self.sem)  # 并发数，一定要在生成task前定义并传入
                tasks = [asyncio.ensure_future(
                    self._download_img(link, share_dict, mysem, )) for link in links]
                loop = asyncio.get_event_loop()
                loop.run_until_complete(asyncio.wait(tasks))

            end = time.time()
            print('共运行了{:.2f}秒'.format(end - start))
            print('下载第{}张图片成功'.format(share_dict['num'] - 1))


def main(para):
    print(para.get('keys_file'))
    spider = Spider(para)  if '作者' in para.get('keys_file') else Spider_keys(para)
    share_dict = Manager().dict()  # 保存多进程的信息，包括页面、下载图片数等信息
    t_process = Process(target=spider.run, args=(
        para.get('q'), para.get('startpage', 1), para.get('endpage', 1), share_dict))
    t_process.daemon = False
    t_process.start()  # 开始启动爬虫进程
    if not para.get('myinterval'):  # 如果间隔为0，那么就等待进程结束，不再启动计时进程。
        t_process.join()
        print('{} 爬完了'.format(para['q']))
        return

    # -------------------------主进程每隔myinterval秒检测下载进程----------

    while para.get('myinterval'):

        old_share_dict = share_dict.copy()  # 保存开始的数据
        for _ in range(para.get('myinterval')):  # 判断是否断线的间隔时间
            if not t_process.is_alive():
                print('{} 爬完了'.format(para.get('q')))
                return  # 如果爬虫进程结束，那就主程序结束
            time.sleep(1)
        if old_share_dict.get('num') == share_dict.get('num'):
            # 如果间隔时间内下载数量没有增加，那么就终止进程重新开始
            t_process.terminate()
            t_process.join()
            time.sleep(3)  # 3秒后重新启动进程
            print('中断后继续下载于：{}{}'.format(time.strftime('%H:%M:%S'), share_dict))
            t_process = Process(target=spider.run,
                                args=(share_dict['q'], share_dict['startpage'], share_dict['endpage'], share_dict))
            t_process.start()


if __name__ == '__main__':
    _mystarttime = time.perf_counter()
    para = dict(
        keys_file=r'd:\download\关键字.txt',  # 根据文件名判断，如果文件名里面有作者，就按照作者。否则按照关键字。
        # keys_file=r'd:\download\作者.txt',
        # down_path=r'E:\下载\呢图\3.20更新',  # 图片存放基础路径,最终文件路径为这个目录加关键字
        down_path=r'd:\download\昵图',  # 图片存放基础路径,最终文件路径为这个目录加关键字
        resize_path='略缩图',  # resize图片的子目录，默认 resize
        crop_path='裁剪图',  # crop图片的子目录，默认crop
        startpage=1,  # 开始页，默认1
        endpage=0,  # 结束页，默认1，如果此参数为0，那么会全部下载
        update_date='1023-08-16',  # 上传日期：不填写默认全部下载，日期为文本'yyyy-mm-dd'('2021-12-01')格式
        myinterval=60,  # 几秒钟检测一次是否还在下载，如果此参数为0，那么就不检测断网情况。默认60秒
        sem=100,  # 并发数，默认100
        delay=0.7,  # 爬取间隔数，防止被服务器踢掉，每爬一张图片间隔时间，默认0.5秒。

        black=r'd:\download\排除作者.txt', # 排除作者
        original=True,  # 这个变量为True，下载原图。

    )
    text = str(cn.from_path(para.get('keys_file')).best())
    keys_list = list(map(str.strip, text.splitlines()))
    print('爬取内容', keys_list)

    para_copy = para.copy()
    for num, q in enumerate(keys_list):  # 开始爬数据(修改参数为：查询内容，裁剪图和略缩图的路径）
        para_copy['q'] = q
        main(para_copy)

    print(f'总用时:{time.perf_counter() - _mystarttime:.0f}秒')
# 线条高清
