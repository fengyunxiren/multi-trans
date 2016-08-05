#!/usr/bin/env python
import paramiko
import threading
import os
import stat
import random
import string
import time
class TransportFile:
    def __init__(self,host,port,username,password):
        self.host=host
        self.port=port
        self.username=username
        self.password=password
        self.__connectHost()

    def __connectHost(self):
        self.ssh=paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.host,self.port,username=self.username,password=self.password)
        self.sftp=self.ssh.open_sftp()

    def getFromRemote(self,remote_path,local_path):

        if stat.S_ISDIR(self.sftp.stat(remote_path).st_mode):
            tar_name='/tmp/'+self.__randomString(16)+'.tar'
            tar_name=str(tar_name)
            tar_dir=remote_path.strip('/').split('/')[-1]
            remote_dir='/'+'/'.join(remote_path.strip('/').split('/')[:-1])
            self.ssh.exec_command('cd %s' % remote_dir)
            self.ssh.exec_command('tar cvf %s %s >/dev/null' % (tar_name,tar_dir))
            time.sleep(0.01)
            
            start_size=self.sftp.stat(tar_name).st_size
            start_time=time.time()
            while (1):
                if (time.time()-start_time)>3600:
                    print 'The file is too big,or something wrong happen!'
                    exit(1)
                later_size=self.sftp.stat(tar_name).st_size
                if later_size==start_size:
                    break
                start_size=later_size
                time.sleep(0.1)

            self.sftp.get(tar_name,tar_name)
            self.ssh.exec_command('rm -rf %s' % tar_name)
            os.system('tar xvf %s -C %s >/dev/null' % (tar_name,local_path))
            os.system('rm -rf %s' % tar_name)
        else:
            file_name='/'+local_path.strip('/')+'/'+os.path.basename(remote_path)
            self.sftp.get(remote_path,file_name)
    
    def putToRemote(self,local_path,remote_path):
        if os.path.isdir(local_path):
            tar_name='/tmp/'+self.__randomString(16)+'.tar'
            tar_name=str(tar_name)
            tar_dir=local_path.strip('/').split('/')[-1]
            local_dir='/'+'/'.join(local_path.strip('/').split('/')[:-1])
            os.system('cd %s;tar cvf %s %s >/dev/null' % (local_dir,tar_name,tar_dir))
            self.sftp.put(tar_name,tar_name)
            os.system('rm -rf %s' % tar_name)
            self.ssh.exec_command('tar xvf %s -C %s >/dev/null' % (tar_name,remote_path))
            self.ssh.exec_command('rm -rf %s' % tar_name)
        else:
            file_name='/'+remote_path.strip('/')+'/'+os.path.basename(local_path)
            self.sftp.put(local_path,file_name)

    def __randomString(self,num):
        return ''.join(random.sample(string.ascii_letters+string.digits,num))
        
        

        
connect=TransportFile('cn05',22,'cn05','airation')
connect.getFromRemote('/home/cn05/fragment','/home/feng/Transfile')
#connect.putToRemote('/home/feng/wyc/trans/trans.py','/home/cn02')
