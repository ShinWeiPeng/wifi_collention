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

            except socket.timeout:
                log("接收超時")
                
            except ConnectionResetError:
                log("連線被對方強制關閉 (RST)")
                break
            
            except ConnectionAbortedError:
                log("連線被本地或中間設備中止")
                break
            
            except OSError as e:
                log(f"其他 socket 錯誤: {e}")
                break
        
    def send_process(self):
        while True:
            data = bytearray()
            try:
                while True:
                    if self.sock ==  None:
                        break
                    try:
                        temp = self.send_buf.get(timeout=0.01)
                        data += temp
                        # if isinstance(temp, (bytes, bytearray)):
                        #     data += temp
                        
                        if len(data) > 500:
                            break

                    except queue.Empty:
                        break

                if len(data) > 0:
                    self.sock.send(data)
                    # log(f"Send {len(data)} bytes")

            except OSError as e:
                if e.winerror == 10038:
                    print("嘗試對非 socket 的對象做操作（可能已關閉或是變數錯誤）")
                else:
                    print(f"其他 OSError: {e}")
