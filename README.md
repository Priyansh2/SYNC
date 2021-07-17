# D-SYNC
An Application Level program to keep two separate directories synced, similar to Dropbox, using sockets to support file download, index search, and file verification using md5 hashing

# Usage
* ``folder1`` and ``folder2`` represent two shared directories according to the problem statement (see ``problem.pdf`` for more detail); both contains ``client`` and ``server`` scripts.

* Run following commands in 4 separate terminal windows

```bash
$ python client1.py
$ python server2.py
$ python client2.py
$ python server1.py
```

* Here ``client1.py`` and ``client2.py`` will interact with ``server2.py`` and ``server1.py`` respectively, and work in a synchronized environment. 
* The auto sync feature is implemented into the application and does not have separate files.



