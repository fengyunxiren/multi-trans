#!/usr/bin/python
import sys
import paramiko
import os
import time
import string
import random
import stat
import thread
import threading
from ftplib import FTP
import socket
import struct
import logging
import sys
import argparse
import getpass

# used for fbtftp
DEFAULT_BLKSIZE = 512
OPCODE_RRQ = 1 
OPCODE_DATA = 3
OPCODE_ACK = 4
OPCODE_OACK = 6
ERROR = 1
SUCCESS = 0 

class BaseTransport(object):
    def __init__(self,host,port,user,password):
        self._host = host
        self._port = port
        self._user = user
        self._password = password


    def _viewBar(self,count,rate,rate_units = 'Kb/s',get_size = '',total_size = '',used_time = ''):
        output = sys.stdout
        output.flush()
        output.write('\r %d%%' % count)
        if count < 10:
            output.write('  ')
        elif count < 100:
            output.write(' ')
        output.write('[')
        length_bar = 50
        i = length_bar * count / 100
        output.write(i * '>' + (length_bar - i) * ' ')
        output.write(']  ')
        output.write('%s/%s Kb' % (get_size,total_size))
        output.write('  %6.2f ' % rate + rate_units)
        output.write('  %.0f s' % used_time)
        output.flush()

    def _progressBarShow(self,file_name,file_size,time_down_start,read_size=os):
        base_dir = os.path.basename(file_name)
        base_name = os.path.basename(file_name)

        while True:
            rate_time = time.time()
            if (read_size == os and os.path.exists(file_name)):
                rate_size = read_size.stat(file_name).st_size
                break
            elif (base_name in read_size.listdir(base_dir)):
                rate_size = read_size.stat(file_name).st_size
                break
            if rate_time - time_down_start > 10:
                print("File %s not exist in %s" % (base_name,base_dir))
                exit(1)
            time.sleep(0.1)

        while True:
            file_receive_size = read_size.stat(file_name).st_size
            time_interval = time.time() - rate_time
            rate_time = time.time()
            count = file_receive_size / (file_size / 100)
            rate = (file_receive_size - rate_size) / time_interval / 1024
            rate_size = file_receive_size
            time_left = (file_size - file_receive_size) / 1024 / (1 if rate == 0 else rate)
            if rate > 1024:
                rate /= 1024
                self._viewBar(count,rate,'Mb/s',file_receive_size/1024,file_size/1024,time_left)
            else:
                self._viewBar(count,rate,get_size = file_receive_size/1024,total_size = file_size/1024,used_time = time_left)
            if file_receive_size == file_size:
                break
            time.sleep(0.8)

        total_time = time.time() - time_down_start
        average_speed = file_size / 1024 / total_time
        rate_units = 'Kb/s'
        if average_speed > 1024:
            average_speed /= 1024
            rate_units = 'Mb/s'
            self._viewBar(100,average_speed,rate_units,file_receive_size/1024,file_size/1024,total_time)
        else:
            self._viewBar(100,average_speed,get_size = file_receive_size/1024,total_size = file_size/1024,used_time = total_time)
        print("\n")


