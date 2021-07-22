import glob
import hashlib
import humanize
import os
import random
import re
import select
import socket
import stat
import subprocess
import sys
import time
import tqdm

from datetime import datetime
from os import name as nm


PORT = 1443
HOST = 'localhost'
BUFFER_SIZE = 1024
UDP_BUFFER_SIZE = 32678
HASH_BUFFER_SIZE = 4096
FIND_CMD = "find"
DELIM = ":::"
PWD = "D:\\Github\\D-SYNC\\folder2"
if nm == 'nt':
    FIND_CMD = "C:\\cmder\\vendor\\git-for-windows\\usr\\bin\\find.exe"


class server:
    def __init__(self):
        try:
            self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.serversocket.bind((HOST, PORT))
            self.serversocket.listen(5)
        except socket.error as e:
            print("Error: Connection `!!")

    def get_hash(self, f):
        hash_function = hashlib.md5()
        with open(f, "rb") as file:
            for chunk in iter(lambda: file.read(HASH_BUFFER_SIZE), b""):
                hash_function.update(chunk)
        return hash_function.hexdigest()

    def get_file_info(self, file_list):
        # Declare a resultant string to store final output of all the files that were modified in this time interval
        result_string = []
        # Extracting required information: filename, filesize, last modified time string, type of file using awk
        for f in file_list:
            if f == '':
                break
            fl = f.replace(' ', '\ ')

            if nm == "nt":
                fl = r'"{}"'.format(f)
            cmd = (
                'ls -l '
                + fl
                + ' | awk \'{print  substr($0,index($0,$9)), $5, $6, $7, $8}\' '
            )
            decoded_bash_command = subprocess.check_output(cmd, shell=True).decode(
                'utf-8'
            )
            '''
            Eg outputs:
                1.  b'./main.py 1720 Jul 17 04:15\n'
                2.  b'./b.txt 13 Jul 17 04:15\n'
                3.  b'./a.txt 0 Jul 17 04:15\n'
                4. b'./New Text Document.txt 0 Jul 22 15:17\n'
            '''
            split_command = re.split(" ", decoded_bash_command.strip())
            file = " ".join(x for x in split_command[:-3][:-1])
            file_size = split_command[:-3][-1]
            mod_time = " ".join(str(x) for x in split_command[-3:])
            # file types
            p = subprocess.Popen(
                'file ' + fl, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            res, errors = p.communicate()
            '''
            eg output:
                1. b'./main.py: Python script, ASCII text executable\n'
                2.  b'./b.txt: ASCII text, with no line terminators\n'
                3.  b'./a.txt: empty \n'

                File types:
                1. Python script, ASCII text executable
                2. ASCII text, with no line terminators
                3. empty (for empty file)
            '''
            file_type = res.decode('utf-8').split(file)[1].split(":")[1].strip()
            temp = [file, file_size, mod_time, file_type]
            result_string += temp
            result_string.append("\n")
        # print(result_string)
        return result_string

    def get_metadata(self, f):
        data = []
        # Attach last modified timestamp
        modtime = os.path.getmtime(f)  ##last modified time in seconds
        '''
            TIME FORMAT:
            %m -> month
            %d -> day
            %Y -> year
            %I -> hours in 12-hour clock
            %M -> minutes
            %S -> seconds
            %p -> AM/PM
        '''
        data.append(
            time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(modtime))
        )  ## get time in pretty output.
        data.append(self.get_hash(f))
        return data

    def send_output(self, client_soc, data, command):
        block_size = 1000
        block_number = 0
        # print(len(data.encode("utf-8")))
        while True:
            # Selected block to send
            block_data = data[
                block_number * block_size : (block_number + 1) * block_size
            ]
            client_soc.send(block_data.encode("utf-8"))
            if not block_data:
                break
            block_number += 1
        print("Sent: Output of command line ==> {}".format(command))

    def run(self):
        while True:
            try:
                # Connect with the client
                client, addr = self.serversocket.accept()
                print("Connected with {} :  {}".format(addr[0], str(addr[1])))

                # Receive the command from the client
                rec_command = client.recv(BUFFER_SIZE).decode('utf-8')
                print("Received: Command Line ==> {}".format(rec_command))
                rec_command = rec_command.split(" ")
                os.chdir(PWD)

                if rec_command[0] == "ls":
                    output = subprocess.check_output(["ls"]).decode('utf-8')
                    self.send_output(client, output, rec_command)

                elif rec_command[0] == "lls":
                    '''eg:
                    -rwxrwxrwx 1 root root    0 Jul 17 04:12 a.txt
                    -rwxrwxrwx 1 root root   13 Jul 17 04:12 b.txt
                    -rwxrwxrwx 1 root root 1750 Jul 17 04:12 main.py'''
                    output = subprocess.check_output(["ls", "-l"]).decode('utf-8')
                    self.send_output(client, output, rec_command)

                elif rec_command[0] == "index":

                    # index shorlist <starttimestamp> <endtimestamp>
                    if rec_command[1] == "shortlist":
                        starttime = (
                            rec_command[2] + ' ' + rec_command[3]
                        )  # year-month-day format
                        endtime = (
                            rec_command[4] + ' ' + rec_command[5]
                        )  # year-month-day format
                        # eg: find . -type f -newermt "2017-11-06 17:30:00" ! -newermt "2017-11-06 22:00:00" (search all files (not directories) which are modified after startime and exclude all files which are modified after endtime ==> files that are modified between start(inclusive) and endtime(exclusive))

                        output = subprocess.check_output(
                            (
                                FIND_CMD,
                                PWD,
                                '-type',
                                'f',
                                '-newermt',
                                starttime,
                                '!',
                                '-newermt',
                                endtime,
                            )
                        ).decode('utf-8')
                        # eg output: ['./main.py', './b.txt', './a.txt', '']
                        output = output.split("\n")

                        if len(output) == 1:
                            client.send(output[0].encode('utf-8'))
                            client.close()
                            continue
                        result_string = self.get_file_info(output)
                        result_string = DELIM.join(str(x) for x in result_string)
                        self.send_output(client, result_string, rec_command)

                    # index longlist
                    elif rec_command[1] == "longlist":
                        result_string = []

                        output = subprocess.check_output(
                            (FIND_CMD, PWD, '-type', 'f')
                        ).decode(
                            'utf-8'
                        )  # recursively finds all files'''
                        output = output.split('\n')
                        if len(output) == 1 and output[0].strip() == "":
                            client.send(output[0].encode('utf-8'))
                            client.close()
                            continue
                        result_string = self.get_file_info(output)
                        result_string = DELIM.join(str(x) for x in result_string)
                        self.send_output(client, result_string, rec_command)

                    # index regex patten
                    elif rec_command[1] == "regex":
                        matched_files = [
                            fl
                            for fl in glob.glob(rec_command[2], recursive=True)
                            if os.path.isfile(fl)
                        ]
                        # see gfg and official python doc for more information
                        print(matched_files)
                        if len(matched_files) == 1:
                            # print("lol", matched_files)
                            client.send(" ".encode('utf-8'))
                            client.close()
                            continue
                        result_string = self.get_file_info(matched_files)
                        result_string = DELIM.join(str(x) for x in result_string)
                        self.send_output(client, result_string, rec_command)

                elif rec_command[0] == "hash":

                    # hash verify <filename>
                    if rec_command[1] == "verify":
                        if not os.path.isfile(rec_command[2]):
                            print("File not found!!")
                            client.send("WRONG".encode('utf-8'))
                            client.close()
                            continue

                        data = self.get_metadata(rec_command[2])
                        data = DELIM.join(str(x) for x in data)
                        # Send the list in the form of a string to the client, ENCODED!!!
                        self.send_output(client, data, rec_command)

                    # hash checkall
                    elif rec_command[1] == "checkall":
                        # Execute command to find all the files ONLY! Otherwise upper command yielded directories, and an error persisted.
                        file_list = subprocess.check_output(
                            (FIND_CMD, PWD, '-type', 'f')
                        ).decode('utf-8')
                        file_list = file_list.split('\n')
                        del file_list[-1]  ##delete the last newline character
                        output = []
                        for f in file_list:
                            temp = []
                            temp.append(f)
                            temp += self.get_metadata(f)
                            temp.append("\n")
                            output += temp
                        output = DELIM.join(str(x) for x in output)
                        # print(output)
                        self.send_output(client, output, rec_command)

                elif rec_command[0] == "download":

                    if not os.path.isfile(rec_command[2]):
                        client.send("WRONG".encode('utf-8'))
                        client.close()
                        continue

                    filesize = os.path.getsize(rec_command[2])
                    client.send(str(filesize).encode('utf-8'))
                    progress = tqdm.tqdm(
                        range(filesize),
                        f"Sending... {rec_command[2]}",
                        unit="B",
                        unit_scale=True,
                        unit_divisor=BUFFER_SIZE,
                    )

                    if rec_command[1] == "TCP":
                        f_list = []
                        filename = rec_command[2]
                        with open(filename, "rb") as f:
                            while True:
                                data = f.read(BUFFER_SIZE)
                                if not data:
                                    break
                                client.send(data)
                                progress.update(len(data))
                                progress.refresh()

                    elif rec_command[1] == "UDP":
                        udp_client_host = rec_command[3]
                        udp_client_port = int(rec_command[4])

                        server_udp_socket = socket.socket(
                            socket.AF_INET, socket.SOCK_DGRAM
                        )
                        f_list = []
                        filename = rec_command[2]

                        with open(filename, "rb") as f:
                            while True:
                                data = f.read(UDP_BUFFER_SIZE)
                                if not data:
                                    break
                                server_udp_socket.sendto(
                                    data, (udp_client_host, udp_client_port)
                                )
                                progress.update(len(data))
                                progress.refresh()
                    progress.close()
                    print("File transfer complete!!")

                elif rec_command[0] == "downloaddata":
                    f_list = []
                    f_list.append(rec_command[2])  # filename
                    f_list += self.get_metadata(rec_command[2])
                    f_list = DELIM.join(str(x) for x in f_list)
                    self.send_output(client, f_list, rec_command)

                elif rec_command[0] == "modified":
                    filename = rec_command[1]
                    last_modified_time = str(os.path.getmtime(filename))
                    self.send_output(client, last_modified_time, rec_command)

                elif rec_command[0] == "filepermission":
                    filename = rec_command[1]
                    permission_str = str(os.lstat(filename).st_mode)
                    self.send_output(client, permission_str, rec_command)
                client.close()

            except socket.error as e:
                print("Error: Connection refused!!")


if __name__ == "__main__":
    Server = server()
    Server.run()
    Server.serversocket.close()
