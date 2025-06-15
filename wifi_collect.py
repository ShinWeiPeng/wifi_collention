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

SAMPLE_FREQUENCY = 2000.0
SAMPLE_PERIOD = 1.0 / SAMPLE_FREQUENCY
FRAME_WIDTH_S = 20.0

HOST = '192.168.0.110'
PORT = 4061

class DataCollector:
    def __init__(self):
        # 儲存資料的初始化
        self.data_queue = []
        self.is_collecting = False
        self.sock = None

        # 動態圖表初始化
        self.fig, self.ax = plt.subplots()
        self.time, self.xdata, self.ydata, self.zdata = [], [], [], []
        self.line_x, = self.ax.plot([], [], label="Accel X")
        self.line_y, = self.ax.plot([], [], label="Accel Y")
        self.line_z, = self.ax.plot([], [], label="Accel Z")
        self.ax.set_xlim(0, FRAME_WIDTH_S)
        self.ax.set_ylim(-1.5, 1.5)
        self.ax.set_xlabel('Time (s))')
        self.ax.set_ylabel('Acceleration (g)')
        self.ax.legend()
        
        self.save_cnt = 0
        self.plt_data_lock = threading.Lock()

        # 讓 Tkinter 不顯示主視窗
        self.root = tk.Tk()
        self.root.withdraw()

        # 創建啟動和停止按鈕
        ax_start = plt.axes([0.2, 0.01, 0.15, 0.075])  # 按鈕的位置
        self.start_button = Button(ax_start, 'Start')
        self.start_button.on_clicked(self.start_button_callback)

        ax_stop = plt.axes([0.01, 0.01, 0.15, 0.075])  # 按鈕的位置
        self.stop_button = Button(ax_stop, 'Stop')
        self.stop_button.on_clicked(self.stop_button_callback)
        
    def update_ylim(self):
        """根據加速度資料動態調整 y 軸範圍"""
        # 計算加速度資料的範圍
        if len(self.time) > 0:
            y_min = min(min(self.xdata), min(self.ydata), min(self.zdata)) - 1
            y_max = max(max(self.xdata), max(self.ydata), max(self.zdata)) + 1
            
            # 動態設定 y 軸範圍
            self.ax.set_ylim(y_min, y_max)
            
            num_ticks = 5
            ticks = np.linspace(y_min, y_max, num_ticks) 
            self.ax.set_yticks(ticks)  
            self.ax.set_yticklabels([f"{tick:.1f}" for tick in ticks]) 
            # self.fig.canvas.draw()
        
    def update_xlim(self):
        if len(self.time) > (FRAME_WIDTH_S / SAMPLE_PERIOD):
            self.time.pop(0)
            self.xdata.pop(0)
            self.ydata.pop(0)
            self.zdata.pop(0)

            time_max = self.time[-1]
            time_min = time_max - FRAME_WIDTH_S
            self.ax.set_xlim(time_max - FRAME_WIDTH_S, time_max)
            
            # 動態設定 X 軸的刻度和標籤
            num_ticks = 10  # 你可以根據需要改變刻度數量
            ticks = np.linspace(time_min, time_max, num_ticks)  # 等間距生成刻度
            self.ax.set_xticks(ticks)  # 設定 X 軸刻度
            self.ax.set_xticklabels([f"{tick:.1f}" for tick in ticks])  # 設定 X 軸刻度的顯示格式
            # self.fig.canvas.draw()
        
    # TCP 資料發送函數
    def send_tcp_data(self, data):
        # 發送資料
        self.sock.send(data)
        print(f"Sent: {data.hex()}")

    # 回調函數：啟動按鈕的事件
    def start_button_callback(self, event):
        # 傳送啟動資料
        start_data = bytes([0x02, 0x53, 0x54, 0x03])
        self.send_tcp_data(start_data)

    # 回調函數：停止按鈕的事件
    def stop_button_callback(self, event):
        # 傳送停止資料
        stop_data = bytes([0x02, 0x45, 0x44, 0x03])
        self.send_tcp_data(stop_data)
        
    def select_save_path(self):
        file_name = "imu_data.csv"
        """讓使用者選擇資料夾並設定儲存 CSV 路徑"""
        self.file_path = filedialog.asksaveasfilename(
        title="選擇儲存檔案",
        defaultextension=".csv",  # 預設檔案副檔名為 .csv
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],  # 檔案類型選項
        initialfile=file_name  # 預設檔名
        )

        if not self.file_path:
            print("未選擇資料夾，程式結束")
            exit()
        
        return self.file_path

    def save_to_csv(self):
        """將資料儲存為 CSV"""
        try:
            # 如果檔案不存在，則創建檔案並寫入標頭
            file_exists = os.path.exists(self.file_path)
            
            # 使用追加模式（'a'）打開文件，避免每次都重寫檔案
            with open(self.file_path, mode='a', newline='') as file:
                writer = csv.writer(file)
                
                if not file_exists:
                    writer.writerow(['Time', 'Accel_X', 'Accel_Y', 'Accel_Z'])
                    
                for data in self.data_queue:
                    writer.writerow(data)
                
                self.save_cnt += len(self.data_queue)
                # print(f'save_to_csv len = {self.save_cnt}')
                self.data_queue.clear()
                
            # print(f"Data saved to: {self.file_path}")
        
        except Exception as e:
            print(f"Error in data collection: {e}")
            
    def start_wifi_data_collection(self, host, port):
        """初始化 Wi-Fi 收集資料，並啟動多線程來收集資料"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.setblocking(False)
        self.is_collecting = True
        threading.Thread(target=self.collect_data_from_wifi, daemon=True).start()
        print(f"connect successed")

    def get_record_data(self):
        i = 0  
        fail_address = 0
        pass_records = []
        failure_records = []

        while i < len(self.data):
            try:
                start_code = self.data[i + 0]
                while start_code != 0x02:
                    if fail_address == 0:
                        fail_address = i 
                    i += 1
                    start_code = self.data[i + 0]
                
                if fail_address != 0:
                    failure_records.append(self.data[fail_address:i])
                    fail_address = 0
                    print(f'start format fail, data:{self.data[fail_address:i]}, len:{len(self.data[fail_address:i])}')
                
                offset = self.data[i + 1] + 1
            
                if (i + offset + 1) > len(self.data) :
                    record = self.data[i:len(self.data)]
                    self.data = b"" 
                    self.data = record
                    break           
                else:           
                    if self.data[i + offset] == 0x0a:
                        end_code_offset = 1 + offset
                    else:
                        end_code_offset = offset

                    end_code = self.data[i + end_code_offset]
                    
                    if start_code == 0x02 and end_code == 0x03:                       
                        record = self.data[i:i + end_code_offset + 1]
                        pass_records.append(record)
                        i += (len(record))
                    else:
                        print(f'format fail, data:{self.data[i:end_code_offset + i]}, len:{len(self.data[i:end_code_offset + i])}')
                        i += 1
                        
            except Exception as e:
                print(f'Exception connect data')
                record = self.data[i:len(self.data)]
                self.data = b"" 
                self.data = record
                print(f'Exception, data = {record}')
                print(f"Error in data collection: {e}")
                break

        return {"PassRecord": pass_records, "FailureRecord": failure_records}
                
    def collect_data_from_wifi(self):
        """從 Wi-Fi 接收三軸加速度資料並更新到數據隊列"""
        timestamp = 0
        self.data = b""  # 清空緩衝區
        
        while self.is_collecting:
            try:
                # 使用 select 來監控 socket 是否有數據可以讀取
                ready_to_read, _, _ = select.select([self.sock], [], [], 0.1)

                if ready_to_read:
                    self.data += self.sock.recv(4096)

                    records = self.get_record_data()

                    for record in records["PassRecord"]:  
                        if len(record) == 0:
                            continue

                        length = record[1]
                        function_code = record[2:4]

                        if function_code == b'DA':
                            fmt = 'h h h h h h H B'  # 這個格式對應於：AccX, AccY, AccZ, GyroX, GyroY, GyroZ, Count, End
                            if len(record[4:length + 4]) != 15:
                                print(f'Length Failure, lenhth = {len(record)}, data = {record}')
                                continue

                            unpacked_data = struct.unpack(fmt, record[4:length + 4])
                            accel_x = unpacked_data[0]
                            accel_y = unpacked_data[1]
                            accel_z = unpacked_data[2]
                            timestamp += SAMPLE_PERIOD
                            self.data_queue.append([timestamp, accel_x, accel_y, accel_z])

                            # 更新動態圖表數據
                            with self.plt_data_lock:
                                self.time.append(timestamp)
                                self.xdata.append(accel_x)
                                self.ydata.append(accel_y)
                                self.zdata.append(accel_z)
                            
                        elif function_code == b'EV':
                            string = record[4:length + 4]
                            print(f'{string}')  
                            
                    self.save_to_csv()   

            except Exception as e:
                print(f'Exception, data = {record}')
                print(f"Error in data collection: {e}")
                break

    def stop_wifi_data_collection(self):
        """停止資料收集"""
        self.is_collecting = False
        self.sock.close()

    def update_plot(self, frame):
        """更新圖表"""
        with self.plt_data_lock:     
            # 更新圖表數據        
            self.line_x.set_data(self.time, self.xdata)
            self.line_y.set_data(self.time, self.ydata)
            self.line_z.set_data(self.time, self.zdata)  

            self.update_xlim()
            self.update_ylim()
        self.fig.canvas.draw()
        return self.line_x, self.line_y, self.line_z

    def plot_dynamic_graph(self):
        """繪製動態圖表"""
        ani = FuncAnimation(self.fig, self.update_plot, frames=100, interval=100, blit=True)
        plt.tight_layout()
        plt.show()

# 主程式
if __name__ == "__main__":
    # 創建資料收集器
    collector = DataCollector()

    # 讓使用者選擇儲存路徑
    collector.select_save_path()

    # 開啟 Wi-Fi 資料收集 (替換為實際的IP與端口)
    collector.start_wifi_data_collection(HOST, PORT)
    
    collector.plot_dynamic_graph() 

    try:
        while True:
            time.sleep(10)
            print(f'save_to_csv')
            # collector.save_to_csv()
                
    except KeyboardInterrupt:
        print("Data collection stopped.")
        collector.stop_wifi_data_collection()
