'''需要使用公开区的代码，这里公开区代码的文件名是defuv_open'''
from defuv_open import *


def main():
    down_path = r'E:\Download'
    spider = Spider(down_path)
    spider.params.update({'type': 'material'})
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(spider.run(startpage=1, endpage=2))  # 这里填写开始页数和结束页数，如果结束页数写0，那么会全量下载。


if __name__ == '__main__':
    main()
