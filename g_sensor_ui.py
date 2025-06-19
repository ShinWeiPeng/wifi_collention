import os
import csv
import numpy as np
import tkinter as tk
from tkinter import filedialog
import time
import threading
import socket
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
import select
import struct
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from wifi_collector import DataCollector
from wifi_collector import AxisPlot
from debug_log import log
import sys
from wifi_command import RegCommand

class GSensorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("G Sensor Data Collector")

        # 預設參數
        self.ip_address = tk.StringVar(value='192.168.0.110')
        self.tcp_port = tk.StringVar(value=4061)
        self.sample_freq_dict = {"1kHz": 1000.0, "2kHz": 2000.0, "4kHz": 4000.0}
        self.data_mode = tk.StringVar(value=AxisPlot.PlotMethod.RAW_DATA.value)
        self.sample_rate = tk.StringVar(value="2kHz")
        self.display_time = tk.StringVar(value="20")
        self.file_path = tk.StringVar(value="imu_data.csv")
        self.reg_addr = tk.StringVar(value=0)
        self.reg_val = tk.StringVar(value=0)

        self.collector = None 

        # 建立 GUI 控制區
        self.build_controls()

    def build_controls(self):
        tk.Label(self.root, text="IP:").grid(row=0, column=0, padx=(5,0), pady=5, sticky="e")
        tk.Entry(self.root, textvariable=self.ip_address, width=17).grid(row=0, column=1, padx=(5,0))
        
        tk.Label(self.root, text="Port:").grid(row=0, column=2, padx=(5,0), pady=5, sticky="e")
        tk.Entry(self.root, textvariable=self.tcp_port, width=7).grid(row=0, column=3, padx=(5,0), sticky="w")
      
        # 下拉選單：資料模式
        tk.Label(self.root, text="資料模式:").grid(row=1, column=0, padx=(5,0), pady=5, sticky="e")
        tk.OptionMenu(self.root, self.data_mode, AxisPlot.PlotMethod.RAW_DATA.value, AxisPlot.PlotMethod.ALL_ACCEL.value).grid(row=1, column=1, padx=(5,0), sticky="w")

        # 下拉選單：取樣率
        tk.Label(self.root, text="取樣率:").grid(row=1, column=2, padx=(5,0), pady=5, sticky="e")
        tk.OptionMenu(self.root, self.sample_rate, *self.sample_freq_dict.keys()).grid(row=1, column=3, padx=(5,0), sticky="w")

        # 輸入框：顯示秒數
        tk.Label(self.root, text="顯示秒數:").grid(row=1, column=4, padx=(5,0), pady=5, sticky="e")
        tk.Entry(self.root, textvariable=self.display_time, width=5).grid(row=1, column=5, padx=(5,0), sticky="w")

        # 檔案選擇與顯示 label
        tk.Label(self.root, text="儲存檔案位置:").grid(row=2, column=0, padx=(5,0), pady=5, sticky="e")
        tk.Entry(self.root, textvariable=self.file_path, width=50).grid(row=2, column=1, columnspan=3, sticky="w", padx=(5,0), pady=5)
        tk.Button(self.root, text="選擇檔案...", command=self.select_save_file).grid(row=2, column=4, columnspan=2)

        # 啟動 / 停止按鈕
        # tk.Button(self.root, text="Connect G-Sensor", bg="yellow", command=self.connect).grid(row=3, column=1, padx=5, pady=10)
        tk.Button(self.root, text="Start G-Sensor", bg="green", command=self.start_collection).grid(row=3, column=2, padx=5, pady=10)
        tk.Button(self.root, text="Stop G-Sensor", bg="red", command=self.stop_collection).grid(row=3, column=3, padx=5, pady=10)

        tk.Label(self.root, text="Register Address(hex) - 2 bytes:").grid(row=4, column=0, padx=(5,0), pady=5, sticky="e")
        tk.Entry(self.root, textvariable=self.reg_addr, width=5).grid(row=4, column=1, padx=(5,0), sticky="w")
        
        tk.Label(self.root, text="Data(hex) - 4 bytes:").grid(row=4, column=2, padx=(5,0), pady=5, sticky="e")
        tk.Entry(self.root, textvariable=self.reg_val, width=10).grid(row=4, column=3, padx=(5,0), sticky="w")
        
        tk.Button(self.root, text="Write Reg", command=self.write_reg).grid(row=4, column=4, columnspan=2)
        tk.Button(self.root, text="Read Reg", command=self.read_reg).grid(row=4, column=6, columnspan=2)
        
    def write_reg(self):
        rc = RegCommand(self.ip_address.get(), int(self.tcp_port.get()))
        rc.write_register(int(self.reg_addr.get()), int(self.reg_val.get()))
        
    def read_reg(self):
        rc = RegCommand(self.ip_address.get(), int(self.tcp_port.get()))
        data = rc.read_register(int(self.reg_addr.get()))
        if data != None:
            self.reg_val.set(tk.StringVar(data['Fuction']))
            
    # def connect(self):
        
        
    def select_save_file(self):
        filename = filedialog.asksaveasfilename(
            title="選擇儲存檔案",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="imu_data.csv",
        )
        
        if filename:
            self.file_path.set(filename)

    def start_collection(self):
        # 設定參數
        mode = self.data_mode.get()
        freq = self.sample_freq_dict[self.sample_rate.get()]
        seconds = float(self.display_time.get())
        path = self.file_path.get()
        self.is_collecting = True

        log(f"啟動模式: {mode}, 頻率: {freq}, 顯示時間: {seconds}s, 檔案: {path}")

        if self.collector == None:
            # 啟動資料收集器
            self.collector = DataCollector(
                data_mode=mode,
                freq=freq,
                frame_width=seconds,
                file_path=path
            )
            
            self.collector.start_wifi_data_collection(self.ip_address.get(), int(self.tcp_port.get()))

        self.collector.plot_dynamic_graph()

    def stop_collection(self):
        if self.collector:
            self.collector.stop_wifi_data_collection()
            self.collector = None
    
    def on_closing(self):
        log('關閉視窗，退出程式')
        self.root.destroy()    # 先關掉 Tkinter 視窗
        sys.exit(0)       # 然後退出整個 Python 程式
        
if __name__ == "__main__":
    root = tk.Tk()
    app = GSensorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()