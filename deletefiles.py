import os, time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor


def delefiles(in_files):
    # 多线程删除文件名
    with ThreadPoolExecutor() as executor:
        executor.map(os.remove, in_files)


def get_files(filepath):
    filenames = dict()
    fileandpath = os.walk(filepath)
    for p, subps, fs in fileandpath:
        for f in fs:
            fullf = os.path.join(p, f)
            filenames[fullf] = f
    return pd.Series(filenames, dtype='object')


if __name__ == '__main__':
    filepath = r'e:\download' # 删除这个目录和子目录下所有文件
    st = time.perf_counter()
    se = get_files(filepath)
    delefiles(se.index)
    print(f'删除文件：{len(se.index)}', f'用时：{time.perf_counter() - st:.2f}秒')
