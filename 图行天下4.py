'''用法：searchpic('要查询的内容',页数,上传的开始日期)
页数不写，默认爬取一页，填写0则爬取所有图片
上传开始日期：默认不判断日期，填写日期的格式为yyyy-mm-dd('2022-01-31')文本格式
图片保存在这个文件所在的目录中'''
import requests
import re,time
from lxml import etree


def getpic(url, headers, date):  # 模块下的图片
    r = requests.get(url=url, headers=headers)
    el = etree.HTML(r.text)
    # print(url)
    # 判断是否jpg格式文档，如果是，那么就不下载
    pictypepath = '//div[@class="download-right-main mt20"]/div[2]/p/text()'
    pictype = el.xpath(pictypepath)[0]
    if 'JPG' in pictype.upper():
        # print(url)
        return 0
    # 判断图片结束
    # 判断上传时间
    uploaddatepath = '//div[@class="download-right-main mt20"]/div/p/text()'
    uploaddate = el.xpath(uploaddatepath)[-2]

    if bool(date) and (uploaddate < date):
        print(uploaddate)
        return 0
    # 判断上传时间结束

    picsrc = el.xpath('//*[@id="pic-main"]/@src')[0]
    picsrc = 'https:' + picsrc.replace('https:', '')
    filename = picsrc.split('/')[-1]
    # with open(r'C:\Users\Administrator\Desktop\新建文件夹 (16)\大牌'+filename, 'wb') as fp:
    with open(r'e:\download\\'+filename, 'wb') as fp:
        fp.write(requests.get(url=picsrc, headers=headers).content)
        print(filename)
        return 1


def searchpic(q, pages=1, date=False):
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
        'referer': 'https://www.photophoto.cn/'
    }
    data = {'kw': q}
    url = 'https://www.photophoto.cn/search/getKeyWords'
    pinyin = requests.get(url=url, headers=headers,
                          params=data).json()['pinyin']
    url = 'https://www.photophoto.cn/all/'+pinyin + '.html'
    r = requests.get(url=url, headers=headers, params=data)
    if re.search('抱歉，我们正在努力研究“', r.text):
        print('查不到图片信息')
        return

    el = etree.HTML(r.text)
    apages = el.xpath('//*[@id = "page"]/div/a//text()')
    if len(apages):
        if apages[-1] == '下一页':
            apages = apages[-2]
        else:
            apages = apages[-1]
    else:
        apages = 1

    if pages == 0:
        pages = apages
    else:
        pages = min(int(pages), int(apages))  # 取页数

    addstr = el.xpath('//*[@id="page"]/div/a/@href')
    if addstr:
        addstr = re.search(r'(?:\-\d+){7}\-', addstr[0]).group()
        urlpagelist = [url]+[
            f'{".".join(url.split(".")[:-1])}{addstr}{page}.html' for page in range(2, int(pages) + 1)]
    else:
        urlpagelist = [url]
    piccount = 0
    for urlehpage in urlpagelist[:]:
        print(urlehpage)
        r = requests.get(url=urlehpage, headers=headers, )
        el = etree.HTML(r.text)
        urls = el.xpath('//*[@id = "Masonry"]/div/div/div/a/@href')
        urls = ['https:' + x.replace('https:', '') for x in urls][:]
        for urlsub in urls:
            # print(urlsub)
            piccount += getpic(urlsub, headers=headers, date=date)
    print('爬完了！！,一共爬取{}张图片'.format(piccount))

st=time.perf_counter()
searchpic('大牌', 3, '2021-01-02')  # 注意日期格式必须是yyyy-mm-dd的文本格式
print(time.perf_counter()-st)
