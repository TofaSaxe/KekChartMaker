import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy, QFileDialog
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
import pandas as pd
import matplotlib.dates as mdates
import numpy as np
import os

current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_script_dir))
crai_path = os.path.join(project_root, 'KekChartMaker')
sys.path.append(crai_path)

import convertor as cnv

class CustomNavigationToolbar(NavigationToolbar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("""
            NavigationToolbar2QT QToolButton {
                background: #333;
                border: 1px solid #666;
                color: white;
                border-radius: 4px;
            }
            NavigationToolbar2QT QToolButton:hover {
                background: #555;
            }
            NavigationToolbar2QT QToolButton:pressed {
                background: #777;
            }
        """)

class DynamicChart(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)

        self.data = None
        self.scalers = {}
        self.feature_buttons = {}

        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate()

    def scale_feature(self, feature, unit):
        """Scale the feature data based on its unit."""
        if unit in ['m³/h', 'kW', 'Celsius']:
            return self.data[feature]
        return self.data[feature]

    def set_y_axis_limits(self, feature, unit):
        """Set y-axis limits and tick spacing based on the feature and its unit."""
        if feature not in self.data.columns:
            return
        
        data = self.data[feature].dropna()  # Remove NaN values
        
        if data.empty:
            return
        
        min_val, max_val = data.min(), data.max()
        
        # Determine reasonable tick spacing
        if unit == 'm³/h':
            tick_interval = max(1, (max_val - min_val) / 10)
        elif unit == 'kW':
            tick_interval = max(10, (max_val - min_val) / 10)
        elif unit == 'Celsius':
            tick_interval = max(1, (max_val - min_val) / 10)
        else:
            tick_interval = max(1, (max_val - min_val) / 10)
        
        self.ax.set_ylim(min_val - tick_interval, max_val + tick_interval)
        self.ax.yaxis.set_major_locator(plt.MultipleLocator(tick_interval))

    def update_plot(self):
        """Update the plot with the loaded data and selected columns."""
        if self.data is None:
            return

        self.ax.clear()
        self.ax.set_xlabel('Datetime')
        self.ax.set_ylabel('Metrics')

        for feature, selected in self.feature_buttons.items():
            if selected:
                unit = self.get_feature_unit(feature)
                data = self.scale_feature(feature, unit)
                label = f'{feature} ({unit})' if unit != 'unknown' else feature
                self.ax.plot(self.x, data, label=label)
                self.set_y_axis_limits(feature, unit)

        if len(self.ax.lines) > 0:
            self.ax.legend(loc='upper left')

        self.draw()

    def get_feature_unit(self, feature):
        """Determine the unit for the feature."""
        units = {
            'm³/h': ['HM1_Flow', 'HM2_Flow'],
            'kW': ['HM1_Power', 'HM2_Power'],
            'Celsius': ['HM1_Inlet_Temp', 'HM1_Outlet_Temp', 'HM2_Inlet_Temp', 'HM2_Outlet_Temp']
        }
        for unit, features in units.items():
            if feature in features:
                return unit
        return 'unknown'
        
    def load_data(self, filepath, feature_buttons):
        """Load data from a CSV file and prepare it for plotting."""
        self.data = pd.read_csv(filepath, parse_dates=['datetime'])
        self.data.ffill(inplace=True)

        # No need to scale data since each feature has its own scale and range
        self.x = self.data['datetime']
        self.feature_buttons = feature_buttons
        self.update_plot()

    def set_features(self, features):
        """Set the features to be plotted based on selected buttons."""
        self.feature_buttons = features
        self.update_plot()

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.filepath = ''
        self.feature_states = {}  # Initialize here
        self.initUI()

    def initUI(self):
        self.setWindowTitle('KekChart')
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(840, 0, 1080, 720)
        self.setFixedSize(1080, 720)
        self.setWindowIcon(QIcon('data/icon.ico'))
        self.setup_background()

        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)

        main_layout = QVBoxLayout(self.main_widget)

        spacer = QSpacerItem(20, 75, QSizePolicy.Minimum, QSizePolicy.Fixed)
        main_layout.addItem(spacer)

        self.setup_buttons()  # Now feature_states is initialized

        self.dynamic_chart = DynamicChart(self.main_widget, width=5, height=3)
        main_layout.addWidget(self.dynamic_chart)

        self.toolbar = CustomNavigationToolbar(self.dynamic_chart, self)
        main_layout.addWidget(self.toolbar)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.move_start = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.move_start)

    def setup_background(self):
        label = QLabel(self)
        pixmap = QPixmap('data/background.png')
        label.setPixmap(pixmap)
        label.resize(1280, 720)

    def setup_buttons(self):
        button_style = "QPushButton {border-radius: 10px; background-color: #555; color: black;}"
        button_style += "QPushButton:pressed {background-color: #333;}"
        self.setup_feature_buttons(button_style)
        self.setup_import_button(button_style)

    def setup_feature_buttons(self, style):
        positions = {
            'SUM_Flow': (540, 40), 'HM1_Flow': (640, 40), 'HM1_Inlet_Temp': (740, 40), 'HM1_Outlet_Temp': (840, 40), 'HM1_Power': (940, 40), 
            'SUM_Power': (540, 75),'HM2_Flow': (640, 75), 'HM2_Inlet_Temp': (740, 75), 'HM2_Outlet_Temp': (840, 75), 'HM2_Power': (940, 75)
        }

        for feature, (x, y) in positions.items():
            btn = QPushButton(feature, self)
            btn.setObjectName(feature)
            btn.setStyleSheet(style)
            btn.setFlat(True)
            btn.move(x, y)
            btn.clicked.connect(lambda ch, f=feature: self.on_feature_button_click(f))
            self.feature_states[feature] = False

    def setup_import_button(self, style):
        btn = QPushButton('Import', self)
        btn.setStyleSheet(style)
        btn.setFlat(True)
        btn.move(20, 40)
        btn.clicked.connect(self.on_import_button_click)

    def on_import_button_click(self):
        """Handle import button click."""
        self.filepath, _ = QFileDialog.getOpenFileName(self, "Select CSV or TXT File")
        cnv.convert(self.filepath)
        self.filepath = 'InitialTable/ConvertedData.csv'
        if self.filepath:
            self.dynamic_chart.load_data(self.filepath, self.feature_states)

    def on_feature_button_click(self, feature):
        """Handle feature button click events."""
        if feature in self.feature_states:
            # Toggle the feature state
            self.feature_states[feature] = not self.feature_states[feature]
            
            # Find the button and update its style
            btn = self.findChild(QPushButton, feature)
            if btn:
                color = "#333" if self.feature_states[feature] else "#555"
                btn.setStyleSheet(f'QPushButton {{background-color: {color}; border-radius: 10px;}}')
            
            # Update the chart with the new feature states
            self.dynamic_chart.set_features(self.feature_states)
        else:
            print(f"Feature '{feature}' not found in feature states.")
            print(self.feature_states)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = App()
    main.show()
    sys.exit(app.exec_())
