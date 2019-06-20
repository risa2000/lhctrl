# Valve v1 lighthouse BT LE power management protocol and commands

## GATT characteristic

Valve v1 lighthouses use the Bluetooth LE protocol for the power management. The _commands_ are data blobs which are written to the particular GATT characteristic (handle 0x0035) which the lighthouses expose publicly. The structure of the command (already mentioned in [README.md](/README.md)) is following:

### Write command

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
and can be written to the lighthouse for example by using `gatttool` from linux `bluez` package like this:
```
gatttool --device=aa:bb:cc:dd:ee:ff -I
[aa:bb:cc:dd:ee:ff][LE]> connect
Attempting to connect to aa:bb:cc:dd:ee:ff
Connection successful
[aa:bb:cc:dd:ee:ff][LE]> char-write-req 0x0035 12ccttttYYXXVVUU000000000000000000000000
```
assuming `aa:bb:cc:dd:ee:ff` is the lighthouse BT MAC address.

### Read command (response)

```
Offset | Type   | Name             | Description
-------|--------|------------------|------------
0x00   | uint8  | ee               | error code, 0x00=Ok
0x01   | uint8  | unknown          | 0x12
0x02   | uint16 | tttt             | timeout in sec. (big-endian), 0x0000 if not set
0x03   | uint8  |                  | 0x00
...    | ...    |                  | ...
0x13   | uint8  |                  | 0x00
```
Consequently the actual state of the power management can be read from the lighthouse by reading the same characteristic (handle 0x0035):
```
gatttool --device=aa:bb:cc:dd:ee:ff -I
[aa:bb:cc:dd:ee:ff][LE]> connect
Attempting to connect to aa:bb:cc:dd:ee:ff
Connection successful
[aa:bb:cc:dd:ee:ff][LE]> char-read-hnd 0x0035
Characteristic value/descriptor: ee 12 tt tt 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

## Commands

There are (currently recognized) three _commands_ which differ by `cc` byte in the written data. These commands will be distinguished as `0x1200`, `0x1201` and `0x1202`. The commands can be executed with the "default ID" (`0xffffffff`) or the "real ID" (unique LH identifier, written on the casing or accessible in OpenVR database).

The command examples will use the verbose output of [lhctrl.py](/lhctrl.py) and will try to set 40 sec. timeout. The replies will show how the different commands handle differently the custom timeout request.

### Command: `0x1200` with the default ID (`0xffffffff`)

`0x1200` puts the LH into the state in which it runs indefinitely without any timeout. The only way to turn it off is either by executing another command, which allows changing the timeout, or by powering the LH down. The reply indicates that the current timeout was set to `0x0000`, which means no timeout.
```
Writing char-cs to 0x35 : 12000028ffffffff000000000000000000000000 -> {‘rsp’: [‘wr’]}
Reading char-cs from 0x35 -> 0012000000000000000000000000000000000000
```

### Command: `0x1201` with the default ID (`0xffffffff`)

`0x1201` puts the LH into a "timeoutable" state, and sets the timeout to the default value 60 secs. Repeating this command keeps the LH running. The custom timeout values provided by the command are ignored. The reply below indicates that the current timeout value is 60 secs. (`0x003c`) even though the script asked for 40 secs. (`0x0028`).
```
Writing char-cs to 0x35 : 12010028ffffffff000000000000000000000000 -> {‘rsp’: [‘wr’]}
Reading char-cs from 0x35 -> 0012003c00000000000000000000000000000000
```

### Command: `0x1202` with the default ID (`0xffffffff`) or the real ID

`0x1202` has two "modes":

* With the **default ID** the command wakes the LH up with the requested timeout, but is not recognized for an additional _pinging_, so cannot be used to reset the timeout and keep the LH running. This means that the LH starts up, and after the specified timeout goes into the stand-but regardless if it received any additional `0x1202` commands (with default ID).
```
Writing char-cs to 0x35 : 12020028ffffffff000000000000000000000000 -> {‘rsp’: [‘wr’]}
Reading char-cs from 0x35 -> 0012002800000000000000000000000000000000
```

* With the **real ID** the command wakes the LH up with the requested timeout, and then **can be used as a ping to keep the LH alive** with the specified (custom) timeout.
```
Writing char-cs to 0x35 : 12020028<lh__id>000000000000000000000000 -> {‘rsp’: [‘wr’]}
Reading char-cs from 0x35 -> 0012002800000000000000000000000000000000
```

### Power On state

When the LH is powered on, it automatically assumes "run indefinitely" state until changed by a subsequent command, or powered down.

## State diagram

![LH v1 power management state diagram](images/LH%20v1%20BT%20power%20management.svg)
