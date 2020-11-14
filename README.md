# lhctrl
## Power management of Valve v1 lighthouses over Bluetooth LE

Valve v1 lighthouses include a power management feature implemented over the Bluetooth LE protocol. The protocol and the message format used by this feature are briefly described (among others) here https://github.com/nairol/LighthouseRedox. How this feature works will follow.

>NOTE: There is a similar Python script to control Valve v2 lighthouses [here](https://github.com/risa2000/lh2ctrl).

### "B" and "C" configuration
In the most usual setup, the lighthouses are used in a pair, where one LH is switched into "B" mode (becomes the master) and the other one into "C" mode (becomes the slave). In this configuration, "C" can only run when also "B" is running. The consequence is that powering off "B" will put "C" into stand-by, i.e. to turn off both LHs it only needs that "B" is turned off. Conversely, if "C" is in stand-by, turning "B" on will also wake up "C".

"B" can be turned off either by simply cutting the power (disconnecting from the power outlet). "B" cannot be directly turned off by a BT LE command, because the BT LE power management of the lighthouses is based on the notion of **keeping the lighthouses on** rather than on **turning them on and off**.

To keep "B" running, one needs to *ping* "B" regularly over BT LE. If those pings stop then "B" will turn off after the specified timeout has been reached. This setup ensures that "B" will turn off even if the controller (e.g. SteamVR running on the user's PC) crashes. This also explains why there is no command for turning the lighthouse off - it will not be reliable.

The *ping* itself, apart from keeping the lighthouse on, **can also turn it on** (from stand-by). So the only solution to turn the already running lighthouse off is to instruct it with relatively short timeout, and then let the timeout expire.

### Pinging the lighthouse
The *ping* uses the command described [here](https://github.com/nairol/LighthouseRedox/blob/master/docs/Base%20Station.md#wake-up-and-set-sleep-timeout). Following examples assume a linux machine with `bluez` package installed. `hcitool`, `hciconfig`, `gatttool` are parts of this package.
```
Offset | Type   | Name             | Description
-------|--------|------------------|------------
0x00   | uint8  | unknown          | 0x12
0x01   | uint8  | cc               | command: 0x00, 0x01, 0x02
0x02   | uint16 | tttt             | timeout in sec. (big-endian)
0x04   | uint32 | YYXXVVUU         | lighthouse ID or 0xffffffff (little-endian)
0x08   | uint8  |                  | 0x00
...    | ...    |                  | ...
0x13   | uint8  |                  | 0x00
```

Let's assume that `aa:bb:cc:dd:ee:ff` is "B" LH MAC address and `UUVVXXYY` is its binhex ID, which can be found either on the LH enclosure or read from OpenVR database, where the LH is identified as `LHB-UUVVXXYY`. Ping can be then executed as BT LE write command to the characteristic with the handle `0x0035` this way:
```
gatttool --device=aa:bb:cc:dd:ee:ff -I
[aa:bb:cc:dd:ee:ff][LE]> connect
[aa:bb:cc:dd:ee:ff][LE]> char-write-req 0x0035 12ccttttYYXXVVUU000000000000000000000000
```
Note that timeout `tttt` is encoded in big-endian, while lighthouse ID uses little-endian. The timeout specifies the time in seconds in which the lighthouse will go into stand-by if it does not receive another *ping*. For the detailed description of the communication protocol (commands) see [PROTOCOL.md](/PROTOCOL.md).

### Solution
The implemented solution [lhctrl.py](/pylhctrl/lhctrl.py) uses Python `bluepy` package to access `bluez` BT LE API. The script runs the *ping* command explained above in the loop. First it wakes the LH "B" up, with the specified timeout, and then keeps pinging it, until it is either killed, or the global timeout expires.

#### Usage
```
usage: lhctrl.py [-h] -b LH_B_ID [-c LH_C_ID] [--lh_b_mac LH_B_MAC]
                 [--lh_c_mac LH_C_MAC] [--lh_timeout LH_TIMEOUT] [--hndl HNDL]
                 [-g GLOBAL_TIMEOUT] [-i INTERFACE] [-p PING_SLEEP]
                 [--try_count TRY_COUNT] [--try_pause TRY_PAUSE] [--cmd2 CMD2]
                 [-v]

Wakes up and runs Vive lighthouse(s) using BT LE power management

optional arguments:
  -h, --help            show this help message and exit
  -b LH_B_ID, --lh_b_id LH_B_ID
                        BinHex ID of the "B" lighthouse (as in
                        LHB-<8_char_id>)
  -c LH_C_ID, --lh_c_id LH_C_ID
                        Hex ID of the "C" lighthouse (as in LHB-<8char_id>)
  --lh_b_mac LH_B_MAC   BT MAC of the "B" lighthouse (in format
                        aa:bb:cc:dd:ee:ff)
  --lh_c_mac LH_C_MAC   BT MAC of the "C" lighthouse (in format
                        aa:bb:cc:dd:ee:ff)
  --lh_timeout LH_TIMEOUT
                        time (sec) in which LH powers off if not pinged [60]
  --hndl HNDL           characteristic handle [53]
  -g GLOBAL_TIMEOUT, --global_timeout GLOBAL_TIMEOUT
                        time (sec) how long to keep the lighthouse(s) alive
                        (0=forever) [0]
  -i INTERFACE, --interface INTERFACE
                        The Bluetooth interface on which to make the
                        connection to be set. On Linux, 0 means /dev/hci0, 1
                        means /dev/hci1 and so on.
  -p PING_SLEEP, --ping_sleep PING_SLEEP
                        time (sec) between two consecutive pings [20.0]
  --try_count TRY_COUNT
                        number of tries to set up a connection [5]
  --try_pause TRY_PAUSE
                        sleep time when reconnecting [2]
  --cmd2 CMD2           second byte in the data written to the LH [2]
  -v, --verbose         increase verbosity of the log to stdout
  ```
