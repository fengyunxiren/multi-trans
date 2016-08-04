#/usr/bin/python
import sys



class BaseTransport(object):
    def __init__(self,host,port,user,password):
        self._host = host
        self._port = port
        self.user = user
        self.password = password


    def _viewBar(self,count,rate):
        output = sys.stdout
        output.write('\r%d%%' % count)
        if count < 10:
            output.write('  ')
        elif count <100:
            output.write(' ')
        output.write('[')
        i=0
        while i <= 100:


