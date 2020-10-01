# Zowe Terminal Explorer

Written for the IBM Master The Mainframe 2000, this is a quick tool that allows you to monitor the jobs list and delete those jobs no longer required.  

![Job listings](img/job_listing.png "Job listings")
![TSU Job listings](img/tsu_job_listing.png "TSU Job listings")

## Installation

Tested only on a Linux machine.

Notes to IBM Z testers:
1. Have git installed.
2. Requires Linux flavour with Python3 installed.  (will warn if not)
3. Requires you to have Zowe installed locally and in your Path as per ZCLI1 instructions. (will warn if not)
4. Requires you to have a Zowe profile already setup as per ZCLI1 instructions.
(For example: ```zowe profiles create zosmf-profile zosmf --host <host> --port <port> --user <username> --password <password> --reject-unauthorized false```)
5. Requires you to have Python 3 curses library installed (should be by default on most installations).
7. If this command (```zowe jobs list jobs```) works for you, then so will Zowe Terminal Explorer.


```
git clone https://github.com/tommccallum/zowe-terminal-explorer
cd zowe-terminal-explorer
./zte
```

## Actions

| Key | Action | 
|-----|--------|
| q   | Quits application |
| d   | Delete job |
| j   | Switch to jobs if available |
| t   | Switch to tsu jobs if available |


## Known Bugs

1. When the display changes sometimes the background colour disappears.
2. When the display resizes very small or the application is open in too small a window, the application will throw an exception.

In either case, restart the application in the appropriately sized terminal.
