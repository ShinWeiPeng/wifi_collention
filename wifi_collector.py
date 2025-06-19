import os
import csv
import tkinter as tk
from tkinter import filedialog
import time
import numpy as np
import threading
import socket
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
import select
import struct
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from enum import Enum
from debug_log import log

SAMPLE_FREQUENCY = 2000.0
SAMPLE_PERIOD = 1.0 / SAMPLE_FREQUENCY
FRAME_WIDTH_S = 20.0

HOST = '192.168.0.110'
PORT = 4061

class AxisPlot:
    class PlotMethod(Enum):
        RAW_DATA = "raw data"
        ALL_ACCEL = "all accel"
        
    def __init__(self, plot_method, ax, label_prefix, frame_width, sample_freq):
        self.plot_method = plot_method
        self.frame_width = frame_width
        self.sample_freq = sample_freq
        self.sample_period = 1.0 / sample_freq
        self.ax = ax
        ax.set_title(f"Accel {label_prefix.upper()}")
        ax.grid(True)

        # 各資料
        self.scale = []
        self.ac = []
        self.envelope_high = []
        self.envelope_low = []
        self.time = []
        self.xdata, self.ydata, self.zdata = [], [], []

        if plot_method == AxisPlot.PlotMethod.RAW_DATA.value:
            self.line_x, = self.ax.plot([], [], label="Accel X")
            self.line_y, = self.ax.plot([], [], label="Accel Y")
            self.line_z, = self.ax.plot([], [], label="Accel Z")
        else:
        # 對應的四條線
            (self.line_scale,) = ax.plot([], [], label="Scale", linewidth=1)
            (self.line_ac,) = ax.plot([], [], label="AC-Coupled", linewidth=1)
            (self.line_env_high,) = ax.plot([], [], label="Envelope High", linestyle='--')
            (self.line_env_low,) = ax.plot([], [], label="Envelope Low", linestyle='--')

        self.ax.set_xlim(0, frame_width)
        self.ax.set_ylim(-1.5, 1.5)
        self.ax.set_xlabel('Time (s))')
        self.ax.legend(loc="upper right")
    
    def update(self):
        try:
            if len(self.time) > 0:
                if self.plot_method == AxisPlot.PlotMethod.RAW_DATA.value:
                    self.line_x.set_data(self.time, self.xdata)
                    self.line_y.set_data(self.time, self.ydata)
                    self.line_z.set_data(self.time, self.zdata)
                else:
                    self.line_scale.set_data(self.time, self.scale)
                    self.line_ac.set_data(self.time, self.ac)
                    self.line_env_high.set_data(self.time, self.envelope_high)
                    self.line_env_low.set_data(self.time, self.envelope_low)
            
                if len(self.time) > (self.frame_width / self.sample_period):
                    self.time.pop(0)
                    
                    if self.plot_method == AxisPlot.PlotMethod.RAW_DATA.value:
                        self.xdata.pop(0)
                        self.ydata.pop(0)
                        self.zdata.pop(0)
                    else:
                        self.scale.pop(0)
                        self.ac.pop(0)
                        self.envelope_high.pop(0)
                        self.envelope_low.pop(0)

                    time_max = self.time[-1]
                    time_min = time_max - self.frame_width
                    self.ax.set_xlim(time_max - self.frame_width, time_max)
                    
                    # 動態設定 X 軸的刻度和標籤
                    num_ticks = 10  # 你可以根據需要改變刻度數量
                    ticks = np.linspace(time_min, time_max, num_ticks)  # 等間距生成刻度
                    self.ax.set_xticks(ticks)  # 設定 X 軸刻度
                    self.ax.set_xticklabels([f"{tick:.1f}" for tick in ticks])  # 設定 X 軸刻度的顯示格式
                    
                if len(self.time) > 0:
                    y_min = 0
                    y_max = 0
                    
                    if self.plot_method == AxisPlot.PlotMethod.RAW_DATA.value:
                        y_min = min(min(self.xdata), min(self.ydata), min(self.zdata)) - 1
                        y_max = max(max(self.xdata), max(self.ydata), max(self.zdata)) + 1
                    else:
                        y_min = min(min(self.scale), min(self.ac), min(self.envelope_high), min(self.envelope_low)) - 1
                        y_max = max(max(self.scale), max(self.ac), max(self.envelope_high), max(self.envelope_low)) + 1
                        
                    # 動態設定 y 軸範圍
                    self.ax.set_ylim(y_min, y_max)
                    
                    num_ticks = 5
                    ticks = np.linspace(y_min, y_max, num_ticks) 
                    self.ax.set_yticks(ticks)  
                    self.ax.set_yticklabels([f"{tick:.1f}" for tick in ticks]) 
        except Exception as e:
            log(f"Exception: {e}")
