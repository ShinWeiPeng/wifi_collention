import os
import csv
import time
import threading
import struct
from enum import Enum
from debug_log import log

        
class DataCollector:
    class PlotMethod(Enum):
        RAW_DATA = "Raw Data"
        ALL_ACCEL = "All Acc Data"
        
    def __init__(self, data_mode, g_sensor_instruction, plot_function, freq, frame_width, file_path):
        self.plot_method = data_mode
        self.freq = freq
        self.frame_width = frame_width
        self.file_path = file_path
        self.plot = plot_function

        self.data = bytearray()
        self.sample_period = 1.0 / self.freq
        self.data_queue = []
        self.is_collecting = False
        self.save_cnt = 0
        self.timestamp = 0
        self.g_sen_instruction = g_sensor_instruction
        
        self.save_csv_handle = threading.Thread(target=self.save_to_csv).start()
        
        if self.plot_method == DataCollector.PlotMethod.RAW_DATA.value:
            self.get_data = self.g_sen_instruction.da_buf.get
            self.queue_hanle = self.g_sen_instruction.da_buf
        else:
            self.get_data = self.g_sen_instruction.aa_buf.get
            self.queue_hanle = self.g_sen_instruction.aa_buf
            
    def collect_data(self):
        while self.is_collecting:
            if self.queue_hanle.empty() == True:
                time.sleep(0.001)
                continue
            
            try:
                data = self.get_data(True, None)
                
                if not data:
                    break  

                if len(data) == 19:
                    fmt = 'B B H h h h h h h H B'
                elif len(data) == 13:
                    fmt = 'B B H h h h H B'
                elif len(data) == 55:
                    fmt = 'B B H f f f f f f f f f f f f H B'
                else:
                    log(f'Length Failure, len = {len(data)}, data = {data}')
                    continue

                unpacked = struct.unpack(fmt, data)

                if self.plot_method == DataCollector.PlotMethod.RAW_DATA.value:
                    ax, ay, az = unpacked[3:6]
                    self.plot.append_plot(self.timestamp, ax, ay, az)
                    acc = [self.timestamp, ax, ay, az]
                else:
                    scale_x, scale_y, scale_z, ac_x, ac_y, ac_z, evl_up_x, evl_up_y, evl_up_z, evl_lo_x, evl_lo_y, evl_lo_z = unpacked[3:15]
                    acc = [self.timestamp,
                        scale_x, scale_y, scale_z,
                        ac_x, ac_y, ac_z,
                        evl_up_x, evl_up_y, evl_up_z,
                        evl_lo_x, evl_lo_y, evl_lo_z]
                    self.plot.append_plot(self.timestamp, scale_x, scale_y, scale_z,
                                          ac_x, ac_y, ac_z,
                                          evl_up_x, evl_up_y, evl_up_z,
                                          evl_lo_x, evl_lo_y, evl_lo_z)

                self.data_queue.append(acc)
                self.timestamp += self.sample_period
            except Exception as e:
                log(f'{e}')

    def save_to_csv(self):
        while True:
            try:
                time.sleep(0.05)
                
                folder_path = os.path.dirname(self.file_path)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                    
                file_exists = os.path.exists(self.file_path)
                with open(self.file_path, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    if not file_exists:
                        if self.plot_method == DataCollector.PlotMethod.RAW_DATA.value:
                            writer.writerow(['Time', 'Accel_X', 'Accel_Y', 'Accel_Z'])
                        else:
                            writer.writerow(['Time', 'Scale_X', 'Scale_Y', 'Scale_Z', 
                                            'AC_Couple_X', 'AC_Couple_Y', 'AC_Couple_Z', 
                                            'Evelope_Upper_X', 'Evelope_Upper_Y', 'Evelope_Upper_Z', 
                                            'Evelope_Low_X', 'Evelope_Low_Y', 'Evelope_Low_Z'])
                    if len(self.data_queue) > 0:
                        for row in self.data_queue:
                            writer.writerow(row)
                        self.data_queue.clear()
            except Exception as e:
                log(f"CSV Save Error: {e}")
                break

