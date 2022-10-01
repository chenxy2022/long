"""
    只要把目录名传入main
    目录都是和第一个参数进行对比，
    除第一个外，目录内有重复的文件名的删除重复的（保留上层的文件）。
    参数:
    del_not_in:默认为True,删除b不在a中如果是False，删除b在a中的。（注意：重点）
"""
import os, time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor


def get_files(filepath):
    filenames = dict()
    fileandpath = os.walk(filepath)
    for p, subps, fs in fileandpath:
        for f in fs:
            fullf = os.path.join(p, f)
            filenames[fullf] = f
    return pd.Series(filenames, dtype='object')


def delefiles(in_files):
    # 多线程删除文件名
    with ThreadPoolExecutor() as executor:
        executor.map(os.remove, in_files)


def main(*filedirs, del_not_in):
    st = time.perf_counter()
    # 多线程读取文件名
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_files, filedir) for filedir in filedirs]
    r = ([x.result() for x in futures])

    if del_not_in:
        # 不包含在第一个目录中的文件
        del_files = pd.concat(x[~x.isin(r[0])] for x in r[1:])
    else:
        # 包含在第一个目录中的文件
        del_files = pd.concat(x[x.isin(r[0])] for x in r[1:])

    # 目录内不在删除范围内的重复文件
    dupli_files = pd.concat((se := x[~x.isin(del_files)])
                            [se.duplicated(keep='first')]
                            for x in r[1:])

    all_deletes = pd.concat((del_files, dupli_files)).index.drop_duplicates()
    # print(all_deletes, not_in_files, in_files)
    # 多线程删除
    delefiles(all_deletes)

    print(f'删除{"不包含" if del_not_in else "包含"}文件：{len(all_deletes)}个文件；\n'
          f'删除重复文件：{len(dupli_files)}个'
          f'用时：{time.perf_counter() - st:.2f}秒')


if __name__ == '__main__':
    '''
    只要把目录名传入main
    目录都是和第一个参数进行对比，
    除第一个外，目录内有重复的文件名的删除重复的（保留上层的文件）。
    参数:
    del_not_in:默认为True,删除b不在a中。如果是False，删除b在a中的。（注意：重点）
    '''
    main(r'D:\temp\a', r'D:\temp\b', r'D:\temp\c', del_not_in=True)
