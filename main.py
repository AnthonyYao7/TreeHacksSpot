import os
import time

from bosdyn.api import image_pb2
from bosdyn.client.image import build_image_request
from spot_controller import SpotController
import socket
import numpy as np
import cv2

ROBOT_IP = "10.0.0.3"
SPOT_USERNAME = "admin"
SPOT_PASSWORD = "2zqa8dgw7lor"

HOST_PORT = 8080
HOST_ADDRESS = os.environ['HOST_ADDRESS']


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


def pixel_format_string_to_enum(enum_string):
    return dict(image_pb2.Image.PixelFormat.items()).get(enum_string)


def take_image_handler(spot, sock, command=None):
    # sources = ['back_fisheye_image', 'frontleft_fisheye_image', 'frontright_fisheye_image', 'left_fisheye_image',
    #            'right_fisheye_image']

    sources = ['frontleft_fisheye_image']

    pixel_format = pixel_format_string_to_enum('PIXEL_FORMAT_GREYSCALE_U8')

    image_request = [
        build_image_request(source, pixel_format=pixel_format)
        for source in sources
    ]

    image_responses = spot.get_images(image_request)

    for image in image_responses:
        num_bytes = 1
        dtype = np.uint8
        extension = '.jpg'

        img = np.frombuffer(image.shot.image.data, dtype=dtype)
        if image.shot.image.format == image_pb2.Image.FORMAT_RAW:
            try:
                img = img.reshape((image.shot.image.rows, image.shot.image.cols, num_bytes))
            except ValueError:
                img = cv2.imdecode(img, -1)
        else:
            img = cv2.imdecode(img, -1)

        image_saved_path = str(int(time.time() * 1000)) + '_' + image.source.name + extension
        cv2.imwrite(image_saved_path, img)

        send_file(image_saved_path, sock)


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

    spot.move_by_velocity_control(v_x=0, v_y=0, v_rot=(x - w // 2) / 6000, cmd_duration=1)
    time.sleep(4)


def asr_handler(spot, sock, command):
    print("Start recording audio")
    dest_file = "spotQuery.wav"
    cmd = f'arecord -vv --format=cd --device={os.environ["AUDIO_INPUT_DEVICE"]} -r 48000 --duration=10 -c 1 {dest_file}'
    try:
        # Execute the audio recording command
        # subprocess.run(cmd, shell=True, check=True)
        # Send the recorded audio file to the local machine
        os.system(cmd)
        send_file(dest_file, sock)
    except Exception as e:
        print(f"Error during audio recording: {e}")
    finally:
        # Clean up: remove the temporary audio file on Spot
        os.remove(dest_file)
    print(cmd)


COMMAND_HANDLERS = {'take_image': take_image_handler,
                    'move_towards_point': move_towards_point_handler,
                    'start_asr': asr_handler}


def main():
    # print("Start recording audio")
    # sample_name = "aaaa.wav"
    # cmd = f'arecord -vv --format=cd --device={os.environ["AUDIO_INPUT_DEVICE"]} -r 48000 --duration=10 -c 1 {sample_name}'
    # print(cmd)
    # os.system(cmd)
    # print("Playing sound")
    # os.system(f"ffplay -nodisp -autoexit -loglevel quiet {sample_name}")

    with SpotController(username=SPOT_USERNAME, password=SPOT_PASSWORD, robot_ip=ROBOT_IP) as spot:

        time.sleep(1)

        spot.move_head_in_points(yaws=[0.2, 0],
                                 pitches=[0.3, 0],
                                 rolls=[0.4, 0],
                                 sleep_after_point_reached=1)

        time.sleep(1)

        # # Make Spot to move by goal_x meters forward and goal_y meters left
        # spot.move_to_goal(goal_x=0.5, goal_y=0)
        # time.sleep(3)
        #
        # # Control Spot by velocity in m/s (or in rad/s for rotation)
        # spot.move_by_velocity_control(v_x=-0.3, v_y=0, v_rot=0, cmd_duration=2)
        # time.sleep(3)

        if spot is None:
            print("Failed to initialize Spot")
            return

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
