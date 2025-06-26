import time
import threading
import socket
from debug_log import log
import queue

class WifiFunction:
    MAX_TIME_OUT = 0.1
    
    def __init__(self, host, port):
        self.is_connect = False
        self.sock = None
        self.host = host
        self.port = port
        self.send_buf = queue.Queue()
        self.read_buf = queue.Queue()
        self.send_process_handle = threading.Thread(target=self.send_process, daemon=True).start()
        self.received_process_handle = threading.Thread(target=self.received_process, daemon=True).start() 
    
    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(WifiFunction.MAX_TIME_OUT)
            self.sock.connect((self.host, self.port))
            self.sock.setblocking(True)
            time.sleep(1)
            self.is_connect = True
            return True
        except Exception as e:
            log(f'{e}')
            self.sock = None
            self.is_connect = False
        
    def write_data(self, data):
        try:
            self.send_buf.put(data, True, WifiFunction.MAX_TIME_OUT)
        except Exception as e:
            log(f'{e}')
        
    def read_data(self):
        data = self.read_buf.get()
        return data
        
    def received_process(self):
        while True:
            try:
                if self.is_connect == False:
                    continue
                
                data = self.sock.recv(4096)
                # print([f'{b:02X}' for b in data])
                if len(data) > 0:
                    self.read_buf.put(data, True, WifiFunction.MAX_TIME_OUT)
                time.sleep(0.01)

            except Exception as e:
                log(f'{e}')
                break
        
    def send_process(self):
        while True:
            data = bytearray()
            try:
                # Collect as many packets as possible within ~5ms
                start_time = time.time()

                while True:
                    try:
                        temp = self.send_buf.get(timeout=0.01)

                        if isinstance(temp, (bytes, bytearray)):
                            data += temp

                        if len(data) > 500:
                            break

                    except queue.Empty:
                        break

                if len(data) > 0:
                    self.sock.send(data)
                    # log(f"Send {len(data)} bytes")

            except Exception as e:
                log(f'Send Error: {e}')
                time.sleep(0.1)