class SFTPTransport(BaseTransport):
    def __init__(self,host,port,user,password):
        super(SFTPTransport,self).__init__(host,port,user,password)
        self.__connectHost()



    def __connectHost(self):
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._ssh.connect(self._host,self._port,username = self._user,password = self._password)
        self._sftp = self._ssh.open_sftp()



    def download(self,remote_path,local_path):
        if stat.S_ISDIR(self._sftp.stat(remote_path).st_mode):
            tar_name = '/tmp/' + self.__randomString(16) + '.tar'
            tar_name = str(tar_name)
            tar_dir = remote_path.strip('/').split('/')[-1]
            remote_dir = '/' + '/'.join(remote_path.strip('/').split('/')[:-1])
            self._ssh.exec_command('cd %s;tar cvf %s %s > /dev/null' % (remote_dir,tar_name,tar_dir))
            time.sleep(0.01)

            start_size = self._sftp.stat(tar_name).st_size
            start_time = time.time()
            while 1:
                if (time.time() - start_time) > 3600:
                    print("The file is too big or something wrong happened")
                    exit(1)
                later_size = self._sftp.stat(tar_name).st_size
                if later_size == start_size:
                    break
                start_size= later_size
                time.sleep(0.1)

            thread.start_new_thread(self._progressBarShow,(tar_name,start_size,start_time))



            self._sftp.get(tar_name,tar_name)
            self._ssh.exec_command('rm -rf %s' % tar_name)
            if os.path.exists(tar_name):
                os.system('tar xvf %s -C %s > /dev/null' % (tar_name,local_path))
                os.system('rm -rf %s' % tar_name)
        else:
            file_name = '/' + local_path.strip('/') + '/' + os.path.basename(remote_path)
            file_size = self._sftp.stat(remote_path).st_size
            time_down_start = time.time()
            if os.path.exists(file_name):
                os.system('rm -rf %s' % file_name)

            thread.start_new_thread(self._sftp.get,(remote_path,file_name))
            self._progressBarShow(file_name,file_size,time_down_start)



    def upload(self,local_path,remote_path):
	if os.path.isdir(local_path):
            tar_name = '/tmp/'+self.__randomString(16)+'.tar'
            tar_name = str(tar_name)
            tar_dir = local_path.strip('/').split('/')[-1]
            local_dir = '/'+'/'.join(local_path.strip('/').split('/')[:-1])
            time_down_start = time.time()
            os.system('cd %s;tar cvf %s %s >/dev/null' % (local_dir,tar_name,tar_dir))
            file_size = os.stat(tar_name).st_size   
            thread.start_new_thread(self._sftp.put,(tar_name,tar_name))
            new_sftp = self._ssh.open_sftp()
            self._progressBarShow(tar_name,file_size,time_down_start,new_sftp)
            new_sftp.close()
            os.system('rm -rf %s' % tar_name)
            self._ssh.exec_command('tar xvf %s -C %s >/dev/null;rm -rf %s' % (tar_name,remote_path,tar_name))
            
        else:
            file_name = '/'+remote_path.strip('/')+'/'+os.path.basename(local_path)
            file_size = os.stat(local_path).st_size
            time_down_start = time.time()

            thread.start_new_thread(self._sftp.put,(local_path,file_name))
            new_sftp = self._ssh.open_sftp()
            self._progressBarShow(file_name,file_size,time_down_start,new_sftp)
            new_sftp.close()
            




    def __randomString(self,num):
        return ''.join(random.sample(string.ascii_letters+string.digits,num))


   # def _progressBarShow(self,file_name,file_size,time_down_start,read_size=os):
   #     base_dir = '/' + '/'.join(file_name.strip('/').split('/')[:-1])
   #     base_name = os.path.basename(file_name)
   #     while 1:
   #         rate_time = time.time()
   #         if (read_size == os and os.path.exists(file_name)):
   #             rate_size = read_size.stat(file_name).st_size
   #             break
   #         elif (base_name in read_size.listdir(base_dir)):
   #             rate_size = read_size.stat(file_name).st_size
   #             break

            
#            if rate_time - time_down_start > 10:
#                print("Some wrong was happen")
#                exit(1)
#            time.sleep(0.1)
#        while 1:
#            file_recive_size = read_size.stat(file_name).st_size
#            time_interval = time.time() - rate_time
#            rate_time = time.time()
#            count = file_recive_size / (file_size / 100)
#            rate = (file_recive_size - rate_size) / time_interval / 1024 / 1024
#            rate_size = file_recive_size
#            self._viewBar(count,rate)
#            if file_recive_size == file_size:
#                break
#            time.sleep(0.18)
#
#        total_time = time.time() - time_down_start
#        average_speed = file_size / 1024 /1024 /total_time
#        self._viewBar(100,average_speed)
#        print("\n")
#        print("Time spend: %.2f s" % total_time)
#        print("File size: %.2f M" % (file_size / 1024 /1024))
#        print("Average speed: %.2f M/s" % average_speed)



