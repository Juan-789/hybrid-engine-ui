# This Python file uses the following encoding: utf-8
import sys
import random
import ipaddress
from collections import namedtuple
from dataclasses import dataclass

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QTcpSocket, QAbstractSocket
from pyqtgraph import mkPen, PlotDataItem
import numpy as np

import packet_spec

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py
from ui_form import Ui_Widget

sim_is_running = False
i = 0
points = np.empty((0,2))

@dataclass
class PlotInfo:
    points: np.array
    data_line: PlotDataItem

class Widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)

        # Point numpy arrays for temperature, pressure and mass
        self.p1_points = np.empty((0,2))
        self.p2_points = np.empty((0,2))
        self.p3_points = np.empty((0,2))
        self.p4_points = np.empty((0,2))
        self.t1_points = np.empty((0,2))
        self.t2_points = np.empty((0,2))
        self.t3_points = np.empty((0,2))
        self.t4_points = np.empty((0,2))
        self.tank_mass_points = np.empty((0,2))
        self.engine_thrust_points = np.empty((0,2))

        # Plot data
        self.plots = {}

        # TCP socket
        self.padTCPSocket = QTcpSocket(self)
        self.padTCPSocket.connected.connect(self.on_connected)
        self.padTCPSocket.readyRead.connect(self.receive_socket_data)
        self.padTCPSocket.errorOccurred.connect(self.on_error)
        self.padTCPSocket.disconnected.connect(self.on_disconnected)

        # Graphing pens
        red_pen = mkPen("r")
        blue_pen = mkPen("g")
        green_pen = mkPen("b")
        pink_pen = mkPen("pink")

        # Set labels and create plot data for each graph
        # each entry in plots contains a PlotInfo dataclass consisting of points and data_line
        # points refers to the np array containing the data
        # data_line refers to the PlotDataItem object used to show data on the plots
        self.ui.pressurePlot.addLegend(offset=(0,0), colCount=4)
        self.ui.pressurePlot.setTitle("Pressure")
        self.ui.pressurePlot.setLabel("left", "Pressure (PSI)")
        self.ui.pressurePlot.setLabel("bottom", "Time")
        self.plots["p1"] = PlotInfo(self.p1_points, self.ui.pressurePlot.plot(self.p1_points, pen=red_pen, name="p1"))
        self.plots["p2"] = PlotInfo(self.p2_points, self.ui.pressurePlot.plot(self.p2_points, pen=blue_pen, name="p2"))
        self.plots["p3"] = PlotInfo(self.p3_points, self.ui.pressurePlot.plot(self.p3_points, pen=green_pen, name="p3"))
        self.plots["p4"] = PlotInfo(self.p4_points, self.ui.pressurePlot.plot(self.p4_points, pen=pink_pen, name="p4"))

        self.ui.temperaturePlot.addLegend(offset=(0,0), colCount=4)
        self.ui.temperaturePlot.setTitle("Temperature")
        self.ui.temperaturePlot.setLabel("left", "Temperature (°C)")
        self.ui.temperaturePlot.setLabel("bottom", "Time")
        self.plots["t1"] = PlotInfo(self.t1_points, self.ui.temperaturePlot.plot(self.t1_points, pen=red_pen, name="t1"))
        self.plots["t2"] = PlotInfo(self.t2_points, self.ui.temperaturePlot.plot(self.t2_points, pen=blue_pen, name="t2"))
        self.plots["t3"] = PlotInfo(self.t3_points, self.ui.temperaturePlot.plot(self.t3_points, pen=green_pen, name="t3"))
        self.plots["t4"] = PlotInfo(self.t4_points, self.ui.temperaturePlot.plot(self.t4_points, pen=pink_pen, name="t4"))

        self.ui.tankMassPlot.addLegend()
        self.ui.tankMassPlot.setTitle("Tank Mass")
        self.ui.tankMassPlot.setLabel("left", "Mass (Kg)")
        self.ui.tankMassPlot.setLabel("bottom", "Time")
        self.plots["tank_mass"] = PlotInfo(self.tank_mass_points, self.ui.tankMassPlot.plot(self.tank_mass_points, pen=red_pen))

        self.ui.engineThrustPlot.addLegend()
        self.ui.engineThrustPlot.setTitle("Engine Thrust")
        self.ui.engineThrustPlot.setLabel("left", "Thrust (KN)")
        self.ui.engineThrustPlot.setLabel("bottom", "Time")
        self.plots["engine_thrust"] = PlotInfo(self.engine_thrust_points, self.ui.engineThrustPlot.plot(self.engine_thrust_points, pen=red_pen))

        # QTimer for simulation, won't be needed once we can emulate
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self.generate_points)
        self.sim_timer.start(25)

        # Button handlers
        self.ui.simButton.clicked.connect(toggle_sim)
        self.ui.tcpConnectButton.clicked.connect(self.tcp_connection_button_handler)


    # Remove this too
    def generate_points(self):
        global i
        global sim_is_running
        if sim_is_running:
            if i >= 250:
                for key in self.plots:
                    self.plots[key].points = np.delete(self.plots[key].points, 0, 0)
            for key in self.plots:
                self.plots[key].points = np.append(self.plots[key].points, np.array([[i, random.randrange(1, 20)]]), axis=0)
                self.plots[key].data_line.setData(self.plots[key].points)
            i += 1

    def tcp_connection_button_handler(self):
        if self.padTCPSocket.state() == QAbstractSocket.SocketState.UnconnectedState:
            ip_addr = self.ui.ipAddressInput.text()
            port = self.ui.portInput.text()

            try:
                ipaddress.ip_address(ip_addr)
            except ValueError:
                self.ui.logOutput.append(f"IP address '{ip_addr}' is invalid")
                return

            try:
                port = int(port)
            except ValueError:
                self.ui.logOutput.append(f"Port '{port}' is invalid")
                return

            self.padTCPSocket.connectToHost(ip_addr, port)
        else:
            self.padTCPSocket.disconnectFromHost()

    # Any connection event should be handled here
    def on_connected(self):
        ip_addr: str = self.padTCPSocket.peerAddress()
        port: str = self.padTCPSocket.peerPort()
        self.ui.logOutput.append(f"Successfully connected to {ip_addr}:{port}")
        self.ui.tcpConnectButton.setText("Close TCP connection")
        self.ui.ipAddressInput.setReadOnly(True)
        self.ui.portInput.setReadOnly(True)

    # Any data received should be handled here
    def receive_socket_data(self):
        data = self.padTCPSocket.readAll().data()
        header_bytes = data[:2]
        message_bytes = data[2:]
        header = packet_spec.parse_packet_header(header_bytes)
        message = packet_spec.parse_packet_message(header, message_bytes)
        print(header)


    # Any errors with the socket should be handled here and logged
    def on_error(self, error):
        if self.padTCPSocket.errorString() == "The address is not available":
            self.ui.logOutput.append(f"Connection failed - {self.padTCPSocket.error()}: {self.padTCPSocket.errorString()}")
        else:
            self.ui.logOutput.append(f"{self.padTCPSocket.error()}: {self.padTCPSocket.errorString()}")
        # print(f"Error: {self.padTCPSocket.errorString()}")

    # Any disconnection event should be handled here and logged
    def on_disconnected(self):
        self.ui.logOutput.append("Socket connection was closed")
        self.ui.tcpConnectButton.setText("Create TCP connection")
        self.ui.ipAddressInput.setReadOnly(False)
        self.ui.portInput.setReadOnly(False)
        # print("Disconnected from server.")


    def update_ui(self):
        pass

    # Handles when the window is closed, have to make sure to disconnect the TCP socket
    def closeEvent(self, event):
        if self.padTCPSocket.state() == QAbstractSocket.SocketState.ConnectedState:
            self.padTCPSocket.disconnectFromHost()
            self.padTCPSocket.waitForDisconnected()
        event.accept()

# and this <3
def toggle_sim():
    global sim_is_running
    sim_is_running = not sim_is_running

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    sys.exit(app.exec())
