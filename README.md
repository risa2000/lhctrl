# lhctrl
## Power management of Valve v1 lighthouses over Bluetooth LE

Valve v1 lighthouses include power management feature over Bluetooth LE protocol. The protocol and message format used by this feature is briefly described (among others) here https://github.com/nairol/LighthouseRedox. How this feature works will follow.

### "B" and "C" configuration
In the most usual setup, the lighthouses are used in a pair, where one LH is switched into "B" mode (becomes master) and the other one in "C" mode (becomes slave). In this configuration, "C" can only run when also "B" is running. The consequence is that powering off "B" will put "C" into stand-by, i.e. to turn off both LHs it only needs that "B" is turned off. Conversely, if "C" is in stand-by, turning "B" on will also wake up "C".

"B" can be turned off either by simply cutting the power (disconnecting from power outlet). "B" cannot be directly turned off by BT LE command, because the BT LE power management of the lighthouses is based on the notion of **keeping the lighthouses on** rather than on **turning them on and off**.

To keep "B" running, one needs to *ping* "B" regularly over BT LE. If those pings stop then "B" will turn off after the specified timeout has been reached. This setup ensures that "B" will turn off even if the controller (e.g. SteamVR running on the user's PC) crashes. This explains why there is no command for turning the lighthouse off - it will not be reliable.

The *ping* itself, apart from keeping the lighthouse on, **can also turn it on** (from stand-by). So the only solution to turn the lighthouse off is to turn it on (with relatively short timeout) and then let the timeout expire.

### Pinging the lighthouse

The *ping* uses the command described [here](https://github.com/nairol/LighthouseRedox/blob/master/docs/Base%20Station.md#wake-up-and-set-sleep-timeout). Following examples assume a linux machine with `bluez` package installed. `hcitool`, `hciconfig`, `gatttool` are part of this package.
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

Let's assume that `aa:bb:cc:dd:ee:ff` is "B" LH MAC address and `UUVVXXYY` is its binhex ID, which can be found either on the LH enclosure or read from OpenVR database, where the LH is identified as `LHB-UUVVXXYY`. Ping can be then executed as BT LE write command to characteristic with handle `0x0035` this way:
```
gatttool --device=aa:bb:cc:dd:ee:ff -I
[aa:bb:cc:dd:ee:ff][LE]> connect
[aa:bb:cc:dd:ee:ff][LE]> char-write-req 0x0035 12ccttttYYXXVVUU000000000000000000000000
```
Note that timeout `tttt` is encoded in big-endian, while lighthouse ID uses little-endian. The timeout specifies the time in seconds in which the lighthouse will go into stand-by if it does not receive another *ping*. For the detailed description of the communication protocol (commands) see [PROTOCOL.md](/PROTOCOL.md).

### Solution

Implemented solution [lhctrl.py](/pylhctrl/lhctrl.py) uses Python `bluepy` package to access `bluez` BT LE API. The script runs in the loop the *ping* command explained above. Once run it wakes up LH "B", with specified timeout and then keeps pinging it, until it is either killed, or the global timeout expires.
