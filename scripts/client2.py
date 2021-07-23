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
import textwrap
import time
import tqdm

from datetime import datetime
from func_timeout import FunctionTimedOut
from func_timeout import func_timeout
from os import name as nm
from pathlib import Path
from tabulate import tabulate

HOST = 'localhost'  # TCP
PORT = 1445  # TCP
UDP_HOST = 'localhost'
UDP_PORT = 1403
DELIM = ":::"
BUFFER_SIZE = 1024
UDP_BUFFER_SIZE = 32678
HASH_BUFFER_SIZE = 4096
UDP_TIME_OUT = 10
STDIN_TIMEOUT = 100
SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_DIR_PATH = os.path.dirname(SCRIPT_PATH)
CLI_PWD = "D:\\Github\\D-SYNC\\folder2"
SV_PWD = "D:\\Github\\D-SYNC\\folder1"


class client:
    def __init__(self):
        pass

    def recieve_output(self, cli_socket):
        cli_output = ""
        while True:
            temp = cli_socket.recv(BUFFER_SIZE).decode('utf-8')
            if not temp:
                break
            cli_output += temp
        return cli_output

    def display(self, cli_output, fields):
        '''
        fields eg: ['FileName', 'FileSize', 'Last Modified Time', 'FileType']
        '''
        temp = []
        if len(cli_output.split()) != 0:
            cli_output = cli_output.split("\n")
            for row in cli_output:
                row = row.split(DELIM)
                row = [textwrap.fill(x, width=60) for x in row if x.strip()]
                if len(row) != len(fields):
                    continue
                temp.append(row)
        t = tabulate(temp, headers=fields)
        print(t)

    def get_hash(self, f):
        hash_function = hashlib.md5()
        with open(f, "rb") as file:
            for chunk in iter(lambda: file.read(HASH_BUFFER_SIZE), b""):
                hash_function.update(chunk)
        return hash_function.hexdigest()

    def download(self, input_command, file_str, sv_dir=SV_PWD, verbose=True):
        if input_command[1] == "TCP":
            # Create a new client socket for connections with the server.
            try:
                cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cli_socket.connect((HOST, PORT))
            except socket.error as e:
                print("TCP Error (1): Connection refused!!")

            input_command.append(sv_dir)
            input_temp_command = DELIM.join(str(x) for x in input_command)
            cli_socket.send(input_temp_command.encode('utf-8'))
            data = cli_socket.recv(BUFFER_SIZE).decode('utf-8')

            if data == 'WRONG':
                print(
                    "TCP Error: {} do not exist!!. Enter the correct file path".format(
                        input_command[2]
                    )
                )
                return

            filesize = int(data)

            progress = tqdm.tqdm(
                range(filesize),
                f"Receiving... {input_command[2]}",
                unit="B",
                unit_scale=True,
                unit_divisor=BUFFER_SIZE,
            )

            # Open a file_str and receive all the data in that file
            with open(file_str, 'wb') as f:
                while True:
                    data = cli_socket.recv(BUFFER_SIZE)
                    if not data:
                        break
                    f.write(data)
                    progress.update(len(data))
                    progress.refresh()

            progress.close()
            # Set file permissions.
            filep = self.get_file_permission(
                ["filepermission", input_command[2]], sv_dir=sv_dir
            )
            filep = int(filep)
            try:
                os.chmod(file_str, filep)
                if verbose:
                    print(
                        "Setting file permissions of {} to {} ...".format(
                            file_str, oct(filep)
                        )
                    )
                # oct output eg: 0o100644 ==> Here  last 3 octal digit i.e, 644 represents the file permission mask and upper parts i.e, 0o100 tells the file type so to get the file's permission we can extract last 3 octal digit -> oct(int_filep)[-3:]
            except:
                if verbose:
                    print(
                        "TCP: Insufficient read permission. Unable to access file {}"
                        .format(input_command[2])
                    )
                else:
                    pass
            print('TCP: Sucessfully downloaded {}'.format(input_command[2]))
            cli_socket.close()

            # Create a new socket function for receiving metadata : filename, filesize, timestamp, md5 hash
            try:
                cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cli_socket.connect((HOST, PORT))
            except socket.error as e:
                print("TCP Error (2): Connection refused!!")

            # download metadata: filename, filesize, timestamp, md5hash
            cmd = ["downloaddata", "TCP", input_command[2], sv_dir]
            cmd = DELIM.join(x for x in cmd)
            cli_socket.send(cmd.encode('utf-8'))
            file_metadata = self.recieve_output(cli_socket)
            cli_socket.close()
            file_metadata = file_metadata.split(DELIM)
            filesize = humanize.naturalsize(filesize)
            if verbose:
                print(
                    "The size and hash of the file {} is {} and {} , last modified on"
                    " {}.".format(
                        file_metadata[0], filesize, file_metadata[2], file_metadata[1]
                    )
                )

            # print(file_metadata)

        elif input_command[1] == "UDP":
            file_str = "udp_" + file_str
            # create a TCP socket for sending command arguements
            try:
                cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cli_socket.connect((HOST, PORT))
            except socket.error as e:
                print("UDP Error (1): Connection refused!!")

            # Create a new UDP client socket server for connections with the original server.
            cli_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket_info = str(UDP_HOST) + DELIM + str(UDP_PORT)
            cli_udp_socket.bind((UDP_HOST, UDP_PORT))
            cli_udp_socket.settimeout(UDP_TIME_OUT)  # Set time-out on the UDP socket.
            input_command += [udp_socket_info, sv_dir]
            input_temp_command = DELIM.join(str(x) for x in input_command)
            cli_socket.send(input_temp_command.encode('utf-8'))
            data = cli_socket.recv(BUFFER_SIZE).decode('utf-8')
            cli_socket.close()

            if data == 'WRONG':
                print(
                    "UDP Error: {} do not exist!!. Enter the correct file name/path"
                    .format(input_command[2])
                )
                return

            filesize = int(data)
            progress = tqdm.tqdm(
                range(filesize),
                f"Receiving... {input_command[2]}",
                unit="B",
                unit_scale=True,
                unit_divisor=BUFFER_SIZE,
            )

            # Open a new file file_str and receive all the data in that file
            with open(file_str, 'wb') as fudp:
                while True:
                    try:
                        data, addr = cli_udp_socket.recvfrom(UDP_BUFFER_SIZE)
                    except socket.timeout:
                        break
                    if not data:
                        break
                    fudp.write(data)
                    progress.update(len(data))
                    progress.refresh()
            progress.clear()
            progress.close()
            cli_udp_socket.close()
            if verbose:
                print('UDP: Verifying downloaded file...')

            # Verify the calculated hash with the received file hash
            # Create a new socket function for receiving file metadata: filename, filesize, timestamp, md5 hash
            try:
                cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cli_socket.connect((HOST, PORT))
            except socket.error as e:
                print("UDP Error (2): Connection refused!!")

            cmd = ["downloaddata", "TCP", input_command[2], sv_dir]
            cmd = DELIM.join(x for x in cmd)
            cli_socket.send(cmd.encode('utf-8'))
            file_metadata = self.recieve_output(cli_socket)
            file_metadata = file_metadata.split(DELIM)
            cli_socket.close()

            file_hash = file_metadata[2]
            udp_hash = self.get_hash(file_str)
            if verbose:
                print("Md5 cheksum of downloaded file ==> {}".format(udp_hash))

            if file_hash == udp_hash:
                if verbose:
                    print("UDP: VERIFIED!!")
                filep = self.get_file_permission(
                    ["filepermission", input_command[2]], sv_dir=sv_dir
                )
                filep = int(filep)

                try:
                    os.chmod(file_str, filep)
                    if verbose:
                        print(
                            "Set file permissions of {} to {}".format(
                                file_str, oct(filep)
                            )
                        )
                    # oct output eg: 0o100644 ==> Here  last 3 octal digit i.e, 644 represents the file permission mask and upper parts i.e, 0o100 tells the file type so to get the file's permission we can extract last 3 octal digit -> oct(int_filep)[-3:]
                except:
                    if verbose:
                        print(
                            "UDP: Insufficient read permissions. Unable to access"
                            " file {}".format(input_command[2])
                        )
                    else:
                        pass
                print("UDP: Sucessfully downloaded {}".format(input_command[2]))

                filesize = humanize.naturalsize(filesize)
                if verbose:
                    print(
                        "The size and hash of the file {} is {} and {} , last modified"
                        " on {}.".format(
                            file_metadata[0],
                            filesize,
                            file_metadata[2],
                            file_metadata[1],
                        )
                    )

            else:
                print("UDP: Download failed!!. {} corrupted".format(input_command[2]))

    def hash(self, input_command, sv_dir=SV_PWD, verbose=True):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Hash Error: Connection refused!!")

        temp = input_command
        input_command.append(sv_dir)
        input_command = DELIM.join(str(x) for x in input_command)
        cli_socket.send(input_command.encode('utf-8'))
        cli_output = self.recieve_output(cli_socket)
        file = temp[2].strip()

        if temp[1] == "verify":
            if cli_output == 'WRONG':
                print(
                    "hash <verify> {}: File do not exist!!. Enter the correct file path"
                    .format(file)
                )
                return

            cli_output = cli_output.split(DELIM)

            file_hash = cli_output[1].strip()
            file_modtime = cli_output[0].strip()
            if verbose:
                print(
                    "The hash of the file {} is {} , last modified on {}.".format(
                        file, file_hash, file_modtime
                    )
                )
            cli_socket.close()
            return file_hash

        elif temp[1] == "checkall":
            if verbose:
                self.display(
                    cli_output,
                    fields=["FileName", "Last Modified Time", " Md5 Checksum"],
                )
            cli_socket.close()

    def index(self, input_command, sv_dir=SV_PWD, verbose=True):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Index Error: Connection refused!!")
        input_command.append(sv_dir)
        input_command = DELIM.join(str(x) for x in input_command)
        cli_socket.send(input_command.encode('utf-8'))
        cli_output = self.recieve_output(cli_socket)
        if verbose:
            self.display(
                cli_output,
                fields=['FileName', 'FileSize', 'Last Modified Time', 'FileType'],
            )
        cli_socket.close()

    def get_ls_content(self, input_command, sv_dir=SV_PWD):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Error: Connection refused!!")
        input_command.append(sv_dir)
        input_command = DELIM.join(str(x) for x in input_command)
        cli_socket.send(input_command.encode('utf-8'))
        cli_output = self.recieve_output(cli_socket)
        print(cli_output)
        cli_socket.close()

    def getlist(self, input_command, sv_dir=SV_PWD):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Error: Connection refused!!")
        input_command.append(sv_dir)
        input_command = DELIM.join(str(x) for x in input_command)
        cli_socket.send(input_command.encode('utf-8'))
        cli_output = self.recieve_output(cli_socket)
        cli_output = cli_output.split("\n")
        cli_socket.close()

        del cli_output[0]  # Remove eg: total 100
        del cli_output[-1]  # Remove the new line character

        return cli_output

    def get_file_permission(self, input_command, sv_dir=SV_PWD):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Error: Connection refused!!")
        input_command.append(sv_dir)
        input_command = DELIM.join(str(x) for x in input_command)
        cli_socket.send(input_command.encode('utf-8'))
        filep = self.recieve_output(cli_socket)
        cli_socket.close()

        return filep

    def get_last_modified_time(self, input_command, sv_dir=SV_PWD):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Error: Connection refused!!")
        input_command.append(sv_dir)
        input_command = DELIM.join(str(x) for x in input_command)
        cli_socket.send(input_command.encode('utf-8'))
        cli_output = self.recieve_output(cli_socket)
        cli_socket.close()

        return cli_output

    def sync(self, cli_dir=CLI_PWD, sv_dir=SV_PWD, verbose=True):
        '''
        NOTE: 1. This is one way sync between cli_dir (folder 1) and sv_dir (folder 2). This means clid_dir will always have same files and directories of sv_dir at any instance of time

        2. For auto sync, we have to do one-way sync for both clients (folder1 and folder2)
        '''
        os.chdir(cli_dir)
        print("Syncronising {} with {}...".format(cli_dir, sv_dir))
        local_file_list = os.listdir(".")  # get files and directories names in cli_dir
        # print("Local files and dirs in {}".format(cli_dir), local_file_list)
        lls_list = self.getlist(["lls"], sv_dir=sv_dir)
        temp_list = []
        # Retrieve the files and directories names in sv_dir
        server_file_list = []
        temp = []
        for row in lls_list:
            row = [x for x in row.split(" ") if x.strip()]
            if not row or (len(row) == 1 and len(row[0].strip()) == 0):
                continue
            typ = 'f'
            if row[0][0] == 'd':
                typ = 'd'
            fl = " ".join(x for x in row[8:])
            temp.append(fl)
            server_file_list.append((fl, typ))
        # print("Server files and dirs in {}".format(sv_dir), temp)
        # print(server_file_list)
        # Iterate over the server_file_list and download missing files and directories from sv_dir to cli_dir
        for fl, typ in server_file_list:
            if fl in local_file_list:
                continue
            if typ == 'd':
                # Recursively syncing directories
                new_sv_dir = os.path.join(sv_dir, fl)
                new_cli_dir = os.path.join(cli_dir, fl)
                Path(new_cli_dir).mkdir(parents=True, exist_ok=True)
                self.sync(cli_dir=new_cli_dir, sv_dir=new_sv_dir, verbose=verbose)
                print(
                    " <===> (1-S-D) Downloaded dir: {} to {} <===>".format(
                        new_cli_dir, new_sv_dir
                    )
                )
                os.chdir(cli_dir)
                continue
            sv_fl_path = os.path.join(sv_dir, fl)
            cli_fl_path = os.path.join(cli_dir, fl)
            self.download(
                ["download", "TCP", sv_fl_path], fl, sv_dir=sv_dir, verbose=False
            )
            print(
                " <===> (2-S-F) Downloaded file: {} to {} <===>".format(
                    cli_fl_path, sv_fl_path
                )
            )

        # Iterate over the server_file_list and download recently modified files and directories from sv_dir to cli_dir
        local_file_list = os.listdir(".")
        for fl, typ in server_file_list:
            if typ == 'd':
                new_sv_dir = os.path.join(sv_dir, fl)
                new_cli_dir = os.path.join(cli_dir, fl)
                self.sync(cli_dir=new_cli_dir, sv_dir=new_sv_dir, verbose=verbose)
                print(
                    " <===> (3-S-D) Mirrored dir: {} to {} <===>".format(
                        new_cli_dir, new_sv_dir
                    )
                )
                os.chdir(cli_dir)
                continue
            sv_fl_path = os.path.join(sv_dir, fl)
            cli_fl_path = os.path.join(cli_dir, fl)
            server_hash = self.hash(
                ["hash", "verify", sv_fl_path], sv_dir=sv_dir, verbose=False
            )
            local_hash = self.get_hash(fl)

            server_last_modified = float(
                self.get_last_modified_time(["modified", sv_fl_path], sv_dir=sv_dir)
            )
            client_last_modified = float(str(os.path.getmtime(fl)))
            # compare lastmodified times of files in cli_dir and sv_dir
            # Any file is said to be recently modified if its lastmodified time (seconds ) is greater than its previous version
            # We will download files from sv_dir to cli_dir in case file on sv_dir is recenlty modified.

            if client_last_modified > server_last_modified:
                continue
            else:
                if local_hash != server_hash:
                    self.download(
                        ["download", "TCP", sv_fl_path],
                        fl,
                        sv_dir=sv_dir,
                        verbose=False,
                    )
                    print(
                        " <===> (4-S-F) Mirrored file: {} to {} <===>".format(
                            cli_fl_path, sv_fl_path
                        )
                    )
        print("Synced!!")

    def run(self):
        while True:
            os.chdir(CLI_PWD)
            print('Client >> ', end=" ", flush=True)
            try:
                ## do auto aync if user dont press "enter" within STDIN_TIMEOUT sec
                input_command = func_timeout(STDIN_TIMEOUT, lambda: input())
                input_command = input_command.strip().split(" ")
                if len(input_command) > 2:
                    filepath = " ".join(input_command[2:])
                    input_command = input_command[:2] + [filepath]
                if len(input_command) == 1:

                    # ls command output handling
                    if input_command[0] == "ls":
                        self.get_ls_content(input_command)

                    # lls is the long-list output (output of ls -l) from the server directory
                    elif input_command[0] == "lls":
                        lls_list = self.getlist(input_command)
                        for f in lls_list:
                            print(f)

                    # force sync with command line
                    elif input_command[0] == "sync":
                        self.sync()

                elif input_command[0] == "index":
                    self.index(input_command)

                elif input_command[0] == "hash":
                    self.hash(input_command)

                elif input_command[0] == "download":
                    file_str = (
                        'received_file_'
                        + str(random.randrange(1, 1000))
                        + "_"
                        + os.path.basename(input_command[2])
                    )
                    while os.path.isfile(file_str):
                        file_str = (
                            'received_file_'
                            + str(random.randrange(1, 1000))
                            + "_"
                            + os.path.basename(input_command[2])
                        )
                    self.download(input_command, file_str)

            except FunctionTimedOut:
                # automatic sync after every 100 seconds
                self.sync()
                if nm == "nt":
                    os.system("cls")
                else:
                    os.system("clear")


if __name__ == "__main__":
    Client = client()
    Client.run()
