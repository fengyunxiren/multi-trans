#!/usr/bin/env python
import paramiko
import threading
import os
import time

def transportFile(host,port,username,password,remote_path,local_path,d_or_u):

    transport=paramiko.Transport((host,port))
    transport.connect(username=username,password=password)
    sftp=paramiko.SFTPClient.from_transport(transport)
    
    if (d_or_u=='d'):
        if (remote_path[-1] =='/'):
            files=sftp.listdir(remote_path)
            for f in files:
                sftp.get(os.path.join(remote_path,f),os.path.join(local_path,f))
        else:
            sftp.get(remote_path,local_path)

        sftp.close()
    elif(d_or_u=='u'):
        if (local_path[-1]=='/'):
            files=os.listdir(local_path)
            for f in files:
                sftp.put(os.path.join(local_path,f),os.path.join(remote_path,f))
        else:
            sftp.put(local_path,remote_path)

        sftp.close()
    else:
        print "Error:The last paramater must 'd' or 'u'\n"
        exit(1)



class transportThread(threading.Thread):
    def __init__(self,host,port,username,password,remotepath,localpath,d_or_u):
        threading.Thread.__init__(self)
        self.host=host
        self.port=port
        self.username=username
        self.password=password
        self.remotepath=remotepath
        self.localpath=localpath
        self.d_or_u=d_or_u

    def run(self):
        print "Starting mission %s->%s\n" % (self.username,self.d_or_u)
        start_time=time.time()

        transportFile(self.host,self.port,self.username,self.password,self.remotepath,self.localpath,self.d_or_u)
        end_time=time.time()
        print "Mission %s->%s success\n" % (self.username,self.d_or_u)
        print "%s->%s Time cost:%d s" % (self.username,self.d_or_u,(end_time-start_time))


################################################################################
if __name__=='__main__':
    #down_cn02=transportThread("cn02",22,"cn02","airation","/home/cn02/fragment_cn02/","/home/feng/Transfile/fragment_cn02/",'d')
    #down_cn05=transportThread("cn05",22,"cn05","airation","/home/cn05/fragment_cn05/","/home/feng/Transfile/fragment_cn05/",'d')
    up_cn02=transportThread("cn02",22,"cn02","airation","/home/cn02/fragment/","/home/feng/Transfile/fragment/",'u')
    #up_cn05=transportThread("cn05",22,"cn05","airation","/home/cn05/fragment/","/home/feng/Transfile/fragment/",'u')


    #down_cn02.start()
    #down_cn05.start()
    up_cn02.start()
    #up_cn05.start()
