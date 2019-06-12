#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:set et ts=4 sw=4:
#
## Copyright (C) 2019 Pho Hale <PhoHale.com>

import os
import sys
import thread

import numpy as np

try:
	from emotiv import epoc, utils
except ImportError:
	sys.path.insert(0, "..")
	from emotiv import epoc, utils

def headsetRead(headset):
	idx, data = headset.acquire_data_fast(9)
	print "Battery: %d %%" % headset.battery
	print "Contact qualities"
	print headset.quality
	metadata = {"quality": headset.quality,"battery": headset.battery}
	utils.save_as_matlab(data, headset.channel_mask, folder="../eeg_data", metadata=metadata)

def input_thread(a_list):
	raw_input()
	a_list.append(True)

def dataAcquisitionLoop(headset):
	a_list = []
	thread.start_new_thread(input_thread, (a_list,))
	while not a_list:
		headsetRead(headset)


def main():
	print "Running Data Aquisition: Press any key to terminate at the end of the block."

	channels = None
	try:
		channels = sys.argv[1].split(",")
	except:
		pass

	# Setup headset
	headset = epoc.EPOC(enable_gyro=False)
	if channels:
		headset.set_channel_mask(channels)

	# Acquire
	dataAcquisitionLoop(headset)
	#print "Data Acquisition Terminated."
	try:
		headset.disconnect()
	except e:
		print e

if __name__ == "__main__":
	sys.exit(main())
