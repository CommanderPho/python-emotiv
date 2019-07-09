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
PacketSendDuration = 9 #Specifies how long between signal quality packets and saving to .mat file. In seconds.

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
	data = headset.acquire_data(PacketSendDuration, sample_callback=single_sample_read_callback)
	print "Battery: %d %%" % headset.battery
	print "Contact qualities"
	print headset.quality
	metadata = {"quality": headset.quality,"battery": headset.battery}
	return (data, metadata)

def input_thread(a_list):
	raw_input()
	a_list.append(True)


def save_as_mat_thread(data, channel_mask, metadata):
	utils.save_as_matlab(data, channel_mask, folder="../eeg_data", metadata=metadata)

# def dataAcquisitionLoop(headset, outlets, clientSock):
def dataAcquisitionLoop(headset, outlets):
	a_list = []
	thread.start_new_thread(input_thread, (a_list,))
	# Build the callback function as a lambda function
	callback_single_single_sample_complete_with_outlet = lambda d: callback_single_sample_complete(outlets['data'], d)
	while not a_list:
		try:
			data, metadata = headsetRead(headset, callback_single_single_sample_complete_with_outlet)
			# Push the complete metadata on write
			metadataOutputVector = []
			# print("battery type:", type(float(metadata["battery"])))
			metadataOutputVector.append( float( metadata["battery"] ) )
			# print("quality type:", type(metadata["quality"]))

			metadataOutputVector.extend( [metadata["quality"][v] for v in headset.channel_mask] )
			# for i,channel in enumerate(e.channel_mask):
			#             print "%10s: %.2f %20s: %.2f" % (channel, data[i], "Quality", e.quality[channel])
			outlets['metadata'].push_sample( pylsl.vectori( metadataOutputVector ), pylsl.local_clock() )
			# Send to the UDP server
			# stringMetadata = json.dumps(metadata)
			# clientSock.sendto(stringMetadata, (UDP_IP_ADDRESS, UDP_PORT_NO))
			# Perform the writing in a separate thread.
			thread.start_new_thread( save_as_mat_thread, (data, headset.channel_mask, metadata) )

		except epoc.EPOCTurnedOffError:
			print("Headset has been disconnected! Trying to reconnect ...")

		except ValueError as e:
			if e == "The device has no langid":
				print("The USB Dongle doesn't appear to be connected.")
				print("\t Please connect it and then try again!")
				raise
			else:
				print("Other Value Error: ", e)
				raise






def setupLabStreamingLayer(headset):
    # (self, name='untitled', type='', channel_count=1, nominal_srate=IRREGULAR_RATE, channel_format=cf_float32, source_id='', handle=None)
	dataStreamInfo = pylsl.stream_info('Emotiv EEG', 'EEG', len(headset.channel_mask), headset.sampling_rate, pylsl.cf_float32, str(headset.serial_number))
	dataStreamInfo_desc = dataStreamInfo.desc()
	dataStreamInfo_desc.append_child_value("manufacturer", "Emotiv")

	# The metadataStream consists of the channel qualities and the battery level
	metadataStreamInfo = pylsl.stream_info('Emotiv EEG Meta', '', (len(headset.channel_mask) + 1), (1.0 / PacketSendDuration), pylsl.cf_float32, str(headset.serial_number))
	metadataStreamInfo_desc = metadataStreamInfo.desc()
	metadataStreamInfo_desc.append_child_value("manufacturer", "Emotiv")

	channels = dataStreamInfo_desc.append_child("channels")
	channelsMeta = metadataStreamInfo_desc.append_child("channels")

	channelsMeta.append_child("channel").append_child_value("label", "battery").append_child_value("unit","PercentCharge").append_child_value("type","")
	for ch in headset.channel_mask:
		channels.append_child("channel").append_child_value("label", ch).append_child_value("unit","microvolts").append_child_value("type","EEG")
		channelsMeta.append_child("channel").append_child_value("label", ch).append_child_value("unit","EmotivQualityUnits").append_child_value("type","")

	# Outgoing buffer size = 360 seconds, transmission chunk size = 32 samples
	# stream_outlet(info, chunk_size=0, max_buffered=360):
	# outlets['data'] = pylsl.stream_outlet(dataStreamInfo, 1, 32)
	# outlets['metadata'] = pylsl.stream_outlet(metadataStreamInfo, 1, 32)
	# return outlets
	return {"data": pylsl.stream_outlet(dataStreamInfo, 1, 32), "metadata": pylsl.stream_outlet(metadataStreamInfo, 1, 32)}

def main():
	print "Running Data Aquisition: Press any key to terminate at the end of the block."

	channels = None
	try:
		channels = sys.argv[1].split(",")
	except:
		pass

	try:
		# Setup headset
		headset = epoc.EPOC(enable_gyro=False)
		if channels:
			headset.set_channel_mask(channels)
			
	except ValueError as e:
		if e == "The device has no langid":
			print("The USB Dongle doesn't appear to be connected.")
			print("\t Please connect it and then try again!")
			raise
		else:
			print("Other Value Error: ", e)
			raise

	# Setup UDP connection if possible
	#clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	#clientSock.sendto(Message, (UDP_IP_ADDRESS, UDP_PORT_NO))

	# Setup LabStreamingLayer connection
	outlets = setupLabStreamingLayer(headset)

	# Acquire
	# dataAcquisitionLoop(headset, outlets, clientSock)
	dataAcquisitionLoop(headset, outlets)
	#print "Data Acquisition Terminated."
	try:
		headset.disconnect()
	except e:
		print e

if __name__ == "__main__":
	sys.exit(main())
