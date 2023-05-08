__author__ = "Edgar Nandayapa"
__version__ = "1.08-2022"

import sys
import matplotlib
from PyQt5 import QtWidgets, QtGui, QtTest
from PyQt5.QtWidgets import QWidget, QLineEdit, QFormLayout, QHBoxLayout, QVBoxLayout, QSpacerItem, QGridLayout
from PyQt5.QtWidgets import QFrame, QPushButton, QCheckBox, QLabel, QToolButton, QTextEdit, QPlainTextEdit
from PyQt5.QtWidgets import QSizePolicy, QMessageBox, QDialog,QInputDialog
from PyQt5.QtCore import QThreadPool
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QTableView
from PyQt5.QtCore import QAbstractTableModel, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib import rcParams
from pymeasure.instruments.keithley import Keithley2450
from sklearn.linear_model import LinearRegression
import pyvisa as visa
import pandas as pd
import numpy as np
import os
from k8090 import relay_card
import serial.tools.list_ports
import serial
from time import time, strftime, localtime, gmtime
from datetime import datetime

rcParams.update({'figure.autolayout': True})
matplotlib.use('Qt5Agg')

class TableModel(QAbstractTableModel):

    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data
        self.highlight_row = self._data["PCE"].idxmax()

    def data(self, index, role):
        if role == Qt.DisplayRole:
            # Get the raw value
            value = self._data.iloc[index.row(), index.column()]

            # Perform per-type checks and render accordingly.
            if isinstance(value, datetime):
                # Render time to YYY-MM-DD.
                return value.strftime("%Y-%m-%d")

            if isinstance(value, float):
                if abs(value) < 0.001:
                    return "%.2e" % value
                else:
                    return "%.3f" % value

            if isinstance(value, str):
                # Render strings with quotes
                return '%s' % value

            # Default (anything not captured above: e.g. int)
            return value

        if role == Qt.BackgroundRole:
            if index.row() == self.highlight_row:
                return QColor(Qt.yellow)

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

            # This makes the plot happen


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=300, tight_layout=True):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        self.axes.set_xlabel('Voltage (V)')
        self.axes.set_ylabel('Current density (mA/cm²)')
        self.axes.grid(True, linestyle='--')
        self.axes.set_xlim([-0.5, 2])
        # self.axes.set_xlim([400,850])
        self.axes.set_ylim([-25, 5])
        self.axes.axhline(0, color='black')
        self.axes.axvline(0, color='black')
        fig.tight_layout()
        super(MplCanvas, self).__init__(fig)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        # Initialize parameters

        self.setWindowTitle("JV Characteristics")
        folder = os.path.abspath(os.getcwd()) + "\\"
        self.setWindowIcon(QtGui.QIcon(folder + "solar.ico"))
        np.seterr(divide='ignore', invalid='ignore')
        self.sample = ""

        self.statusBar().showMessage("Program by Edgar Nandayapa - 2022", 10000)

        try:
            self.relaycard = relay_card.connect('COM4')
            #print(f'Firmware version: {self.relaycard.firmware_version}')
            self.relaycard.factory_reset()
            self.is_relay = True

            self.relays = []
            for r in range(8):
                self.relays.append(self.relaycard.relays[r])
        except:
            ports = serial.tools.list_ports.comports()

            # for port, desc, hwid in sorted(ports):
            #     print("{}: {} [{}]".format(port, desc, hwid))
            self.is_relay = False
            print("relay not found")


        try:
            # Modify this in case multiple keithley
            rm = visa.ResourceManager()  # Load piVisa
            print(rm.list_resources())
            device = rm.list_resources()[0]  # Get the first keithley on the list
            self.keithley = Keithley2450(device)
            self.keithley.wires = 4
        except:
            device = None
            self.keithley = None
            self.statusBar().showMessage("##    Keithley not found    ##")

        try:
            # susi = serial.Serial()  # open serial port
            self.susi = serial.Serial("COM3")
            self.susi.baudrate = 9600
            self.susi.bytesize = 8
            self.susi.parity = 'N'
            self.susi.stopbits = 1
            self.susi.timeout = 5
            self.is_susi = True
            self.is_shutter_open = False


        except:
            self.is_susi = False

            if not self.keithley:
                self.statusBar().showMessage("##    Keithley and susi not found    ##")
                self.popup_message("  Keithley\n"
                                   "  and susi\n"
                                   "were not found")
            else:
                self.statusBar().showMessage("##    susi not found    ##")
                self.popup_message("    susi\n"
                                   "was not found")



        # self.threadpool = QThreadPool()

        self.create_widgets()

        self.button_actions()  # Set button actions

    def create_widgets(self):
        widget = QWidget()
        layH1 = QHBoxLayout()  # Main (horizontal) Layout

        # Create the maptlotlib FigureCanvas for plotting
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.canvas.setMinimumWidth(600)  # Fix width so it doesn't change
        self.canvas.setMinimumHeight(450)
        self.setCentralWidget(self.canvas)
        self._plot_ref = None
        self.is_meas_live = False
        self.is_first_plot = True
        self.is_recipe = False
        # Add a toolbar to control plotting area
        toolbar = NavigationToolbar(self.canvas, self)

        self.Lqtable = QTableView()
        self.Lqtable.resize(600, 10)
        # self.jvvals.horizontalHeader().setStretchLastSection(True)
        self.Lqtable.setAlternatingRowColors(True)
        self.Lqtable.setSelectionBehavior(QTableView.SelectRows)
        # self.Ljvvars.setColumnWidth(10)

        jvstart = pd.DataFrame(
            columns=["Voc\n(V)", "Jsc\n(mA/cm²)", "FF\n(%)", "PCE\n(%)", "V_mpp\n(V)", "J_mpp\n(mA/cm²)",
                     "P_mpp\n(mW/cm²)", "R_series\n\U00002126cm²", "R_shunt\n\U00002126cm²"])

        self.model = TableModel(jvstart)
        self.Lqtable.setModel(self.model)

        # Add to (first) vertical layout
        layV1 = QtWidgets.QVBoxLayout()
        # Add Widgets to the layout
        layV1.addWidget(toolbar)
        layV1.addWidget(self.canvas,5)
        layV1.addWidget(self.Lqtable, 2)

        # Add first vertical layout to the main horizontal one
        layH1.addLayout(layV1, 8)

        # Make second vertical layout for measurement settings
        layV2 = QtWidgets.QVBoxLayout()
        verticalSpacerV2 = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)  # To center the layout

        # Relevant fields for sample, user and folder names
        self.LEsample = QLineEdit()
        self.LEuser = QLineEdit()
        self.LEfolder = QLineEdit()

        # Make a grid layout and add labels and fields to it
        LsetGeneral = QGridLayout()
        LsetGeneral.addWidget(QLabel("Sample:"), 0, 0)
        LsetGeneral.addWidget(self.LEsample, 0, 1)
        LsetGeneral.addWidget(QLabel("User:"), 1, 0)
        LsetGeneral.addWidget(self.LEuser, 1, 1)
        self.Bpath = QToolButton()
        self.Bpath.setToolTip("Create a folder containing today's date")
        LsetGeneral.addWidget(self.Bpath, 1, 2)
        LsetGeneral.addWidget(QLabel("Folder:"), 2, 0)
        LsetGeneral.addWidget(self.LEfolder, 2, 1)
        self.Bfolder = QToolButton()
        self.Bfolder.setToolTip("Choose a folder where to save the data")
        LsetGeneral.addWidget(self.Bfolder, 2, 2)

        # Set defaults
        self.Bpath.setText("\U0001F4C6")
        self.Bfolder.setText("\U0001F4C1")
        self.LEfolder.setText("C:/Data/")

        # Second set of setup values
        LsetParameters = QGridLayout()
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
        # self.sun_ref = QLineEdit()
        self.curr_ref = QLabel("0\n0%")

        # Set maximum width of widgets
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
        # self.sun_ref.setMaximumWidth(sMW)

        # Set widget texts
        self.volt_start.setText("-0.2")
        self.volt_end.setText("1.2")
        self.volt_step.setText("0.1")
        self.ave_pts.setText("2")
        self.int_time.setText("0.1")
        self.set_time.setText("0.1")
        self.curr_lim.setText("300")
        self.sam_area.setText("0.16")
        self.pow_dens.setText("100")
        # self.sun_ref.setText("74")
        # self.cell_num.setText("1")#module

        # Position labels and field in a grid
        LsetParameters.addWidget(QLabel(" "), 0, 0)
        LsetParameters.addWidget(QLabel("Start Voltage (V)"), 1, 0, Qt.AlignRight)
        LsetParameters.addWidget(self.volt_start, 1, 1, Qt.AlignLeft)
        LsetParameters.addWidget(QLabel("End Voltage (V)"), 1, 2, Qt.AlignRight)
        LsetParameters.addWidget(self.volt_end, 1, 3, Qt.AlignLeft)
        LsetParameters.addWidget(QLabel("Step size(V)"), 2, 0, Qt.AlignRight)
        LsetParameters.addWidget(self.volt_step, 2, 1, Qt.AlignLeft)
        LsetParameters.addWidget(QLabel("Averaging points"), 2, 2, Qt.AlignRight)
        LsetParameters.addWidget(self.ave_pts, 2, 3, Qt.AlignLeft)
        LsetParameters.addWidget(QLabel("Integration time (s)"), 3, 0, Qt.AlignRight)
        LsetParameters.addWidget(self.int_time, 3, 1, Qt.AlignLeft)
        LsetParameters.addWidget(QLabel("Settling time (s)"), 3, 2, Qt.AlignRight)
        LsetParameters.addWidget(self.set_time, 3, 3, Qt.AlignLeft)
        LsetParameters.addWidget(QLabel("Current Limit (mA)"), 4, 0, Qt.AlignRight)
        LsetParameters.addWidget(self.curr_lim, 4, 1, Qt.AlignLeft)
        LsetParameters.addWidget(QLabel("Cell area (cm²)"), 4, 2, Qt.AlignRight)
        LsetParameters.addWidget(self.sam_area, 4, 3, Qt.AlignLeft)
        LsetParameters.addWidget(QLabel("Power Density (mW/cm²)"), 5, 0, Qt.AlignRight)
        LsetParameters.addWidget(self.pow_dens, 5, 1, Qt.AlignLeft)
        # LTsetup.addWidget(QLabel("1-Sun Reference (mA)"), 5, 2, Qt.AlignRight)
        # LTsetup.addWidget(self.sun_ref, 5, 3, Qt.AlignLeft)
        # LTsetup.addWidget(QLabel("Ref. Current (mA)\nSun percentage"),6,2,Qt.AlignRight)
        # LTsetup.addWidget(self.curr_ref,6,3,Qt.AlignLeft)

        # Third set of setup values
        sbb = 15
        self.for_bmL = QCheckBox()
        self.rev_bmL = QCheckBox()
        self.for_bmD = QCheckBox()
        self.rev_bmD = QCheckBox()
        self.for_bmL.setMaximumWidth(sbb)
        self.rev_bmL.setMaximumWidth(sbb)
        self.for_bmD.setMaximumWidth(sbb)
        self.rev_bmD.setMaximumWidth(sbb)
        self.four_wire = QCheckBox()
        self.logyaxis = QCheckBox()
        self.for_bmL.setChecked(True)
        self.rev_bmL.setChecked(True)
        self.four_wire.setChecked(False)
        # self.refCurrent = QToolButton(self)
        # self.refCurrent.setText("Current (Reference)")
        # self.refCurrent.setFixedSize(int(sMW * 2.3), 40)
        # self.refCurrent.setCheckable(True)
        self.susiShutter = QToolButton(self)
        self.susiShutter.setText("SuSi Shutter")
        self.susiShutter.setFixedSize(int(sMW * 2.3), 40)
        self.susiShutter.setCheckable(True)
        label_for = QLabel("\U0001F80A")
        label_rev = QLabel("\U0001F808")
        label_for.setFont(QFont("Arial", 14))
        label_rev.setFont(QFont("Arial", 14))
        self.label_currcurr = QLabel("")
        self.label_currvolt = QLabel("")
        # self.refPower.setMaximumWidth(sMW*2)

        LsetProcess = QGridLayout()
        LsetProcess.setColumnMinimumWidth(1, 0)
        LsetProcess.setColumnMinimumWidth(2, 0)
        LsetProcess.addWidget(QLabel(" "), 0, 0)
        LsetProcess.addWidget(label_for, 1, 1)
        LsetProcess.addWidget(label_rev, 1, 2)
        LsetProcess.addWidget(QLabel("Dark measurement"), 2, 0, Qt.AlignRight)
        LsetProcess.addWidget(self.for_bmD, 2, 1)
        LsetProcess.addWidget(self.rev_bmD, 2, 2)
        LsetProcess.addWidget(QLabel("Light measurement"), 3, 0, Qt.AlignRight)
        LsetProcess.addWidget(self.for_bmL, 3, 1)
        LsetProcess.addWidget(self.rev_bmL, 3, 2)
        LsetProcess.addWidget(QLabel("4-Wire"), 4, 0, Qt.AlignRight)
        LsetProcess.addWidget(self.four_wire, 4, 1)
        LsetProcess.addWidget(QLabel("log Y-axis"), 5, 0, Qt.AlignRight)
        LsetProcess.addWidget(self.logyaxis, 5, 1)
        # Lsetup.addWidget(self.refCurrent, 2, 3, 2, 1, Qt.AlignRight)
        LsetProcess.addWidget(self.susiShutter, 4, 3, 2, 1, Qt.AlignRight)

        LsetProcess.addWidget(QLabel(" "), 5, 0)

        LsetCells = QGridLayout()
        LsetCells.maximumSize().setWidth(10)
        self.multiplex = QCheckBox()
        self.cell_a = QCheckBox()
        self.cell_b = QCheckBox()
        self.cell_c = QCheckBox()
        self.cell_d = QCheckBox()
        self.cell_e = QCheckBox()
        self.cell_f = QCheckBox()
        self.cell_g = QCheckBox()

        self.multiplex.setChecked(True)
        self.cell_a.setChecked(True)
        self.cell_b.setChecked(True)
        self.cell_c.setChecked(True)
        self.cell_d.setChecked(True)
        self.cell_e.setChecked(True)
        self.cell_f.setChecked(True)
        self.cell_g.setChecked(True)

        self.area_a = QLineEdit()
        self.area_b = QLineEdit()
        self.area_c = QLineEdit()
        self.area_d = QLineEdit()
        self.area_e = QLineEdit()
        self.area_f = QLineEdit()
        self.area_g = QLineEdit()

        cells = [self.area_a, self.area_b, self.area_c, self.area_d, self.area_e, self.area_f, self.area_g]

        for ce in cells:
            ce.setMaximumWidth(40)
            ce.setText("0.16")

        self.area_g.setText("1")

        LsetCells.addWidget(QLabel(" "), 0, 0)
        LsetCells.addWidget(QLabel("Multiplexing"), 1, 0, Qt.AlignRight)
        LsetCells.addWidget(self.multiplex, 1, 1, Qt.AlignLeft)
        LsetCells.addWidget(QLabel("B"), 2, 0, Qt.AlignRight)
        LsetCells.addWidget(self.area_b, 2, 1, Qt.AlignCenter)
        LsetCells.addWidget(self.cell_b, 2, 2, Qt.AlignRight)
        LsetCells.addWidget(QLabel("D"), 3, 0, Qt.AlignRight)
        LsetCells.addWidget(self.area_d, 3, 1, Qt.AlignCenter)
        LsetCells.addWidget(self.cell_d, 3, 2, Qt.AlignRight)
        LsetCells.addWidget(QLabel("F"), 4, 0, Qt.AlignRight)
        LsetCells.addWidget(self.area_f, 4, 1, Qt.AlignCenter)
        LsetCells.addWidget(self.cell_f, 4, 2, Qt.AlignRight)
        LsetCells.addWidget(QLabel("A"), 2, 6, Qt.AlignLeft)
        LsetCells.addWidget(self.area_a, 2, 5, Qt.AlignCenter)
        LsetCells.addWidget(self.cell_a, 2, 4, Qt.AlignLeft)
        LsetCells.addWidget(QLabel("C"), 3, 6, Qt.AlignLeft)
        LsetCells.addWidget(self.area_c, 3, 5, Qt.AlignCenter)
        LsetCells.addWidget(self.cell_c, 3, 4, Qt.AlignLeft)
        LsetCells.addWidget(QLabel("E"), 4, 6, Qt.AlignLeft)
        LsetCells.addWidget(self.area_e, 4, 5, Qt.AlignCenter)
        LsetCells.addWidget(self.cell_e, 4, 4, Qt.AlignLeft)
        LsetCells.addWidget(QLabel(" "), 5, 3)

        # Four set of setup values
        LsetStart = QGridLayout()

        self.BStart = QPushButton("START")
        self.BStart.setFont(QFont("Arial", 14, QFont.Bold))
        self.BStart.setStyleSheet("color : green;")
        LsetStart.addWidget(self.BStart, 1, 0, 1, 4)
        LsetStart.addWidget(self.label_currvolt, 2, 0, 1, 1)
        LsetStart.addWidget(self.label_currcurr, 3, 0, 1, 1)
        # Lsetup.addRow(" ",QFrame())

        LsetMPP = QGridLayout()

        self.mpptitle = QLabel("Maximum Power Point Tracking")
        self.mpptitle.setFont(QtGui.QFont("Arial", 9, weight=QtGui.QFont.Bold))

        self.mpp_ttime = QLineEdit()
        self.mpp_inttime = QLineEdit()
        self.mpp_stepSize = QLineEdit()
        self.mpp_voltage = QLineEdit()

        self.mpp_ttime.setMaximumWidth(sMW)
        self.mpp_inttime.setMaximumWidth(sMW)
        self.mpp_stepSize.setMaximumWidth(sMW)
        self.mpp_voltage.setMaximumWidth(sMW)

        self.mpp_ttime.setText("1")
        self.mpp_inttime.setText("100")
        self.mpp_stepSize.setText("0.001")
        self.mpp_voltage.setText("0.45")

        LsetMPP.addWidget(self.mpptitle, 0, 0, 1, 3)
        LsetMPP.addWidget(QLabel("Total time (min)  "), 1, 0, Qt.AlignRight)
        LsetMPP.addWidget(self.mpp_ttime, 1, 1)
        LsetMPP.addWidget(QLabel("Int. time (ms)  "), 1, 2, Qt.AlignRight)
        LsetMPP.addWidget(self.mpp_inttime, 1, 3)
        LsetMPP.addWidget(QLabel("Step size (V)  "), 2, 0, Qt.AlignRight)
        LsetMPP.addWidget(self.mpp_stepSize, 2, 1)
        LsetMPP.addWidget(QLabel("Voltage (V)  "), 2, 2, Qt.AlignRight)
        LsetMPP.addWidget(self.mpp_voltage, 2, 3)
        self.mppStart = QPushButton("START")
        self.mppStart.setFont(QFont("Arial", 10, QFont.Bold))
        self.mppStart.setStyleSheet("color : blue;")
        LsetMPP.addWidget(self.mppStart, 3, 0, 1, 4)

        # Position all these sets into the second layout V2
        layV2.addItem(verticalSpacerV2)
        layV2.addLayout(LsetGeneral)
        layV2.addLayout(LsetParameters)
        layV2.addLayout(LsetProcess)
        layV2.addItem(verticalSpacerV2)
        layV2.addLayout(LsetCells)
        layV2.addLayout(LsetStart)
        layV2.addItem(verticalSpacerV2)
        layV2.addItem(LsetMPP)
        layV2.addItem(verticalSpacerV2)

        # Add to main horizontal layout with a spacer (for good looks)
        horizontalSpacerH1 = QSpacerItem(10, 70, QSizePolicy.Minimum, QSizePolicy.Minimum)
        layH1.addItem(horizontalSpacerH1)
        layH1.addLayout(layV2, 3)

        ## Make third vertical layout for metadata 
        layV3 = QtWidgets.QVBoxLayout()

        # List of relevant values
        self.exp_labels = ["Material", "Additives", "Concentration", "Solvents", "Solvents Ratio", "Substrate"]
        self.exp_vars = []
        self.glv_labels = ["Temperature ('C)", "Water content (ppm)", "Oxygen content (ppm)"]
        self.glv_vars = []

        self.setup_labs_jv = ["Sample", "User", "Folder", "Voltage_start (V)", "Voltage_end (V)", "Voltage_step (V)",
                              "Averaged Points", "Integration time(s)", "Setting time (s)", "Current limit (mA)",
                              "Cell area(cm²)",
                              "Power Density (mW/cm²)"]#, "Sun Reference (mA)"]
        self.setup_vals_jv = [self.LEsample, self.LEuser, self.LEfolder, self.volt_start,
                              self.volt_end, self.volt_step, self.ave_pts, self.int_time, self.set_time, self.curr_lim,
                              self.sam_area,
                              self.pow_dens]#, self.sun_ref]
        self.setup_labs_mpp = ["Sample", "User", "Folder", "Total time (s)", "Integration time (ms)",
                               "Voltage_step (V)",
                               "Starting Voltage (V)", "Cell area(cm²)"]
        self.setup_vals_mpp = [self.LEsample, self.LEuser, self.LEfolder, self.mpp_ttime,
                               self.mpp_inttime, self.mpp_stepSize, self.mpp_voltage, self.sam_area]

        # Make a new layout and position relevant values
        LmetaSample = QFormLayout()
        LmetaSample.addRow(QLabel('EXPERIMENT VARIABLES'))

        for ev in self.exp_labels:
            Evar = QLineEdit()
            # Evar.setMaximumWidth(160)
            LmetaSample.addRow(ev, Evar)
            self.exp_vars.append(Evar)

        LmetaGlovebox = QFormLayout()
        LmetaGlovebox.addRow(" ", QFrame())
        LmetaGlovebox.addRow(QLabel('GLOVEBOX VARIABLES'))
        for eb in self.glv_labels:
            Evar = QLineEdit()
            # Evar.setMaximumWidth(120)
            LmetaGlovebox.addRow(eb, Evar)
            self.glv_vars.append(Evar)
        self.com_labels = QTextEdit()
        self.com_labels.setMaximumHeight(50)
        self.com_labels.setMaximumWidth(120)
        LmetaGlovebox.addRow("Comments", self.com_labels)

        LextraButtons = QGridLayout()
        self.BsaveM = QToolButton()
        self.BloadM = QToolButton()
        self.Bsusi_intensity = QToolButton()
        self.Bsusi_off = QToolButton()
        self.Bsusi_on = QToolButton()
        self.Brecipe = QToolButton()
        self.BsaveM.setText("Save")
        self.BloadM.setText("Load")
        self.Bsusi_intensity.setText("Set")
        self.Bsusi_off.setText("Off")
        self.Bsusi_on.setText("On")
        self.Brecipe.setText("Recipe")
        self.BsaveM.setMaximumWidth(40)
        self.BloadM.setMaximumWidth(40)
        self.Bsusi_intensity.setMaximumWidth(40)
        self.Bsusi_off.setMaximumWidth(40)
        self.Bsusi_on.setMaximumWidth(40)

        LextraButtons.addWidget(QLabel(""), 0, 0)
        LextraButtons.addWidget(QLabel("Metadata:"), 0, 1)
        LextraButtons.addWidget(QLabel("SuSi Intensity:"), 1, 1, 1, 2)
        LextraButtons.addWidget(QLabel("SuSi Off:"), 2, 1)
        LextraButtons.addWidget(self.BsaveM, 0, 2)
        LextraButtons.addWidget(self.BloadM, 0, 3)
        LextraButtons.addWidget(self.Bsusi_intensity, 1, 3)
        LextraButtons.addWidget(self.Bsusi_on, 2, 2)
        LextraButtons.addWidget(self.Bsusi_off, 2, 3)
        LextraButtons.addWidget(self.Brecipe, 3, 3)

        # Position layouts inside the third vertical layout V3
        layV3.addItem(verticalSpacerV2)
        layV3.addLayout(LmetaSample)
        layV3.addItem(verticalSpacerV2)
        layV3.addLayout(LmetaGlovebox)
        layV3.addItem(verticalSpacerV2)
        layV3.addLayout(LextraButtons)
        layV3.addItem(verticalSpacerV2)

        # Add to main horizontal layout with a spacer (for good looks)
        horizontalSpacerH2 = QSpacerItem(30, 70, QSizePolicy.Minimum, QSizePolicy.Minimum)
        layH1.addItem(horizontalSpacerH2)
        layH1.addLayout(layV3, 2)

        # self.statusBar = QStatusBar()

        widget.setLayout(layH1)
        self.setCentralWidget(widget)
        self.show()
        # print(self.keithley.voltage)
        self.other_buttons = [self.for_bmL, self.rev_bmL, self.for_bmD, self.rev_bmD, self.four_wire,  # self.logyaxis,
                              self.BsaveM, self.BloadM, self.Bsusi_intensity]

        if not self.is_relay:
            self.multiplex.setChecked(False)
            self.multiplexing_allow()
            self.multiplex.setEnabled(False)
        else:
            self.is_multiplex = True

        if self.is_susi:
            self.susi_startup()
        else:
            self.disable_susi()

    def button_actions(self):
        self.folder = self.LEfolder.text()
        self.Bfolder.clicked.connect(self.select_folder)
        self.Bpath.clicked.connect(self.automatic_folder)
        self.BsaveM.clicked.connect(self.save_meta)
        self.BloadM.clicked.connect(self.load_meta)
        self.susiShutter.clicked.connect(self.susi_button)
        self.Bsusi_intensity.clicked.connect(self.susi_intensity_fix)
        self.BStart.clicked.connect(self.jv_start_stop)
        self.mppStart.clicked.connect(self.mpp_start_stop)
        self.logyaxis.stateChanged.connect(self.yaxis_to_log)
        self.four_wire.stateChanged.connect(self.two_four_wires_measurement)
        self.Bsusi_off.clicked.connect(self.susi_shutdown)
        self.Bsusi_on.clicked.connect(self.susi_startup)
        self.Brecipe.clicked.connect(self.recipe_popup)
        self.multiplex.stateChanged.connect(self.multiplexing_allow)

    def popup_message(self, text):
        qmes = QMessageBox.about(self, "Something happened...", text)

    def select_folder(self):
        old_folder = self.LEfolder.text()  # Read entry line

        if not old_folder:  # If empty, go to default
            old_folder = "C:/Data/"

        # Select directory from selection
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Where do you want your data saved?", old_folder)

        if not directory:  # if cancelled, keep the old one
            directory = old_folder

        self.LEfolder.setText(directory)
        self.folder = directory

        # Arrow function, to create folderpath with User and Date

    def automatic_folder(self):
        user = self.LEuser.text()
        folder = self.LEfolder.text()
        date = datetime.now().strftime("%Y%m%d")

        if len(user) > 0:
            newfolder = folder + user + "/" + date + "/"
        else:
            newfolder = folder + date

        self.LEfolder.setText(newfolder)
        self.folder = newfolder

        self.create_folder(False)

        self.Bpath.setEnabled(False)

    def create_folder(self, sample, retry=1):
        self.folder = self.LEfolder.text()
        if self.folder[-1] != "/":
            self.folder = self.folder + "/"  # Add "/" if non existent
            self.LEfolder.setText(self.folder)
        else:
            pass
        if sample:
            self.sample = self.LEsample.text()
            self.folder = self.folder + self.sample + "/"

            # If sample name is duplicated, make a "-d#" folder
            if os.path.exists(self.folder):
                self.folder = self.folder.rsplit("/", 1)[0] + "-d" + str(retry) + "/"
                if os.path.exists(self.folder):
                    retry += 1
                    self.create_folder(True, retry)
                self.statusBar().showMessage("Sample is duplicated", 10000)

        # If folders don't exist, make them
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
            self.statusBar().showMessage("Folder " + self.folder + " created", 5000)
        else:
            pass

    def save_meta(self):
        self.create_folder(False)
        self.gather_all_metadata()
        metadata = pd.DataFrame.from_dict(self.meta_dict, orient='index')
        metadata.to_csv(self.folder + "metadata.txt", header=False, sep="\t")
        self.statusBar().showMessage("Metadata file saved successfully", 5000)

    def load_meta(self):
        folder = self.LEfolder.text()
        metafile = QtWidgets.QFileDialog.getOpenFileName(self, "Choose your metadata file", folder)
        if metafile:
            metadata = pd.read_csv(metafile[0], header=None, index_col=0, nrows=21)
            # print(metadata)
            labels = self.setup_labs_jv + self.exp_labels
            objects = self.setup_vals_jv + self.exp_vars

        for cc, oo in enumerate(objects):
            if labels[cc] == "Sample":
                pass
            else:
                # print(cc, labels[cc])
                # print(metadata.loc[labels[cc]])
                oo.setText(metadata.loc[labels[cc]][1])

        # self.LEfolder.setText(metadata.loc["Folder"])

        self.statusBar().showMessage("Metadata successfully loaded", 5000)

    def gather_all_metadata(self):
        self.sample = self.LEsample.text()
        self.meta_dict = {}  # All variables will be collected here

        if not hasattr(self, "Rcurrent"):
            self.Rcurrent = 0
            self.RsunP = 0

        if not self.is_mpp_bool:
            all_metaD_labs = self.setup_labs_jv + self.exp_labels + self.glv_labels
            all_metaD_vals = self.setup_vals_jv + self.exp_vars + self.glv_vars

        else:
            all_metaD_labs = self.setup_labs_mpp + self.exp_labels + self.glv_labels
            all_metaD_vals = self.setup_vals_mpp + self.exp_vars + self.glv_vars

        # Add data to dictionary
        try:
            self.meta_dict["Date"] = strftime("%H:%M:%S - %d.%m.%Y", localtime(self.start_time))
        except:
            self.meta_dict["Date"] = strftime("%H:%M:%S - %d.%m.%Y", localtime(time()))
        self.meta_dict["Location"] = os.environ['COMPUTERNAME']
        try:
            self.meta_dict["Device"] = (self.spec.model + " - Serial No.:" + self.spec.serial_number)
        except:
            pass

        for cc, di in enumerate(all_metaD_labs):
            self.meta_dict[di] = all_metaD_vals[cc].text()

        self.meta_dict["Ref. Current(mA)"] = self.Rcurrent
        self.meta_dict["Sun%"] = self.RsunP

        # for cp,ad in enumerate(addit_labl):
        #     self.meta_dict[ad] = addit_data[cp]

        self.meta_dict[
            "Comments"] = self.com_labels.toPlainText()  # This field has a diffferent format than the others

    def two_four_wires_measurement(self):
        if self.four_wire.isChecked():
            self.keithley.wires = 4
        else:
            self.keithley.wires = 2
        # print(self.keithley.wires)

    def multiplexing_allow(self):
        fields = [self.area_a, self.area_b, self.area_c, self.area_d, self.area_e, self.area_f,
                  self.cell_a, self.cell_b, self.cell_c, self.cell_d, self.cell_e, self.cell_f]

        if self.multiplex.isChecked():
            self.is_multiplex = True
            for f in fields:
                f.setEnabled(True)
        else:
            self.is_multiplex = False
            for f in fields:
                f.setEnabled(False)
    def disable_susi(self):
        wi_dis = [self.susiShutter, self.for_bmD, self.rev_bmD, self.Bsusi_intensity, self.Bsusi_off, self.Bsusi_on]

        for wd in wi_dis:
            wd.setEnabled(False)

    def dis_enable_widgets(self, status, process):

        wi_dis = self.setup_vals_jv + self.setup_vals_mpp + self.other_buttons + \
                 [self.Bfolder, self.Bpath]#, self.refCurrent]

        self.dis_enable_starts(status, process)

        for wd in wi_dis:
            if status:
                wd.setEnabled(False)
                # self.is_meas_live = True
            else:
                wd.setEnabled(True)
                # self.is_meas_live = False

    def dis_enable_starts(self, status, process):
        if status:
            if process == "jv":
                self.mppStart.setEnabled(False)
                self.BStart.setText("S T O P")
                self.BStart.setStyleSheet("color : red;")
            else:
                self.BStart.setEnabled(False)
                self.mppStart.setText("S T O P")
                self.mppStart.setStyleSheet("color : red;")

        else:
            self.BStart.setEnabled(True)
            self.BStart.setText("START")
            self.BStart.setStyleSheet("color : green;")

            self.mppStart.setEnabled(True)
            self.mppStart.setText("START")
            self.mppStart.setStyleSheet("color : Blue;")

    def fix_jv_chars_for_save(self):
        names = ["Voc (V)", "Jsc (mA/cm2)", "FF (%)", "PCE (%)", "V_mpp (V)", "J_mpp (mA/cm2)", "P_mpp (mW/cm2)",
                 "R_series (Ohm cm2)", "R_shunt (Ohm cm2)", "Time"]
        names_f = [na.replace(" ", "") for na in names]
        # names_t = [na.replace(" ","\n") for na in names]
        # empty = ["","","","","","","","",""]

        self.jv_chars_results = self.jv_chars_results.T
        self.jv_chars_results.columns = names_f

    def jv_char_qtabledisplay(self):
        names = ["Voc (V)", "Jsc (mA/cm²)", "FF (%)", "PCE (%)", "V_mpp (V)", "J_mpp (mA/cm²)", "P_mpp (mW/cm²)",
                 "R_series (\U00002126cm²)", "R_shunt (\U00002126cm²)", "Time"]
        # names_f = [na.replace(" ","") for na in names] 
        names_t = [na.replace(" ", "\n") for na in names]
        values = self.jv_chars_results.T.copy()
        # print(values)
        values.columns = names_t
        for v in values.index:
            if "Dark" in v:
                values = values.drop(index=v, axis=1)
                self.jv_chars_results = self.jv_chars_results.drop(columns=v, axis=0)
            else:
                values.rename(index={v: v[:-6]}, inplace=True)
        self.model = TableModel(values)
        self.Lqtable.setModel(self.model)

    def vmpp_value_to_tracking(self):
        vmpp = round(self.jv_chars_results["V_mpp(V)"].iat[-1], 3)
        self.mpp_voltage.setText(str(vmpp))

    def check_filename(self, type, count=0):
        if type == "jv":
            tag = "JV_"
        elif type == "mpp":
            tag = "MPP_"
        else:
            tag = "Recipe_"

        file_name = self.folder + tag + self.sample + ".txt"

        while os.path.exists(file_name):
            count += 1

            file_name = self.folder + tag + self.sample + "-" + str(count) + ".txt"
            # print(file_name)
        else:
            return file_name

    def save_data(self):
        self.is_mpp_bool = False
        self.gather_all_metadata()

        metadata = pd.DataFrame.from_dict(self.meta_dict, orient='index')
        empty = pd.DataFrame(data={"": ["--"]})
        filename = self.check_filename("jv")
        # print("  " + filename)
        metadata.to_csv(filename, index=True, header=False, sep="\t")
        empty.to_csv(filename, mode="a", index=False, header=False, lineterminator='\n', sep="\t")
        self.jv_chars_results.T.to_csv(filename, mode="a", index=True, header=True, sep="\t")
        empty.to_csv(filename, mode="a", index=False, header=False, lineterminator='\n', sep="\t")
        self.curr_volt_results.to_csv(filename, mode="a", index=False, header=True, sep="\t")
        self.statusBar().showMessage("Data saved successfully", 5000)

    def save_mpp(self):
        self.is_mpp_bool = True
        self.gather_all_metadata()
        metadata = pd.DataFrame.from_dict(self.meta_dict, orient='index')
        mpp_data = pd.DataFrame({"Time (min)": self.mpp_time, "Hour":self.mpp_zeit, "Voltage (V)": self.res_mpp_voltage,
                                 "Current (mA/cm²)": self.mpp_current, "Power (mW/cm²)": self.mpp_power})

        filename = self.check_filename("mpp")

        metadata.to_csv(filename, header=False, sep="\t")
        mpp_data.to_csv(filename, mode="a", index=False, sep="\t")

        self.statusBar().showMessage("Data saved successfully", 5000)

        self.mpp_current = []
        self.res_mpp_voltage = []
        self.mpp_power = []

    def keithley_startup_setup(self):
        curr_limit = float(self.curr_lim.text())
        self.keithley.apply_voltage(compliance_current=curr_limit / 1000)
        self.keithley.measure_current(nplc=1, current=0.5, auto_range=True)

    def test_actual_current(self):
        self.keithley_startup_setup()
        ref = float(self.sun_ref.text())

        self.keithley.enable_source()
        self.keithley.source_voltage = 0.0
        QtTest.QTest.qWait(int(1 * 1000))
        self.Rcurrent = self.keithley.current * 1000
        self.RsunP = abs(self.Rcurrent / ref * 100)

        self.keithley.disable_source()

    def recipe_popup(self):
        text, ok = QInputDialog.getText(self, 'Make a Recipe', 'Use "F", "B" for Forward and Backward\n'
                                                               '  and "D", "L" for Dark and light\n'
                                                               '  separate with commas (,)\n'
                                                               '    e.g. BL,BL,BL,BD,...')
        if ok:
            self.recipe_measurement(text)


    def recipe_measurement(self,text):
        # TODO make a recipe
        self.is_recipe = True
        self.recipe_list = list(text.split(",")) #TODO make it fool proof
        self.is_meas_live = True

        self.create_folder(False)
        self.dis_enable_widgets(True, "jv")
        self.statusBar().showMessage("Measuring Recipe of "+str(len(self.recipe_list))+" steps: "+text)
        self.keithley.enable_source()
        self.fix_data_and_send_to_measure()
        try:
            self.fix_jv_chars_for_save()
            self.vmpp_value_to_tracking()
            self.save_data()
        except:
            pass

        self.susi_shutter_close()
        self.keithley.disable_source()
        self.dis_enable_widgets(False, "jv")
        self.popup_message("Recipe measurement done")
        self.is_recipe = False
        print(text)


    def jv_chars_calculation(self, volt, curr):
        # Find Isc (find voltage value closest to 0 Volts)
        volt = np.array(volt)
        curr = np.array(curr)

        # if reverse measurement, flip it around
        if volt[0] > volt[-1]:
            volt = np.flip(volt)
            curr = np.flip(curr)

        v0 = np.argmin(abs(volt))  # Find voltage closest to zero

        # Fit datapoint around Jsc to get Shunt(parallel) resistance
        reg_par = LinearRegression()
        co = 1 #Change here to increase number of fitted points (co=1 -> 3 points)
        try:
            v_par = volt[v0 - co: v0 + co].reshape(-1, 1)
            c_par = curr[v0 - co: v0 + co].reshape(-1, 1)
        except:
            v_par = volt[v0 : v0 + co].reshape(-1, 1)
            c_par = curr[v0 : v0 + co].reshape(-1, 1)

        reg_par.fit(v_par, c_par)
        m_i = reg_par.coef_[0][0]

        if volt[v0] <= 0.0001:  # If voltage is equal to zero
            isc = curr[v0]
        else:  # Otherwise calculate from slope
            b_i = -curr[v0] - m_i * volt[v0]
            isc = -b_i

        # For Voc, find closest current values to 0
        i1 = np.where(curr < 0, curr, -np.inf).argmax()
        i2 = np.where(curr > 0, curr, np.inf).argmin()

        c1 = curr[i1]
        c2 = curr[i2]

        # Get Voc by finding x-intercept (y=mx+b)
        v1 = volt[i1]
        v2 = volt[i2]
        m_v = (c2 - c1) / (v2 - v1)
        b_v = c1 - m_v * v1
        voc = -b_v / m_v

        # Calculate resistances, parallel and series
        r_par = abs(1 / m_i) * 1000 # 1000 factor to make it Ohms (since using mA)
        r_ser = abs(1 / m_v) * 1000

        # Find mpp values
        mpp = np.argmax(-volt * curr)

        mpp_v = volt[mpp]
        mpp_c = curr[mpp]
        mpp_p = mpp_v * mpp_c

        # Calculate FF
        ff = mpp_v * mpp_c / (voc * isc) * 100

        # Calculate PCE (this is wrong, it needs correct P_in)
        # pin = 75#mW/cm²
        pin = float(self.pow_dens.text())  # mW/cm²
        pce = abs(voc * isc * ff) / pin

        uhrzeit = strftime("%d.%m.%Y %H:%M:%S", gmtime())

        jv_char = [voc, isc, ff, pce, mpp_v, mpp_c, mpp_p, r_ser, r_par, uhrzeit]

        return jv_char

    def susi_button(self):
        if self.is_susi:
            answer = self.susim_check()
            if b"SHUTTER=0" in answer:
                self.susi_shutter_close()
            else:
                self.susi_shutter_open()

    def susi_status(self):
        answer = self.susim_check()
        print(answer)

    def susi_startup(self):
        # TODO if is_susi, add settings to save metadata
        if self.is_susi:
            self.susi.write(b'C1')  # Enable cooling
            QtTest.QTest.qWait(int(1 * 1000))
            self.susi.write(b'L1')  # Light On
            QtTest.QTest.qWait(int(2 * 1000))
            self.susi_startup_intensity()
            QtTest.QTest.qWait(int(1 * 1000))
            self.statusBar().showMessage("susi startup done", 3000)

    def susi_shutdown(self):
        reply = QMessageBox.question(self, 'Turn SuSi off', 'Are you sure you want to turn the SuSi off?',
                                     QMessageBox.Yes | QMessageBox.No)#, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.susi_shutter_close()
            QtTest.QTest.qWait(int(1 * 1000))
            self.susi.write(b'L0')  # Light Off
            QtTest.QTest.qWait(int(1 * 1000))

        else:
            pass

    def susi_startup_intensity(self, intensity=90.5):
        if self.is_susi:
            intensity = self.log_susi_open()
            self.set_intensity_susim(intensity)

    def susi_intensity_fix(self):
        if self.is_susi:
            self.susi_dialog()

            self.dlg.exec_()

    def susi_dialog(self):
        self.susi_shutter_open()
        self.dlg = QDialog()
        self.dlg.setWindowTitle("SuSi Intensity Set-up")

        # Set layout
        wid = QWidget()
        layout = QGridLayout()
        self.susi_intensity = QLineEdit()
        self.ref_area = QLineEdit()
        self.sun_ref = QLineEdit()
        self.Bsusi_set = QToolButton()
        self.Lcurrcurr = QLabel("")
        self.Bcurrtest = QToolButton()
        self.bstatus = QToolButton()
        self.bsave = QToolButton()
        self.bcancel = QToolButton()

        self.susi_intensity.setMaximumWidth(60)
        self.ref_area.setMaximumWidth(60)
        self.sun_ref.setMaximumWidth(60)
        self.Bsusi_set.setMaximumWidth(40)
        self.bstatus.setMaximumWidth(40)
        self.Bcurrtest.setMaximumWidth(40)
        self.bsave.setMaximumWidth(40)
        self.bcancel.setMaximumWidth(40)

        self.susi_intensity.setText(str(self.susi_percentage))
        self.ref_area.setText("1")
        self.sun_ref.setText("130.3")
        self.Bsusi_set.setText("Set")
        self.Bcurrtest.setText("Test")
        self.bstatus.setText("Status")
        self.bsave.setText("Save")
        self.bcancel.setText("Cancel")

        # Active widgets
        layout.addWidget(QLabel("Set Intensity (%):"), 0, 0)
        layout.addWidget(self.susi_intensity, 0, 1)
        layout.addWidget(self.Bsusi_set, 0, 2)
        layout.addWidget(QLabel("Range: 75-105%"), 1, 0)
        layout.addWidget(QLabel("Ref. cell area (cm²)"), 2, 0)
        layout.addWidget(self.ref_area, 2, 1)
        layout.addWidget(QLabel("Ref. current (mA)"), 3, 0)
        layout.addWidget(self.sun_ref, 3, 1)
        layout.addWidget(QLabel("Measure Ref:"), 4, 0)
        layout.addWidget(self.Lcurrcurr, 4, 1)
        layout.addWidget(self.Bcurrtest, 4, 2)
        layout.addWidget(self.bsave, 5, 0)
        layout.addWidget(self.bcancel, 5, 2)
        layout.addWidget(self.bstatus, 6, 0)

        self.dlg.setLayout(layout)

        self.bstatus.clicked.connect(self.susi_status)
        self.bcancel.clicked.connect(self.dialog_close)
        self.bsave.clicked.connect(self.dialog_save)
        self.Bsusi_set.clicked.connect(self.dialog_set_intensity)
        self.Bcurrtest.clicked.connect(self.dialog_test_current)

    def log_susi_open(self):
        logpath = "C:\\Data\\susi_log.txt"

        try:
            df = pd.read_csv(logpath, index_col=None)
        except:
            df = pd.DataFrame(columns=["Date", "Lamp Power(%)"])
            df = self.log_susi_newinput(90.5, df)
            df.to_csv(logpath, index=False, sep="\t")

        intensity = df["Lamp Power(%)"].iloc[-1]
        self.susi_percentage = intensity

        return intensity

    def log_susi_save(self, intensity):
        logpath = "C:\\Data\\susi_log.txt"

        df = pd.read_csv(logpath, index_col=None)
        df = self.log_susi_newinput(intensity, df)
        df.to_csv(logpath, index=False, sep="\t")

        return intensity

    def log_susi_newinput(self, power, dframe):
        now = localtime()
        date = strftime("%Y-%m-%d %H:%M:%S", now)

        # dframe.concat({"Date": time.strftime("%Y-%m-%d %H:%M:%S", now), "Lamp Power(%)": power}, ignore_index=True)
        dframe.loc[len(dframe.index)] = [date, power]

        return dframe

    def dialog_close(self):
        self.dlg.close()

    def dialog_save(self):
        intensity = self.susi_intensity.text()
        self.log_susi_save(intensity)
        self.susi_intensity.setText(intensity)
        self.popup_message("SuSi intensity saved in log file")

    def dialog_set_intensity(self):
        try:
            intensity = float(self.susi_intensity.text()) #Check if float
        except:
            intensity = 0

        if intensity > 105:
            int_val = 105
        elif intensity < 75:
            int_val = 75
        else:
            int_val = round(intensity, 1)

        self.susi_intensity.setText(str(int_val))
        self.set_intensity_susim(int_val)

        QtTest.QTest.qWait(int(3 * 1000))

    def set_intensity_susim(self, intensity):

        # print(intensity)
        # self.susi_start_intensity = int(intensity)
        intensity = int(intensity * 10)
        value = "{:04d}".format(intensity)
        message = "P=" + value
        print(message)

        self.susi.write(message.encode('utf-8'))  # Set light intensity

    def dialog_test_current(self):
        self.test_actual_current()

        self.Lcurrcurr.setText(str(round(self.Rcurrent, 2)) + " mA")

        ref_current = float(self.sun_ref.text())

        power = abs(round(float(self.Rcurrent) / ref_current * 100, 2))

        self.pow_dens.setText(str(power))

    def susim_check(self):
        if self.is_susi:
            self.susi.write(b'FS')  # Read data
            susi_ans = self.susi.read_until(b"END\r\n")

            return susi_ans

    def susi_shutter_open(self):
        if self.is_susi:
            self.susi.write(b'S0')  # Shutter Open
            self.susiShutter.setText("SuSi Shutter (Opened)")
            QtTest.QTest.qWait(int(3 * 1000))
            self.is_shutter_open = True

    def susi_shutter_close(self):
        if self.is_susi:
            self.susi.write(b'S1')  # Shutter Closed
            self.susiShutter.setText("SuSi Shutter (Closed)")
            QtTest.QTest.qWait(int(3 * 1000))
            self.is_shutter_open = False

    def namestr(self, obj, namespace):
        return [name for name in namespace if namespace[name] is obj]

    def fix_data_and_send_to_measure(self):
        self.reset_plot_jv()

        area = float(self.sam_area.text())
        volt_begin = float(self.volt_start.text())
        volt_end = float(self.volt_end.text())
        volt_step = float(self.volt_step.text())
        ap = int(self.ave_pts.text())
        time = float(self.set_time.text())

        self.res_fwd_curr = []
        self.res_fwd_volt = []
        self.res_bkw_curr = []
        self.res_bkw_volt = []

        forwa_vars = [volt_begin, volt_end + volt_step * 0.95, volt_step]
        rever_vars = [volt_end, volt_begin - volt_step * 0.95, -volt_step]
        fixed_vars = [time, ap, area]

        if self.is_recipe:
            meas_process = self.recipe_list

        else:
            check_box_buttons = [self.for_bmD, self.rev_bmD, self.for_bmL, self.rev_bmL]

            meas_process = []
            for ck, cbb in enumerate(check_box_buttons):
                if cbb.isChecked():
                    if ck == 0:
                        meas_process.append("FD")
                    elif ck == 1:
                        meas_process.append("RD")
                    elif ck == 2:
                        meas_process.append("FL")
                    else:
                        meas_process.append("RL")

        self.jv_chars_results = pd.DataFrame()
        self.curr_volt_results = pd.DataFrame()

        if self.is_multiplex:
            cell_list = [self.cell_a,self.cell_b,self.cell_c,self.cell_d,self.cell_e,self.cell_f]
            cell_name = ["a","b","c","d","e","f"]
        else:
            cell_list = [self.cell_g]
            cell_name = [""]
        while self.is_meas_live:
            if self.is_multiplex:
                for cn, cell in enumerate(cell_list):
                    if cell.isChecked():
                        self.relays[cn].on()
                        print("on ",cn,cell)
                        self.measurement_steps(meas_process,forwa_vars,rever_vars,fixed_vars, cell_name, cn,cell)
                        self.relays[cn].off()
                        print("off ",cn, cell)

            else:
                self.measurement_steps(meas_process,forwa_vars,rever_vars,fixed_vars, cell_name)

            self.is_meas_live = False
    def measurement_steps(self, meas_process,forwa_vars,rever_vars,fixed_vars, cell_name, cn=0,cell=""):
        # while self.is_meas_live:
        for ck, mpr in enumerate(meas_process):
            # print(mpr)
            self.is_first_plot = True
            if "D" in mpr:  # if it is a dark measurement
                if self.is_shutter_open:
                    self.susi_shutter_close()
                ilum = "Dark"
            else:
                if not self.is_shutter_open:
                    self.susi_shutter_open()
                ilum = "Light"

            if "F" in mpr:  # if it is forward
                direc = "Forward"
                all_vars = forwa_vars + fixed_vars + [ilum + direc]
            else:
                direc = "Reverse"
                all_vars = rever_vars + fixed_vars + [ilum + direc]

            # print(all_vars)
            volt, curr = self.curr_volt_measurement(all_vars, cn)

            if self.is_recipe:
                if not self.is_multiplex:
                    m_name = str(ck)
                else:
                    m_name = cell_name[cn] + "-" + str(ck)
                # rep_count += 1
            else:
                m_name = cell_name[cn]

            if self.is_meas_live:
                chars = self.jv_chars_calculation(volt, curr)
                self.jv_chars_results[m_name + "_" + direc + "_" + ilum] = chars
                self.jv_char_qtabledisplay()
            self.curr_volt_results["Voltage (V)_" + m_name + "_" + direc + "_" + ilum] = volt
            self.curr_volt_results["Current Density(mA/cm²)_" + m_name + "_" + direc + "_" + ilum] = curr

            # if self.is_multiplex:
            #     self.relays[cn].off()


    def display_live_voltage(self, value, live=True):
        if live:
            if abs(value) < 0.01:
                label = '{:.3e}'.format(value)
            else:
                label = '{:.3f}'.format(value)

            self.label_currvolt.setText("Live :   " + str(label) + "   V")

        else:
            self.label_currvolt.setText("")

    def display_live_current(self, value, live=True):
        if live:
            if abs(value) < 0.01:
                label = '{:.3e}'.format(value)
            else:
                label = '{:.3f}'.format(value)

            self.label_currcurr.setText("Live :   " + str(label) + "   mA/cm²")

        else:
            self.label_currcurr.setText("")

    def curr_volt_measurement(self, variables, counter):
        volt_0, volt_f, step, time_s, average_points, area, mode = variables

        current = []
        voltage = []

        for i in np.arange(volt_0, volt_f, step):
            meas_currents = []
            meas_voltages = []

            for t in range(average_points):
                self.keithley.source_voltage = i

                if self.is_meas_live:
                    QtTest.QTest.qWait(int(time_s * 1000))
                    meas_voltages.append(i)
                    meas_currents.append(self.keithley.current * 1000 / area)
                else:
                    meas_voltages.append(np.nan)
                    meas_currents.append(np.nan)
                    # pass

            ave_curr = np.mean(meas_currents)
            self.display_live_current(ave_curr)
            self.display_live_voltage(i)
            current.append(ave_curr)
            voltage.append(np.mean(meas_voltages))

            self.plot_jv(voltage, current, mode, counter)

        # jv_chars = self.jv_chars_calculation(voltage, current)
        self.display_live_current(ave_curr, False)
        self.display_live_voltage(0, False)

        return voltage, current

    def jv_start_stop(self):
        self.keithley_startup_setup()
        # toggle live
        if not self.is_meas_live:
            self.is_meas_live = True
            self.jv_process()
        else:
            self.is_meas_live=False

    def jv_process(self):
        # Reset values
        while self.is_meas_live:
            self.create_folder(False)
            self.dis_enable_widgets(True, "jv")
            self.statusBar().showMessage("Measuring JV curve")
            self.keithley.enable_source()
            self.fix_data_and_send_to_measure()
            try:
                self.fix_jv_chars_for_save()
                self.vmpp_value_to_tracking()
                self.save_data()
            except:
                pass

            self.susi_shutter_close()
            self.keithley.disable_source()
            self.dis_enable_widgets(False, "jv")
            self.popup_message("JV measurement done")


    def mpp_start_stop(self):
        self.keithley_startup_setup()
        # toggle live
        if not self.is_meas_live:
            self.is_meas_live = True
            self.mpp_process()
        else:
            self.is_meas_live = False

    def mpp_process(self):
        self.keithley_startup_setup()
        while self.is_meas_live:
            self.susi_shutter_open()
            self.reset_plot_mpp()
            self.create_folder(False)
            self.dis_enable_widgets(True, "mpp")
            self.keithley.enable_source()
            self.curr_volt_tracking()
            self.save_mpp()

            self.keithley.disable_source()
            self.susi_shutter_close()
            self.dis_enable_widgets(False, "mpp")

    def curr_volt_tracking(self):
        area = float(self.sam_area.text())

        mpp_total_time = float(self.mpp_ttime.text()) * 60
        mpp_int_time = float(self.mpp_inttime.text())
        mpp_step = float(self.mpp_stepSize.text())
        mpp_voltage = float(self.mpp_voltage.text())

        self.statusBar().showMessage("Tracking Maximum Power Point")

        self.mpp_current = []
        self.res_mpp_voltage = []
        self.mpp_power = []
        self.mpp_time = []
        self.mpp_zeit = []

        max_voltage = mpp_voltage
        time_c = time()

        # TODO mpp cell choose
        for i in np.arange(0, mpp_total_time / 3, mpp_int_time / 1000):
            voltage_test = [max_voltage - mpp_step, max_voltage, max_voltage + mpp_step]
            # print(voltage_test)
            mpp_test_current = []
            mpp_test_voltage = []
            mpp_test_power = []

            for v in voltage_test:
                if self.is_meas_live:
                    self.keithley.source_voltage = v
                    # Wait for stabilized measurement
                    QtTest.QTest.qWait(int(mpp_int_time))
                    # Measure current & voltage
                    m_current = self.keithley.current * 1000 / area
                    m_voltage = v  # self.keithley.voltage

                    mpp_test_current.append(m_current)
                    mpp_test_voltage.append(m_voltage)
                    mpp_test_power.append(abs(m_voltage * m_current))
                else:
                    mpp_test_current.append(np.nan)
                    mpp_test_voltage.append(np.nan)
                    mpp_test_power.append(np.nan)
                    break

            index_max = mpp_test_power.index(max(mpp_test_power))
            self.mpp_current.append(mpp_test_current[index_max])
            max_voltage = mpp_test_voltage[index_max]
            self.res_mpp_voltage.append(max_voltage)

            self.display_live_voltage(max_voltage)
            self.display_live_current(mpp_test_current[index_max])

            self.mpp_power.append(mpp_test_power[index_max])

            if i == 0:
                tc = time() - time_c
                elapsed_t = 0
            else:
                elapsed_t = (time() - time_c - tc)

            self.mpp_time.append(elapsed_t / 60)
            uhrzeit = strftime("%d.%m.%Y %H:%M:%S", gmtime())
            self.mpp_zeit.append(uhrzeit)
            try:
                self.plot_mpp()
            except:
                pass

            if elapsed_t > mpp_total_time:
                break

        self.display_live_current(0, False)
        self.display_live_voltage(0, False)

    def collect_all_values_iv(self, voltage=[], current=[]):
        # Gather all measurements till now
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
            volt = [-0.01, 0.01]
            curr = [-0.01, 0.01]

        volt = volt + voltage
        curr = curr + current

        # print(volt)
        # print(curr)

        return volt, curr

    def yaxis_to_log(self):
        if self.logyaxis.isChecked():
            self.canvas.axes.set_yscale('log')
        else:
            self.canvas.axes.set_yscale('linear')

        volta, curre = self.collect_all_values_iv()

        self.center_plot(volta, curre)

        self.canvas.draw_idle()

    def reset_plot_jv(self):
        self.canvas.axes.cla()
        self.canvas.axes.set_xlabel('Voltage (V)')
        self.canvas.axes.set_ylabel('Current density (mA/cm²)')
        self.canvas.axes.grid(True, linestyle='--')
        self.canvas.axes.set_xlim([-0.5, 2])
        self.canvas.axes.set_ylim([-25, 5])
        self.canvas.axes.axhline(0, color='black')
        self.canvas.axes.axvline(0, color='black')
        self._plot_ref = None

    def reset_plot_mpp(self):
        self.canvas.axes.cla()
        self.canvas.axes.set_xlabel('Time (min)')
        self.canvas.axes.set_ylabel('Power (mW/cm²)')
        self.canvas.axes.grid(True, linestyle='--')
        self.canvas.axes.set_xlim([0, 2])
        self.canvas.axes.set_ylim([5, 25])
        self.canvas.axes.axhline(0, color='black')
        self.canvas.axes.axvline(0, color='black')
        self._plot_ref = None

    def plot_jv(self, voltage, current, mode, counter):

        if counter == 0:
            colli ="#0000FF" #blue
            # collib = "#0000FF90"
            colda ="#0000FF55"
            # coldaf = "#0000FF45"
            name = "a_"
        elif counter == 1:
            colli = "#008000"  # green
            colda = "#00800055"
            name = "b_"
        elif counter == 2:
            colli = "#FF0000"  # red
            colda = "#FF000055"
            name = "c_"
        elif counter == 3:
            colli = "#00FFFF"  # cyan
            colda = "#00FFFF55"
            name = "d_"
        elif counter == 4:
            colli = "#FF00FF"  # magenta
            colda = "#FF00FF55"
            name = "e_"
        elif counter == 5:
            colli = "#964b00"  # yellow
            colda = "#964b0055"
            name = "f_"
        else:
            colli = "#000000"  # black
            colda = "#00000055"
            name = "g_"

        # Make plot
        if self.is_first_plot:
            if "Light" in mode:
                if "Forward" in mode:
                    # self._plot_ref = self.canvas.axes.plot(voltage, current, 'xb-', label=name+"Forward")
                    self._plot_ref = self.canvas.axes.plot(voltage, current, color=colli, linestyle="-",
                                                           marker = ".", label=name + "Forward")
                    self.is_first_plot = False
                else:
                    # self._plot_ref = self.canvas.axes.plot(voltage, current, '.r--', label=name+"Backward")
                    self._plot_ref = self.canvas.axes.plot(voltage, current, color=colli, linestyle="--",
                                                           marker = "x",label=name + "Backward")
                    self.is_first_plot = False
            else:
                if "Forward" in mode:
                    # self._plot_ref = self.canvas.axes.plot(voltage, current, linestyle='--',
                    #                                        marker='x', color='black', label=name+"Dark For")
                    self._plot_ref = self.canvas.axes.plot(voltage, current, linestyle='-.',
                                                           marker = ".",color=colda, label=name + "Dark For")
                    self.is_first_plot = False

                else:
                    # self._plot_ref = self.canvas.axes.plot(voltage, current, linestyle='--',
                    #                                        marker='.', color='grey', label=name+"Dark Back")
                    self._plot_ref = self.canvas.axes.plot(voltage, current, linestyle=':',
                                                           marker = "x",color=colda, label=name + "Dark Back")
                    self.is_first_plot = False

        else:
            if "Light" in mode:
                if "Forward" in mode:
                    # self.canvas.axes.plot(voltage, current, 'xb-')
                    self._plot_ref = self.canvas.axes.plot(voltage, current, marker = ".", color=colli, linestyle="-")
                else:
                    # self.canvas.axes.plot(voltage, current, '.r--')
                    self.canvas.axes.plot(voltage, current, marker = "x", color=colli, linestyle="--")
            else:
                if "Forward" in mode:
                    # self.canvas.axes.plot(voltage, current, linestyle='--', marker='x', color='black')
                    self._plot_ref = self.canvas.axes.plot(voltage, current, marker = ".", linestyle='-.',color=colda)
                else:
                    # self.canvas.axes.plot(voltage, current, linestyle='--', marker='.', color='grey')
                    self._plot_ref = self.canvas.axes.plot(voltage, current, marker = "x", linestyle=':',color=colda)

        self.canvas.axes.legend(fontsize="8")

        volt, curr = self.collect_all_values_iv(voltage, current)
        self.center_plot(volt, curr)

        # Draw plot
        self.canvas.draw_idle()

    def center_plot(self, voltage, current):
        if self.logyaxis.isChecked():
            current = [cu for cu in current if cu > 0]
            if len(current) == 0:
                current = [0]
        else:
            pass

        # Get min and max values to center plot
        if not voltage:
            min_x = -0.1
            max_x = 0.1
            min_y = -0.1
            max_y = 0.1
        else:
            min_x = np.min(voltage)
            max_x = np.max(voltage)
            min_y = np.min(current)
            max_y = np.max(current)

        ex = (max_x - min_x) * 0.05
        ey = (max_y - min_y) * 0.05

        room = 0.05

        try:
            if min_x != max_x:
                if self.logyaxis.isChecked():
                    try:
                        self.canvas.axes.set_ylim([min_y * 0.99, max_y + ey])
                    except:
                        self.canvas.axes.set_ylim([0, max_y + ey])
                else:
                    self.canvas.axes.set_ylim([min_y - ey, max_y + ey])
                self.canvas.axes.set_xlim([min_x - ex, max_x + ex])
            else:
                self.canvas.axes.set_ylim([min_y - room, max_y + room])
                self.canvas.axes.set_xlim([min_x - room, max_x + room])
        except:
            self.canvas.axes.set_ylim([-0.1, 0.1])
            self.canvas.axes.set_xlim([-0.1, 0.1])

    def plot_mpp(self):
        # Make plot
        if self._plot_ref is None:
            self._plot_ref = self.canvas.axes.plot(self.mpp_time, self.mpp_power, 'xb-', label="Power")

        else:
            self.canvas.axes.plot(self.mpp_time, self.mpp_power, 'xb-')

        # Get min and max values to center plot
        min_x = np.min(self.mpp_time)
        max_x = np.max(self.mpp_time)
        min_y = np.min(self.mpp_power)
        max_y = np.max(self.mpp_power)

        ex = (max_x - min_x) * 0.05
        ey = (max_y - min_y) * 0.05

        room = 0.05
        if min_x != max_x:
            self.canvas.axes.set_ylim([min_y - ey, max_y + ey])
            self.canvas.axes.set_xlim([min_x - ex, max_x + ex])
        else:
            self.canvas.axes.set_ylim([min_y - room, max_y + room])
            self.canvas.axes.set_xlim([min_x - room, max_x + room])

        # Draw plot
        self.canvas.draw_idle()

    def finished_plotting(self):
        self.statusBar().showMessage("Plotting process finished and images saved", 5000)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Window Close', 'Are you sure you want to close the window?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            print('Window closed')
            if self.keithley:
                self.keithley.disable_source()
            if self.is_susi:
                self.susi.close()
            # if True:
            #     k8090.__del__
            event.accept()

        else:
            event.ignore()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    app.exec_()
