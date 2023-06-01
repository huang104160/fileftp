import os
import sys
import json
import socket 
import threading 


from .utils import check_hash, get_bin_hash, update_hash, bytes_to_int, int_to_bytes, file_size, remove_file, get_hash_data, create_blank_file, unzip, get_file_content

 
''' 上传下载文件 TCP 服务端 '''


print(sys.argv)
path = sys.argv[1].split('=')[1] if len(sys.argv) >= 2 else r'C:\upload'
# path = sys.argv[1].split('=')[1] if len(sys.argv) >= 2 else '/Users/dushanchen/githome/whale/bak/'

class Uploader(object):

    part_size = 3*1024*1024  
    global path
    base_dir = path

    def __init__(self, client, addr):
        self.client = client
        self.addr = addr
        self.auth = False
        self.taskid = None
        self.hash = ''
        self.hash_data = None
        self.filename = ''
        self.total = -1
        self.uploaded = 0 

    def loop(self):
        handlers = {
            3: self.__start_upload,
            5: self.__save_file_part, 
            7: self.__start_download,
            9: self.__download_part, 
        }
         
        while 1:
            try:
                msg_type, msg, bin = self.__receive() 
                
                if msg_type in handlers:
                    func = handlers[msg_type]
                    func(msg, bin)
                else: break

            except InterruptedError:
                print('client disconnected !')
                break
            except FileNotFoundError as e: 
                self.__send_error(f'File not found: {self.taskid}/{self.filename}')
                break
            except Exception as e:
                self.__send_error(e)
                break
 

    def __read_bytes(self, l):
        count = 0
        result = b''
        while count < l:
            data = self.client.recv(l - count)
            count += len(data)
            result += data

        return result

    def __receive(self):
        '''读取一次消息''' 
        data = self.client.recv(12)
        if len(data) == 0: raise InterruptedError()

        msg_type = bytes_to_int(data[:4])
        msg_length = bytes_to_int(data[4:8])
        binary_length = bytes_to_int(data[8:])
        # print(f'client --> {msg_type}, {msg_length}, {binary_length}')
        
        msg = json.loads(self.__read_bytes(msg_length).decode()) 
        bin = self.__read_bytes(binary_length) 
 
        return msg_type, msg, bin
    
    def __send(self, msg_type, msg, bin=b''):
        '''发送一次消息'''
        print(f'--> client {msg_type}, {msg}')
        msg = json.dumps(msg).encode('utf-8') 
        msg_len = int_to_bytes(len(msg))
        msg_type = int_to_bytes(msg_type)
        bin_len = int_to_bytes(len(bin) if bin else 0)
        
        write_buffer = msg_type + msg_len + bin_len + msg + bin
        self.client.send(write_buffer)

    def __check_auth(self, msg, bin):
        pass 
        '''鉴权'''
        self.auth = True

    def __start_upload(self, msg, bin):
        self.taskid = taskid = msg['taskid']
        self.filename = filename = msg['filename']
        self.total = size = msg['size']
        self.hash = msg['hash']
        
        print ('Start uploading file for task: ', taskid)
        
        short_name = filename.split('/')[-1]
        file_dir = os.path.join(self.base_dir, taskid)
        file_path = os.path.join(file_dir, short_name)
         
        start = 0
        
        if not os.path.exists(file_dir): # 创建文件目录
            os.mkdir(file_dir)

           # 检查hash值是否变化
        if os.path.exists(file_path + '.hash'): 
            with open(file_path + '.hash', 'r+') as f:
                hash = f.readline() 
                if hash != self.hash: 
                    print('hash', self.hash)
                    print('old hash', hash)
                    f.seek(0)
                    f.write(self.hash) # hash 不一致， 说明文件有变化， 删除旧文件
                    remove_file(file_path) 
                    print(f'old file deleted: {filename}')
        else:
            with open(file_path + '.hash', 'w') as f:
                f.write(self.hash)
        if os.path.exists(file_path):
            # 文件无变化， 找到断点重传
            start = file_size(file_path)  
            self.hash_data = get_hash_data(file_path)
            self.uploaded = start 
        else:
            create_blank_file(file_path) # 创建空文件
            
        print ('file upload start: ', filename, size)

        self.__send(4, {
            'filename': filename,
            'start': start,
            'size': self.part_size
        })

    def __save_file_part(self, msg, bin):  # 分段接收文件
        print(f'recv file - msg:{msg}, bin_len: {len(bin)} ')
        filename = msg['filename']
        file_path = os.path.join(self.base_dir, self.taskid, filename)
        self.hash_data = update_hash(bin, self.hash_data)  # 更新全文件 hash对象
             
        if not check_hash(bin, msg['hash']): # 校验part hash
            raise Exception(f'check part hash error: {msg["hash"]}') 
        if len(bin) > self.part_size:
            raise Exception(f'file length error: {len(bin)} > {self.part_size} ')
        with open(file_path, 'ab') as f:  # 保存 part
            f.write(bin) 

        if self.uploaded + msg['size'] >= self.total:  # 如果已传完
            if not check_hash(self.hash_data, self.hash):
                print(f'End file hash error, taskid:{self.taskid}, filename:{self.filename}')
            elif file_size(file_path) != self.total: 
                print(f'File size error, taskid:{self.taskid}, filename:{self.filename}')
            else:
                print(f'File upload success !!! ---- taskid:{self.taskid}, filename:{self.filename}') 
         
            print('start unzip ...')
            if 'zip' in filename: unzip(file_path)
            self.__finished()
            print('Finished !!!')
            return

        self.uploaded = msg['start'] + self.part_size
 
        self.__send(4, {
            'filename': filename,
            'start': self.uploaded,
            'size': self.part_size
        })

    def __start_download(self, msg, bin):  # 开始下载文件
        # 文件 hash， size， 
        print('ready to download ...') 
        print('msg--:', msg)
        self.taskid = msg['taskid']
        self.filename = msg['filename'] 
        self.filepath = os.path.join(self.base_dir, self.taskid, self.filename)
        size = file_size(self.filepath)
        hash = get_file_content(self.filepath + '.hash')

        self.__send(8, {
            'taskid': self.taskid,
            'filename': self.filename,
            'size': size,
            'hash': hash
        })  

    def __download_part(self, msg, bin):
        # 获取文件部分，
        start = msg['start']
        if start > file_size(self.filepath): # 下载完毕
            self.__finished()
            return
        with open(self.filepath, 'rb') as f:
            f.seek(start)
            bin = f.read(self.part_size)
            hash = get_bin_hash(bin)
        self.__send(10, {
            'taskid': self.taskid,
            'filename': self.filename,
            'hash': hash, 
            'start': start + len(bin), 
            'size': len(bin)
        }, bin)

    def __send_error(self, e):
        self.__send(12, {
            'taskid': self.taskid,
            'filename': self.filename,
            'error': str(e)
        })

    def __finished(self):
        self.__send(0, {
            'taskid': self.taskid,   
            'size': 0
        }) 
        

def worker():
    client, addr = server.accept()
    print ('Connected:', addr)
  
    upload = Uploader(client, addr) 
    
    thread = threading.Thread(target=upload.loop)
    thread.start() 
    print(' Connection stopped, ', addr)


if __name__ == '__main__':
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    host = '0.0.0.0'
    port = 7322

    server.bind((host, port)) 
    server.listen()
    print(f'server start, listen on {host}:{port} ...')
    print(f'filepath: {path}')
    while True:
        worker()
  
 