class SCPTransport(BaseTransport):
    def __init__(self,host,port,user,password):
        super(SCPTransport,self).__init__(host,port,user,password)



    def download(self,remote_path,local_path):
        os.system('scp -r %s@%s:%s %s' % (self._user,self._host,remote_path,local_path))


    def upload(self,local_path,remote_path):
        os.system('scp -r %s %s@%s:%s' % (local_path,self._user,self._host,remote_path))



class FTPTransport(BaseTransport):
    def __init__(self,host,port,user,password):
        super(FTPTransport,self).__init__(host,port,user,password)
        #self._ftp = None
        self.__connectHost()


    def __del__(self):
        if self._ftp:
            self._ftp.close()



    def __connectHost(self):
        self._ftp = FTP()
#        self._ftp.set_debuglevel(1)
        self._ftp.connect(self._host,self._port)
        self._ftp.login(self._user,self._password)



    def download(self,remote_path,local_path):
        remote_dir = os.path.dirname(remote_path)
        remote_file = os.path.basename(remote_path)
        local_file = '/' + local_path.strip('/') + '/' + remote_file
        bufsize = 1024

        #file_list= []
        #self._ftp.dir(remote_dir,file_list.append)
        #for name in file_list:
        #     file_name = name.split()
        #     if file_name[-1] == remote_file:
        #         if file_name[0][0] == 'd':
        #             os.system('mkdir -p %s' % local_file)
        #             self._ftp.cwd(remote_path)
        #             trans_files = self._ftp.nlst()
        #             for trans_file in trans_files:
        #                 self.download(remote_path+'/'+trans_file,local_file)
        #         else:
        #             self._ftp.cwd(remote_dir)
        #             file_handler = open(local_file,'wb').write
        #             file_size = self._ftp.size(remote_path)
        #             time_down_start = time.time()
        #             self._ftp.retrbinary('RETR %s' % remote_file,file_handler,bufsize)
        file_list = self._ftp.nlst(remote_path)
        if len(file_list) > 1 or file_list[0] != remote_path:
             os.system('mkdir -p %s' % local_file)
             self._ftp.cwd(remote_path)
             trans_files = self._ftp.nlst()
             for trans_file in trans_files:
                 trans_path = '/' + remote_path.strip('/') + '/' + trans_file
                 self.download(trans_path,local_file)
        else:
             self._ftp.cwd(remote_dir)
             file_handler = open(local_file,'wb').write
             file_size = self._ftp.size(remote_path)
             time_down_start = time.time()
             #thread.start_new_thread(self._progressBarShow,(local_file,file_size,time_down_start))
             #t1 = threading.Thread(target = self._progressBarShow,args = (local_file,file_size,time_down_start))
             #t1.start()
             thread.start_new_thread(self._progressBarShow,(local_file,file_size,time_down_start))
             self._ftp.retrbinary('RETR %s' % remote_file,file_handler,bufsize)
             #thread.start_new_thread(self._ftp.retrbinary,('RETR %s' % remote_file,file_handler,bufsize))
             #self._progressBarShow(local_file,file_size,time_down_start)




    def upload(self,local_path,remote_path):
        if os.path.isdir(local_path):
            save_path = '/' + remote_path.strip('/') +'/' + os.path.basename(local_path)
            self._ftp.mkd(save_path)
            self._ftp.cwd(save_path)
            trans_files = os.listdir(local_path)
            for trans_file in trans_files:
                trans_path = '/' + local_path.strip('/') + '/' + trans_file
                self.upload(trans_path,save_path)
        else:
            self._ftp.cwd(remote_path)
            bufsize =1024
            file_handler = open(local_path,'rb')
            self._ftp.storbinary('STOR %s' % os.path.basename(local_path),file_handler,bufsize)
            file_handler.close()