class AccelPlotter:
    class Axis(Enum):
        ACCEL_X = 'x'
        ACCEL_Y = 'y'
        ACCEL_Z = 'z'
        
    class SigPrpcessMethod(Enum):
        SCALE = 'scale'
        AC_COUPLER = 'ac'
        ENVELOPE_HIGH = 'envelope_hi'
        ENVELOPE_LOW = 'envelope_lo'
        
    def __init__(self, plot_method, frame_width, sample_freq):
        self.plot_method = plot_method
        self.plt_data_lock = threading.Lock()
        
        if plot_method == AxisPlot.PlotMethod.RAW_DATA.value:
            self.fig, ax = plt.subplots(figsize=(12, 8))
            plt.ion()   # 開啟交互模式
            self.axis_plot = AxisPlot(plot_method, ax, "Raw Data", frame_width, sample_freq)
        else:       
            self.fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

            # 開啟交互模式
            plt.ion()

            # 插入各軸的 AxisPlot 對象
            self.axis_plots = {
                'x': AxisPlot(plot_method, axes[0], 'x', frame_width, sample_freq),
                'y': AxisPlot(plot_method, axes[1], 'y', frame_width, sample_freq),
                'z': AxisPlot(plot_method, axes[2], 'z', frame_width, sample_freq)
            }

        self.fig.tight_layout()

        # 加入互動工具列：可滑鼠 zoom / pan
        self.toolbar = plt.get_current_fig_manager().toolbar
        # 如果在嵌入GUI中（例如Tkinter），可以用 NavigationToolbar2Tk

    def append_data(self, t, acc_dict):
        with self.plt_data_lock:
            if self.plot_method == AxisPlot.PlotMethod.RAW_DATA.value:
                ap = self.axis_plot
                ap.time.append(t)
                ap.xdata.append(acc_dict['x'])
                ap.ydata.append(acc_dict['y'])
                ap.zdata.append(acc_dict['z'])
            else:
                for axis in ['x', 'y', 'z']:
                    ap = self.axis_plots[axis]
                    ap.time.append(t)
                    ap.scale.append(acc_dict[axis]['scale'])
                    ap.ac.append(acc_dict[axis]['ac'])
                    ap.envelope_high.append(acc_dict[axis]['envelope_hi'])
                    ap.envelope_low.append(acc_dict[axis]['envelope_lo'])

    def update_plots(self, frame):
        with self.plt_data_lock:
            if self.plot_method == AxisPlot.PlotMethod.RAW_DATA.value:
                ap = self.axis_plot
                ap.update()
            else:
                for axis in ['x', 'y', 'z']:
                    ap = self.axis_plots[axis]
                    ap.update()
                
        self.fig.canvas.draw()
        # self.fig.canvas.flush_events()
        
