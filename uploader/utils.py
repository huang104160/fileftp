import os

import logging
import hashlib
import _hashlib


logger = logging.getLogger(__name__)

# 获取给定文件的 md5 哈希值，并返回 _HASH() 对象
def get_hash_data(path):
    '''获取一个 _HASH 对象'''
    hash = hashlib.md5()
    with open(path, 'rb') as f:
        while 1:
            data = f.read(64 * 1024)
            if data:
                hash.update(data)
            else: break
    return hash

"""
也是用于获取文件哈希值，但是该函数不返回 _HASH() 对象，而是返回哈希值的十六进制表示字符.
"""
def get_bin_hash(bin):
    return hashlib.md5(bin).hexdigest()
 

def get_file_hash(path):
    return get_hash_data(path).hexdigest()

# 检查文件或数据的哈希值是否与指定的哈希值相等。
def check_hash(bin, hash_str):
    if isinstance(bin, _hashlib.HASH):
        hash_str1 = bin.hexdigest()
    elif isinstance(bin, bytes):
        hash = hashlib.md5()
        hash.update(bin)
        hash_str1 = hash.hexdigest()
    else: raise TypeError(f'check_hash parameter type error: {type(bin)}')

    return hash_str1 == hash_str

# 函数用于更新数据的哈希值。
def update_hash(bin, hash=None):
    ''' hash _Hash 对象'''
    if not hash:
        hash = hashlib.md5()
    hash.update(bin) 
    return hash

# 用于将 byte 数组类型的数据转换成 int 对象以及将 int 类型的数据转换成 byte 数组类型。
def bytes_to_int(bin):
    return int.from_bytes(bin, byteorder='big', signed=False)


def int_to_bytes(number):
    return int(number).to_bytes(length=4, byteorder='big', signed=False)

# 函数用于获取文件的大小。
def file_size(path):  
    return os.path.getsize(path)
  
# 函数用于删除指定的文件。
def remove_file(path): 
    if os.path.exists(path):
        os.remove(path) 

# 用于创建一个空文件。
def create_blank_file(path):
    with open(path, 'wb') as f:
        f.write(b'')

# 用于解压缩 zip 格式的文件。
def unzip(file):
    import zipfile
    f = zipfile.ZipFile(file, 'r')
    path = os.path.dirname(file)
    for _ in f.namelist():
        #使用成员的全名将其从存档文件中提取到当前工作目录。
        # 它的文件信息被尽可能准确地提取出来。member'可以是文件名或ZipInfo对象。您可以使用path'指定一个不同的目录。
        f.extract(_, path)
         
# 函数用于获取指定文件的内容。
def get_file_content(file):
    with open(file, 'r') as f:
        data = f.read()
    return data
 

if __name__ == '__main__':
    import time
    start = time.time()
    get_file_hash('/Users/dushanchen/githome/whale/bak/test/test.zip')
    print('time: ', time.time() - start)