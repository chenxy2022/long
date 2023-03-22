import os
import time
# import pandas as pd
from concurrent.futures import ThreadPoolExecutor


def delefiles(in_files):
    # 多线程删除文件名
    with ThreadPoolExecutor() as executor:
        executor.map(os.remove, in_files)


def get_files(filepath):
    return [os.path.join(root, f)
            for root, _, files in os.walk(filepath)
            for f in files]


if __name__ == '__main__':
    filepath = r'D:\download'  # 删除这个目录和子目录下所有文件
    st = time.perf_counter()
    filenames = get_files(filepath)
    delefiles(filenames)
    print(f'删除文件：{len(filenames)}', f'用时：{time.perf_counter() - st:.2f}秒')