class DataCollector:
    def __init__(self, data_mode, freq, frame_width, file_path):
        self.plot_method = data_mode
        self.freq = freq
        self.frame_width = frame_width
        self.file_path = file_path

        self.data = bytearray()
        self.sample_period = 1.0 / self.freq
        self.data_queue = []
        self.is_collecting = False
        self.sock = None
        self.save_cnt = 0
        self.timestamp = 0

        self.plotter = AccelPlotter(self.plot_method, self.frame_width, self.freq)
        
    def connect(self, host, port):
        try:
            if self.sock == None:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(3)
                self.sock.connect((host, port))
                self.sock.setblocking(True)
                log("✅ 連線成功")
                log(f"🌐 本地端: {self.sock.getsockname()}，遠端: {self.sock.getpeername()}")
                return self.sock
            
        except socket.error as e:
            log(f"❌ 連線失敗: {e}")
            return None
            
    def start_wifi_data_collection(self, host, port):
        if self.sock:
            self.sock.close()
            self.sock = None
        
        self.connect(host, port)
        if self.sock:
            self.is_collecting = True
            threading.Thread(target=self.collect_data_from_wifi, daemon=True).start()
            time.sleep(1)
            
            if self.plot_method == AxisPlot.PlotMethod.ALL_ACCEL.value:
                mode_data = bytes([0x02, 0x57, 0x4D, 0x01, 0x00, 0x01, 0x00, 0x00, 0x00, 0x03])
                self.sock.send(mode_data)
                time.sleep(0.5)
                
            self.is_collecting = True
            self.timestamp = 0
            start_data = bytes([0x02, ord('S'), ord('T'), 0x03])
            self.sock.send(start_data)

    def stop_wifi_data_collection(self):
        self.is_collecting = False
        
        try:    
            stop_data = bytes([0x02, 0x45, 0x44, 0x03])
            self.sock.send(stop_data)
        except Exception as e:
            log(f"Exception: {e}")
            pass
        
        if self.sock:
            self.sock.close()
            self.sock = None

    def get_record_data(self):
        i = 0
        pass_records = []
        while i < len(self.data):
            try:
                if self.data[i] != 0x02:
                    i += 1
                    continue
                length = self.data[i + 1] + 1
                if i + length + 1 > len(self.data):
                    self.data = self.data[i:]
                    break
                if self.data[i + length] == 0x03:
                    pass_records.append(self.data[i:i + length + 1])
                    i += length + 1
                else:
                    i += 1
            except Exception:
                self.data = self.data[i:]
                break
        return pass_records

    def collect_data_from_wifi(self):
        while self.is_collecting:
            try:
                # ready_to_read, _, _ = select.select([self.sock], [], [], 0.1)
                # if ready_to_read:
                self.data += self.sock.recv(4096)
                
                if not self.data:
                    log("⚠️ 無資料")
                    time.sleep(0.05)
                    continue
                
                records = self.get_record_data()

                for record in records:
                    if len(record) == 0:
                        continue
                    
                    length = record[1]
                    function_code = record[2:4]
                    
                    if function_code == b'DA':
                        if len(record[4:length + 4]) == 15:
                            fmt = 'h h h h h h H B'  # 這個格式對應於：AccX, AccY, AccZ, GyroX, GyroY, GyroZ, Count, End
                        elif len(record[4:length + 4]) == 9:
                            fmt = 'h h h H B'  # 這個格式對應於：AccX, AccY, AccZ, Count, End
                        else:
                            log(f'Length Failure, lenhth = {len(record)}, data = {record}')
                            continue

                        unpacked = struct.unpack(fmt, record[4:length + 4])
                        ax, ay, az = unpacked[:3]
                        
                        acc_dict = {AccelPlotter.Axis.ACCEL_X.value: ax, 
                                    AccelPlotter.Axis.ACCEL_Y.value: ay,
                                    AccelPlotter.Axis.ACCEL_Z.value: az}

                        self.plotter.append_data(self.timestamp, acc_dict)
                        self.data_queue.append([self.timestamp, ax, ay, az])
                        
                        self.timestamp += self.sample_period
                    elif function_code == b'AA':
                        if len(record[4:length + 4]) == 51:
                            fmt = 'f f f f f f f f f f f f H B'  
                        else:
                            log(f'Length Failure, lenhth = {len(record)}, data = {record}')
                            continue
                        
                        unpacked = struct.unpack(fmt, record[4:length + 4])
                        scale_x, scale_y, scale_z, ac_x, ac_y, ac_z, evlh_x, evlh_y, evlh_z, evll_x, evll_y, evll_z  = unpacked[:12]
                        acc_dict = {AccelPlotter.Axis.ACCEL_X.value: {AccelPlotter.SigPrpcessMethod.SCALE.value: scale_x,
                                                                        AccelPlotter.SigPrpcessMethod.AC_COUPLER.value: ac_x,
                                                                        AccelPlotter.SigPrpcessMethod.ENVELOPE_HIGH.value: evlh_x,
                                                                        AccelPlotter.SigPrpcessMethod.ENVELOPE_LOW.value: evll_x}, 
                                    AccelPlotter.Axis.ACCEL_Y.value: {AccelPlotter.SigPrpcessMethod.SCALE.value: scale_y,
                                                                        AccelPlotter.SigPrpcessMethod.AC_COUPLER.value: ac_y,
                                                                        AccelPlotter.SigPrpcessMethod.ENVELOPE_HIGH.value: evlh_y,
                                                                        AccelPlotter.SigPrpcessMethod.ENVELOPE_LOW.value: evll_y},
                                    AccelPlotter.Axis.ACCEL_Z.value: {AccelPlotter.SigPrpcessMethod.SCALE.value: scale_z,
                                                                        AccelPlotter.SigPrpcessMethod.AC_COUPLER.value: ac_z,
                                                                        AccelPlotter.SigPrpcessMethod.ENVELOPE_HIGH.value: evlh_z,
                                                                        AccelPlotter.SigPrpcessMethod.ENVELOPE_LOW.value: evll_z}}
                        
                        self.plotter.append_data(self.timestamp, acc_dict)
                        self.data_queue.append([self.timestamp, scale_x, scale_y, scale_z, ac_x, ac_y, ac_z, evlh_x, evlh_y, evlh_z, evll_x, evll_y, evll_z])
                        
                        self.timestamp += self.sample_period
                    elif function_code == b'EV':
                        string = record[4:length + 4]
                        log(f'{string}') 
                         
                self.save_to_csv()
                time.sleep(0.01)

            except Exception as e:
                log(f"Exception: {e}")
                break

    def save_to_csv(self):
        try:
            file_exists = os.path.exists(self.file_path)
            with open(self.file_path, mode='a', newline='') as file:
                writer = csv.writer(file)
                if not file_exists:
                    if self.plot_method == AxisPlot.PlotMethod.RAW_DATA.value:
                        writer.writerow(['Time', 'Accel_X', 'Accel_Y', 'Accel_Z'])
                    else:
                        writer.writerow(['Time', 'Scale_X', 'Scale_Y', 'Scale_Z', 
                                         'AC_Couple_X', 'AC_Couple_Y', 'AC_Couple_Z', 
                                         'Evelope_Upper_X', 'Evelope_Upper_Y', 'Evelope_Upper_Z', 
                                         'Evelope_Low_X', 'Evelope_Low_Y', 'Evelope_Low_Z'])
                for row in self.data_queue:
                    writer.writerow(row)
                self.data_queue.clear()
        except Exception as e:
            log(f"CSV Save Error: {e}")

    def plot_dynamic_graph(self):
        self.ani = FuncAnimation(self.plotter.fig, self.plotter.update_plots, interval=50, cache_frame_data=False)
        plt.show()
