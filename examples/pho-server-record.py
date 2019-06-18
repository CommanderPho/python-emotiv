#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:set et ts=4 sw=4:
#
## Copyright (C) 2019 Pho Hale <PhoHale.com>

import os
import sys
import thread

import numpy as np

import pylsl
import time

import socket
import json

UDP_IP_ADDRESS = "10.0.0.90"
UDP_PORT_NO = 6789
Message = "Hello, Server"

try:
	from emotiv import epoc, utils
except ImportError:
	sys.path.insert(0, "..")
	from emotiv import epoc, utils


def callback_single_sample_complete(outlet, sampleData):
    #print("Items processed: {}. Running result: {}.".format(i, result))
    outlet.push_sample(pylsl.vectori(sampleData), pylsl.local_clock())



def headsetRead(headset, single_sample_read_callback):
	#idx, data = headset.acquire_data_fast(9)
	data = headset.acquire_data(9, sample_callback=single_sample_read_callback)
	print "Battery: %d %%" % headset.battery
	print "Contact qualities"
	print headset.quality
	metadata = {"quality": headset.quality,"battery": headset.battery}
	return (data, metadata)

def input_thread(a_list):
	raw_input()
	a_list.append(True)

def dataAcquisitionLoop(headset, outlet, clientSock):
	a_list = []
	thread.start_new_thread(input_thread, (a_list,))
	# Build the callback function as a lambda function
	callback_single_single_sample_complete_with_outlet = lambda d: callback_single_sample_complete(outlet, d)
	while not a_list:
		data, metadata = headsetRead(headset, callback_single_single_sample_complete_with_outlet)
		# Push the complete metadata on write
		#
		# Send to the UDP server
		stringMetadata = json.dumps(metadata)
		clientSock.sendto(stringMetadata, (UDP_IP_ADDRESS, UDP_PORT_NO))
		# Could do in a separate thread?
		utils.save_as_matlab(data, headset.channel_mask, folder="../eeg_data", metadata=metadata)


def setupLabStreamingLayer(headset):
	info = pylsl.stream_info('Emotiv EEG', 'EEG', len(headset.channel_mask), headset.sampling_rate, pylsl.cf_float32, str(headset.serial_number))
	info_desc = info.desc()
	info_desc.append_child_value("manufacturer", "Emotiv")
	channels = info_desc.append_child("channels")

	for ch in headset.channel_mask:
		channels.append_child("channel").append_child_value("label", ch).append_child_value("unit","microvolts").append_child_value("type","EEG")

	# Outgoing buffer size = 360 seconds, transmission chunk size = 32 samples
	outlet = pylsl.stream_outlet(info, 1, 32)
	return (outlet, info_desc)

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

	# Setup UDP connection if possible
	clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	clientSock.sendto(Message, (UDP_IP_ADDRESS, UDP_PORT_NO))

	# Setup LabStreamingLayer connection
	(outlet, info_desc) = setupLabStreamingLayer(headset)

	# Acquire
	dataAcquisitionLoop(headset, outlet, clientSock)
	#print "Data Acquisition Terminated."
	try:
		headset.disconnect()
	except e:
		print e

if __name__ == "__main__":
	sys.exit(main())
