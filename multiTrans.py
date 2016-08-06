#!/usr/bin/python
import sys
import paramiko
import os
import time
import string
import random
import stat
import thread
from ftplib import FTP




class BaseTransport(object):
    def __init__(self,host,port,user,password):
        self._host = host
        self._port = port
        self._user = user
        self._password = password


    def _viewBar(self,count,rate):
        output = sys.stdout
        output.write('\r%d%%' % count)
        if count < 10:
            output.write('  ')
        elif count < 100:
            output.write(' ')
        output.write('[')
        i=0
        while i <= 100:
            if i <= count:
                output.write('>')
            else:
                output.write(' ')
            i += 1.5

        output.write(']    ')
        output.write('%6.2f M/s' % rate)
        output.flush()


    def _progressBarShow(self,file_name,file_size,time_down_start,read_size=os):
        base_dir = '/' + '/'.join(file_name.strip('/').split('/')[:-1])
        base_name = os.path.basename(file_name)
        while 1:
            rate_time = time.time()
            if (read_size == os and os.path.exists(file_name)):
                rate_size = read_size.stat(file_name).st_size
                break
            elif (base_name in read_size.listdir(base_dir)):
                rate_size = read_size.stat(file_name).st_size
                break

            
            if rate_time - time_down_start > 10:
                print("Some wrong was happen")
                exit(1)
            time.sleep(0.1)
        while 1:
            file_recive_size = read_size.stat(file_name).st_size
            time_interval = time.time() - rate_time
            rate_time = time.time()
            count = file_recive_size / (file_size / 100)
            rate = (file_recive_size - rate_size) / time_interval / 1024 / 1024
            rate_size = file_recive_size
            self._viewBar(count,rate)
            if file_recive_size == file_size:
                break
            time.sleep(0.18)

        total_time = time.time() - time_down_start
        average_speed = file_size / 1024 /1024 /total_time
        self._viewBar(100,average_speed)
        print("\n")
        print("Time spend: %.2f s" % total_time)
        print("File size: %.2f M" % (file_size / 1024 /1024))
        print("Average speed: %.2f M/s" % average_speed)



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


    def _progressBarShow(self,file_name,file_size,time_down_start,read_size=os):
        base_dir = '/' + '/'.join(file_name.strip('/').split('/')[:-1])
        base_name = os.path.basename(file_name)
        while 1:
            rate_time = time.time()
            if (read_size == os and os.path.exists(file_name)):
                rate_size = read_size.stat(file_name).st_size
                break
            elif (base_name in read_size.listdir(base_dir)):
                rate_size = read_size.stat(file_name).st_size
                break

            
            if rate_time - time_down_start > 10:
                print("Some wrong was happen")
                exit(1)
            time.sleep(0.1)
        while 1:
            file_recive_size = read_size.stat(file_name).st_size
            time_interval = time.time() - rate_time
            rate_time = time.time()
            count = file_recive_size / (file_size / 100)
            rate = (file_recive_size - rate_size) / time_interval / 1024 / 1024
            rate_size = file_recive_size
            self._viewBar(count,rate)
            if file_recive_size == file_size:
                break
            time.sleep(0.18)

        total_time = time.time() - time_down_start
        average_speed = file_size / 1024 /1024 /total_time
        self._viewBar(100,average_speed)
        print("\n")
        print("Time spend: %.2f s" % total_time)
        print("File size: %.2f M" % (file_size / 1024 /1024))
        print("Average speed: %.2f M/s" % average_speed)



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
        self._ftp.set_debuglevel(1)
        self._ftp.connect(self._host,self._port)
        self._ftp.login(self._user,self._password)



    def download(self,remote_path,local_path):
        remote_dir = os.path.dirname(remote_path)
        remote_file = os.path.basename(remote_path)
        local_file = '/' + local_path.strip('/') + '/' + remote_file
        bufsize = 1024

        file_list= []
        self._ftp.dir(remote_dir,file_list.append)
        for name in file_list:
             file_name = name.split()
             if file_name[-1] == remote_file:
                 if file_name[0][0] == 'd':
                     os.system('mkdir -p %s' % local_file)
                     self._ftp.cwd(remote_path)
                     trans_files = self._ftp.nlst()
                     for trans_file in trans_files:
                         self.download(remote_path+'/'+trans_file,local_file)
                 else:
                     self._ftp.cwd(remote_dir)
                     file_handler = open(local_file,'wb').write
                     file_size = self._ftp.size(remote_path)
                     time_down_start = time.time()
                     self._ftp.retrbinary('RETR %s' % remote_file,file_handler,bufsize)

        #thread.start_new_thread(self._ftp.retrbinary,('RETR %s' % remote_file,file_handler,bufsize))
        #self._progressBarShow(local_file,file_size,time_down_start)


    def upload(self,local_path,remote_path):
        self._ftp.cwd(remote_path)
        bufsize =1024
        file_handler = open(local_path,'rb')
        self._ftp.storbinary('STOR %s' % os.path.basename(local_path),file_handler,bufsize)
        file_handler.close()


if __name__ == '__main__':
    #connect=SFTPTransport('cn02',22,'cn02','airation')
    #connect.download('/home/cn02/test/test.tar','/home/feng/test')
    #connect.upload('/home/feng/Transfile/fragment_cn05','/home/cn02/test')
    #connect = SCPTransport('cn02',22,'cn02','')
    #connect.download('/home/cn02/test/test.tar','/home/feng/test')
    #connect.upload('/home/feng/test/test.tar','/home/cn02/test')
    #connect.download('/home/cn02/test/test.tar','/home/feng/test')
    connect = FTPTransport('cn02',21,'cn02','airation')
    connect.download('/home/cn02/test/test','home/feng/test')
    #connect.upload('/home/feng/test/test.tar','/home/cn02/test/')
