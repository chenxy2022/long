'''
只要把目录名传入main就可以删除重复
目录都是和第一个参数进行对比，除第一个文档外有重复的全部删除
'''
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
    return pd.Series(filenames)


def delefiles(in_files):
    # 多线程删除文件名
    with ThreadPoolExecutor() as executor:
        executor.map(os.remove, in_files)


def main(*filedirs):
    st = time.perf_counter()
    # 多线程读取文件名
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_files, filedir) for filedir in filedirs]
    r = ([x.result() for x in futures])

    # 包含在第一个目录中的文档
    in_files = pd.concat(x[x.isin(r[0])] for x in r[1:])
    # 重复的文档
    dupli_files = pd.concat((se := x[~x.isin(r[0])])
                            [se.duplicated(keep='first')]
                            for x in r[1:])
    all_deletes = pd.concat((in_files, dupli_files)).index
    # 多线程删除
    delefiles(all_deletes)

    print(f'删除包含文件：{len(in_files)}个文件；\n删除重复文件：{len(dupli_files)}个。\n用时：{time.perf_counter() - st:.2f}秒')


if __name__ == '__main__':
    '''
    只要把目录名传入main就可以删除重复
    目录都是和第一个参数进行对比，
    除第一个外，目录内有重复的文件名的删除重复的（保留上层的文件）。
    '''
    main(r'D:\temp\a', r'D:\temp\b', r'D:\temp\c')
