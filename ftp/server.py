from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import socket
import os

def main():
    HOST_PORT = 8080

    # Grab the IP address of the host machine
    HOST_ADDRESS = socket.gethostbyname(socket.gethostname())

    # Instantiate a dummy authorizer for managing 'virtual' users
    authorizer = DummyAuthorizer()

    # Define a new user having full read/write permissions (username, password, directory)
    authorizer.add_anonymous("./files")

    # Instantiate an FTP handler object
    handler = FTPHandler
    handler.authorizer = authorizer

    # Instantiate an FTP server
    server = FTPServer((HOST_ADDRESS, HOST_PORT), handler)

    # Set a limit for connections. Can remove or adjust this if needed.
    server.max_cons = 10
    server.max_cons_per_ip = 5

    # Start the FTP server
    server.serve_forever()

if __name__ == "__main__":
    main()
