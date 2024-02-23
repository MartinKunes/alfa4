import socket
import threading
import json
import time
import http.server
import socketserver

# Global variables
peer_id = "kunes-peer1"
chat_history = {}
peers = {}

# UDP server for discovery
def udp_server():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', 9876))
        while True:
            data, addr = sock.recvfrom(1024)
            message = json.loads(data)
            if 'command' in message and 'peer_id' in message:
                if message['command'] == 'hello' and message['peer_id'] != peer_id:
                    print(f"Received 'hello' from {message['peer_id']}")
                    peers[message['peer_id']] = addr
                    sock.sendto(json.dumps({"status": "ok", "peer_id": peer_id}).encode(), addr)
                    print(f"Sent 'ok' to {message['peer_id']}")
    except Exception as e:
        print(f"Exception in udp_server: {e}")



# UDP client for discovery
def udp_client():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            sock.sendto(json.dumps({"command": "hello", "peer_id": peer_id}).encode(), ('<broadcast>', 9876))
            print(f"Sent 'hello' from {peer_id}")
            time.sleep(5)
    except Exception as e:
        print(f"Exception in udp_client: {e}")

# TCP server for receiving messages
def tcp_server():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', 9876))
        sock.listen(1)
        while True:
            conn, addr = sock.accept()
            data = conn.recv(1024)
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                print(f"EXCEPTION: tcp_server: received data is not valid JSON: {data}")
                continue
            if isinstance(message, dict) and 'command' in message:
                if message['command'] == 'hello':
                    print(f"Received 'hello' from {addr}")
                    conn.send(json.dumps({"status": "ok", "messages": chat_history}).encode())
                    print(f"Sent 'ok' to {addr}")
                elif message['command'] == 'new_message':
                    chat_history[message['message_id']] = message
                    conn.send(json.dumps({"status": "ok"}).encode())
                    print(f"Sent 'ok' to {addr}")
            conn.close()
    except Exception as e:
        print(f"Exception in tcp_server: {e}")

# TCP client for sending messages
# TCP client for sending messages
def tcp_client(message=None):
    try:
        for peer_id, addr in peers.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(addr)
                if message:
                    # Send new message to peer
                    sock.send(json.dumps({"command": "new_message", "message_id": str(time.time()), "message": message}).encode())
                else:
                    # Send hello command to peer
                    sock.send(json.dumps({"command": "hello", "peer_id": peer_id}).encode())
                data = sock.recv(1024)
                message = json.loads(data)
                if isinstance(message, dict):
                    if message['status'] == 'ok':
                        print(f"Received 'ok' from {peer_id}")
                        if 'messages' in message:
                            # Merge chat histories
                            for msg_id, msg in message['messages'].items():
                                if msg_id not in chat_history:
                                    chat_history[msg_id] = msg
                        elif 'message_id' in message:
                            # Add new message to chat history
                            chat_history[message['message_id']] = {"peer_id": message['peer_id'], "message": message['message']}
                else:
                    print(f"EXCEPTION: new_peer_handler: {peer_id}: expected dictionary, got {type(message)}")
                sock.close()
            except ConnectionError:
                print(f"EXCEPTION: new_peer_handler: {peer_id}: connection closed")
    except Exception as e:
        print(f"Exception in tcp_client: {e}")

# HTTP server for user interaction
class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        try:
            if self.path == '/send':
                length = int(self.headers.get('content-length'))
                message = json.loads(self.rfile.read(length))
                message_id = str(time.time())
                chat_history[message_id] = {"peer_id": peer_id, "message": message}
                tcp_client(message)
                self.send_response(200)
                self.end_headers()
        except Exception as e:
            print(f"Exception in HTTP server: {e}")

def http_server():
    try:
        with socketserver.TCPServer(('', 8000), Handler) as httpd:

            httpd.serve_forever()
    except Exception as e:
        print(f"Exception in http_server: {e}")

# Start all servers
try:
    threading.Thread(target=udp_server).start()
    threading.Thread(target=udp_client).start()
    threading.Thread(target=tcp_server).start()
    threading.Thread(target=http_server).start()
except Exception as e:
    print(f"Exception in starting servers: {e}")