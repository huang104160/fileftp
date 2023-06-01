import sys
import time
import json
import socket 


from .utils import *


''' 上传下载文件 TCP 客户端  '''
 

class Client:
    sock = None
    def __init__(self, ip, port, token=None) -> None:
        self.ip, self.port = ip, port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.ip, self.port))
        self.sock = sock

        self.hash_data = None
        self.finished = False
        self.file_reader = None
        self.file_writer = None

    def upload(self, taskid, filepath):
        '''
            params: filepath, file absolute path
        '''
        print('ready to upload... ')
        self.start_time = time.time()
        
        if not self.sock:
            self.__init__(self.ip, self.port)
            
        self.taskid = taskid
        self.filepath = filepath
        self.filename = filename = filepath.replace('\\','/').split('/')[-1]
        
        hash = get_file_hash(filepath)
        file_len = file_size(filepath) 

        self.file_reader = open(self.filepath, 'rb')

        self.__send(3, msg={
            'filename': filename, 
            'size': file_len,
            'taskid': taskid, 
            'hash': hash
        })
        print('start upload ... ')
        self.__loop()

    def __upload_part(self, msg, bin):
        start = msg['start']
        size = msg['size']

        self.file_reader.seek(start)
        bin = self.file_reader.read(size)
        bin_len = len(bin)
       
        hash = get_bin_hash(bin)

        self.__send(5, msg={
            'filename': self.filename, 
            'taskid': self.taskid,
            'start': start,
            'size': bin_len,
            'hash': hash
        }, bin=bin)
        

    def download(self, taskid, filename, target_dir='.'):
        '''
            target_dir: A local path where to save file
        '''
        if not self.sock:
            self.__init__(self.ip, self.port)
        self.start_time = time.time()

        self.target_dir = target_dir 
        self.filename = filename
        self.taskid = taskid
        if not os.path.exists(os.path.join(target_dir, taskid)):
            os.mkdir(os.path.join(target_dir, taskid))
        self.filepath = os.path.join(self.target_dir, self.taskid, self.filename)
        self.file_writer = open(self.filepath, 'ab')

        self.__send(7, msg={
            'filename': filename,
            'taskid': taskid,
        })

        self.__loop()

    def __download_part(self, msg, bin):
        
        self.hash = hash = msg['hash']
        start = 0

        hash_dir = self.filepath+'.hash'
        if os.path.exists(hash_dir):
            old_hash = get_file_content(hash_dir)
            if old_hash != hash:
                with open(hash_dir, 'w') as f:
                    f.write(hash)
                create_blank_file(self.filepath)
            else:
                start = file_size(self.filepath)
                self.hash_data = get_hash_data(self.filepath)
        else:
            with open(hash_dir, 'w') as f:
                f.write(hash)
            create_blank_file(self.filepath)

        self.__send(9, msg={
            'filename': self.filename,
            'taskid': self.taskid,
            'start': start
        })
    
    def __save_part(self, msg, bin):
        hash = msg['hash']
        size = msg['size']
        start = msg['start']
        file_hash = get_bin_hash(bin)
        self.hash_data = update_hash(bin, self.hash_data)

        if size == 0: # 已经下载完毕
            if not check_hash(self.hash_data, self.hash):
                raise Exception('End check hash faild!')
            else:
                print('file download success')
            self.__close()
            return 
        if hash != file_hash: raise Exception(f'Hash check faild!')

        self.file_writer.write(bin)
        
        self.__send(9, msg={
            'filename': self.filename,
            'taskid': self.taskid,
            'start': start
        })

    def __check_auth(self):
        pass
 
    def __receive(self):
        '''读取一次消息''' 
        data = self.sock.recv(12)
        msg_type = bytes_to_int(data[:4])
        msg_length = bytes_to_int(data[4:8])
        binary_length = bytes_to_int(data[8:]) 

        msg = json.loads(self.__read_bytes(msg_length).decode()) 
        bin = self.__read_bytes(binary_length) 
        
        print(f'server --> , {msg_type}, {msg_length}, {binary_length}, {msg}')
 
        return msg_type, msg, bin

    def __send(self, msg_type, msg, bin=b''):
        '''发送一次消息'''
        print(f'--> server, {msg_type}, {msg}')
        msg = json.dumps(msg).encode('utf-8')
        msg_len = int_to_bytes(len(msg))
        msg_type = int_to_bytes(msg_type)
        bin_len = int_to_bytes(len(bin) if bin else 0)
        
        write_buffer = msg_type + msg_len + bin_len + msg + bin
        self.sock.send(write_buffer)

    def __read_bytes(self, l):
        count = 0
        result = b''
        while count < l:
            data = self.sock.recv(l - count)
            count += len(data)
            result += data

        return result
    
    def __raise_error(self, msg, bin):
        error = msg['error']
        raise Exception(error)
    
    def __close(self, msg=None, bin=None):
        if self.sock: 
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            self.sock = None
        if self.file_reader:
            self.file_reader.close()
        if self.file_writer:
            self.file_writer.close()
        self.finished = True
        
        print(f'传输用时： {round(time.time() - self.start_time)} s')

    def __loop(self):
        types = {
            0: self.__close,
            2: self.__check_auth,
            4: self.__upload_part,
            6: self.__close,
            8: self.__download_part,
            10: self.__save_part,
            12: self.__raise_error
        }
        try:
            while not self.finished:
                msg_type, msg, bin = self.__receive()
                print(msg_type, msg)
                types[msg_type](msg, bin)
                 
        except InterruptedError:
            self.__close()

        print('Connection closed !')


'''test'''

def test_upload():
    path = '/Users/dushanchen/githome/whale/bak/task3/test.zip'
    client = Client('localhost', 7322)
    # client = Client('192.168.91.24', 7322)
    client.upload('10', path)


def test_download():
    path = '/Users/dushanchen/githome/whale/bak'
    # client = Client('localhost', 7322)
    client = Client('192.168.91.23', 7322)
    client.download('588', 'result.zip', path)


if __name__ == '__main__':
    test_download() 