class FBTFTPTransport(BaseTransport):
    def __init__(self,host,port,user,password = '',mode = 'octet',options={'retries':3,'tsize':1}):
        self._host=host
        self._port=port
        self._user=user
        self._mode=mode
        self._options=options
        self._client_socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self._read_size=0
        if 'timeout' in self._options:
            self._timeout=self._options['timeout']
        else:
            self._timeout=10
        if 'blksize' in self._options:
            self._blksize=self._options['blksize']
        else:
            self._blksize=DEFAULT_BLKSIZE

    def _sendToServer(self,path):
        if self._mode != 'netascii' and self._mode != 'octet':
            logging.error(
                    "Unexpected mode: %s, expected 'netascii' or 'octet'" % self._mode)
            return ERROR
        
        packet=[]
        packet.append(
                struct.pack(
                    '%dsx%dsx' % (len(path),len(self._mode)),bytes(path.encode('latin-1')),bytes(self._mode.encode('latin-1'))
                    )
                )
        for key,value in self._options.items():
            fmt=str('%dsx%ds' % (len(key),len(str(value))))
            packet.append(
                    struct.pack(
                        fmt,bytes(key.encode('latin-1')),bytes(str(value).encode('latin-1'))
                        )
                    )
        packet.append(b'')
        send_pack=struct.pack('!H',OPCODE_RRQ) +b'\x00'.join(packet)

        self._client_socket.sendto(send_pack,(self._host,self._port))
        return SUCCESS

    def _receiveFromServer(self,path):
        if 'timeout' in self._options or 'blksize' in self._options or 'tsize' in self._options:
            try:
                self._client_socket.settimeout(self._timeout)
                recv_oack,oack_addr=self._client_socket.recvfrom(DEFAULT_BLKSIZE)
                self._client_socket.settimeout(self._timeout)
                oack_head=struct.unpack('!H',recv_oack[:2])[0]
                if oack_head != OPCODE_OACK:
                    error_infos=list(filter(bool,recv_oack[2:].decode('latin-1').split('\x00')))
                    for error_info in error_infos:
                        print(error_info)
                    logging.error(
                            "OACK head error:%s,expected %s" % (oack_head,OPCODE_OACK)
                            )
                    return ERROR
                tokens=list(filter(bool,recv_oack[2:].decode('latin-1').split('\x00')))
                if len(tokens) <2 or len(tokens) %2 !=0:
                    logging.error(
                            "OACK body error!"
                            )
                    exit(1)
                pos=0
                while pos<len(tokens):
                    self._options[tokens[pos].lower()]=int(tokens[pos+1])
                    pos+=2

                send_oack=struct.pack('!HH',OPCODE_ACK,0)
                self._client_socket.sendto(send_oack,oack_addr)
            except socket.timeout:
                logging(
                        "Timeout occured on socket.recvfrom"
                        )
                return ERROR

        file_open=open(path,'wb')
        rate_time=time.time()
        rate_size=self._read_size
        start_time=rate_time
        while True:
            try:
                self._client_socket.settimeout(self._timeout)
                recv_packet,server_addr=self._client_socket.recvfrom((DEFAULT_BLKSIZE+4))
                self._client_socket.settimeout(None)
            except socket.timeout:
                logging.error(
                        "Timeout occurred on socket.recvfrom"
                        )
                file_open.close()
                return ERROR

            recv_head=recv_packet[:4]
            head=struct.unpack('!HH',recv_head)
            if head[0] != OPCODE_DATA:
                error_infos=list(filter(bool,recv_packet[2:].decode('latin-1').split('\x00')))
                for error_info in error_infos:
                    print(error_info)

                logging.error(
                        "Unexpected receive block head: %d expected %d" % (head[0],OPCODE_DATA)
                        )
                return ERROR
            file_open.write(recv_packet[4:])
            self._read_size+=len(recv_packet[4:])
            if len(recv_packet[4:]) < self._blksize or self._read_size==self._options['tsize']:
                break
            send_head=struct.pack('!HH',OPCODE_ACK,head[1])
            self._client_socket.sendto(send_head,server_addr)
            time_interval=time.time()-rate_time

