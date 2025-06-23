from PyQt5 import QtCore, QtWidgets, uic
from plot_aa_ui import Ui_formAaGraphics
import pyqtgraph as pg
from collections import deque
from debug_log import log

class FormGraphicsPlotAa(QtWidgets.QMainWindow):
    def __init__(self, frame_width, frame_count, lock):
        super().__init__() # in python3, super(Class, self).xxx = super().xxx
        self.ui = Ui_formAaGraphics()
        self.ui.setupUi(self)
        
        self.frame_width = frame_width
        self.frame_count = frame_count
        self.lock = lock
        
        self.plot_x = self.ui.widgetAaX.addPlot(title="Accel X")
        self.plot_x.showGrid(x=True, y=True)
        self.plot_x.addLegend()
        
        self.curve_x_scale = self.plot_x.plot(pen='r', name='Scale')
        self.curve_x_ac = self.plot_x.plot(pen='g', name='AC Coulper')
        self.curve_x_evlh = self.plot_x.plot(pen='b', name='Envelope Upper')
        self.curve_x_evll = self.plot_x.plot(pen='y', name='Envelope Lower')
        
        self.plot_y = self.ui.widgetAaY.addPlot(title="Accel Y")
        self.plot_y.showGrid(x=True, y=True)
        self.plot_y.addLegend()
        
        self.curve_y_scale = self.plot_y.plot(pen='r', name='Scale')
        self.curve_y_ac = self.plot_y.plot(pen='g', name='AC Coulper')
        self.curve_y_evlh = self.plot_y.plot(pen='b', name='Envelope Upper')
        self.curve_y_evll = self.plot_y.plot(pen='y', name='Envelope Lower')
        
        self.plot_z = self.ui.widgetAaZ.addPlot(title="Accel Z")
        self.plot_z.showGrid(x=True, y=True)
        self.plot_z.addLegend()
        
        self.curve_z_scale = self.plot_z.plot(pen='r', name='Scale')
        self.curve_z_ac = self.plot_z.plot(pen='g', name='AC Coulper')
        self.curve_z_evlh = self.plot_z.plot(pen='b', name='Envelope Upper')
        self.curve_z_evll = self.plot_z.plot(pen='y', name='Envelope Lower')
        
        self.time = deque(maxlen=self.frame_count)
        self.scale_x = deque(maxlen=self.frame_count)
        self.scale_y = deque(maxlen=self.frame_count)
        self.scale_z = deque(maxlen=self.frame_count)
        
        self.ac_x = deque(maxlen=self.frame_count)
        self.ac_y = deque(maxlen=self.frame_count)
        self.ac_z = deque(maxlen=self.frame_count)
        
        self.evlh_x = deque(maxlen=self.frame_count)
        self.evlh_y = deque(maxlen=self.frame_count)
        self.evlh_z = deque(maxlen=self.frame_count)
        
        self.evll_x = deque(maxlen=self.frame_count)
        self.evll_y = deque(maxlen=self.frame_count)
        self.evll_z = deque(maxlen=self.frame_count)
        
        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(int(1000 / 30))
        
    def append_plot(self, time, scale_x, scale_y, scale_z,
                    ac_x, ac_y, ac_z,
                    evlh_x, evlh_y, evlh_z,
                    evll_x, evll_y, evll_z):
        with self.lock:
            self.time.append(time)
            self.scale_x.append(scale_x)
            self.scale_y.append(scale_y)
            self.scale_z.append(scale_z)
            
            self.ac_x.append(ac_x)
            self.ac_y.append(ac_y)
            self.ac_z.append(ac_z)
            
            self.evlh_x.append(evlh_x)
            self.evlh_y.append(evlh_y)
            self.evlh_z.append(evlh_z)
            
            self.evll_x.append(evll_x)
            self.evll_y.append(evll_y)
            self.evll_z.append(evll_z)
            
    def update_plot(self):
        with self.lock:
            try:
                self.curve_x_scale.setData(list(self.time), list(self.scale_x))
                self.curve_x_ac.setData(list(self.time), list(self.ac_x))
                self.curve_x_evlh.setData(list(self.time), list(self.evlh_x))
                self.curve_x_evll.setData(list(self.time), list(self.evll_x))
                
                self.curve_y_scale.setData(list(self.time), list(self.scale_y))
                self.curve_y_ac.setData(list(self.time), list(self.ac_y))
                self.curve_y_evlh.setData(list(self.time), list(self.evlh_y))
                self.curve_y_evll.setData(list(self.time), list(self.evll_y))
                
                self.curve_z_scale.setData(list(self.time), list(self.scale_z))
                self.curve_z_ac.setData(list(self.time), list(self.ac_z))
                self.curve_z_evlh.setData(list(self.time), list(self.evlh_z))
                self.curve_z_evll.setData(list(self.time), list(self.evll_z))
                
                if len(self.time) >= self.frame_count:
                    self.plot_x.setXRange(max(self.time[-1] - self.frame_width, 0), self.time[-1])
                    self.plot_y.setXRange(max(self.time[-1] - self.frame_width, 0), self.time[-1])
                    self.plot_z.setXRange(max(self.time[-1] - self.frame_width, 0), self.time[-1])
            except Exception as e:
                log(f'{e}')
      