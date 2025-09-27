import socket
import os
import sys

if len(sys.argv) != 2:
    print("Usage: python myftp.py server-name")
    sys.exit(1)

HOST = sys.argv[1]  # server-name from command line
PORT = 2121  # match the pyftpdlib server port
BUFFER_SIZE = 1024

def recv_response(sock):
    data = sock.recv(BUFFER_SIZE).decode()
    print(data.strip())
    return data

def parse_pasv(response):
    import re
    m = re.search(r'\((.*?)\)', response)
    if not m:
        return None, None
    parts = m.group(1).split(',')
    ip = '.'.join(parts[:4])
    port = int(parts[4]) * 256 + int(parts[5])
    return ip, port

def open_data_connection(ip, port):
    data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_sock.connect((ip, port))
    return data_sock

def main():
    ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ctrl_sock.connect((HOST, PORT))
    
    recv_response(ctrl_sock)
    
    username = input("Username: ")
    ctrl_sock.sendall(f"USER {username}\r\n".encode())
    recv_response(ctrl_sock)
    
    password = input("Password: ")
    ctrl_sock.sendall(f"PASS {password}\r\n".encode())
    recv_response(ctrl_sock)
    
    while True:
        cmd = input("myftp> ").strip()
        if not cmd:
            continue
        
        if cmd.lower() == "quit":
            ctrl_sock.sendall(b"QUIT\r\n")
            recv_response(ctrl_sock)
            break
        
        elif cmd.lower() == "ls":
            ctrl_sock.sendall(b"PASV\r\n")
            pasv_resp = recv_response(ctrl_sock)
            ip, data_port = parse_pasv(pasv_resp)
            if not ip:
                print("Failed to enter passive mode.")
                continue
            ctrl_sock.sendall(b"LIST\r\n")
            data_sock = open_data_connection(ip, data_port)
            data = b""
            while True:
                chunk = data_sock.recv(BUFFER_SIZE)
                if not chunk:
                    break
                data += chunk
            data_sock.close()
            print(data.decode())
            recv_response(ctrl_sock)
        
        elif cmd.lower().startswith("cd "):
            path = cmd[3:]
            ctrl_sock.sendall(f"CWD {path}\r\n".encode())
            recv_response(ctrl_sock)
        
        elif cmd.lower().startswith("get "):
            filename = cmd[4:]
            ctrl_sock.sendall(b"PASV\r\n")
            pasv_resp = recv_response(ctrl_sock)
            ip, data_port = parse_pasv(pasv_resp)
            if not ip:
                print("Failed to enter passive mode.")
                continue
            ctrl_sock.sendall(f"RETR {filename}\r\n".encode())
            data_sock = open_data_connection(ip, data_port)
            with open(filename, "wb") as f:
                while True:
                    chunk = data_sock.recv(BUFFER_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
            data_sock.close()
            recv_response(ctrl_sock)
            print(f"{filename} downloaded.")
        
        elif cmd.lower().startswith("put "):
            filename = cmd[4:]
            if not os.path.isfile(filename):
                print(f"File {filename} does not exist locally.")
                continue
            ctrl_sock.sendall(b"PASV\r\n")
            pasv_resp = recv_response(ctrl_sock)
            ip, data_port = parse_pasv(pasv_resp)
            if not ip:
                print("Failed to enter passive mode.")
                continue
            ctrl_sock.sendall(f"STOR {filename}\r\n".encode())
            data_sock = open_data_connection(ip, data_port)
            with open(filename, "rb") as f:
                data_sock.sendall(f.read())
            data_sock.close()
            recv_response(ctrl_sock)
            print(f"{filename} uploaded.")
        
        elif cmd.lower().startswith("delete "):
            filename = cmd[7:]
            ctrl_sock.sendall(f"DELE {filename}\r\n".encode())
            recv_response(ctrl_sock)
        
        else:
            print("Unknown command. Use ls, cd, get, put, delete, quit.")

    ctrl_sock.close()

if __name__ == "__main__":
    main()
