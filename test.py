import socket
from bitstring import BitArray, BitStream, ConstBitStream
import ephem

server = 'localhost'
port = 10000

def client(ip, port, data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    try:
        sock.sendall(data)
        response = sock.recv(1024)
        print response
    finally:
        sock.close()


def location(lon, lat, alt):
    data = ConstBitStream('0x14000100')
    data += ConstBitStream('floatle:32=%f' % (lon*ephem.degree))
    data += ConstBitStream('floatle:32=%f' % (lat*ephem.degree))
    data += ConstBitStream('floatle:32=%f' % alt)
    data += ConstBitStream('int:%d=0' % (160-data.len))
    client(server, port, data.tobytes())

def start_stop(nr, on):
    data = ConstBitStream('0x14000200')
    data += ConstBitStream('intle:16=%d' % nr)
    data += ConstBitStream('intle:16=%d' % on)
    data += ConstBitStream('int:%d=0' % (160-data.len))
    client(server, port, data.tobytes())

def step(az, alt):
    data = ConstBitStream('0x14000300')
    data += ConstBitStream('intle:16=%d' % az)
    data += ConstBitStream('intle:16=%d' % alt)
    data += ConstBitStream('int:%d=0' % (160-data.len))
    client(server, port, data.tobytes())
