from PyQt5 import QtCore, QtWidgets, uic
from plot_raw_ui import Ui_formGraphics
import pyqtgraph as pg
from debug_log import log

class FormGraphicsPlotRaw(QtWidgets.QMainWindow):
    def __init__(self, frame_width, frame_count, lock):
        super().__init__() # in python3, super(Class, self).xxx = super().xxx
        self.ui = Ui_formGraphics()
        self.ui.setupUi(self)
        
        self.plot = self.ui.graphWidget.addPlot()
        self.plot.showGrid(x=True, y=True)
        self.plot.addLegend()

        self.frame_width = frame_width
        self.frame_count = frame_count
        self.lock = lock
        
        self.curve_x = self.plot.plot(pen='r', name='Acc X')
        self.curve_y = self.plot.plot(pen='g', name='Acc Y')
        self.curve_z = self.plot.plot(pen='b', name='Acc Z')
       
        self.time = []
        self.acc_x = []
        self.acc_y = []
        self.acc_z = []
        
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(int(1000 / 30))
        
    def append_plot(self, time, acc_x, acc_y, acc_z):
        with self.lock:
            if len(self.time) > self.frame_count:
                self.time.pop(0)
                self.acc_x.pop(0)
                self.acc_y.pop(0)
                self.acc_z.pop(0)
                
            self.time.append(time)
            self.acc_x.append(acc_x)
            self.acc_y.append(acc_y)
            self.acc_z.append(acc_z)
            
            # log(f'time len = {len(self.time)}')
            
    def update_plot(self):
        with self.lock:
            try:
                self.curve_x.setData(self.time, self.acc_x)
                self.curve_y.setData(self.time, self.acc_y)
                self.curve_z.setData(self.time, self.acc_z)
                if len(self.time) > self.frame_count:
                    self.plot.setXRange(max(self.time[-1] - self.frame_width, 0), self.time[-1])
            except Exception as e:
                log(f'{e}')

         