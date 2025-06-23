from PyQt5 import QtWidgets
from main_ui import Ui_MainWindow
import sys
from private_formate import GesnsorInstruction
from wifi_function import WifiFunction
from collector import DataCollector
from PyQt5.QtWidgets import QFileDialog
from plot_raw import FormGraphicsPlotRaw
from plot_aa import FormGraphicsPlotAa
import threading
import time

class MainWindow(QtWidgets.QMainWindow):
 
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.ui.btnStart.clicked.connect(self.btnStart_clicked)
        self.ui.btnStop.clicked.connect(self.btnStop_clicked)
        self.ui.lblConnectState.setStyleSheet('color: red')
        self.ui.btnSaveForder.clicked.connect(self.btnbtnSaveForder_clicked)
        
        self.ui.txtAddress.textChanged.connect(self.txtAddress_textChanged)
        self.ui.txtPort.textChanged.connect(self.txtPort_textChanged)
        self.ui.txtFrameWidth.textChanged.connect(self.txtFrameWidth_textChanged)
        self.ui.cbbMode.currentIndexChanged.connect(self.cbbMode_currentIndexChanged)
        self.ui.txtEnvelopeInterval.textChanged.connect(self.txtEnvelopeInterval_textChanged)
        self.ui.cbbDataSrc.currentIndexChanged.connect(self.cbbDataSrc_currentIndexChanged)
        self.ui.btnConnect.clicked.connect(self.btnConnect_clicked)
        self.ui.btnShow.clicked.connect(self.btnShow_clicked)
        
        self.host = self.ui.txtIP.text()
        self.port = int(self.ui.txtPort.text())
        self.frame_width = int(self.ui.txtFrameWidth.text())
        self.mode = self.ui.cbbMode.currentText()
        self.envelope_interval = int(self.ui.txtEnvelopeInterval.text())
        self.data_src = self.ui.cbbDataSrc.currentIndex()
        self.freq = 2000.0
        self.sample_period = 1.0 / self.freq
        timestr = time.strftime('%Y%m%d_%H%M%S')
        self.file_path = f'./save_data/{timestr}.csv'
        self.ui.lblSavePath.setText(self.file_path)
        self.is_connect = False
        
        self.lock = threading.Lock()
        
        self.wifi = WifiFunction(self.host, self.port)
        self.instruction = GesnsorInstruction(self.wifi)
    
    def btnShow_clicked(self):
        if self.mode == DataCollector.PlotMethod.RAW_DATA.value:
            self.plot_raw.show()
        else:
            self.plot_aa.show()
        
    def btnConnect_clicked(self):
        self.wifi.connect()
        if self.wifi.sock:
            self.ui.lblConnectState.setStyleSheet('color: green')
            self.is_connect = True
            version_code = self.instruction.read_register(GesnsorInstruction.GsenAddress.EGA_VERSION.value)
            main_ver = (version_code >> 16) & 0xFFFF
            sub_ver  = (version_code >> 8) & 0xFF
            test_ver = version_code & 0xFF
            version = main_ver + sub_ver / 1000.0 + test_ver / 1000000.0
            self.ui.lblVersion.setText('Version: ' + str(version))     
        
    def btnStart_clicked(self):
        if self.wifi.sock == None:
            return 
        
        if self.mode == DataCollector.PlotMethod.RAW_DATA.value:
            self.plot_raw = FormGraphicsPlotRaw(self.frame_width, self.frame_width / self.sample_period, self.lock)
            self.plot_raw.show()
            self.collector = DataCollector(self.mode, self.instruction, self.plot_raw, self.freq,
                                self.frame_width, self.file_path)
        else:
            self.plot_aa = FormGraphicsPlotAa(self.frame_width, int(self.frame_width / self.sample_period), self.lock)
            self.plot_aa.show()
            self.collector = DataCollector(self.mode, self.instruction, self.plot_aa, self.freq,
                                self.frame_width, self.file_path)
            
        self.collector.is_collecting = True
        self.collector_thread = threading.Thread(target=self.collector.collect_data)
        self.collector_thread.start()
        self.instruction.start()
        
    def btnStop_clicked(self):
        self.instruction.stop()
        
        while(self.collector.queue_hanle.empty() == False):
            continue
        
        self.collector.is_collecting = False
        self.collector_thread.join()
        
    def btnbtnSaveForder_clicked(self):
        timestr = time.strftime('%Y%m%d_%H%M%S')
        self.file_path, _ = QFileDialog.getSaveFileName(self, 
            "Save File", 
            f"./save_data/{timestr}.csv",          # 預設檔案名
            "CSV Files (*.csv);;All Files (*)")   # 檔案過濾器
        self.ui.lblSavePath.setText(self.file_path)
        
    def txtAddress_textChanged(self):
        self.host = self.ui.txtAddress.text()
        
    def txtPort_textChanged(self):
        self.port = int(self.ui.txtPort.text())
        
    def txtFrameWidth_textChanged(self):
        self.frame_width = int(self.ui.txtFrameWidth.text())
        
    def cbbMode_currentIndexChanged(self):
        self.mode = self.ui.cbbMode.currentText()
        
        if self.is_connect:
            if self.mode == DataCollector.PlotMethod.RAW_DATA.value:
                self.instruction.write_register(GesnsorInstruction.GsenAddress.EGA_RUN_MODE.value, 0x00)
            else:
                self.instruction.write_register(GesnsorInstruction.GsenAddress.EGA_RUN_MODE.value, 0x01)
    
    def txtEnvelopeInterval_textChanged(self):
        self.envelope_interval = int(self.ui.txtEnvelopeInterval.text())
        
        # if self.is_connect:
        #     self.instruction.write_register(GesnsorInstruction.GsenAddress.EGA_ENVELOPE_INTERVAL, self.envelope_interval)
    
    def cbbDataSrc_currentIndexChanged(self):
        self.data_src = self.ui.cbbDataSrc.currentIndex()
        
        if self.is_connect:
            self.instruction.write_register(GesnsorInstruction.GsenAddress.EGA_DATA_SRC, self.data_src)
            
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main_ui = MainWindow()
    main_ui.show()
    
    sys.exit(app.exec())