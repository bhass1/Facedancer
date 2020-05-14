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

from serial import Serial, PARITY_NONE

from facedancer import FacedancerUSBApp
from USBMassStorage import *

class TrickDiskImage(DiskImage):
    """
        Raw disk image backed by a file.
    """

    def __init__(self, filename1, filename2, block_size, verbose=0):
        self.block_size = block_size
        self.verbose = verbose

        self.filename1 = filename1
        statinfo1 = os.stat(self.filename1)
        self.size1 = statinfo1.st_size

        self.file1 = open(self.filename1, 'r+b')
        self.image1 = mmap(self.file1.fileno(), 0)


        self.filename2 = filename2
        statinfo2 = os.stat(self.filename2)
        self.size2 = statinfo2.st_size

        self.file2 = open(self.filename2, 'r+b')
        self.image2 = mmap(self.file2.fileno(), 0)

    def close(self):
        self.image1.flush()
        self.image1.close()

    def get_sector_count(self):
        return int(self.size1 / self.block_size) - 1

    def get_sector_data(self, address):

        if self.verbose == 2:
            print("<-- reading sector {}".format(address))

        block_start1= address * self.block_size
        block_end1  = (address + 1) * self.block_size   # slices are non-inclusive
        #TODO Change offsets as appropriate to match your target payload
        fat32_offset = 2496
        fat32_offset_end = 2499
        ntfs_offset = 1313672
        block_start2= (address+ntfs_offset-fat32_offset) * self.block_size
        block_end2  = ((address+ntfs_offset-fat32_offset) + 1) * self.block_size   # slices are non-inclusive
        if address >= fat32_offset and address <= fat32_offset_end:
          data = self.image2[block_start2:block_end2]
        else:
          data = self.image1[block_start1:block_end1]

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

        self.image1[block_start:block_end] = data[:self.block_size]
        self.image1.flush()


if len(sys.argv)!=3:
    print("Usage: facedancer-umass.py disk1.img disk2.img");
    sys.exit(1);

u = FacedancerUSBApp(verbose=3)
i = TrickDiskImage(sys.argv[1], sys.argv[2], 512, verbose=2)
d = USBMassStorageDevice(u, i, verbose=3)

d.connect()

try:
    d.run()
except KeyboardInterrupt:
    d.disconnect()
