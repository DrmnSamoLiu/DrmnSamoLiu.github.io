#!/usr/bin/env python3

# Author : DrmnSamoLiu

import serial
from time import sleep



def accessshell():
	print('[-]Accessing U-boot shell.')
	while ser.in_waiting:
		
		# Enter "slp" when console says "Autobooting in 1 seconds"

		a = ser.readline().decode().strip('\r\n')
		if a == 'Autobooting in 1 seconds':
			ser.write(b'slp'+b'\r')


		elif a == ('rlxboot# '):
			print('[+]Got U-boot shell.')
			addbinsh()
			return 0
	
	raise(Exception,"Can't get U-boot shell.")

def addbinsh():
	
	print('[-]Add "init=/bin/sh" to bootargs')
	ser.write(b'setenv bootargs console=ttyS1,57600 root=/dev/mtdblock6 rw rts-quadspi.channels=quad init=/bin/sh'+b'\r\r')
	sleep(0.1)

	while ser.in_waiting:
		a = ser.readline().decode().strip('\r\n')

		# We need to ignore the command we just entered cuz it will be displayed as command history.
		if a == 'rlxboot# setenv bootargs console=ttyS1,57600 root=/dev/mtdblock6 rw rts-quadspi.channels=quad init=/bin/sh':
			continue

		elif a == 'rlxboot# ':
			print('[+]Added.')
			boot()
			return 0

	raise(Exception,"Failed to proceed.")

def boot():
	
	print('[-]Booting into system shell...')
	ser.write(b'sf probe;sf read 0x82000000 0x60000 0x300000;bootm 0x82000000'+b'\r')
	sleep(1)

	while ser.in_waiting:
		a = ser.readline().decode().strip('\r\n')

		# Sometimes our program will read too fast and ser.in_waiting will be zero in mid boot, causing some bug. So we wait 0.03 second on each read to avoid reading too fast.
		sleep(0.03)
		ser.write(b'\r')
		if a == '/ # ':
			print('[+]Got shell')
			return 0

	raise(Exception,"Failed to get system shell.")



COM_PORT = '/dev/ttyUSB0' # Change this if your device is not ttyUSB0
BAUD_RATES = 57600
ser = serial.Serial(COM_PORT, BAUD_RATES)

booted = False

print('[-]Waiting for C200 boot....')


while not booted:
	if ser.in_waiting:
		print('[+]Boot confirmed.')
		accessshell()
		break
	else:
		continue

print("[+]Done! Access shell from screen or minicom.")

