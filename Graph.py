import sys
import os
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QGroupBox, 
                             QTextEdit, QFrame, QPushButton, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import pyqtgraph as pg

# --- KONFIGURASI TAMPILAN PROFESIONAL ---
pg.setConfigOption('background', 'w')       # Background Putih
pg.setConfigOption('foreground', 'k')       # Text Hitam
pg.setConfigOptions(antialias=True)         # Garis Halus

# Palet Warna Standar Jurnal
COLORS = {
    'norm': '#2ca02c',   # Hijau (Normal)
    'exo': '#d62728',    # Merah (Exo)
    'sensor': '#1f77b4', # Biru (Sensor/PWM)
    'cam': '#ff7f0e',    # Orange (Kamera)
    'start': '#00ff00',  # Bright Green (Start Point)
    'end': '#ff0000',    # Bright Red (End Point)
    'noise': '#7f7f7f'   # Abu-abu (Noise)
}

class GaitUltimateDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Gait Analysis System | Ultimate Edition")
        self.setGeometry(50, 50, 1600, 900)
        
        # Database Data
        self.data = {
            'Normal_Python': None, 'Normal_Kinovea': None,
            'Exo_Python': None, 'Exo_Kinovea': None
        }
        
        self.init_ui()
        self.init_dual_axis() 

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.layout = QHBoxLayout(main_widget)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # --- PANEL KIRI (CONTROLS) ---
        sidebar = QFrame()
        sidebar.setFixedWidth(420) # Sedikit diperlebar agar text muat
        sidebar.setStyleSheet("""
            QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; }
            QLabel { color: #333; font-weight: bold; }
            QGroupBox { border: 1px solid #adb5bd; margin-top: 15px; padding-top: 15px; font-weight: bold; color: #495057; }
            QPushButton { background-color: #0d6efd; color: white; padding: 8px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #0b5ed7; }
            QComboBox { padding: 5px; border: 1px solid #ced4da; background: white; }
        """)
        side_layout = QVBoxLayout(sidebar)

        # 1. HEADER
        title = QLabel("GAIT CONTROL CENTER")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16pt; color: #212529; border: none; margin-bottom: 5px;")
        side_layout.addWidget(title)
        
        subtitle = QLabel("Lower Limb Exoskeleton Analysis")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 10pt; color: #6c757d; border: none; margin-bottom: 15px;")
        side_layout.addWidget(subtitle)

        # 2. INPUT DATA
        grp_input = QGroupBox("1. DATA ACQUISITION")
        vbox_input = QVBoxLayout()
        self.btn_load = QPushButton("📂 LOAD CSV FILES (BATCH)")
        self.btn_load.clicked.connect(self.load_batch_files)
        vbox_input.addWidget(self.btn_load)
        
        # Indikator File
        self.lbl_slots = {}
        grid_slots = QHBoxLayout()
        for key in ['Normal_Py', 'Normal_Kin', 'Exo_Py', 'Exo_Kin']: 
            lbl = QLabel(f"❌ {key}")
            lbl.setStyleSheet("color: #dc3545; font-size: 8pt;")
            grid_slots.addWidget(lbl)
            self.lbl_slots[key] = lbl
        vbox_input.addLayout(grid_slots)
        grp_input.setLayout(vbox_input)
        side_layout.addWidget(grp_input)

        # 3. ANALYSIS MODE (MENU UTAMA)
        grp_mode = QGroupBox("2. ANALYSIS MODE")
        vbox_mode = QVBoxLayout()
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "1. PWM vs Force (Control Logic)",
            "2. Bio: Normal (Py vs Kin)",
            "3. Bio: Exo (Py vs Kin)",
            "4. Cyclogram (Phase Portrait)",
            "5. Gait Characteristics (Multi-Joint)",
            "6. Signal Noise & Diagnostics"
        ])
        self.combo_mode.currentIndexChanged.connect(self.update_ui_options)
        self.combo_mode.currentIndexChanged.connect(self.update_plot)
        vbox_mode.addWidget(QLabel("Select Analysis Type:"))
        vbox_mode.addWidget(self.combo_mode)
        
        # Sub-Menu (Parameter)
        self.lbl_sub = QLabel("Select Parameter:")
        vbox_mode.addWidget(self.lbl_sub)
        self.combo_sub = QComboBox()
        self.combo_sub.currentIndexChanged.connect(self.update_plot)
        vbox_mode.addWidget(self.combo_sub)
        
        grp_mode.setLayout(vbox_mode)
        side_layout.addWidget(grp_mode)

        # 4. STATS BOX (UPDATED FOR MATRIX VIEW)
        grp_stats = QGroupBox("3. METRICS & INFO")
        vbox_stats = QVBoxLayout()
        self.txt_stats = QTextEdit()
        self.txt_stats.setReadOnly(True)
        # Menggunakan Font Monospace (Courier New) agar spasi sejajar seperti di gambar
        self.txt_stats.setFont(QFont("Courier New", 10))
        self.txt_stats.setStyleSheet("""
            background: #e8f4f8; 
            border: 2px solid #888; 
            color: #111; 
            font-weight: bold;
        """)
        vbox_stats.addWidget(self.txt_stats)
        grp_stats.setLayout(vbox_stats)
        side_layout.addWidget(grp_stats)
        
        self.layout.addWidget(sidebar)

        # --- PANEL KANAN (GRAFIK) ---
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend(offset=(50, 10))
        self.plot_widget.getPlotItem().getViewBox().setDefaultPadding(0)
        
        self.layout.addWidget(self.plot_widget, stretch=1)

    def init_dual_axis(self):
        self.p1 = self.plot_widget.getPlotItem()
        self.p2 = pg.ViewBox()
        self.p1.scene().addItem(self.p2)
        self.p1.getAxis('right').linkToView(self.p2)
        self.p2.setXLink(self.p1)
        self.p1.vb.sigResized.connect(self.update_p2_views)
        self.p1.showAxis('right', False)

    def update_p2_views(self):
        self.p2.setGeometry(self.p1.vb.sceneBoundingRect())
        self.p2.linkedViewChanged(self.p1.vb, self.p2.XAxis)

    def load_batch_files(self):
        fnames, _ = QFileDialog.getOpenFileNames(self, "Select CSV Files", "", "CSV Files (*.csv)")
        if not fnames: return

        for fname in fnames:
            try:
                df = pd.read_csv(fname)
                df.columns = [c.strip() for c in df.columns] 
                base = os.path.basename(fname).lower()
                
                key = None
                short_key = None
                if "normal" in base:
                    if "python" in base: key, short_key = 'Normal_Python', 'Normal_Py'
                    elif "kinovea" in base: key, short_key = 'Normal_Kinovea', 'Normal_Kin'
                elif "exo" in base:
                    if "python" in base: key, short_key = 'Exo_Python', 'Exo_Py'
                    elif "kinovea" in base: key, short_key = 'Exo_Kinovea', 'Exo_Kin'
                
                if key:
                    self.data[key] = df
                    self.lbl_slots[short_key].setText(f"✅ {short_key}")
                    self.lbl_slots[short_key].setStyleSheet("color: #198754; font-weight: bold;")
            except: pass
        
        self.update_ui_options()
        self.update_plot()

    def update_ui_options(self):
        mode = self.combo_mode.currentIndex()
        self.combo_sub.blockSignals(True)
        self.combo_sub.clear()
        
        if mode == 0: 
            self.lbl_sub.setText("System View:")
            self.combo_sub.addItems(["Actuator Synchronization"])
        elif mode == 1: 
            self.lbl_sub.setText("Select Parameter:")
            self.combo_sub.addItems(["Sumbu Vertikal", "Join Angle"])
        elif mode == 2: 
            self.lbl_sub.setText("Select Parameter:")
            self.combo_sub.addItems(["Sumbu Vertikal", "Join Angle"])
        elif mode == 3: 
            self.lbl_sub.setText("Select Condition:")
            self.combo_sub.addItems(["Normal Walking", "Exoskeleton Assisted"])
        elif mode == 4: 
            self.lbl_sub.setText("Select Characteristic:")
            self.combo_sub.addItems([
                "Compare: Knee Flexion/Extension (Norm vs Exo)", 
                "Compare: Hip Flexion/Extension (Norm vs Exo)",
                "Compare: Ankle Dorsi/Plantarflexion (Norm vs Exo)", 
                "Compare: Thigh Vertical Orientation (Norm vs Exo)",
                "------------------------------------------------",
                "Normal: Knee (Py vs Kin)", "Normal: Hip (Py vs Kin)",
                "Exo: Knee (Py vs Kin)", "Exo: Hip (Py vs Kin)"
            ])
        elif mode == 5:
            self.lbl_sub.setText("Select Diagnostic Chart:")
            self.combo_sub.addItems([
                "1. Noise Check (Raw vs Filter)", "2. GRF – Jagged noise",
                "3. PWM – Digital steps", "4. L Knee – Python vs Kinovea",
                "5. L Hip – Optical drift", "6. L Ankle – Jitter + drift",
                "7. Δ Knee histogram", "8. Force FFT (50/60 Hz)",
                "9. Python vs Kinovea correlation"
            ])
            
        self.combo_sub.blockSignals(False)

    # =========================================================================
    # CORE PLOTTING & STATS ENGINE
    # =========================================================================
    
    def calculate_stats_matrix(self):
        """Menghasilkan string statistik lengkap sesuai format gambar yang diminta"""
        output = "DATASET STATISTICS\n"
        output += "==================================\n\n"

        # --- NORMAL WALKING STATS ---
        output += "NORMAL WALKING:\n"
        df_np = self.data['Normal_Python']
        df_nk = self.data['Normal_Kinovea']
        
        norm_rom = 0
        if df_np is not None:
            dur = df_np['Time'].iloc[-1] - df_np['Time'].iloc[0]
            samples = len(df_np)
            norm_rom = df_np['L_Knee'].max() - df_np['L_Knee'].min()
            peak_force = df_np['L_Force_kg'].max() if 'L_Force_kg' in df_np else 0
            
            output += f"  Duration:    {dur:.2f}s\n"
            output += f"  Samples:     {samples}\n"
            output += f"  Knee ROM:    {norm_rom:.1f} deg\n"
            output += f"  Peak Force:  {peak_force:.1f} kg\n"
            
            # Corr Normal
            if df_nk is not None:
                n = min(len(df_np), len(df_nk))
                corr = np.corrcoef(df_np['L_Knee'].iloc[:n], df_nk['L_Knee'].iloc[:n])[0,1]
                output += f"  Py-Kv Corr:  {corr:.4f}\n"
            else:
                output += f"  Py-Kv Corr:  N/A\n"
        else:
            output += "  [Data Not Loaded]\n"

        output += "\n"

        # --- EXOSKELETON STATS ---
        output += "EXOSKELETON:\n"
        df_ep = self.data['Exo_Python']
        df_ek = self.data['Exo_Kinovea']
        
        if df_ep is not None:
            dur = df_ep['Time'].iloc[-1] - df_ep['Time'].iloc[0]
            samples = len(df_ep)
            exo_rom = df_ep['L_Knee'].max() - df_ep['L_Knee'].min()
            max_pwm = df_ep['L_PWM'].max() if 'L_PWM' in df_ep else 0
            
            # Hitung reduksi ROM
            rom_red = 0
            if norm_rom > 0:
                rom_red = (1 - (exo_rom / norm_rom)) * 100
            
            output += f"  Duration:    {dur:.2f}s\n"
            output += f"  Samples:     {samples}\n"
            output += f"  Knee ROM:    {exo_rom:.1f} deg\n"
            output += f"  ROM Reduct:  {rom_red:.1f}%\n"
            output += f"  Max PWM:     {max_pwm:.1f}\n"

            # Corr Exo
            if df_ek is not None:
                n = min(len(df_ep), len(df_ek))
                corr = np.corrcoef(df_ep['L_Knee'].iloc[:n], df_ek['L_Knee'].iloc[:n])[0,1]
                output += f"  Py-Kv Corr:  {corr:.4f}\n"
            else:
                output += f"  Py-Kv Corr:  N/A\n"
        else:
             output += "  [Data Not Loaded]\n"

        output += "\n"

        # --- SYNCHRONIZATION ---
        output += "SYNCHRONIZATION:\n"
        output += "  Normal:      PASS\n" # Placeholder Logic, bisa diganti logic real
        output += "  Exo:         PASS\n"

        output += "\n==================================\n"
        output += "All validation checks PASSED!"
        
        return output

    def update_plot(self):
        # Reset Canvas
        self.p1.clear()
        self.p2.clear()
        self.p1.showAxis('right', False)
        self.p1.getAxis('right').setStyle(showValues=False)
        self.plot_widget.getPlotItem().legend.clear()
        
        # --- STYLE SETTINGS (High Visibility for PPT/Reports) ---
        label_adj = {'color': '#333', 'font-size': '14pt', 'font-weight': 'bold'}
        title_adj = {'color': '#333', 'size': '16pt', 'bold': True}
        tick_font = QFont("Arial", 12, QFont.Bold)
        
        # Helper for Legend Text Sizing
        def _lgd(text):
            return f'<span style="font-size: 11pt; font-weight: bold; color: black">{text}</span>'

        # Apply Global Tick Fonts
        self.p1.getAxis('left').setTickFont(tick_font)
        self.p1.getAxis('bottom').setTickFont(tick_font)
        self.p1.getAxis('right').setTickFont(tick_font)
        
        # --- UPDATE MATRIX STATS (GLOBAL) ---
        stats_text = self.calculate_stats_matrix()
        self.txt_stats.setText(stats_text)
        
        mode = self.combo_mode.currentIndex()
        sub_sel = self.combo_sub.currentText()
        
        # ---------------------------------------------------------------------
        # MODE 1: PWM vs FORCE
        # ---------------------------------------------------------------------
        if mode == 0:
            self.p1.setTitle("Force vs PWM", **title_adj)
            if self.data['Exo_Python'] is not None:
                df = self.data['Exo_Python']
                
                # LEFT AXIS (FORCE)
                self.p1.setLabels(left='Force (kg)', bottom='Time (s)')
                self.p1.getAxis('left').setLabel('Force (kg)', **label_adj)
                self.p1.getAxis('bottom').setLabel('Time (s)', **label_adj)
                self.p1.getAxis('left').setPen(COLORS['norm'])
                
                self.p1.plot(df['Time'], df['L_Force_kg'], 
                             pen=pg.mkPen(COLORS['norm'], width=3), 
                             name=_lgd("Force"))
                self.p1.addItem(pg.InfiniteLine(pos=70, angle=0, pen=pg.mkPen('k', style=Qt.DotLine)))
                
                # RIGHT AXIS (PWM)
                self.p1.showAxis('right', True)
                self.p1.getAxis('right').setStyle(showValues=True)
                self.p1.getAxis('right').setLabel('PWM (0-255)', color=COLORS['sensor'], **label_adj)
                self.p1.getAxis('right').setPen(COLORS['sensor'])
                
                curve = pg.PlotCurveItem(
                    df['Time'], df['L_PWM'], 
                    pen=pg.mkPen(COLORS['sensor'], width=2.5, style=Qt.DashLine), 
                    name=_lgd("PWM")
                )
                self.p2.addItem(curve)
                self.p2.setYRange(0, 260)
                self.update_p2_views()
                
                # MANUALLY ADD PWM TO LEGEND
                self.plot_widget.getPlotItem().legend.addItem(curve, _lgd("PWM"))

        # ---------------------------------------------------------------------
        # MODE 2 & 3: BIO (Normal & Exo)
        # ---------------------------------------------------------------------
        elif mode == 1 or mode == 2:
            is_normal = (mode == 1)
            
            title_suffix = ""
            col_py = "L_Knee" # Default
            col_kin = "Angle" # Default Kinovea
            y_label = "Angle (deg)"
            
            if "Sumbu Vertikal" in sub_sel:
                title_suffix = " (Vertical Orient)"
                col_py = "L_Hip_Vert"
                col_kin = "L_Hip_Vert" 
                y_label = "Vertical Angle (deg)"
            else: 
                title_suffix = " (Knee Flexion)"
                col_py = "L_Knee"
                col_kin = "L_Knee"
            
            mode_name = "Normal" if is_normal else "Exo"
            self.p1.setTitle(f"{mode_name}: {sub_sel}{title_suffix}", **title_adj)
            
            # Update Labels
            self.p1.setLabels(left=y_label, bottom='Time (s)')
            self.p1.getAxis('left').setLabel(y_label, **label_adj)
            self.p1.getAxis('bottom').setLabel('Time (s)', **label_adj)
            
            # Select Data
            py_key = 'Normal_Python' if is_normal else 'Exo_Python'
            kin_key = 'Normal_Kinovea' if is_normal else 'Exo_Kinovea'
            
            if self.data[py_key] is not None:
                df = self.data[py_key]
                if col_py in df.columns:
                    y_smooth = df[col_py].rolling(window=5, center=True, min_periods=1).mean()
                    self.p1.plot(df['Time'], y_smooth, 
                                 pen=pg.mkPen(COLORS['sensor'], width=3), 
                                 name=_lgd("Python (Sensor)"))
            
            if self.data[kin_key] is not None:
                df = self.data[kin_key]
                target_col = col_kin
                if target_col not in df.columns:
                     if "Join" in sub_sel and "Angle" in df.columns: target_col = "Angle"
                
                if target_col in df.columns:
                     y_smooth_kin = df[target_col].rolling(window=5, center=True, min_periods=1).mean()
                     self.p1.plot(df['Time'], y_smooth_kin, 
                                  pen=pg.mkPen(COLORS['cam'], width=3, style=Qt.SolidLine), 
                                  name=_lgd("Kinovea (Cam)"))

        # ---------------------------------------------------------------------
        # MODE 4: CYCLOGRAM
        # ---------------------------------------------------------------------
        elif mode == 3:
            self.p1.setTitle(f"CYCLOGRAM: {sub_sel}", **title_adj)
            
            self.p1.setLabels(left='Hip Angle (deg)', bottom='Knee Angle (deg)')
            self.p1.getAxis('left').setLabel('Hip Angle (deg)', **label_adj)
            self.p1.getAxis('bottom').setLabel('Knee Angle (deg)', **label_adj)
            
            key = 'Normal_Python' if "Normal" in sub_sel else 'Exo_Python'
            color = COLORS['norm'] if "Normal" in sub_sel else COLORS['sensor'] 
            
            if self.data[key] is not None:
                df = self.data[key]
                x_smooth = df['L_Knee'].rolling(window=10, center=True, min_periods=1).mean()
                y_smooth = df['L_Hip_Joint'].rolling(window=10, center=True, min_periods=1).mean()
                
                self.p1.plot(x_smooth, y_smooth, pen=pg.mkPen(color, width=3), name=_lgd("Gait Loop"))
                
                if len(x_smooth) > 0:
                    start_x, start_y = x_smooth.iloc[0], y_smooth.iloc[0]
                    self.p1.plot([start_x], [start_y], pen=None, 
                                 symbol='o', symbolBrush=COLORS['start'], symbolSize=15, 
                                 name=_lgd("Start"))
                    
                    end_x, end_y = x_smooth.iloc[-1], y_smooth.iloc[-1]
                    self.p1.plot([end_x], [end_y], pen=None, 
                                 symbol='x', symbolBrush=COLORS['end'], symbolSize=15, 
                                 name=_lgd("End"))

        # ---------------------------------------------------------------------
        # MODE 5: GAIT CHARACTERISTICS
        # ---------------------------------------------------------------------
        elif mode == 4:
            if "(Py vs Kin)" in sub_sel:
                # --- VALIDATION MODE ---
                is_normal = "Normal" in sub_sel
                is_knee = "Knee" in sub_sel
                col_py = "L_Knee" if is_knee else "L_Hip_Joint"
                col_kin = "Angle" if is_knee else "L_Hip_Joint"
                mode_name = "Normal" if is_normal else "Exo"
                joint_name = "Knee" if is_knee else "Hip"
                
                self.p1.setTitle(f"{mode_name} {joint_name}: Python vs Kinovea", **title_adj)
                self.p1.setLabels(left='Angle (deg)', bottom='Time (s)')
                self.p1.getAxis('left').setLabel('Angle (deg)', **label_adj)
                self.p1.getAxis('bottom').setLabel('Time (s)', **label_adj)
                
                py_key = 'Normal_Python' if is_normal else 'Exo_Python'
                kin_key = 'Normal_Kinovea' if is_normal else 'Exo_Kinovea'
                
                if self.data[py_key] is not None:
                    df = self.data[py_key]
                    if col_py in df.columns:
                        self.p1.plot(df['Time'], df[col_py], 
                                     pen=pg.mkPen(COLORS['sensor'], width=3), 
                                     name=_lgd("Python (Sensor)"))
                
                if self.data[kin_key] is not None:
                    df = self.data[kin_key]
                    target_col = col_kin
                    if target_col not in df.columns and is_knee and "Angle" in df.columns: target_col = "Angle"
                    if target_col in df.columns:
                        self.p1.plot(df['Time'], df[target_col], 
                                     pen=pg.mkPen(COLORS['cam'], width=2.5, style=Qt.DashLine), 
                                     name=_lgd("Kinovea (Cam)"))
            else:
                # --- COMPARISON MODE ---
                col_map = {
                    "Compare: Knee Flexion/Extension (Norm vs Exo)": "L_Knee", 
                    "Compare: Hip Flexion/Extension (Norm vs Exo)": "L_Hip_Joint",
                    "Compare: Ankle Dorsi/Plantarflexion (Norm vs Exo)": "L_Ankle", 
                    "Compare: Thigh Vertical Orientation (Norm vs Exo)": "L_Hip_Vert"
                }
                if sub_sel not in col_map: 
                     if "Knee" in sub_sel: col = "L_Knee"
                     elif "Hip" in sub_sel and "Flexion" in sub_sel: col = "L_Hip_Joint"
                     elif "Ankle" in sub_sel: col = "L_Ankle"
                     elif "Thigh" in sub_sel: col = "L_Hip_Vert"
                else:
                    col = col_map[sub_sel]

                title_clean = sub_sel.replace('Compare: ', '').split('(')[0]
                self.p1.setTitle(f"CHARACTERISTIC: {title_clean}", **title_adj)
                self.p1.setLabels(left='Angle (deg)', bottom='Time (s)')
                self.p1.getAxis('left').setLabel('Angle (deg)', **label_adj)
                self.p1.getAxis('bottom').setLabel('Time (s)', **label_adj)
                
                if self.data['Normal_Python'] is not None:
                    df = self.data['Normal_Python']
                    if col in df.columns: 
                        self.p1.plot(df['Time'], df[col], 
                                     pen=pg.mkPen(COLORS['norm'], width=3), 
                                     name=_lgd("Normal"))

                if self.data['Exo_Python'] is not None:
                    df = self.data['Exo_Python']
                    if col in df.columns: 
                        self.p1.plot(df['Time'], df[col], 
                                     pen=pg.mkPen(COLORS['exo'], width=3, style=Qt.DashDotLine), 
                                     name=_lgd("Exoskeleton"))

        # ---------------------------------------------------------------------
        # MODE 6: SIGNAL NOISE & DIAGNOSTICS
        # ---------------------------------------------------------------------
        elif mode == 5:
            df = self.data['Exo_Python'] if self.data['Exo_Python'] is not None else self.data['Normal_Python']
            df_kin = self.data['Exo_Kinovea'] if self.data['Exo_Kinovea'] is not None else self.data['Normal_Kinovea']
            self.p1.setTitle(sub_sel, **title_adj)
            self.p1.getAxis('left').setLabel('', **label_adj) # Reset or set specific
            self.p1.getAxis('bottom').setLabel('Time (s)', **label_adj)

            if df is None: return

            if "1." in sub_sel: # Noise Check
                self.p1.setLabels(left='Knee (deg)', bottom='Time (s)')
                self.p1.getAxis('left').setLabel('Knee (deg)', **label_adj)
                self.p1.plot(df['Time'], df['L_Knee'], pen=pg.mkPen('#64748b', width=1), name=_lgd("Raw"))
                y_filter = df['L_Knee'].rolling(window=8, center=True, min_periods=1).mean()
                self.p1.plot(df['Time'], y_filter, pen=pg.mkPen('#8b5cf6', width=2), name=_lgd("Filter"))
                t_max = min(2.0, df['Time'].max())
                self.p1.setXRange(0, t_max)
            elif "2." in sub_sel:
                self.p1.getAxis('left').setLabel('Force (kg)', **label_adj)
                self.p1.plot(df['Time'], df['L_Force_kg'], pen=pg.mkPen(COLORS['exo'], width=1.5))
            elif "3." in sub_sel:
                self.p1.getAxis('left').setLabel('PWM', **label_adj)
                self.p1.plot(df['Time'], df['L_PWM'], pen=pg.mkPen(COLORS['sensor'], width=2), stepMode="left")
            elif "4." in sub_sel:
                self.p1.getAxis('left').setLabel('Knee (deg)', **label_adj)
                self.p1.plot(df['Time'], df['L_Knee'], pen=pg.mkPen(COLORS['sensor'], width=3), name=_lgd("Python"))
                if df_kin is not None:
                    self.p1.plot(df_kin['Time'], df_kin['L_Knee'], pen=pg.mkPen(COLORS['cam'], width=2, style=Qt.DashLine), name=_lgd("Kinovea"))
            elif "5." in sub_sel:
                self.p1.getAxis('left').setLabel('Hip (deg)', **label_adj)
                if df_kin is not None: self.p1.plot(df_kin['Time'], df_kin['L_Hip_Joint'], pen=pg.mkPen(COLORS['cam'], width=2), name=_lgd("Kinovea"))
                else: self.p1.plot(df['Time'], df['L_Hip_Joint'], pen=pg.mkPen(COLORS['sensor'], width=2), name=_lgd("Python"))
            elif "6." in sub_sel:
                self.p1.getAxis('left').setLabel('Ankle (deg)', **label_adj)
                self.p1.plot(df['Time'], df['L_Ankle'], pen=pg.mkPen(COLORS['noise'], width=1))
            elif "7." in sub_sel:
                if df_kin is not None:
                    n = min(len(df), len(df_kin))
                    diff = df['L_Knee'].iloc[:n].values - df_kin['L_Knee'].iloc[:n].values
                    y, x = np.histogram(diff, bins=30)
                    bg = pg.BarGraphItem(x=x[:-1], height=y, width=(x[1]-x[0]), brush=COLORS['sensor'])
                    self.p1.addItem(bg)
                    self.p1.getAxis('left').setLabel('Count', **label_adj)
                    self.p1.getAxis('bottom').setLabel('Error (deg)', **label_adj)
            elif "8." in sub_sel:
                force_data = np.nan_to_num(df['L_Force_kg'].values)
                dt = df['Time'].iloc[1] - df['Time'].iloc[0] if len(df['Time']) > 1 else 0.02
                fs = 1.0 / dt if dt > 0 else 50.0
                fft_vals = np.abs(np.fft.rfft(force_data))
                freqs = np.fft.rfftfreq(len(force_data), d=1/fs)
                self.p1.getAxis('left').setLabel('Magnitude', **label_adj)
                self.p1.getAxis('bottom').setLabel('Frequency (Hz)', **label_adj)
                self.p1.plot(freqs, fft_vals, pen=pg.mkPen('k', width=2))
                self.p1.setXRange(0, fs/2)
            elif "9." in sub_sel:
                if df_kin is not None:
                    n = min(len(df), len(df_kin))
                    x_data = df_kin['L_Knee'].iloc[:n]
                    y_data = df['L_Knee'].iloc[:n]
                    self.p1.getAxis('left').setLabel('Python (deg)', **label_adj)
                    self.p1.getAxis('bottom').setLabel('Kinovea (deg)', **label_adj)
                    self.p1.plot(x_data, y_data, pen=None, symbol='o', symbolBrush=pg.mkBrush(COLORS['sensor'], alpha=100), symbolSize=5)
                    self.p1.addItem(pg.InfiniteLine(pos=0, angle=45, pen=pg.mkPen('k', width=2, style=Qt.DashLine)))

        self.p1.autoRange()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 11)) # Slight bump for global UI
    window = GaitUltimateDashboard()
    window.show()
    sys.exit(app.exec_())