#            print self._read_size
#            print self._options['tsize']

            if time_interval>0.18:
                count=self._read_size / (self._options['tsize'] / 100)
                rate=(self._read_size-rate_size)/1024/1024/time_interval
                self._viewBar(count,rate)
                rate_time=time.time()
                rate_size=self._read_size

        file_open.close()
        total_time=time.time()-start_time
        count=self._read_size / (self._options['tsize'] / 100)
        rate=(self._read_size/1024/1024)/total_time
        self._viewBar(count,rate)
        print('\nFile size: %.2f (M)' % (self._read_size/1024/1024))
        print('Spend Time: %.2f (s)' % total_time)
        print('Average speed: %.2f (M/s)' % rate)
        self._read_size=0
        return SUCCESS



    def download(self,remote_path,local_path):
        local_path = '/' + local_path.strip('/') + '/' + os.path.basename(remote_path)
        self._sendToServer(remote_path)
        self._receiveFromServer(local_path)
        self._close()
    def upload(self,local_path,remote_path):
        print("Now fbtftp can not upload file!")

    def _close(self):
        self._client_socket.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
            "-t",
            "--transport",
            type = str,
            default = 'scp',
            help = "Select your desired transfer protocol(scp,ftp,sftp,fbtftp). default scp."
            )
    parser.add_argument(
            "-p",
            "--port",
            default = 1969,
            help = "port to bind to, fbtftp used."
            )
    parser.add_argument(
            "send_file",
            help = "The file you want to transfer"
            )
    parser.add_argument(
            "receive_path",
            help = "recerve path"
            )
    
    args = parser.parse_args()
    trans_method = {
            'scp':SCPTransport,
            'sftp':SFTPTransport,
            'ftp':FTPTransport,
            'fbtftp':FBTFTPTransport
            }
    port = {
            'scp': '',
            'sftp':22,
            'ftp':21,
            'fbtftp':args.port
            }

    if len(args.receive_path.split(':')) > 1:
        up_or_down = 'up'
        send_file = args.send_file
        temp = args.receive_path.split(':')
        receive_path = temp[-1]

        user_and_host = temp[0].split('@')
        if len(user_and_host) > 1:
            user = user_and_host[0]
            host = user_and_host[-1]
        else:
            user = getpass.getuser()
            host = user_and_host[0]
    else:
        up_or_down = 'down'
        receive_path = args.receive_path
        if len(args.send_file.split(':')) > 1:
            temp = args.send_file.split(':')
            send_file = temp[-1]
            user_and_host = temp[0].split('@')
            if len(user_and_host) > 1:
                user = user_and_host[0]
                host = user_and_host[-1]
            else:
                user = getpass.getuser()
                host = user_and_host[0]
        else:
            send_file = args.send_file
            user = getpass.getuser()
            host = socket.gethostname()
    if args.transport != 'scp':
        password = getpass.getpass(prompt = "%s's pass word:" % '@'.join([user,host]))
    else:
        password = ''
    connect=trans_method.get(args.transport)(host,port.get(args.transport),user,password)
    call_function = {
        'up':connect.upload,
        'down':connect.download
        }
    call_function.get(up_or_down)(send_file,receive_path)




if __name__ == '__main__':
    #connect=SFTPTransport('cn02',22,'cn02','airation')
    #connect.download('/home/cn02/test/test.tar','/home/feng/test')
    #connect.upload('/home/feng/Transfile/test.tar','/home/cn02/test')
    #connect = SCPTransport('cn02',22,'cn02','')
    #connect.download('/home/cn02/test/test.tar','/home/feng/test')
    #connect.upload('/home/feng/test/test.tar','/home/cn02/test')
    #connect.download('/home/cn02/test/test.tar','/home/feng/test')
    #connect = FTPTransport('cn02',21,'cn02','airation')
    #connect.download('/home/cn02/test/test.tar','home/feng/test')
    #connect.upload('/home/feng/test/test.tar','/home/cn02/test')
    #server_path=sys.argv[1]
    #local_path=sys.argv[2]
    #connect=FBTFTPTransport('127.0.0.1',1969,'octet')
    #connect.download('/home/feng/test/test.tar','/home/feng/Transfile')
    main()

