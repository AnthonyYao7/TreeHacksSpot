import socket
import numpy as np
import os
import cv2
import time

HOST_PORT = 8080
HOST_ADDRESS = "localhost"


def send_file(file, sock):
    # send 4 byte integer representing number of characters in the filename.
    # send filename.
    # send 4 byte integer representing number of bytes in file.
    # send file contents.

    sock.sendall(len(file).to_bytes(4, 'little'))
    sock.sendall(file.encode('utf-8'))

    with open(file, 'rb') as f:
        bt = f.read()
        sock.sendall(len(bt).to_bytes(4, 'little'))
        sock.sendall(bt)


def take_image_handler(spot, sock, command=None):
    sources = ['back_fisheye_image', 'frontleft_fisheye_image', 'frontright_fisheye_image', 'left_fisheye_image',
               'right_fisheye_image']

    # img = 128 * np.ones((512, 512, 3), dtype=np.uint8)

    cap = cv2.VideoCapture(0)

    ret, frame = cap.read()

    filename = str(int(time.time() * 1000)) + '_' + 'frontleft_fisheye_image' + '.jpg'
    cv2.imwrite(filename, frame)

    send_file(filename, sock)

def remove_non_numeric(s):
    # Using filter and lambda to remove non-numeric characters
    filtered = filter(lambda x: x.isdigit(), s)
    # Joining the filtered characters back into a string
    return ''.join(filtered)

def move_towards_point_handler(spot, sock, command):
    print(command)
    point = command[len('move_towards_point'):]
    x, w = point.split(',')
    x = int(remove_non_numeric(x))
    w = int(remove_non_numeric(w))

    print(x, w)

    print(f"Moving {(x - w // 2) / 6000} radians")


def asr_handler(spot, sock, command):
    sample_name = str(int(time.time() * 1000)) + '.wav'
    cmd = f'arecord -vv --format=cd -r 48000 --duration=10 -c 1 {sample_name}'
    os.system(cmd)
    send_file(sample_name, sock)


COMMAND_HANDLERS = {'take_image': take_image_handler,
                    'move_towards_point': move_towards_point_handler,
                    'start_asr': asr_handler}


def main():
    spot = "Balls"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.connect((HOST_ADDRESS, HOST_PORT))
        print(f"Successfully connected to {HOST_ADDRESS}:{HOST_PORT}")

    except Exception as e:
        print(f"Failed to connect to {HOST_ADDRESS}:{HOST_PORT}")
        print(f"Error: {e}")
        s.close()
        return

    buffer = ''

    while True:
        data = s.recv(4096)
        if not data:
            print("Disconnected from the server.")
            break

        buffer += data.decode('utf-8')
        while '\n' in buffer:
            command, buffer = buffer.split('\n', 1)

            for comm, handler in COMMAND_HANDLERS.items():
                if comm in command:
                    handler(spot, s, command)
                    break

    s.close()


# 10.19.187.105

if __name__ == '__main__':
    main()


