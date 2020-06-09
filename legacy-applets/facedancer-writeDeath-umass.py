#!/usr/bin/env python3
#
# facedancer-umass.py
#
# Creating a disk image under linux:
#
#   # fallocate -l 100M disk.img
#   # fdisk disk.img
#   # losetup -f --show disk.img
#   # kpartx -a /dev/loopX
#   # mkfs.XXX /dev/mapper/loopXpY
#   # mount /dev/mapper/loopXpY /mnt/point
#       do stuff on /mnt/point
#   # umount /mnt/point
#   # kpartx -d /dev/loopX
#   # losetup -d /dev/loopX

import sys
import argparse

from serial import Serial, PARITY_NONE

from facedancer import FacedancerUSBApp
from USBMassStorage import *

class RawDiskImage(DiskImage):
    """
        Raw disk image backed by a file.
    """

    def __init__(self, filename, block_size, verbose=0):
        self.filename = filename
        self.block_size = block_size
        self.verbose = verbose

        statinfo = os.stat(self.filename)
        self.size = statinfo.st_size

        self.file = open(self.filename, 'r+b')
        self.image = mmap(self.file.fileno(), 0)

    def close(self):
        self.image.flush()
        self.image.close()

    def get_sector_count(self):
        return int(self.size / self.block_size) - 1

    def get_sector_data(self, address):

        if self.verbose == 2:
            print("<-- reading sector {}".format(address))

        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive
        data = self.image[block_start:block_end]

        if self.verbose > 3:

            if not any(data):
                print("<-- reading sector {} [all zeroes]".format(address))
            else:
                print("<-- reading sector {} [{}]".format(address, data))

        return data

    def put_data(self, address, data):
        if self.verbose > 1:
            blocks = int(len(data) / self.block_size)
            print("--> writing {} blocks at lba {}".format(blocks, address))

        super().put_data(address, data)


    def put_sector_data(self, address, data):
        quit()

        if self.verbose == 2:
            print("--> writing sector {}".format(address))

        if len(data) > self.block_size:
            print("WARNING: got {} bytes of sector data; expected a max of {}".format(len(data), self.block_size))

        block_start = address * self.block_size
        block_end   = (address + 1) * self.block_size   # slices are NON-inclusive

        if self.verbose > 3:
            if not any(data):
                print("--> writing sector {} [all zeroes]".format(address))
            else:
                print("--> writing sector {} [{}]".format(address, data))

        self.image[block_start:block_end] = data[:self.block_size]
        self.image.flush()

def getOpts():
    parser = argparse.ArgumentParser(description='Emulate USB Mass Storage w/ Facedancer. And die when a write request is received. ')
    parser.add_argument('disk', type=str,
                                default="disk.img",
                                help='Disk img file to emulate')
    parser.add_argument('-q', dest='quiet', 
                                required=False,
                                action='store_true',
                                help="Quiet. Don't output to console")

    args = parser.parse_args()
    print("> using disk: "+args.disk)
    print("> using quiet: {}".format(args.quiet))

    return args

def main():
    args = getOpts()
    if args.quiet:
        vbose = 0
    else:
        vbose = 3
    
    u = FacedancerUSBApp(verbose=vbose, backend="greatfet")
    i = RawDiskImage(args.disk, 512, verbose=vbose)
    d = USBMassStorageDevice(u, i, verbose=vbose)
    
    d.connect()
    
    try:
        d.run()
    except KeyboardInterrupt:
        d.disconnect()

if __name__=="__main__":
    main()
