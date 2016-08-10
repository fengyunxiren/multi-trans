对scp，sftp，ftp，fbtftp进行了封装，在四种方法中，scp和ftp传输速度最快，fbtftp传输速度最慢，可以用fbtftp传输小文件。 
使用方法：

$ multi_trans.py [-t method] send_file receive_path
-t 用来指定传输方法，默认的传输方法为scp，这是因为其传输的速度快，同时，其也为系统自带的传输方法，不用额外安装，ftp在Ubuntu 14.04 上没有安装，如需用到，需要安装在远程服务端，debian类linux安装：

$ sudo apt-get install vsftpd
如果要需要上传文件到ftp服务器，需要修改/etc/vsftpd.conf,将write_enable=YES前的注释符号去掉。fbtftp 方法需要安装服务端。

如果使用时遇到bug，可以反馈给我
