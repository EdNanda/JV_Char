__author__ = "Edgar Nandayapa"
__version__ = "1.08-2022"

import sys
import matplotlib
matplotlib.use('Qt5Agg')

from PyQt5 import QtWidgets, QtGui, QtTest
from PyQt5.QtWidgets import QWidget,QLineEdit,QFormLayout,QHBoxLayout,QSpacerItem,QGridLayout
from PyQt5.QtWidgets import QFrame,QPushButton,QCheckBox,QLabel,QToolButton,QTextEdit,QScrollBar
from PyQt5.QtWidgets import QSizePolicy,QMessageBox, QGroupBox
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QRunnable, pyqtSlot, QThreadPool
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QTableView, QApplication
from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex


from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})

# from IPython import get_ipython

from pymeasure.instruments.keithley import Keithley2450
import pyvisa as visa
import pandas as pd
import numpy as np
import os
import serial
import math
import random 
from time import time, sleep, strftime, localtime
from datetime import datetime
import traceback
from decimal import Decimal

# global size
# size = 2046


## These two classes make parallel measurement of PL spectra possible
# class WorkerSignals(QObject):
#     finished = pyqtSignal()
#     error = pyqtSignal(tuple)
#     result = pyqtSignal(object)
#     progress = pyqtSignal(object)
    
# class Worker(QRunnable):
    
#     def __init__(self, fn, *args, **kwargs):
#         super(Worker, self).__init__()

#         # Store constructor arguments (re-used for processing)
#         self.fn = fn
#         self.args = args
#         self.kwargs = kwargs
#         self.signals = WorkerSignals()
        
#         self.kwargs['progress_callback'] = self.signals.progress

#     @pyqtSlot()
#     def run(self):
    
#         try:
#             result = self.fn(*self.args, **self.kwargs)
#         except:
#             traceback.print_exc()
#             exctype, value = sys.exc_info()[:2]
#             self.signals.error.emit((exctype, value, traceback.format_exc()))
#         else:
#             self.signals.result.emit(result)  # Return the result of the processing
#         finally:
#             self.signals.finished.emit()  # Done
            
## Worker class to do reference current measurement
class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(float)

    def run(self):
        # """Long-running task."""
        # for i in range(5):
        #     sleep(1)
        #     self.progress.emit(i + 1)
        # self.finished.emit()
        # ref = float(self.sun_ref.text())
        
        while True:
            sleep(0.1)
            self.keithley.source_voltage = 0
            current = self.keithley.current*1000
            self.progress.emit(current)
        self.finished.emit()
        #     self.keithley.enable_source()
        
        #     self.keithley.source_voltage = 0
        #     current = self.keithley.current
        #     sunP = current/ref
            
        #     self.refCurrent.setText("Ref. current (Sun %)\n"+str(round(current,2))+
        #                             " ("+str(round(sunP,2))+")")
        
        # self.finished.emit()
        # self.keithley.disable_source()
        
class TableModel(QAbstractTableModel):

    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value)

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]

    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])

            if orientation == Qt.Vertical:
                return str(self._data.index[section])        
        
## This makes the plot happen
class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=300,tight_layout=True):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        self.axes.set_xlabel('Voltage (V)')
        self.axes.set_ylabel('Current density (mA/cm²)')
        self.axes.grid(True,linestyle='--')
        self.axes.set_xlim([-0.5,2])
        # self.axes.set_xlim([400,850])
        self.axes.set_ylim([-25,5])
        self.axes.axhline(0, color='black')
        self.axes.axvline(0, color='black')
        fig.tight_layout()
        super(MplCanvas, self).__init__(fig)



