import socket
from bitstring import BitArray, BitStream, ConstBitStream
import ephem

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
    data += ConstBitStream('0x00000000')
    client('localhost', 10000, data.tobytes())

def start_stop():
    data = ConstBitStream('0x1400020000000000000000000000000000000000')
    client('localhost', 10000, data.tobytes())
