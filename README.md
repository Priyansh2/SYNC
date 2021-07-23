# D-SYNC
An Application Level program to keep two separate directories synced, similar to Dropbox, using sockets to support file download, index search, and file verification using md5 hashing

# Usage

* ``folder1`` and ``folder2`` represent two separate directories on the same or different machine according to the problem statement (see ``problem.pdf`` for more detail). I have included test data in both of them for testing purposes.  

* ``scripts`` directory contains all necessary programs needed to run the D-SYNC application

* Set following static variables before running any program

| Variable | Default Value | Description  | Target File  |  
| :---         |     :---      |      :---    |      :---    |
| CLI_PWD   | Path of `folder1` and `folder2` in `client1.py` and `client2.py` respectively    | First directory path   |  client1.py, client2.py           |
| SV_PWD     | Path of `folder2` and `folder1` in `client1.py` and `client2.py` respectively     | Second directory path      | client1.py, client2.py|
| PWD   | `folder1` path in `server1.py` and `folder2` in `server2.py`      | First/Second directory path. <br/> **NOTE:** PWD of `server1.py` and `server2.py` are SV_PWD of `client2.py` and `client1.py` respectively.     |server1.py , server2.py|
| PORT     | 1443 in `client1.py, server2.py` and 1445 in `client2.py, server2.py`       | TCP port      | ALL |
| UDP_PORT   | 1401 in `client1.py` and 1403 in `client2.py`     | UDP PORT    | client1.py, client2.py |
| BUFFER_SIZE     | 1024 in ALL     | TCP buffer size. <br/> **NOTE:** This value must be same for very program    | ALL | 
| UDP_BUFFER_SIZE   | 32678 in ALL     | UDP buffer size. <br/> **NOTE:** This value must be same for every program     | ALL |
| HASH_BUFFER_SIZE   | 4096 in ALL     | File chunk size to get MD5 checksum. <br/> **NOTE:** This value must be same for every program     | ALL |
| DELIM     | `:::`  in ALL    | Delimeter to parse command line     | ALL |
| UDP_TIME_OUT   | 10 in `client1.py, client2.py`     | Time limit (in seconds) for UDP socket    |  client1.py, client2.py | 
| STDIN_TIMEOUT     | 100 in `client1.py, client2.py`       | Time out for input command (in seconds). <br/> **NOTE:** If the user is idle for ``STDIN_TIMEOUT``, then auto-synchronization starts, and the user will be allowed to give input only after it gets completed    | client1.py, client2.py | 

* The `D-SYNC` application uses the bash command: 'find' for extracting file information, and it is expected from the user to set the location of this command in `server1.py` and `server2.py`. Without this, application won't work. **NOTE:** For windows, the application is tested on the `cmder` terminal, so make sure to install that before using this repository.  

* Run following scripts in 4 separate terminals
```bash
Run Servers:
$ python server1.py
$ python server2.py

Run Clients:
$ python client1.py
$ python client2.py
```

* The ``client1.py`` and ``client2.py`` will interact with ``server2.py`` and ``server1.py`` respectively, and work in a synchronized environment. 

* The auto sync feature is implemented into the application and does not have separate files.

## Comamnds (Please see problem.pdf for detail)
- [x] index longlist 
- [x] index shorlist <start_time_stamp> <end_time_stamp>
- [x] index regex <search_pattern>
- [x] hash verfy <filename/filepath>
- [x] hash checkall
- [x] download TCP <filename/filepath>
- [x] download UDP <filename/filepath>
- [x] sync


# TODO

- [ ] Data compression and archiving
- [ ] Encryption for security purposes
- [ ] Conflict detection for the scenerio where a file has been modified on both sources, as opposed to where it has only been modified on one (Preserve file versions).  
