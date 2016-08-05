#!/usr/bin/env python3

import socket
import struct
import os
import logging
import sys
import time
DEFAULT_BLKSIZE=512
OPCODE_RRQ=1
OPCODE_DATA=3
OPCODE_ACK=4
OPCODE_OACK=6
ERROR=1
SUCCESS=0

class FBTFTPClients:
    def __init__(self,address,port,mode,options={'retries':3,'tsize':1}):
        self._address=address
        self._port=port
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
                    "Unexpected mode: %s, expected 'netascii' or 'octet'" % mode)
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

        self._client_socket.sendto(send_pack,(self._address,self._port))
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

            if time_interval>0.18:
                count=int(self._read_size/self._options['tsize']*100)
                rate=(self._read_size-rate_size)/1024/1024/time_interval
                self._viewBar(count,rate)
                rate_time=time.time()
                rate_size=self._read_size

        file_open.close()
        total_time=time.time()-start_time
        count=int(self._read_size/self._options['tsize']*100)
        rate=(self._read_size/1024/1024)/total_time
        self._viewBar(count,rate)
        print('\nFile size: %.2f (M)' % (self._read_size/1024/1024))
        print('Spend Time: %.2f (s)' % total_time)
        print('Average speed: %.2f (M/s)' % rate)
        self._read_size=0
        return SUCCESS

    def _viewBar(self,count,rate):
        output=sys.stdout
        output.write('\r%d%%' % count)
        if count<10:
            output.write('  ')
        elif count<100:
            output.write(' ')
        output.write('[')
        i=0
        while i<=100:
            if i<=count:
                output.write('>')
            else:
                output.write(' ')
            i+=1.5
        output.write(']    ')
        output.write('%6.2f M/s' % rate)
        output.flush()
        




    def run(self,server_path,local_path):
        self._sendToServer(server_path)
        self._receiveFromServer(local_path)
        self._close()

    def _close(self):
        self._client_socket.close()



def main():
    server_path=sys.argv[1]
    local_path=sys.argv[2]
    fb_client=FBTFTPClients('127.0.0.1',1969,'octet')
    fb_client.run(server_path,local_path)

if __name__ == '__main__':
    main()

