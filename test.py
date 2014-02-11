import socket
from bitstring import BitArray, BitStream, ConstBitStream
import ephem

#server = 'rigel'
server = 'localhost'
port = 10000

def client(ip, port, data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    data += ConstBitStream('int:%d=0' % (160-data.len))
    try:
        sock.sendall(data.tobytes())
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
    client(server, port, data)

def start_calibration():
    data = ConstBitStream('0x14000200')
    client(server, port, data)

def stop_calibration():
    data = ConstBitStream('0x14000300')
    client(server, port, data)

def step(az, alt):
    data = ConstBitStream('0x14000400')
    data += ConstBitStream('intle:16=%d' % az)
    data += ConstBitStream('intle:16=%d' % alt)
    client(server, port, data)

def set_angles(nr):
    data = ConstBitStream('0x14000500')
    data += ConstBitStream('intle:16=%d' % nr)
    client(server, port, data)

def start(nr, on):
    data = ConstBitStream('0x14000600')
    data += ConstBitStream('intle:16=%d' % nr)
    data += ConstBitStream('intle:16=%d' % on)
    client(server, port, data)
