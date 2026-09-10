# fix_mic.py - Parche para colores del micrófono
with open('ui/main_window.py', 'r', encoding='utf-8') as f:
    s = f.read()

old = '''    def set_listening_state(self, listening):
        if listening:
            self.mic_btn.setText("STOP")
            self.mic_btn.setStyleSheet("background-color: #FF3B3B; color: white; border-radius: 8px; font-weight: bold;")
            self.mic_status.setText('<span style="color:#FF3B3B;">ESCUCHANDO AL PACIENTE...</span>')
        else:
            self.mic_btn.setText("MIC")
            self.mic_btn.setStyleSheet("")
            self.mic_status.setText("")'''

new = '''    def set_listening_state(self, listening):
        if listening:
            self.mic_btn.setText("STOP")
            self.mic_btn.setStyleSheet('background-color: #00FF9D; color: #05070A; border-radius: 8px; font-weight: bold;')
            self.mic_status.setText('<span style="color:#00FF9D; font-weight:bold;">● ESCUCHANDO...</span>')
        else:
            self.mic_btn.setText("MIC")
            self.mic_btn.setStyleSheet('background-color: #FF3B3B; color: white; border-radius: 8px; font-weight: bold;')
            self.mic_status.setText('<span style="color:#8B949E;">Micrófono listo</span>')'''

if old in s:
    s = s.replace(old, new, 1)
    with open('ui/main_window.py', 'w', encoding='utf-8') as f:
        f.write(s)
    print(' Parche aplicado: ESCUCHANDO=Verde, NORMAL=Rojo')
else:
    print(' No se encontró el código. Buscando versión alternativa...')
    # Intento con variación
    if 'def set_listening_state' in s:
        print(' El método existe pero con formato diferente. Revisa manualmente.')
    else:
        print(' El método no existe en el archivo.')