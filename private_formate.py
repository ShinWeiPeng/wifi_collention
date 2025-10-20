from debug_log import log
import struct
from wifi_function import WifiFunction 
import queue
import threading
from enum import Enum
import time

class GesnsorInstruction:
    TIME_OUT = 5
    START_CODE = 0x02
    END_CODE = 0x03
    
    class GsenAddress(Enum):
        EGA_VERSION = 0
        EGA_RUN_MODE = 1
        EGA_RUN = 2
        EGA_ENVELOPE_INTERVAL = 3
        EGA_INITIAL = 4
        EGA_OUTPUT = 5
        EGA_DATA_SRC = 6
        EGA_IMU_ACCEL_FSR = 7
        EGA_IMU_GYRO_FSR = 8
        EGA_IMU_ACCEL_X_OFFSET = 10
        EGA_IMU_ACCEL_Y_OFFSET = 11
        EGA_IMU_ACCEL_Z_OFFSET = 12
    
    def __init__(self, interface):
        self.data = bytearray()
        self.wifi = interface
        self.event_buf = queue.Queue()
        self.da_buf = queue.Queue()
        self.aa_buf = queue.Queue()
        self.ack_buf = queue.Queue()
        self.arrange_process_handle = threading.Thread(target=self.arrange_process, daemon=True).start()
        self.event_process_handle = threading.Thread(target=self.enent_display, daemon=True).start()
        
    def split_data(self):
        i = 0
        pass_records = []

        while True:
            try:
                if i >= len(self.data):
                    self.data = bytearray()
                    break
                
                if self.data[i] != GesnsorInstruction.START_CODE:
                    i += 1
                    continue
                
                length = self.data[i + 1] + 1
                
                if i + length + 1 > len(self.data):
                    self.data = self.data[i:]
                    break
                
                if self.data[i + length] == GesnsorInstruction.END_CODE:
                    pass_records.append(self.data[i:i + length + 1])
                    i += length + 1
                elif self.data[i + length + 1] == GesnsorInstruction.END_CODE:
                    pass_records.append(self.data[i:i + length + 1])
                    i += length + 2
                else:
                    log(f'data = {self.data[i:i + length]}')
                    i += 1
                    
            except Exception as e:
                # log(f'{e}, data = {self.data[i:]}, i = {i}, len = {len(self.data)}')
                self.data = self.data[i:]
                break

        return pass_records
    
    def enent_display(self):
        while True:
            data = self.event_buf.get(True, None)
            log(f'{data}')
    
    def arrange_process(self):
        while True:
            try:
                if self.wifi.sock == None:
                    continue
                
                # if self.wifi.read_buf.empty() == True:
                #     log(f'self.wifi.read_buf.empty')
                #     continue
                
                self.data += self.wifi.read_buf.get(True, None)
            
                if not self.data:
                    log(f'no data')
                    continue

                records = self.split_data()
                
                for record in records:
                    if len(record) == 0:
                        log(f'no data')
                        continue

                    function_code = record[2:4]
                    if bytes(function_code) == b'DA':
                        self.da_buf.put(record, True, GesnsorInstruction.TIME_OUT)
                    elif bytes(function_code) == b'AA':
                        self.aa_buf.put(record, True, GesnsorInstruction.TIME_OUT)
                    elif bytes(function_code) == b'EV':
                        self.event_buf.put(record, True, GesnsorInstruction.TIME_OUT)
                    else:
                        log(f'data = {record}')
                        self.ack_buf.put(record, True, GesnsorInstruction.TIME_OUT)
            except Exception as e:
                log(f'{e}')

    def start(self):
        try:
            send_data = bytes([GesnsorInstruction.START_CODE, ord('S'), ord('T'), GesnsorInstruction.END_CODE])

            self.wifi.write_data(send_data)

            data = self.ack_buf.get(True, GesnsorInstruction.TIME_OUT)
            fmt = 'B B H B'  # 這個格式對應於：Start, Len, function, End
            unpacked = struct.unpack(fmt, data)
            function_code = unpacked[2]
            
            if function_code != ((ord('T') << 8) + ord('S')):
                log('Ack Fail')
        except Exception as e:
            log(f'{e}')
            
    def stop(self):
        try:
            send_data = bytes([GesnsorInstruction.START_CODE, ord('E'), ord('D'), GesnsorInstruction.END_CODE])

            self.wifi.write_data(send_data)
            
            data = self.ack_buf.get(True, GesnsorInstruction.TIME_OUT)
            fmt = 'B B H B'  # 這個格式對應於：Start, Len, function, End
            unpacked = struct.unpack(fmt, data)
            function_code = unpacked[2]
            
            if function_code != ((ord('D') << 8) + ord('E')):
                log('Ack Fail')
                
        except Exception as e:
            log(f'{e}')
        
    def write_register(self, reg, data):
        try:
            # 資料對應順序:
            # Start (u8)
            # Function (u16)
            # Address (u16)
            # Data (u32)
            # End (u8)
            start_code = GesnsorInstruction.START_CODE
            end_code = GesnsorInstruction.END_CODE
            function_code  = ((ord('W') << 8) + ord('M'))
            
            part1 = struct.pack('>B H', start_code, function_code)
            part2 = struct.pack('<H I B', reg, data, end_code)
            send_data = part1 + part2

            self.wifi.write_data(send_data)
            
            data = self.ack_buf.get(True, GesnsorInstruction.TIME_OUT)
            fmt = 'B B H B'  # 這個格式對應於：Start, Len, function, End
            unpacked = struct.unpack(fmt, data)
            function_code = unpacked[2]
            
            if function_code != ((ord('M') << 8) + ord('W')):
                log('Ack Fail')
        except Exception as e:
            log(f"Exception: {e}")
    
    def read_register(self, reg):
        try:
            # 資料對應順序:
            # Start (u8)
            # Function (u16)
            # Address (u16)
            # End (u8)
            start_code = 0x02
            end_code = 0x03
            function_code  = (ord('R') << 8) + ord('M')
            
            part1 = struct.pack('>B H', start_code, function_code)
            part2 = struct.pack('<H B', reg, end_code)
            send_data = part1 + part2

            self.wifi.write_data(send_data)
            
            data = self.ack_buf.get(True, GesnsorInstruction.TIME_OUT)
            fmt = 'B B H I B'
            # 資料對應順序:
            # Start (u8)
            # Len (u8)
            # Function (u16)
            # Data (u32)
            # End (u8)
            unpacked = struct.unpack(fmt, data)
            function_code, return_data = unpacked[2:4]
            
            if function_code != ((ord('M') << 8) + ord('R')):
                log('Ack Fail')
            else:
                return return_data
                
        except Exception as e:
            log(f"Exception: {e}")
            return None
    
                
    def is_send_finish(self):
        return self.wifi.read_buf.empty()
    
    def write_accel_raw(self, acc_x, acc_y, acc_z, cnt):
        try:
            # 資料對應順序:
            # Start (u8)
            # Function (u16)
            # Accel X (s16)
            # Accel Y (s16)
            # Accel Z (s16)
            # End (u8)
            start_code = GesnsorInstruction.START_CODE
            end_code = GesnsorInstruction.END_CODE
            function_code  = ((ord('D') << 8) + ord('A'))
            part1 = struct.pack('>B H', start_code, function_code)
            part2 = struct.pack('h h h H B', acc_x, acc_y, acc_z, cnt, end_code)
            send_data = part1 + part2
            self.wifi.write_data(send_data)

        except Exception as e:
            log(f"Exception: {e}")
            