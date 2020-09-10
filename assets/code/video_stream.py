#!/usr/bin/env python3

# Author : DuSu


import binascii
import os
from pwn import *
from Crypto.Hash import MD5
from Crypto.Cipher import AES

USER = 'admin'
PASSWORD = '' # Change this to the passwd hash you found in user config
HOST = '192.168.1.xx' # camera's IP


PORT = 8800
OUTFILE_NAME = 'c200_stream.m2ts'
PLAYER = 'mpv'
CIPHER = None
RN = '\r\n'
BOUNDARY = '--client-stream-boundary--'
_BOUNDARY = '--' + BOUNDARY
MARKER_LENGTH = _BOUNDARY + RN \
	+ 'Content-Type: video/mp2t' + RN \
	+ 'Content-Length: ' + RN
METHOD = 'POST'
URI = '/stream'
USER_AGENT = 'CIA_Camera_Inspector_Agent'
REALM = 'TP-Link IP-Camera'
ALGO = 'MD5'
NC = '00000001'
CNONCE = 'cafebabedeadc0de'
OPAQUE = '64943214654649846565646421'
HTTP_REQ_GET_AUTH_NONCE = '{} {} HTTP/1.1\r\nHost: {}:{}\r\nUser-Agent: {}\r\nAccept: */*\r\nContent-Type: multipart/mixed; boundary={}\r\nContent-Length: 0\r\n\r\n'
HTTP_REQ_START_STREAM = '{} {} HTTP/1.1\r\nHost: {}:{}\r\nUser-Agent: {}\r\nAccept: */*\r\nContent-Type: multipart/mixed; boundary={}\r\nAuthorization: Digest username="{}",realm="{}",uri="{}",algorithm={},nonce="{}",nc={},cnonce="{}",qop=auth,response="{}",opaque="{}"\r\nConnection: keep-alive\r\nContent-Length: -1\r\n\r\n'

# dunno if the \r\n at the end should be there... does not match len 120 if they are kept...
JSON_REQ_1 = '----client-stream-boundary--\r\nContent-Type: application/json\r\nContent-Length: 120\r\n\r\n{"type":"request","seq":1,"params":{"preview":{"channels":[0],"resolutions":["HD"],"audio":["default"]},"method":"get"}}'#\r\n'

def get_auth_nonce(p):
	# returns auth_nonce as string
	req = HTTP_REQ_GET_AUTH_NONCE.format(METHOD, URI, HOST, PORT, USER_AGENT, \
		BOUNDARY)
	p.send(req)
	'RCV: %r' % p.recvuntil('nonce="')
	auth_nonce = p.recvuntil('"', drop=True)
	p.recvuntil('Connection: close' + RN * 2)
	return auth_nonce.decode()

def make_response(auth_nonce):
	to_be_hashed = '{}:{}:{}'.format(USER, REALM, PASSWORD)
	HA1 = MD5.new(to_be_hashed.encode()).hexdigest()
	to_be_hashed = '{}:{}'.format(METHOD, URI)
	HA2 = MD5.new(to_be_hashed.encode()).hexdigest()
	to_be_hashed = '{}:{}:{}:{}:auth:{}'.format(HA1, auth_nonce, NC, CNONCE, HA2)
	response = MD5.new(to_be_hashed.encode()).hexdigest()
	return response

def start_stream(p, auth_nonce, response):
	# returns aes_nonce from "key exchange" as a string
	req = HTTP_REQ_START_STREAM.format(METHOD, URI, HOST, PORT, USER_AGENT, \
		BOUNDARY, USER, REALM, URI, ALGO, auth_nonce, NC, CNONCE, response, \
		OPAQUE)
	p.send(req)
	#print('REQ: %r' % req)
	p.recvuntil('nonce="')
	aes_nonce = p.recvuntil('"', drop=True)
	p.recvuntil('Connection: keep-alive' + RN * 2)
	p.send(JSON_REQ_1)
	return aes_nonce.decode()

def make_cipher(aes_nonce, verbose=False):
	global CIPHER
	to_be_hashed = '{}:{}'.format(aes_nonce, PASSWORD)
	key = MD5.new(to_be_hashed.encode()).digest()
	to_be_hashed = '{}:{}'.format(USER, aes_nonce)
	iv = MD5.new(to_be_hashed.encode()).digest()
	CIPHER = AES.new(key, AES.MODE_CBC, iv)
	if verbose:
		log.info('AES KEY: {}'.format(binascii.hexlify(key).decode()))
		log.info('AES IV:  {}'.format(binascii.hexlify(iv).decode()))

def decrypt(enc):
	plain = CIPHER.decrypt(enc)
	npad = plain[-1]
	pad = plain[-npad:]
	if pad != bytes([npad] * npad):
		log.error('Problem with padding')
	plain = plain[:-npad]
	return plain

def main():
	# create and open file
#	if os.path.exists(OUTFILE_NAME):
#		os.remove(OUTFILE_NAME)
#	os.mkfifo(OUTFILE_NAME)
	fd = os.open(OUTFILE_NAME, os.O_RDWR)
	# launch player
#	player = process([PLAYER, OUTFILE_NAME])
	# get connection, auth, aes nonce, cipher
	p = remote(LOCALHOST, PORT)
	auth_nonce = get_auth_nonce(p)
	log.info('AUTH NONCE: {}'.format(auth_nonce))
	response = make_response(auth_nonce)
	aes_nonce = start_stream(p, auth_nonce, response)
	log.info('AES NONCE: {}'.format(aes_nonce))
	make_cipher(aes_nonce, verbose=True)

	content_type = b'application/json'
	while (content_type == b'application/json'):
		rcv = p.recvuntil(RN * 2, drop=True)
		pos_start_type = rcv.find(b'Content-Type: ')
		pos_end_type = rcv[pos_start_type:].find(b'\r\n')
		content_type = rcv[pos_start_type + len('Content-Type: '):pos_start_type + pos_end_type]
		pos_start_len = rcv.find(b'Content-Length: ')
		pos_end_len = rcv[pos_start_len:].find(b'\r\n')
		content_len = int(rcv[pos_start_len + len('Content-Length: '):pos_start_len + pos_end_len])
		content = p.recv(content_len)
		if p.recv(2) != b'\r\n':
			log.info('DID NOT RCV %r' % '\r\n')

	enc = content
	print('RCV: {} encrypted bytes (Content-Length: {})'.format(len(enc), content_len))
	plain = decrypt(enc)
	os.write(fd, plain)
	# process stream: recv, decrypt and write to file
	while (True):
		rcv = p.recvuntil(RN * 2, drop=True)
		pos_start_len = rcv.find(b'Content-Length: ')
		pos_end_len = rcv[pos_start_len:].find(b'\r\n')
		content_len = int(rcv[pos_start_len + len('Content-Length: '):pos_start_len + pos_end_len])
		enc = b''
		 # fetching everything in one go fails... so byte by byte it is!!!
		for i in range(content_len):
			enc += p.recv(1)
		print('RCV: {} encrypted bytes (Content-Length: {})'.format(len(enc), content_len))
		if p.recv(2) != b'\r\n':
			log.info('DID NOT RCV %r' % '\r\n')
		plain = decrypt(enc)
		os.write(fd, plain)

if __name__ == '__main__':
	main()
