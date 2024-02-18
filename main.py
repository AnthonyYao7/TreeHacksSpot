import os
import time

from bosdyn.api import image_pb2
from bosdyn.client.image import build_image_request
from spot_controller import SpotController
from ftplib import FTP
import socket
import numpy as np
import cv2


ROBOT_IP = "10.0.0.3"#os.environ['ROBOT_IP']
SPOT_USERNAME = "admin"#os.environ['SPOT_USERNAME']
SPOT_PASSWORD = "2zqa8dgw7lor"#os.environ['SPOT_PASSWORD']

HOST_PORT = 8080
HOST_ADDRESS = os.environ['HOST_ADDRESS']


def pixel_format_string_to_enum(enum_string):
    return dict(image_pb2.Image.PixelFormat.items()).get(enum_string)


def take_image_handler(spot, command=None):
    sources = ['back_fisheye_image', 'frontleft_fisheye_image', 'frontright_fisheye_image', 'left_fisheye_image',
               'right_fisheye_image']
    pixel_format = pixel_format_string_to_enum('PIXEL_FORMAT_RGB_U8')

    image_request = [
        build_image_request(source, pixel_format=pixel_format)
        for source in sources
    ]

    image_responses = spot.get_images(image_request)

    for image in image_responses:
        num_bytes = 3
        dtype = np.uint8
        extension = '.jpg'

        img = np.frombuffer(image.shot.image.data, dtype=dtype)
        if image.shot.image.format == image_pb2.Image.FORMAT_RAW:
            try:
                # Attempt to reshape array into an RGB rows X cols shape.
                img = img.reshape((image.shot.image.rows, image.shot.image.cols, num_bytes))
            except ValueError:
                # Unable to reshape the image data, trying a regular decode.
                img = cv2.imdecode(img, -1)
        else:
            img = cv2.imdecode(img, -1)

        # Save the image from the GetImage request to the current directory with the filename
        # matching that of the image source.
        image_saved_path = "f"
        cv2.imwrite(image_saved_path + extension, img)


def move_towards_point_handler(spot, command):
    pass

def upload_file(hostname, filepath):
    try:
        # Connect to the FTP server
        ftp = FTP(hostname)
        ftp.login()

        # Change to binary mode to ensure correct file transfer
        ftp.cwd('/')
        ftp.storbinary('STOR ' + filepath.split('/')[-1], open(filepath, 'rb'))

        print(f"File '{filepath}' uploaded successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the FTP connection
        ftp.quit()


def main():
    #example of using micro and speakers
    print("Start recording audio")
    sample_name = "aaaa.wav"
    cmd = f'arecord -vv --format=cd --device={os.environ["AUDIO_INPUT_DEVICE"]} -r 48000 --duration=10 -c 1 {sample_name}'
    print(cmd)
    os.system(cmd)
    print("Playing sound")
    os.system(f"ffplay -nodisp -autoexit -loglevel quiet {sample_name}")

    # Capture image
    camera_capture = cv2.VideoCapture(0)
    rv, image = camera_capture.read()
    print(f"Image Dimensions: {image.shape}")
    camera_capture.release()

    with SpotController(username=SPOT_USERNAME, password=SPOT_PASSWORD, robot_ip=ROBOT_IP) as spot:

        time.sleep(1)

        # Move head to specified positions with intermediate time.sleep
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

        # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # try:
        #     s.connect((HOST_ADDRESS, HOST_PORT))
        #     print(f"Successfully connected to {HOST_ADDRESS}:{HOST_PORT}")

        #     # You can send and receive data here using s.sendall() and s.recv()
        #     # Example: s.sendall(b'Hello, server')
        # except Exception as e:
        #     print(f"Failed to connect to {HOST_ADDRESS}:{HOST_PORT}")
        #     print(f"Error: {e}")
        #     s.close()
        #     return

        # buffer = ''

        # while True:

        #     pass

            # data = s.recv(4096)

            # if not data:
            #     print("Disconnected from the server.")
            #     break

            # buffer += data.decode('utf-8')
            # while '\n' in buffer:
            #     command, buffer = buffer.split('\n', 1)

            #     commands = {'take_image': take_image_handler,
            #                 'move_towards_point': move_towards_point_handler}

            #     for comm, handler in commands:
            #         if comm in command:
            #             handler(spot, command)
            #             break

                    # depth_bytes = depth.tobytes()
                    # visual_bytes = visual.tobytes()
                    # s.sendall(len(depth_bytes).to_bytes(4, 'little'))
                    # s.sendall(depth_bytes)
                    # s.sendall(len(visual_bytes).to_bytes(4, 'little'))
                    # s.sendall(visual_bytes)

        # s.close()


# 10.19.187.105

if __name__ == '__main__':
    main()
