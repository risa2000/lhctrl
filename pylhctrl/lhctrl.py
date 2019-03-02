"""
Simple HTC Vive v1 lighthouse power management control over BT LE
"""

# external libs
from bluepy import btle

# standard imports
import time
import sys
from struct import pack

#   globals
#-------------------------------------------------------------------------------
# wake-up command header
CMD_HDR1 = 0x12
CMD_HDR2 = 0x02
# wake-up command tail
CMD_TAIL = bytes.fromhex('000000000000000000000000')
# Characteristic handle 
HCHAR = 0x35
# return error code
ERR = -1
# ping to LH timeout factor
TO_FACTOR = 0.75
# verbosity level INFO
INFO   = 1
INFO2  = 2

#   defaults
#-------------------------------------------------------------------------------
PING_SLEEP      = 20
LH_TIMEOUT      = 60
TRY_COUNT       = 5
TRY_PAUSE       = 2
GLOBAL_TIMEOUT  = 0

#   functions
#-------------------------------------------------------------------------------
def makeUpCmd(lh_id, off_timeout, cmd2=None):
    """create LH wake-up command."""
    # need to convert off timeout to big endian
    hdr1 = CMD_HDR1.to_bytes(1, 'little')
    if cmd2 is None:
        hdr2 = CMD_HDR2.to_bytes(1, 'little')
    else:
        hdr2 = cmd2.to_bytes(1, 'little')
    b_ot = off_timeout.to_bytes(2, 'big')
    b_id = lh_id.to_bytes(4, 'little')
    return pack('ss2s4s12s', hdr1, hdr2, b_ot, b_id, CMD_TAIL)

def argsCheck(args):
    """Sanity check for command line arguments."""
    if args.lh_b_id and not args.lh_b_mac:
        print('Scanning not implemented. MAC of "B" LH (option "--lh_b_mac") has to be specified.')
        sys.exit(ERR)
#    if args.lh_c_id and not args.lh_c_mac:
#        print('Scanning not implemented. MAC of "C" LH (option "--lh_c_mac") has to be specified.')
#        sys.exit(ERR)
    if (args.ping_sleep and args.lh_timeout) and (args.ping_sleep >= TO_FACTOR * args.lh_timeout):
        print('Ping sleep should be at max {:2f} of LH timeout'.format(TO_FACTOR))
        sys.exit(ERR)

def argsProcess(args):
    if args.lh_b_id:
        args.lh_b_id_int = int(args.lh_b_id, 16)
#    if args.lh_c_id:
#        args.lh_c_id_int = int(args.lh_c_id, 16)

def writeCmd(lh, hndl, cmd, verb=0):
    """Send write command and log to stdout if requested."""
    if (verb >= INFO):
        print('Writing char-cs to 0x{:x} : {:s} -> '.format(hndl, cmd.hex()), end='')
    res = lh.writeCharacteristic(hndl, cmd)
    if (verb >= INFO):
        print(res)
    return res

def readCmd(lh, hndl, verb=0):
    """Send read command and log to stdout if requested."""
    if (verb >= INFO):
        print('Reading char-cs from 0x{:x} -> '.format(hndl), end='')
    res = lh.readCharacteristic(hndl)
    if (verb >= INFO):
        print(res.hex())
    return res

def writeReadCmd(lh, hndl, cmd, verb=0):
    """Write data and read the same characterstic after."""
    res = writeCmd(lh, hndl, cmd, verb)
    return res, readCmd(lh, hndl, verb)

def connect(lh, mac, try_count, try_pause, verb=0):
    """Connect to LH, try it `try_count` times."""
    while True:
        try:
            if (verb >= INFO):
                print('Connecting to {:s} at {:s} -> '.format(mac, time.asctime()), end='')
            lh.connect(mac)
            if (verb >= INFO):
                print(lh.getState())
            break
        except btle.BTLEDisconnectError as e:
            if try_count <= 1:
                raise e
            if (verb >= INFO):
                print(e)
            try_count -= 1;
            time.sleep(try_pause)
            continue
        except:
            raise

def disconnect(lh, verb=0):
    if (verb >= INFO):
        print('Diconnecting at {:s}'.format(time.asctime()))
    lh.disconnect()

def wait(psleep, verb=0):
    if (verb >= INFO):
        print('Sleeping for {:d} sec ... '.format(psleep), end='', flush=True)
    time.sleep(psleep)
    if (verb >= INFO):
        print('Done!', flush=True)

def loop(args):
    """Run the whole loop, control only "B" lighthouse."""

    lh = btle.Peripheral()
    upCmd = makeUpCmd(args.lh_b_id_int, args.lh_timeout, args.cmd2)
    start = time.monotonic()

    while True:
        connect(lh, args.lh_b_mac, args.try_count, args.try_pause, verb=args.verbose)
        writeCmd(lh, args.hndl, upCmd, verb=args.verbose)
        if args.verbose >= INFO2:
            readCmd(lh, args.hndl, verb=args.verbose)
        disconnect(lh, verb=args.verbose)
        wait(args.ping_sleep, verb=args.verbose)
        now = time.monotonic()
        if args.global_timeout and (now - start > args.global_timeout):
            break

#   main
#-------------------------------------------------------------------------------
if __name__ == '__main__':

    from argparse import ArgumentParser

    ap = ArgumentParser(description='Wakes up and runs Vive lighthouse(s) using BT LE power management')
    ap.add_argument('-b', '--lh_b_id', type=str, required=True, help='BinHex ID of the "B" lighthouse (as in LHB-<8_char_id>)')
#    ap.add_argument('-c', '--lh_c_id', type=int, help='Hex ID of the "C" lighthouse (as in LHB-<8char_id>)')
    ap.add_argument('--lh_b_mac', type=str, help='BT MAC of the "B" lighthouse (in format XX:XX:XX:XX:XX:XX)')
#    ap.add_argument('--lh_c_mac', type=str, help='BT MAC of the "C" lighthouse')
    ap.add_argument('--lh_timeout', type=int, default=LH_TIMEOUT, help='time (sec) in which LH powers off if not pinged [%(default)s]')
    ap.add_argument('--hndl', type=int, default=HCHAR, help='characteristic handle [%(default)s]')
    ap.add_argument('-g', '--global_timeout', type=int, default=GLOBAL_TIMEOUT, help='time (sec) how long to keep the lighthouse(s) alive (0=forever) [%(default)s]')
    ap.add_argument('-p', '--ping_sleep', type=int, default=PING_SLEEP, help='time (sec) between two consecutive pings [%(default)s]')
    ap.add_argument('--try_count', type=int, default=TRY_COUNT, help='number of tries to set up a connection [%(default)s]')
    ap.add_argument('--try_pause', type=int, default=TRY_PAUSE, help='sleep time when reconnecting [%(default)s]')
    ap.add_argument('--cmd2', type=int, default=CMD_HDR2, help='second byte in the data written to the LH [%(default)s]')
    ap.add_argument('-v', '--verbose', action='count', default=0, help='increase verbosity of the log to stdout')

    args = ap.parse_args()
    argsCheck(args)
    argsProcess(args)
    loop(args)
