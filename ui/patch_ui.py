# patch_ui.py - Ejecutar UNA vez: python patch_ui.py
import io

P = 'ui/main_window.py'
s = io.open(P, encoding='utf-8').read()
orig = s

METHODS = '''
    def _on_mic_clicked(self):
        self.mic_toggle_requested.emit()

    def set_listening_state(self, listening: bool):
        if listening:
            self.mic_btn.setText("⏹")
            self.mic_btn.setStyleSheet("background-color: #FF3B3B; color: white; border-radius: 8px; font-size: 16px;")
            self.mic_status.setText('<span style="color:#FF3B3B;">● ESCUCHANDO AL PACIENTE...</span>')
        else:
            self.mic_btn.setText("🎤")
            self.mic_btn.setStyleSheet("")
            self.mic_status.setText("")

    def append_analysis_result(self, result):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        linea = (f'<p style="color:#8B949E;">[{ts}] '
                 f'<span style="color:#00E5FF; font-weight:bold;">{result.emotional_state.upper()}</span> | '
                 f'Región: <b>{result.dominant_region}</b> | '
                 f'Activación: {result.activation_level*100:.1f}%</p>')
        self.results_view.append(linea)
'''

# 0) Import QTabWidget
if 'QTabWidget' not in s:
    assert 'QFrame, QApplication)' in s, 'ancla imports no encontrada'
    s = s.replace('QFrame, QApplication)', 'QFrame, QApplication, QTabWidget)', 1)
    print('✅ import QTabWidget')

# 1) Señal mic
if 'mic_toggle_requested' not in s:
    assert 'send_message_signal = Signal(str)' in s, 'ancla señal no encontrada'
    s = s.replace('send_message_signal = Signal(str)',
                  'send_message_signal = Signal(str)\n    mic_toggle_requested = Signal()', 1)
    print('✅ señal mic')

# 2) Pestañas ENTREVISTA / RESULTADOS
if 'self.chat_tabs' not in s:
    old = ('        self.chat_history = QTextEdit()\n'
           '        self.chat_history.setObjectName("ChatHistory")\n'
           '        self.chat_history.setReadOnly(True)\n'
           '        chat_layout.addWidget(self.chat_history)')
    new = ('        self.chat_tabs = QTabWidget()\n'
           '        self.chat_tabs.setObjectName("ChatTabs")\n'
           '\n'
           '        self.chat_history = QTextEdit()\n'
           '        self.chat_history.setObjectName("ChatHistory")\n'
           '        self.chat_history.setReadOnly(True)\n'
           '\n'
           '        self.results_view = QTextEdit()\n'
           '        self.results_view.setObjectName("ChatHistory")\n'
           '        self.results_view.setReadOnly(True)\n'
           '\n'
           '        self.chat_tabs.addTab(self.chat_history, "ENTREVISTA")\n'
           '        self.chat_tabs.addTab(self.results_view, "RESULTADOS")\n'
           '        chat_layout.addWidget(self.chat_tabs)')
    assert old in s, 'ancla chat_history no encontrada'
    s = s.replace(old, new, 1)
    print('✅ pestañas ENTREVISTA/RESULTADOS')

# 3) Botón mic + etiqueta de estado
if 'self.mic_btn' not in s:
    old = ('        input_layout.addWidget(self.chat_input)\n'
           '        input_layout.addWidget(self.send_btn)\n'
           '        chat_layout.addLayout(input_layout)')
    new = ('        self.mic_btn = QPushButton("🎤")\n'
           '        self.mic_btn.setObjectName("MicButton")\n'
           '        self.mic_btn.setFixedWidth(50)\n'
           '        self.mic_btn.setToolTip("Activar micrófono")\n'
           '        self.mic_btn.clicked.connect(self._on_mic_clicked)\n'
           '\n'
           '        input_layout.addWidget(self.chat_input)\n'
           '        input_layout.addWidget(self.send_btn)\n'
           '        input_layout.addWidget(self.mic_btn)\n'
           '        chat_layout.addLayout(input_layout)\n'
           '\n'
           '        self.mic_status = QLabel("")\n'
           '        self.mic_status.setObjectName("MicStatus")\n'
           '        self.mic_status.setAlignment(Qt.AlignCenter)\n'
           '        chat_layout.addWidget(self.mic_status)')
    assert old in s, 'ancla input_layout no encontrada'
    s = s.replace(old, new, 1)
    print('✅ botón mic + estado')

# 4) Métodos al final de la clase
if 'def set_listening_state' not in s:
    s = s.rstrip() + '\n' + METHODS
    print('✅ métodos mic/resultados')

if s != orig:
    io.open(P, 'w', encoding='utf-8').write(s)
    print('💾 parche guardado en disco')
else:
    print('ℹ️ ya estaba todo aplicado')