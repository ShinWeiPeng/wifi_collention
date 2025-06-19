from debug_log import log
import struct
import socket
import time

class RegCommand:
    def __init__(self, sock):
        self.sock = sock

    def write_register(self, reg, data):
        fmt = 'B B H H I B'
        # 資料對應順序:
        # Start (u8)
        # Len (u8)
        # Function (u16)
        # Address (u16)
        # Data (u32)
        # End (u8)
        start_code = 0x02
        end_code = 0x03
        function_code  = (ord('W') << 8) + ord('M')
        
        total_size = struct.calcsize(fmt)
        len = total_size - 2
            
        send_data = struct.pack(
            fmt,
            start_code,
            len,
            function_code,
            reg,
            data,
            end_code
        )

        try:
            self.sock.send(send_data)
        except Exception as e:
            log(f"Exception: {e}")
    
    def read_register(self, reg):
        fmt = 'B B H H B'
        # 資料對應順序:
        # Start (u8)
        # Len (u8)
        # Function (u16)
        # Address (u16)
        # End (u8)
        start_code = 0x02
        end_code = 0x03
        function_code  = (ord('R') << 8) + ord('M')
        
        total_size = struct.calcsize(fmt)
        len = total_size - 2
            
        send_data = struct.pack(
            fmt,
            start_code,
            len,
            function_code,
            reg,
            end_code
        )
    
        log(f'send_data = {send_data.hex()}')
        
        try:
            self.sock.send(send_data)
        except Exception as e:
            log(f"Exception: {e}")
        
        fmt = 'B B H I B'
        # 資料對應順序:
        # Start (u8)
        # Len (u8)
        # Function (u16)
        # Data (u32)
        # End (u8)
        
        try:
            received_data = self.sock.recv(4096)
            unpacked = struct.unpack(fmt, received_data)
            (start, len, func, data, end) = unpacked
        except Exception as e:     
            log(f"Exception: {e}")   
        
        log(f'received_data = {received_data.hex()}')
        if start != start_code or end != end_code:
            log('資料檢查碼錯誤')
            return None
        elif func != ((ord('R') << 8) + ord('M')):
            log('資料功能碼錯誤')
            return None
        else:
            return {'Fuction': func, 'Data': data}