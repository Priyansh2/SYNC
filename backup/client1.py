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
from os import name as nm
from tabulate import tabulate

HOST = 'localhost'  # TCP
PORT = 1443  # TCP
UDP_HOST = 'localhost'
UDP_PORT = 1401
DELIM = ":::"
BUFFER_SIZE = 1024
UDP_BUFFER_SIZE = 32678
HASH_BUFFER_SIZE = 4096
UDP_TIME_OUT = 10


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
            # print("ok!!")
        return cli_output

    def display(self, cli_output, fields):
        temp = []
        '''
        fields eg: ['FileName', 'FileSize', 'Last Modified Time', 'FileType']
        '''
        # t = PrettyTable(fields)
        if len(cli_output.split()) != 0:
            cli_output = cli_output.split("\n")
            for row in cli_output:
                row = row.split(DELIM)
                row = [textwrap.fill(x, width=60) for x in row if x.strip()]
                if len(row) != len(fields):
                    continue
                # t.add_row(row)
                temp.append(row)
        t = tabulate(temp, headers=fields)
        print(t)

    def get_hash(self, f):
        hash_function = hashlib.md5()
        with open(f, "rb") as file:
            for chunk in iter(lambda: file.read(HASH_BUFFER_SIZE), b""):
                hash_function.update(chunk)
        return hash_function.hexdigest()

    def download(self, input_command, file_str):
        if input_command[1] == "TCP":
            # Create a new client socket for connections with the server.
            try:
                cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cli_socket.connect((HOST, PORT))
            except socket.error as e:
                print("TCP Error (1): Connection refused!!")

            input_temp_command = " ".join(str(x) for x in input_command)
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
            # Set file permissions. BONUS!
            filep = self.get_file_permission(["filepermission", input_command[2]])
            filep = int(filep)
            try:
                os.chmod(file_str, filep)
                print(
                    "Setting file permissions of {} to {} ...".format(
                        file_str, oct(filep)
                    )
                )
                # oct output eg: 0o100644 ==> Here  last 3 octal digit i.e, 644 represents the file permission mask and upper parts i.e, 0o100 tells the file type so to get the file's permission we can extract last 3 octal digit -> oct(int_filep)[-3:]
            except:
                print(
                    "TCP: Insufficient read permission. Unable to access file {}"
                    .format(input_command[2])
                )

            print('TCP: Sucessfully downloaded {}'.format(input_command[2]))
            cli_socket.close()

            # Create a new socket function for receiving metadata : filename, filesize, timestamp, md5 hash
            try:
                cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cli_socket.connect((HOST, PORT))
            except socket.error as e:
                print("TCP Error (2): Connection refused!!")

            # download metadata: filename, filesize, timestamp, md5hash
            cmd = "downloaddata TCP " + input_command[2]
            cli_socket.send(cmd.encode('utf-8'))
            file_metadata = self.recieve_output(cli_socket)
            cli_socket.close()
            file_metadata = file_metadata.split(DELIM)
            filesize = humanize.naturalsize(filesize)
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
            udp_socket_info = str(UDP_HOST) + " " + str(UDP_PORT)
            cli_udp_socket.bind((UDP_HOST, UDP_PORT))
            cli_udp_socket.settimeout(UDP_TIME_OUT)  # Set time-out on the UDP socket.

            input_temp_command = (
                " ".join(str(x) for x in input_command).strip() + " " + udp_socket_info
            )
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
                        print("UDP Error (2): Timed out!!")
                        break
                    fudp.write(data)
                    progress.update(len(data))
                    progress.refresh()
                    if not data or data == "":
                        break
            progress.close()
            cli_udp_socket.close()
            print('UDP: Verifying downloaded file...')

            # Verify the calculated hash with the received file hash
            # Create a new socket function for receiving file metadata: filename, filesize, timestamp, md5 hash
            try:
                cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cli_socket.connect((HOST, PORT))
            except socket.error as e:
                print("UDP Error (3): Connection refused!!")

            cmd = "downloaddata TCP " + input_command[2]
            cli_socket.send(cmd.encode('utf-8'))
            file_metadata = self.recieve_output(cli_socket)
            file_metadata = file_metadata.split(DELIM)
            cli_socket.close()

            file_hash = file_metadata[2]
            udp_hash = self.get_hash(file_str)
            print("Md5 cheksum of downloaded file ==> {}".format(udp_hash))

            if file_hash == udp_hash:
                print("UDP: VERIFIED!!")
                filep = self.get_file_permission(["filepermission", input_command[2]])
                filep = int(filep)

                try:
                    os.chmod(file_str, filep)
                    print(
                        "Set file permissions of {} to {}".format(file_str, oct(filep))
                    )
                    # oct output eg: 0o100644 ==> Here  last 3 octal digit i.e, 644 represents the file permission mask and upper parts i.e, 0o100 tells the file type so to get the file's permission we can extract last 3 octal digit -> oct(int_filep)[-3:]
                except:
                    print(
                        "UDP: Insufficient read permissions. Unable to access file {}"
                        .format(input_command[2])
                    )
                print("UDP: Sucessfully downloaded {}".format(input_command[2]))

                filesize = humanize.naturalsize(filesize)
                print(
                    "The size and hash of the file {} is {} and {} , last modified on"
                    " {}.".format(
                        file_metadata[0], filesize, file_metadata[2], file_metadata[1]
                    )
                )

            else:
                print("UDP: Downloaded file corrupted!!")

    def hash(self, input_command):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Hash Error: Connection refused!!")

        if input_command[1] == "verify":
            filename = input_command[2]
            input_command = " ".join(str(x) for x in input_command)
            cli_socket.send(input_command.encode('utf-8'))
            cli_output = self.recieve_output(cli_socket)
            if cli_output == 'WRONG':
                print(
                    "hash <verify> {}: File do not exist!!. Enter the correct file path"
                    .format(input_command[2])
                )
                return

            cli_output = cli_output.split(DELIM)

            file_hash = cli_output[1].strip()
            file_modtime = cli_output[0].strip()
            print(
                "The hash of the file {} is {} , last modified on {}.".format(
                    filename, file_hash, file_modtime
                )
            )
            cli_socket.close()
            return file_hash

        elif input_command[1] == "checkall":
            input_command = " ".join(str(x) for x in input_command)
            cli_socket.send(input_command.encode('utf-8'))
            cli_output = self.recieve_output(cli_socket)
            self.display(
                cli_output, fields=["FileName", "Last Modified Time", " Md5 Checksum"]
            )
            cli_socket.close()

    def index(self, input_command):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Index Error: Connection refused!!")

        input_command = " ".join(str(x) for x in input_command)
        cli_socket.send(input_command.encode('utf-8'))
        cli_output = self.recieve_output(cli_socket)
        self.display(
            cli_output,
            fields=['FileName', 'FileSize', 'Last Modified Time', 'FileType'],
        )
        cli_socket.close()

    def get_ls_content(self, input_command):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Error: Connection refused!!")

        input_command = " ".join(str(x) for x in input_command)
        cli_socket.send(input_command.encode('utf-8'))
        cli_output = self.recieve_output(cli_socket)
        print(cli_output)
        cli_socket.close()

    def getlist(self, input_command):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Error: Connection refused!!")

        input_command = " ".join(str(x) for x in input_command)
        cli_socket.send(input_command.encode('utf-8'))
        cli_output = self.recieve_output(cli_socket)
        cli_output = cli_output.split("\n")
        cli_socket.close()

        del cli_output[0]  # Remove eg: total 100
        del cli_output[-1]  # Remove the new line character

        return cli_output

    def get_file_permission(self, input_command):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Error: Connection refused!!")

        input_command = " ".join(str(x) for x in input_command)
        cli_socket.send(input_command.encode('utf-8'))
        filep = self.recieve_output(cli_socket)
        cli_socket.close()

        return filep

    def get_last_modified_time(self, input_command):
        # Create a new client socket for connections with the server.
        try:
            cli_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cli_socket.connect((HOST, PORT))
        except socket.error as e:
            print("Error: Connection refused!!")

        input_command = " ".join(str(x) for x in input_command)
        cli_socket.send(input_command.encode('utf-8'))
        cli_output = self.recieve_output(cli_socket)
        cli_socket.close()

        return cli_output

    def sync(self):
        # Retrieve the files and directories names in remote folder (client shared directory)
        local_file_list = os.listdir(".")
        print(local_file_list)
        lls_list = self.getlist(["lls"])
        temp_list = []
        # Retrieve the files and directories names in server folder (other client's shared directory)
        server_file_list = []
        for element in lls_list:
            temp_list = element.split(" ")
            server_file_list.append(temp_list[-1])
        print(server_file_list)
        # Iterate over the elements and download missing files from server to remote folder
        for element in server_file_list:
            if not element or len(element.strip())=0 or element in local_file_list:
                continue
            self.download(["download", "TCP", element], element)
            print("<== (1) File downloaded ==> {}".format(element))

        # Iterate over the elements and download recently modified filesas per question to remote folder
        local_file_list = os.listdir(".")
        for element in server_file_list:
            if not element:
                continue

            server_hash = self.hash(["hash", "verify", element])
            # Compute the hash function for local file
            local_hash = self.get_hash(element)
            server_last_modified = int(
                self.get_last_modified_time(["modified", element])
            )
            client_last_modified = int(str(os.path.getmtime(element)))
            # compare lastmodified times of files in client_folder and server_folder
            # Any file is said to be recently modified if its lastmodified time (seconds ) is greater than its previous version
            # We will download files from server to client folder. Similarly, the other client (acting as server) will do the same thing for its server (our client acting as server)

            if client_last_modified > server_last_modified:
                continue
            else:
                if local_hash != server_hash:
                    self.download(["download", "TCP", element], element)
                    print("<== (2) File downloaded ==> {}".format(element))

    def run(self):
        while True:
            print('Client > ', end=" ", flush=True)
            # Time-out for automatic sync. User is not allowed to perform any action until sync is completed.
            # This is to avoid file locking (read online)
            # i, o, e = select.select([sys.stdin], [], [], 100)
            i = True
            if i:
                ## Parse commands
                input_command = sys.stdin.readline().strip()
                input_command = input_command.split(" ")

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
                        + input_command[2].split("/")[-1]
                    )
                    # print(input_command[2].split("/"))
                    while os.path.isfile(file_str):
                        file_str = (
                            'received_file_'
                            + str(random.randrange(1, 1000))
                            + "_"
                            + input_command[2].split("/")[-1]
                        )
                    self.download(input_command, file_str)

                else:
                    print("No such command!!. Choose one among the below commands:")
                    print(
                        """1. ls\n2. lls\n3. index <flag> [args]...\n4. hash <flag> [args]...\n5. download <flag> [args]...\n6. sync"""
                    )
            else:
                # automatic sync after every 100 seconds
                self.sync()
                if nm == "nt":
                    os.system("cls")
                else:
                    os.system("clear")


if __name__ == "__main__":
    Client = client()
    Client.run()