class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        ## Initialize parameters

        self.setWindowTitle("JV Characteristics")
        folder = os.path.abspath(os.getcwd())+"\\"
        self.setWindowIcon(QtGui.QIcon(folder+"solar.ico"))
        np.seterr(divide='ignore', invalid='ignore')
        
        self.statusBar().showMessage("Program by Edgar Nandayapa - 2022",10000)

        try:
            ## Modify this in case multiple keithleys
            rm = visa.ResourceManager() ##Load piVisa
            device = rm.list_resources()[0] ## Get the first keithley on the list
            self.keithley = Keithley2450(device)
            self.keithley.wires = 4
        except:
            device = None
            self.keithley = None
            self.statusBar().showMessage("####    Keithley not found    ####")
           
        
        try:
            # susi = serial.Serial()  # open serial port
            self.susi = serial.Serial("COM3")
            self.susi.baudrate = 9600
            self.susi.bytesize = 8
            self.susi.parity = 'N'
            self.susi.stopbits = 1
            self.susi.timeout = 5
            self.susi_bool = True
            
        except:
            ##TODO pop-up window saying there is no susi
            self.susi_bool = False
            
            if not self.keithley:
                self.statusBar().showMessage("####    Keithley and SuSi not found    ####")
            else:
                self.statusBar().showMessage("####    SuSi not found    ####")
            

        self.threadpool = QThreadPool()
               
        self.create_widgets()
        
        self.button_actions() ##Set button actions
        

    def create_widgets(self):
        widget = QWidget()
        layH1 = QHBoxLayout() ##Main (horizontal) Layout
        
        ## Create the maptlotlib FigureCanvas for plotting
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.canvas.setMinimumWidth(600)##Fix width so it doesn't change
        self.canvas.setMinimumHeight(450)
        self.setCentralWidget(self.canvas)
        self._plot_ref = None
        ## Add a toolbar to control plotting area
        toolbar = NavigationToolbar(self.canvas, self)
        
        ##JV characteristics fields
        # Ljvvars = QGridLayout()
        # Ljvvars.addWidget(QLabel(" "),0,0)
        # Ljvvars.addWidget(QLabel("Voc\n V"),0,1,Qt.AlignCenter)
        # Ljvvars.addWidget(QLabel(" Jsc\n mA/cm²"),0,2,Qt.AlignCenter)
        # Ljvvars.addWidget(QLabel("FF\n %"),0,3,Qt.AlignCenter)
        # Ljvvars.addWidget(QLabel("PCE\n %"),0,4,Qt.AlignCenter)
        # Ljvvars.addWidget(QLabel("V_mpp\n       V"),0,5,Qt.AlignCenter)
        # Ljvvars.addWidget(QLabel("J_mpp\n  mA/cm²"),0,6,Qt.AlignCenter)
        # Ljvvars.addWidget(QLabel("P_mpp\n    mW/cm²"),0,7,Qt.AlignCenter)
        # Ljvvars.addWidget(QLabel("R_series\n  \U00002126cm²"),0,8,Qt.AlignCenter)
        # Ljvvars.addWidget(QLabel("R_shunt\n  \U00002126cm²"),0,9,Qt.AlignCenter)
        # Ljvvars.addWidget(QLabel("Forward "),1,0,Qt.AlignCenter)
        # Ljvvars.addWidget(QLabel("Backward"),2,0,Qt.AlignCenter)
        
        # self.jvvals =[]
        # for j in range(1,3):
        #     for i in range(1,10):
        #         lab = QLabel("0.00")
        #         Ljvvars.addWidget(lab,j,i,Qt.AlignCenter)
        #         self.jvvals.append(lab)
        self.Ljvvars = QTableView()
        self.Ljvvars.resize(600, 10)
        # self.jvvals.horizontalHeader().setStretchLastSection(True)
        self.Ljvvars.setAlternatingRowColors(True)
        self.Ljvvars.setSelectionBehavior(QTableView.SelectRows)
        # self.Ljvvars.setColumnWidth(10)
        
        jvstart = pd.DataFrame(columns = ["Voc\n(V)","Jsc\n(mA/cm²)","FF\n(%)","PCE\n(%)","V_mpp\n(V)","J_mpp\n(mA/cm²)","P_mpp\n(mW/cm²)","R_series\n\U00002126cm²","R_shunt\n\U00002126cm²"])
        
        self.model = TableModel(jvstart)
        self.Ljvvars.setModel(self.model)
                
        # print(len(self.jvvals))         
        #[isc, voc, ff, pce, mpp_p, mpp_c, mpp_v, r_ser, r_par
        # Lsetup.addWidget(self.BBrightDel,1,2)
        
        ### Place all widgets 
        ## First in a grid
        # LBgrid = QGridLayout()
        # LBgrid.addWidget(QLabel(" "),0,0)
        # LBgrid.addWidget(self.Braw,0,1)
        # LBgrid.addWidget(self.Brange,0,2)
        # LBgrid.addWidget(self.BSavePlot,0,3)
        # LBgrid.addWidget(QLabel(" "),0,4)
        ## Add to (first) vertical layout
        layV1 = QtWidgets.QVBoxLayout() 
        ## Add Widgets to the layout
        layV1.addWidget(toolbar)
        layV1.addWidget(self.canvas)
        layV1.addWidget(self.Ljvvars)
        
        ## Add first vertical layout to the main horizontal one
        layH1.addLayout(layV1,5)
        
        ##TODO show current value somewhere
        
        ### Make second vertical layout for measurement settings
        layV2 = QtWidgets.QVBoxLayout()
        verticalSpacerV2 = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding) ## To center the layout
        
        ## Relevant fields for sample, user and folder names
        self.LEsample = QLineEdit()
        self.LEuser = QLineEdit()
        self.LEfolder = QLineEdit()
        
        ## Make a grid layout and add labels and fields to it
        LGsetup = QGridLayout()
        LGsetup.addWidget(QLabel("Sample:"),0,0)
        LGsetup.addWidget(self.LEsample,0,1)
        LGsetup.addWidget(QLabel("User:"),1,0)
        LGsetup.addWidget(self.LEuser,1,1)
        self.Bpath = QToolButton()
        self.Bpath.setToolTip("Create a folder containing today's date")
        LGsetup.addWidget(self.Bpath,1,2)
        LGsetup.addWidget(QLabel("Folder:"),2,0)
        LGsetup.addWidget(self.LEfolder,2,1)
        self.Bfolder = QToolButton()
        self.Bfolder.setToolTip("Choose a folder where to save the data")
        LGsetup.addWidget(self.Bfolder,2,2)
        
        ## Set defaults
        self.Bpath.setText("\U0001F4C6")
        self.Bfolder.setText("\U0001F4C1")
        self.LEfolder.setText("C:/Data/")
        
        ## Second set of setup values
        LTsetup = QGridLayout()
        self.volt_start = QLineEdit()
        self.volt_end = QLineEdit()
        self.volt_step = QLineEdit()
        self.ave_pts = QLineEdit()
        self.int_time = QLineEdit()
        self.set_time = QLineEdit()
        self.curr_lim = QLineEdit()
        self.sam_area = QLineEdit()
        self.pow_dens = QLineEdit()
        self.cell_num = QLineEdit()
        self.sun_ref = QLineEdit()
        self.curr_ref = QLabel("0\n0%")
        
        ## Set maximum width of widgets
        sMW = 60
        self.volt_start.setMaximumWidth(sMW)
        self.volt_end.setMaximumWidth(sMW)
        self.volt_step.setMaximumWidth(sMW)
        self.ave_pts.setMaximumWidth(sMW)
        self.int_time.setMaximumWidth(sMW)
        self.set_time.setMaximumWidth(sMW)
        self.curr_lim.setMaximumWidth(sMW)
        self.sam_area.setMaximumWidth(sMW)
        self.pow_dens.setMaximumWidth(sMW)
        self.cell_num.setMaximumWidth(sMW)
        self.sun_ref.setMaximumWidth(sMW)
        
        ## Set widget texts
        self.volt_start.setText("-0.2")
        self.volt_end.setText("0.8")
        self.volt_step.setText("0.05")
        self.ave_pts.setText("3")
        self.int_time.setText("0.1")
        self.set_time.setText("0.1")
        self.curr_lim.setText("300")
        self.sam_area.setText("0.04")
        self.pow_dens.setText("100")
        self.sun_ref.setText("130.3")
        # self.cell_num.setText("1")#module
        
        ## Position labels and field in a grid
        LTsetup.addWidget(QLabel(" "),0,0)
        LTsetup.addWidget(QLabel("Start Voltage (V)"),1,0,Qt.AlignRight)
        LTsetup.addWidget(self.volt_start,1,1,Qt.AlignLeft)
        LTsetup.addWidget(QLabel("End Voltage (V)"),1,2,Qt.AlignRight)
        LTsetup.addWidget(self.volt_end,1,3,Qt.AlignLeft)
        LTsetup.addWidget(QLabel("Step size(V)"),2,0,Qt.AlignRight)
        LTsetup.addWidget(self.volt_step,2,1,Qt.AlignLeft)
        LTsetup.addWidget(QLabel("Averaging points"),2,2,Qt.AlignRight)
        LTsetup.addWidget(self.ave_pts,2,3,Qt.AlignLeft)
        LTsetup.addWidget(QLabel("Integration time (s)"),3,0,Qt.AlignRight)
        LTsetup.addWidget(self.int_time,3,1,Qt.AlignLeft)
        LTsetup.addWidget(QLabel("Settling time (s)"),3,2,Qt.AlignRight)
        LTsetup.addWidget(self.set_time,3,3,Qt.AlignLeft)
        LTsetup.addWidget(QLabel("Current Limit (mA)"),4,0,Qt.AlignRight)
        LTsetup.addWidget(self.curr_lim,4,1,Qt.AlignLeft)
        LTsetup.addWidget(QLabel("Cell area (cm²)"),4,2,Qt.AlignRight)
        LTsetup.addWidget(self.sam_area,4,3,Qt.AlignLeft)
        LTsetup.addWidget(QLabel("Power Density (mW/cm²)"),5,0,Qt.AlignRight)
        LTsetup.addWidget(self.pow_dens,5,1,Qt.AlignLeft)
        LTsetup.addWidget(QLabel("1-Sun Reference (mA)"),5,2,Qt.AlignRight)
        LTsetup.addWidget(self.sun_ref,5,3,Qt.AlignLeft)
        # LTsetup.addWidget(QLabel("Ref. Current (mA)\nSun percentage"),6,2,Qt.AlignRight)
        # LTsetup.addWidget(self.curr_ref,6,3,Qt.AlignLeft)
        
        
        ## Third set of setup values
        sbb = 15
        self.for_bmL = QCheckBox()
        self.rev_bmL = QCheckBox()
        self.for_bmD = QCheckBox()
        self.rev_bmD = QCheckBox()
        self.for_bmL.setMaximumWidth(sbb)
        self.rev_bmL.setMaximumWidth(sbb)
        self.for_bmD.setMaximumWidth(sbb)
        self.rev_bmD.setMaximumWidth(sbb)
        self.dark_meas = QCheckBox()
        self.four_wire = QCheckBox()
        self.logyaxis = QCheckBox()
        self.for_bmL.setChecked(True)
        self.rev_bmL.setChecked(True)
        self.four_wire.setChecked(False)
        self.refCurrent = QToolButton(self)
        self.refCurrent.setText("Current (Reference)")
        self.refCurrent.setFixedSize(int(sMW*2.3), 40)
        self.refCurrent.setCheckable(True)
        self.susiShutter = QToolButton(self)
        self.susiShutter.setText("SuSi Shutter")
        self.susiShutter.setFixedSize(int(sMW*2.3), 40)
        self.susiShutter.setCheckable(True)
        label_for = QLabel("\U0001F80A")
        label_rev = QLabel("\U0001F808")
        label_for.setFont(QFont("Arial", 14))
        label_rev.setFont(QFont("Arial", 14))
        self.label_currcurr = QLabel("")
        # self.refPower.setMaximumWidth(sMW*2)

        Lsetup = QGridLayout()
        Lsetup.setColumnMinimumWidth(1,0)
        Lsetup.setColumnMinimumWidth(2,0)
        Lsetup.addWidget(QLabel(" "),0,0)
        Lsetup.addWidget(label_for,1,1)
        Lsetup.addWidget(label_rev,1,2)
        Lsetup.addWidget(QLabel("Light measurement"),2,0,Qt.AlignRight)
        Lsetup.addWidget(self.for_bmL,2,1)
        Lsetup.addWidget(self.rev_bmL,2,2)
        Lsetup.addWidget(QLabel("Dark measurement"),3,0,Qt.AlignRight)
        Lsetup.addWidget(self.for_bmD,3,1)
        Lsetup.addWidget(self.rev_bmD,3,2)
        Lsetup.addWidget(QLabel("4-Wire"),4,0,Qt.AlignRight)
        Lsetup.addWidget(self.four_wire,4,1)
        Lsetup.addWidget(QLabel("log Y-axis"),5,0,Qt.AlignRight)
        Lsetup.addWidget(self.logyaxis,5,1)
        Lsetup.addWidget(self.refCurrent,2,3,2,1,Qt.AlignRight)
        Lsetup.addWidget(self.susiShutter,4,3,2,1,Qt.AlignRight)

        Lsetup.addWidget(QLabel(" "),5,0)
        
        ## Four set of setup values
        LGlabels = QGridLayout()

        self.BStart = QPushButton("START")
        self.BStart.setFont(QFont("Arial", 14, QFont.Bold))
        self.BStart.setStyleSheet("color : green;")
        LGlabels.addWidget(self.BStart,1,0,1,4)
        LGlabels.addWidget(self.label_currcurr,2,0,1,1)
        # Lsetup.addRow(" ",QFrame())
        
        mppLabels = QGridLayout()
        
        self.mpptitle = QLabel("Maximum Power Point Tracking")
        self.mpptitle.setFont(QtGui.QFont("Arial",9,weight=QtGui.QFont.Bold))
        
        self.mpp_ttime = QLineEdit()
        self.mpp_inttime = QLineEdit()
        self.mpp_stepSize = QLineEdit()
        self.mpp_voltage = QLineEdit()
        
        self.mpp_ttime.setMaximumWidth(sMW)
        self.mpp_inttime.setMaximumWidth(sMW)
        self.mpp_stepSize.setMaximumWidth(sMW)
        self.mpp_voltage.setMaximumWidth(sMW)
        
        self.mpp_ttime.setText("60")
        self.mpp_inttime.setText("100")
        self.mpp_stepSize.setText("0.01")
        self.mpp_voltage.setText("0.9")
        
        mppLabels.addWidget(self.mpptitle,0,0,1,3)
        mppLabels.addWidget(QLabel("Total time (s)  "),1,0,Qt.AlignRight)
        mppLabels.addWidget(self.mpp_ttime,1,1)
        mppLabels.addWidget(QLabel("Int. time (ms)  "),1,2,Qt.AlignRight)
        mppLabels.addWidget(self.mpp_inttime,1,3)
        mppLabels.addWidget(QLabel("Step size (V)  "),2,0,Qt.AlignRight)
        mppLabels.addWidget(self.mpp_stepSize,2,1)
        mppLabels.addWidget(QLabel("Voltage (V)  "),2,2,Qt.AlignRight)
        mppLabels.addWidget(self.mpp_voltage,2,3)
        self.mppStart = QPushButton("START")
        self.mppStart.setFont(QFont("Arial", 10, QFont.Bold))
        self.mppStart.setStyleSheet("color : blue;")
        mppLabels.addWidget(self.mppStart,3,0,1,4)
        
        ## Position all these sets into the second layout V2
        layV2.addItem(verticalSpacerV2)
        layV2.addLayout(LGsetup)
        layV2.addLayout(LTsetup)
        layV2.addLayout(Lsetup)
        layV2.addLayout(LGlabels)
        layV2.addItem(verticalSpacerV2)
        layV2.addItem(mppLabels)
        
        ## Add to main horizontal layout with a spacer (for good looks)
        horizontalSpacerH1 = QSpacerItem(10, 70, QSizePolicy.Minimum, QSizePolicy.Minimum)
        layH1.addItem(horizontalSpacerH1)
        layH1.addLayout(layV2,3)
        
        ### Make third vertical layout for metadata 
        layV3 = QtWidgets.QVBoxLayout()

        ## List of relevant values
        self.exp_labels = ["Material","Additives","Concentration","Solvents","Solvents Ratio","Substrate"]
        self.exp_vars = []
        self.glv_labels = ["Temperature ('C)","Water content (ppm)","Oxygen content (ppm)"]
        self.glv_vars = []
        
        self.setup_labs_jv = ["Sample","User","Folder","Voltage_start (V)", "Voltage_end (V)", "Voltage_step (V)", 
                      "Averaged Points","Integration time(s)","Setting time (s)","Current limit (mA)","Cell area(cm²)",
                      "Power Density (mW/cm²)", "Sun Reference (mA)"]
        self.setup_vals_jv = [self.LEsample, self.LEuser, self.LEfolder, self.volt_start,
                           self.volt_end,self.volt_step,self.ave_pts,self.int_time,self.set_time,self.curr_lim,self.sam_area,
                           self.pow_dens,self.sun_ref]
        self.setup_labs_mpp = ["Sample","User","Folder","Total time (s)", "Integration time (ms)", "Voltage_step (V)", 
                      "Starting Voltage (V)","Cell area(cm²)"]
        self.setup_vals_mpp = [self.LEsample, self.LEuser, self.LEfolder, self.mpp_ttime,
                           self.mpp_inttime,self.mpp_stepSize,self.mpp_voltage,self.sam_area]
        
        
        ## Make a new layout and position relevant values
        LmDataExp = QFormLayout()
        LmDataExp.addRow(QLabel('EXPERIMENT VARIABLES'))
        
        for ev in self.exp_labels:
            Evar = QLineEdit()
            # Evar.setMaximumWidth(160)
            LmDataExp.addRow(ev,Evar)
            self.exp_vars.append(Evar)
            
        LmDataBox = QFormLayout()
        LmDataBox.addRow(" ",QFrame())
        LmDataBox.addRow(QLabel('GLOVEBOX VARIABLES'))
        for eb in self.glv_labels:
            Evar = QLineEdit()
            # Evar.setMaximumWidth(120)
            LmDataBox.addRow(eb,Evar)
            self.glv_vars.append(Evar)
        self.com_labels= QTextEdit()
        self.com_labels.setMaximumHeight(50)
        self.com_labels.setMaximumWidth(120)
        LmDataBox.addRow("Comments",self.com_labels)
        
        LGmeta = QGridLayout()
        self.BsaveM = QToolButton()
        self.BloadM = QToolButton()
        self.BsaveM.setText("Save")
        self.BloadM.setText("Load")
        
        LGmeta.addWidget(QLabel(""),0,0)
        LGmeta.addWidget(QLabel("Metadata:"),0,1)
        LGmeta.addWidget(self.BsaveM,0,2)
        LGmeta.addWidget(self.BloadM,0,3)
        
        
        ## Position layouts inside of the third vertical layout V3
        layV3.addItem(verticalSpacerV2)
        layV3.addLayout(LmDataExp)
        layV3.addLayout(LmDataBox)
        layV3.addLayout(LGmeta)
        layV3.addItem(verticalSpacerV2)
        
        ## Add to main horizontal layout with a spacer (for good looks)
        horizontalSpacerH2 = QSpacerItem(30, 70, QSizePolicy.Minimum, QSizePolicy.Minimum)
        layH1.addItem(horizontalSpacerH2)
        layH1.addLayout(layV3,2)
        
        # self.statusBar = QStatusBar()
        
        widget.setLayout(layH1)
        self.setCentralWidget(widget)
        self.show()
        # print(self.keithley.voltage)
        
      
    def button_actions(self):
        
    #     self.send_to_Qthread()
        self.folder = self.LEfolder.text()
        self.Bfolder.clicked.connect(self.select_folder)
        self.Bpath.clicked.connect(self.automatic_folder)
        self.BsaveM.clicked.connect(self.save_meta)
        self.BloadM.clicked.connect(self.load_meta)
        self.refCurrent.clicked.connect(self.reference_current_measure)
        self.susiShutter.clicked.connect(self.SuSi_button)
    #     self.LEinttime.returnPressed.connect(self.set_integration_time)
    #     self.SBinttime.valueChanged.connect(self.scrollbar_action)
    #     self.BDarkMeas.clicked.connect(self.dark_measurement)
    #     self.BBrightMeas.clicked.connect(self.bright_measurement)
        self.BStart.clicked.connect(self.press_start_jv)
        self.mppStart.clicked.connect(self.press_start_mpp)
        self.logyaxis.stateChanged.connect(self.yaxis_to_log)
        self.four_wire.stateChanged.connect(self.two_four_wires_measurement)
    #     self.LEmeatime.textChanged.connect(self.update_number_of_frames)
    #     self.Brange.stateChanged.connect(self.set_axis_range)
    #     self.Braw.stateChanged.connect(self.set_axis_range)
    #     self.BBrightDel.clicked.connect(self.delete_bright_measurement)
    #     self.BDarkDel.clicked.connect(self.delete_dark_measurement)
        


    def select_folder(self):
        old_folder = self.LEfolder.text() ##Read entry line
        
        if not old_folder: ## If empty, go to default
            old_folder = "C:/Data/"
        
        ## Select directory from selection
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Where do you want your data saved?", old_folder) 
        
        if not directory: ## if cancelled, keep the old one
            directory = old_folder
            
        self.LEfolder.setText(directory)
        self.folder = directory  
        
    ## Arrow function, to create folderpath with User and Date
    def automatic_folder(self):
        user = self.LEuser.text()
        folder = self.LEfolder.text()
        date = datetime.now().strftime("%Y%m%d")
        
        if len(user) > 0:
            newfolder = folder+user+"/"+date+"/"
        else:
            newfolder = folder+date
        
        self.LEfolder.setText(newfolder)
        self.folder = newfolder
        
        self.create_folder(False)
        
        self.Bpath.setEnabled(False)
        
    def create_folder(self,sample, retry = 1):
        self.folder = self.LEfolder.text()
        if self.folder[-1] != "/":
            self.folder = self.folder +"/"## Add "/" if non existent
            self.LEfolder.setText(self.folder)
        else:
            pass
        if sample:
            self.sample = self.LEsample.text()
            self.folder = self.folder + self.sample + "/"
            
            ## If sample name is duplicated, make a "-d#" folder
            if os.path.exists(self.folder):
                self.folder = self.folder.rsplit("/",1)[0]+"-d"+str(retry)+"/"
                if os.path.exists(self.folder):
                    retry += 1
                    self.create_folder(True,retry)
                self.statusBar().showMessage("Sample is duplicated", 10000)
                
        ##If folders don't exist, make them        
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
            self.statusBar().showMessage("Folder "+self.folder+" created", 5000)
        else:
            pass
    
    
    def save_meta(self):
        self.create_folder(False)
        self.gather_all_metadata()
        metadata = pd.DataFrame.from_dict(self.meta_dict, orient='index')
        metadata.to_csv(self.folder+"metadata.csv", header = False)
        self.statusBar().showMessage("Metadata file saved successfully", 5000)
        
    def load_meta(self):
        folder = self.LEfolder.text()
        metafile = QtWidgets.QFileDialog.getOpenFileName(self, "Choose your metadata file", folder)
        # print(metafile[0])
        metadata = pd.read_csv(metafile[0], header=None, index_col=0, squeeze=True, nrows=21)
        # print(metadata)
        labels = self.setup_labs+self.exp_labels
        objects = self.setup_vals+self.exp_vars
        
        for cc,oo in enumerate(objects):
            if labels[cc] == "Sample":
                pass
            else:
                if labels[cc] == "Material":
                    try:
                        oo.setText(metadata["Perovskite"])
                    except:
                        oo.setText(str(metadata["Material"]))
                else:
                    oo.setText(str(metadata[labels[cc]]))
        self.LEfolder.setText(metadata["Folder"])
        
        self.statusBar().showMessage("Metadata successfully loaded", 5000)
    
    
    def gather_all_metadata(self):
        self.sample = self.LEsample.text()
        self.meta_dict = {} ## All variables will be collected here
        
        if not hasattr(self,"Rcurrent"):
            self.Rcurrent = 0
            self.RsunP = 0
        
        
        if not self.mpp_bool:
            all_metaD_labs = self.setup_labs_jv+self.exp_labels+self.glv_labels
            all_metaD_vals = self.setup_vals_jv+self.exp_vars+self.glv_vars
            
        else:
            all_metaD_labs = self.setup_labs_mpp+self.exp_labels+self.glv_labels
            all_metaD_vals = self.setup_vals_mpp+self.exp_vars+self.glv_vars
        

        ## Add data to dictionary
        try:
            self.meta_dict["Date"] = strftime("%H:%M:%S - %d.%m.%Y",localtime(self.start_time))
        except:
            self.meta_dict["Date"] = strftime("%H:%M:%S - %d.%m.%Y",localtime(time()))
        self.meta_dict["Location"] = os.environ['COMPUTERNAME']
        try:
            self.meta_dict["Device"] = (self.spec.model+" - Serial No.:"+self.spec.serial_number)
        except:
            pass

        for cc,di in enumerate(all_metaD_labs):
            self.meta_dict[di] = all_metaD_vals[cc].text()
        
        self.meta_dict["Ref. Current(mA)"] = self.Rcurrent
        self.meta_dict["Sun%"] = self.RsunP
            
        # for cp,ad in enumerate(addit_labl):
        #     self.meta_dict[ad] = addit_data[cp]
        
        self.meta_dict["Comments"] = self.com_labels.toPlainText() ## This field has a diffferent format than the others


    def two_four_wires_measurement(self):
        if self.four_wire.isChecked():
            self.keithley.wires = 4
        else:
            self.keithley.wires = 2
        print(self.keithley.wires)
    
    def dis_enable_widgets(self, status):
        
        wi_dis = self.setup_vals_jv + [self.Bfolder,self.Bpath,self.refCurrent]
        
        for wd in wi_dis:
            # TODO fix stop button
            if status:
                wd.setEnabled(False)
                self.BStart.setText("S T O P")
                self.BStart.setStyleSheet("color : red;")
                self.meas_live = True
            else:
                wd.setEnabled(True)
                self.BStart.setText("START")
                self.BStart.setStyleSheet("color : green;")
                self.meas_live = False
    
    def jv_char_display(self):
        names = ["Voc (V)","Jsc (mA/cm²)","FF (%)","PCE (%)","V_mpp (V)","J_mpp (mA/cm²)","P_mpp (mW/cm²)","R_series (\U00002126cm²)","R_shunt (\U00002126cm²)"]
        names_f = [na.replace(" ","") for na in names] 
        names_t = [na.replace(" ","\n") for na in names]
        # empty = ["","","","","","","","",""]
        
        self.jv_chars_results = self.jv_chars_results.T
        self.jv_chars_results.columns = names_f
        
        values = self.jv_chars_results.copy()
        values.columns = names_t
        
        for  v in values.index:
            if "Dark" in v:
                values = values.drop([v],axis=1)
            else:
                values.rename(index = {v:v[:-6]},inplace=True)
            
        self.model = TableModel(values.round(3))
        self.Ljvvars.setModel(self.model)

    
    def save_data(self):
        self.mpp_bool = False
        self.gather_all_metadata()
        ## TODO fix save here
        metadata = pd.DataFrame.from_dict(self.meta_dict, orient='index')
        
        # if self.jv_bkw:
        #     jv_data = pd.DataFrame({"Voltage_fwd (V)":self.res_fwd_volt,"Current_fwd (mA/cm²)":self.res_fwd_curr,
        #                             "Voltage_bkw (V)":self.res_bkw_volt,"Current_bkw (mA/cm²)":self.res_bkw_curr})
        # else:
        #     jv_data = pd.DataFrame({"Voltage_fwd (V)":self.res_fwd_volt,"Current_fwd (mA/cm²)":self.res_fwd_curr})
            
            
        empty = pd.DataFrame(data={"":["--"]})
            
        filename = self.folder+self.sample+"_JV_characteristics.csv"
        metadata.to_csv(filename, index = True, header = False)
        empty.to_csv(filename, mode="a", index=False, header=False, line_terminator='\n')
        self.jv_chars_results.T.to_csv(filename, mode="a", index=True, header=True)
        empty.to_csv(filename, mode="a", index=False, header=False, line_terminator='\n')
        self.curr_volt_results.to_csv(filename, mode="a", index=False, header = True)
        
        # print(self.curr_volt_results)
        self.statusBar().showMessage("Data saved successfully", 5000)
    #     # get_ipython().magic('reset -sf')
        
    
    def save_mpp(self):
        self.mpp_bool = True
        self.gather_all_metadata()
        metadata = pd.DataFrame.from_dict(self.meta_dict, orient='index')
        mpp_data = pd.DataFrame({"Time (s)":self.mpp_time,"Voltage (V)":self.res_mpp_voltage,
                                "Current (mA/cm²)":self.mpp_current,"Power (mW/cm²)":self.mpp_power})
            
        filename = self.folder+self.sample+"_MPP_measurement.csv"
        metadata.to_csv(filename, header = False)
        mpp_data.to_csv(filename, mode="a", index=False)
        

        self.statusBar().showMessage("Data saved successfully", 5000)
        
        self.mpp_current = []
        self.res_mpp_voltage = []
        self.mpp_power = []

                
          
    def press_start_jv(self):
        self.create_folder(True)
        
        curr_limit = float(self.curr_lim.text())
        self.keithley.apply_voltage(compliance_current=curr_limit/1000)
        self.keithley.measure_current(nplc=1, current=0.135, auto_range=True)
        
        self.jv_measurement()
        
    def press_start_mpp(self):
        self.create_folder(True)
        
        curr_limit = float(self.curr_lim.text())
        self.keithley.apply_voltage(compliance_current=curr_limit/1000)
        self.keithley.measure_current(nplc=1, current=0.135, auto_range=True)
        
        self.mpp_measurement()
        

    def reference_current_measure(self):
        ref = float(self.sun_ref.text())
        
        # while self.refCurrent.isChecked():
        
        self.keithley.enable_source()
    
        self.keithley.source_voltage = 0
        self.Rcurrent = self.keithley.current*1000
        self.RsunP = self.Rcurrent/ref*100
        
        self.refCurrent.setText("Ref. current  (Sun%)\n"+str(round(self.Rcurrent,2))+
                                "   ("+str(round(self.RsunP,2))+")")
        
        self.pow_dens.setText(str(round(self.RsunP,2)))
        
        self.keithley.disable_source()


    def jv_chars_calculation(self,volt,curr):
        
        ## find Isc (find voltage value closest to 0 Volts)
        volt = np.array(volt)
        curr = np.array(curr)
        
        ## if reverse measurement, flip it around
        if volt[0] > volt[-1]:
            volt = np.flip(volt)
            curr = np.flip(curr)
        
        
        v0 = np.argmin(abs(volt)) #Find voltage closest to zero
        m_i = (curr[v0]-curr[v0-1]) / (volt[v0]-volt[v0-1]) #Slope at Jsc
        
        if volt[v0] <= 0.0001: #If voltage is equal to zero
            isc = curr[v0]
        else:## Otherwise calculate from slope
            b_i = -curr[v0]-m_i*volt[v0]
            isc = -b_i

        ##For Voc, find closest current values to 0
        i1 = np.where(curr < 0, curr, -np.inf).argmax()
        i2= np.where(curr > 0, curr, np.inf).argmin()
        
        c1 = curr[i1]
        c2 = curr[i2]

        
        ## Get Voc by finding x-intercept
        v1 = volt[i1]
        v2 = volt[i2]
        m_v = (c2-c1)/(v2-v1)
        b_v = c1-m_v*v1
        voc = -b_v/m_v
        
        #Calculate resistances, parallel and series
        r_par = 1/m_i
        r_ser = 1/m_v


        ## Find mpp values
        mpp = np.argmax(-volt*curr)

        mpp_v = volt[mpp]
        mpp_c = curr[mpp]
        mpp_p = mpp_v * mpp_c
        
        ## Calculate FF
        ff = mpp_v*mpp_c/(voc*isc)*100
        
        ## Calculate PCE (this is wrong, it needs correct P_in)
        # pin = 75#mW/cm²
        pin = float(self.pow_dens.text())#mW/cm²
        pce = abs(voc*isc*ff)/pin
        
        jv_char = [voc,isc,ff,pce, mpp_v,mpp_c,mpp_p, r_ser,r_par]

        return jv_char    
    
    def SuSi_button(self):
        answer = self.SuSi_check()
        
        if "SHUTTER=0" in answer:
            self.SuSi_light_on()
        else:
            self.SuSi_light_off()
    
    def SuSi_check(self):
        self.susi.write(b'FS') #Read data
        susi_ans = self.susi.read_until(b"END\r\n")
        
        return susi_ans
        
    
    def SuSi_light_on(self):
        if self.susi_bool:
            susi_state = self.SuSi_check()
            #TODO check correct string
            if "SHUTTER=0" in susi_state: ##it is closed, open
                self.susi.write(b'S1') #Shutter Open
            else:
                pass## it is already open
        else:
            pass## There is no SuSi, so skip
    
    def SuSi_light_off(self):
        if self.susi_bool:
            susi_state = self.SuSi_check()
            if "SHUTTER=1" in susi_state: ##it is closed, open
                self.susi.write(b'S0') #Shutter Closed
            else:
                pass## it is already open
        ##TODO if False, make a popup so it can be done manually
    
    def namestr(self,obj, namespace):
        return [name for name in namespace if namespace[name] is obj]

    def fix_data_and_send_to_measure(self):
        area = float(self.sam_area.text())
        self.reset_plot_jv()
        volt_begin = float(self.volt_start.text())
        volt_end = float(self.volt_end.text())
        time_step = float(self.volt_step.text())
        
        ap = int(self.ave_pts.text())
        time = float(self.set_time.text())
        
        self.res_fwd_curr = []
        self.res_fwd_volt = []
        self.res_bkw_curr = []
        self.res_bkw_volt = []
        
        forwa_vars = [volt_begin, volt_end+time_step*0.95,  time_step]
        rever_vars = [volt_end, volt_begin-time_step*0.95, -time_step]
        fixed_vars = [time,ap,area]
        
        check_box_buttons = [self.for_bmD,self.rev_bmD, self.for_bmL,self.rev_bmL]
        
        self.jv_chars_results = pd.DataFrame()
        self.curr_volt_results = pd.DataFrame()
        
        ##TODO with multiplexing, there will be another loop here that goes through the cells
        for n, cbb in enumerate(check_box_buttons):
            if cbb.isChecked():
                if n == 0 or n == 1: #if it is a dark measurement
                    self.SuSi_light_off()
                    ilum = "Dark"
                else:
                    self.SuSi_light_on()
                    ilum = "Light"
                
                
                if n == 0 or n == 2: ## if it is forward
                    direc = "Forward"
                    all_vars = forwa_vars + fixed_vars +[ilum+direc]
                else:
                    direc = "Reverse"
                    all_vars = rever_vars + fixed_vars +[ilum+direc]
                    
                
                # print(all_vars)
                volt, curr, chars = self.curr_volt_measurement(all_vars)
                
                self.jv_chars_results[direc+"_"+ilum] = chars
                self.curr_volt_results["Voltage_"+direc+"_"+ilum] = volt
                self.curr_volt_results["Current_"+direc+"_"+ilum] = curr
                # print(self.curr_volt_results)
            
            
    def display_current(self,value,live=True):
        if live:
            if abs(value) < 0.01:
                label = '{:.2e}'.format(value)
            else:
                label = '{:.2f}'.format(value)
            
            self.label_currcurr.setText("Live :   "+str(label)+"   mA/cm²")
            
        else:
            self.label_currcurr.setText("")
            
    def curr_volt_measurement(self, variables):
        
        volt_0 = variables[0]
        volt_f = variables[1]
        step = variables[2]
        time = variables[3]
        average_points = variables[4]
        area = variables[5]
        mode = variables[6]
        
        current = []
        voltage = []
        
        for i in np.arange(volt_0, volt_f, step):
            meas_currents = []
            meas_voltages = []
            for t in range(average_points):
                if self.meas_live:
                    self.keithley.source_voltage = i
                    QtTest.QTest.qWait(int(time*1000))
                    meas_voltages.append(i)
                    meas_currents.append(self.keithley.current*1000/area)
                else:
                    meas_voltages.append(np.nan)
                    meas_currents.append(np.nan)

            ave_curr = np.mean(meas_currents)
            self.display_current(ave_curr)
            current.append(ave_curr)
            voltage.append(np.mean(meas_voltages))
            
            self.plot_jv(voltage,current,mode)
            
        jv_chars = self.jv_chars_calculation(voltage, current)
        self.display_current(ave_curr,False)
        
        return voltage, current, jv_chars
        

    def jv_measurement(self):
        ## Reset values
        
        # self.jv_bkw = []
        
        # area = float(self.sam_area.text())
        # self.reset_plot_jv()
        # volt_begin = float(self.volt_start.text())
        # volt_end = float(self.volt_end.text())
        # time_step = float(self.volt_step.text())
        
        # average_points = int(self.ave_pts.text())
        # time = float(self.set_time.text())
        
        self.dis_enable_widgets(True)
        
        self.statusBar().showMessage("Measuring JV curve")
                
        self.keithley.enable_source()
        
        self.fix_data_and_send_to_measure()
        

        self.jv_char_display()

        self.keithley.disable_source()
        self.dis_enable_widgets(False)
        
        self.save_data()
        
    def mpp_measurement(self):
        self.reset_plot_mpp()
        
        area = float(self.sam_area.text())
        
        mpp_total_time = float(self.mpp_ttime.text())
        mpp_int_time = float(self.mpp_inttime.text())
        mpp_step = float(self.mpp_stepSize.text())
        mpp_voltage = float(self.mpp_voltage.text())
        
        self.statusBar().showMessage("Tracking Maximum Power Point")

        self.keithley.enable_source()
        
        self.mpp_current = []
        self.res_mpp_voltage = []
        self.mpp_power = []
        self.mpp_time = []
        
        max_voltage = mpp_voltage
        time_c = time()
        for i in np.arange(0,mpp_total_time/3,mpp_int_time/1000):
            voltage_test = [max_voltage-mpp_step , max_voltage , max_voltage+mpp_step]
            mpp_test_current = []
            mpp_test_voltage = []
            mpp_test_power = []
            
            for v in voltage_test:
                self.keithley.source_voltage = v
                ## Wait for stabilized measurement
                QtTest.QTest.qWait(int(mpp_int_time))
                ## Measure current & voltage
                m_current = self.keithley.current*1000/area
                m_voltage = self.keithley.voltage
                
                mpp_test_current.append(m_current)
                mpp_test_voltage.append(m_voltage)
                mpp_test_power.append(abs(m_voltage*m_current))
                
            index_max = mpp_test_power.index(max(mpp_test_power))
            
            self.mpp_current.append(mpp_test_current[index_max])
            # print(mpp_test_power, index_max)
            max_voltage = mpp_test_voltage[index_max]
            # print(max_voltage)
            self.res_mpp_voltage.append(max_voltage)
            
            self.mpp_power.append(mpp_test_power[index_max])
            
            if i == 0:
                to = time() - time_c
            elapsed_t = (time() - time_c - to)
            self.mpp_time.append(elapsed_t / 60)            
            self.plot_mpp()
            # print(i, elapsed_t)
            if elapsed_t > mpp_total_time:
                # print(elapsed_t, mpp_total_time)
                break
        
        self.keithley.disable_source()
        
        self.save_mpp()        
    

    def spectra_measurement(self):
        self.start_time = time() ## Start of stopwatch
        self.set_integration_time() ## Reset int time to what is in entry field
        self.spectra_meas_array = np.ones((self.total_frames,self.array_size))
        self.spectra_raw_array = np.ones((self.total_frames,self.array_size))
        self.time_meas_array = np.ones(self.total_frames)
        self.spectra_meas_array[:] = np.nan
        self.spectra_raw_array[:] = np.nan
        self.time_meas_array[:] = np.nan
        self.measuring = True
        self.spectra_measurement_bool = True
        self.spectra_counter = 0
        self.counter = 0
        self.array_count = 0
        
    def collect_all_values_iv(self, voltage=[],current=[]):
        ## Gather all measurements till now
        volt = []
        curr = []
        try:
            # print(self.curr_volt_results.keys())
            for key in self.curr_volt_results.keys():
                if "Volt" in key:
                    volt.append(self.curr_volt_results[key].values.tolist()[0])
                elif "Curr" in key:
                    curr.append(self.curr_volt_results[key].values.tolist()[0])
                else:
                    pass
        except:
            volt = [-0.01,0.01]
            curr = [-0.01,0.01]
            
        volt = volt + voltage
        curr = curr + current
        
        # print(volt)
        # print(curr)
        
        return volt,curr

    
    def yaxis_to_log(self):
        if self.logyaxis.isChecked():
            self.canvas.axes.set_yscale('log')
        else:
            self.canvas.axes.set_yscale('linear')
        
        volt, curr = self.collect_all_values_iv()

        self.center_plot(volt,curr)
        
        self.canvas.draw_idle()
            
    
    def reset_plot_jv(self):
        self.canvas.axes.cla()
        self.canvas.axes.set_xlabel('Voltage (V)')
        self.canvas.axes.set_ylabel('Current density (mA/cm²)')
        self.canvas.axes.grid(True,linestyle='--')
        self.canvas.axes.set_xlim([-0.5,2])
        self.canvas.axes.set_ylim([-25,5])
        self.canvas.axes.axhline(0, color='black')
        self.canvas.axes.axvline(0, color='black')
        # if self.logyaxis.isChecked():
        #     self.canvas.axes.set_yscale('log')
        # else:
        #     self.canvas.axes.set_yscale('linear')
        self._plot_ref = None
        
    def reset_plot_mpp(self):
        self.canvas.axes.cla()
        self.canvas.axes.set_xlabel('Time (min)')
        self.canvas.axes.set_ylabel('Power (mW/cm²)')
        self.canvas.axes.grid(True,linestyle='--')
        self.canvas.axes.set_xlim([0,2])
        self.canvas.axes.set_ylim([5,25])
        self.canvas.axes.axhline(0, color='black')
        self.canvas.axes.axvline(0, color='black')
        # if self.logyaxis.isChecked():
        #     self.canvas.axes.set_yscale('log')
        # else:
        #     self.canvas.axes.set_yscale('linear')
        self._plot_ref = None
        


    def plot_jv(self,voltage,current,mode):
        ## Make plot
        if self._plot_ref is None:
            if "Forward" in mode:
                self._plot_ref = self.canvas.axes.plot(voltage, current, 'xb-', label="Forward")
                
            else:
                self._plot_ref = self.canvas.axes.plot(voltage, current, '.r--', label="Backward")
                self.canvas.axes.legend()
        else:
            if "Forward" in mode:
                self.canvas.axes.plot(voltage, current, 'xb-')
            else:
                self.canvas.axes.plot(voltage, current, '.r--')
            
        # if self.logyaxis.isChecked():
        #     self.canvas.axes.set_yscale('log')
        # else:
        #     self.canvas.axes.set_yscale('linear')
        
        volt, curr = self.collect_all_values_iv(voltage,current)
        self.center_plot(volt,curr)
        
        ## Draw plot
        self.canvas.draw_idle()
        
        
    def center_plot(self,voltage, current):
        # print(voltage)
        # print(current)
        
        if self.logyaxis.isChecked():
            current = [cu for cu in current if cu > 0]
        else:
            pass
        

        ## Get min and max values to center plot
        if not voltage:
            min_x = -0.1
            max_x = 0.1
            min_y = -0.1
            max_y = 0.1
        else:            
            min_x = min(voltage)
            max_x = np.max(voltage)
            min_y = np.min(current)
            max_y = np.max(current)

        
        ex = (max_x-min_x)*0.05
        ey = (max_y-min_y)*0.05
        
        room = 0.05
        
        try:
            if min_x != max_x:
                self.canvas.axes.set_ylim([min_y-ey,max_y+ey])
                self.canvas.axes.set_xlim([min_x-ex,max_x+ex])
            else:
                self.canvas.axes.set_ylim([min_y-room,max_y+room])
                self.canvas.axes.set_xlim([min_x-room,max_x+room])
        except:
            self.canvas.axes.set_ylim([-0.1,0.1])
            self.canvas.axes.set_xlim([-0.1,0.1])
            
        
    def plot_mpp(self):
        ## Make plot
        if self._plot_ref is None:
            self._plot_ref = self.canvas.axes.plot(self.mpp_time, self.mpp_power, 'xb-', label="Power")
                        
        else:
            self.canvas.axes.plot(self.mpp_time, self.mpp_power, 'xb-')

        # if self.logyaxis.isChecked():
        #     self.canvas.axes.set_yscale('log')
        # else:
        #     self.canvas.axes.set_yscale('linear')
            
        ## Get min and max values to center plot
        min_x = np.min(self.mpp_time)
        max_x = np.max(self.mpp_time)
        min_y = np.min(self.mpp_power)
        max_y = np.max(self.mpp_power)
        
        ex = (max_x-min_x)*0.05
        ey = (max_y-min_y)*0.05
        
        room = 0.05
        if min_x != max_x:
            self.canvas.axes.set_ylim([min_y-ey,max_y+ey])
            self.canvas.axes.set_xlim([min_x-ex,max_x+ex])
        else:
            self.canvas.axes.set_ylim([min_y-room,max_y+room])
            self.canvas.axes.set_xlim([min_x-room,max_x+room])
        
        ## Draw plot
        self.canvas.draw_idle()

        
    def finished_plotting(self):
        self.statusBar().showMessage("Plotting process finished and images saved",5000)
              
    def closeEvent(self, event):
        reply = QMessageBox.question(self,'Window Close', 'Are you sure you want to close the window?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            print('Window closed')
            if self.keithley:
                self.keithley.disable_source()
            event.accept()
            # if self.spectrometer:
            #     self.spec.close()
        else:
            event.ignore()


if __name__ == "__main__": 
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    app.exec_()
