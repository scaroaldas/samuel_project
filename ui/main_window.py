# ui/main_window.py
import sys
import os
import numpy as np
import time

from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QTextEdit, QLineEdit, QPushButton, QLabel, 
                               QProgressBar, QFrame, QApplication, QTabWidget)
from PySide6.QtCore import Qt, Signal, QFile, QTextStream, QTimer
from PySide6.QtGui import QFont
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from OpenGL.GL import *
from OpenGL.GLU import *

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importación segura del backend
try:
    from corebackend_skeleton import ChatMessage, Role, BrainWaveData, BrainRegion, BrainActivationResult
except ImportError as e:
    print(f"⚠️ Error importando backend: {e}")
    sys.exit(1)

class BrainVisualizer3D(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_loaded = False
        self.gl_ready = False
        self.rotation_x = 15.0
        self.rotation_y = -25.0
        self.zoom = -2.8
        self.last_mouse_pos = None
        self.setMinimumSize(400, 400)
        
        self.vbo_vertices = None
        self.vbo_normals = None
        self.vbo_faces = None
        self.vbo_colors = None
        self.vbo_glow = None
        self.num_faces = 0
        self.num_vertices = 0
        
        self.region = None
        self.hemi = None
        self.sulcus_mask = None
        self.sulcus_phase = None
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        stl_path = os.path.join(base_dir, "assets", "brain_anatomy.stl")
        
        if not os.path.exists(stl_path):
            print("⚠️ STL no encontrado en assets/brain_anatomy.stl. Usando modo fallback.")
            return
            
        try:
            import trimesh
            mesh = trimesh.load(stl_path, force='mesh', process=True)
            print(f"📊 Malla original: {len(mesh.faces)} caras")
            
            try:
                mesh = mesh.simplify_quadric_decimation(face_count=150000)
                print(f"✅ Malla decimada a {len(mesh.faces)} caras")
            except Exception:
                print("⚠️ Decimación no disponible, usando malla original")
            
            vertices = np.array(mesh.vertices, dtype=np.float32)
            faces = np.array(mesh.faces, dtype=np.uint32)
            normals = np.array(mesh.vertex_normals, dtype=np.float32)
            
            center = vertices.mean(axis=0)
            vertices -= center
            max_dim = np.max(np.abs(vertices))
            if max_dim > 0:
                vertices = vertices / max_dim
            
            self.vertices = vertices
            self.faces = faces
            self.normals = normals
            self.num_faces = len(faces)
            self.num_vertices = len(vertices)
            self.is_loaded = True
            
        except Exception as e:
            print(f"❌ Error cargando STL: {e}")

    def initializeGL(self):
        if not self.is_loaded:
            return
        try:
            glClearColor(0.02, 0.02, 0.03, 1.0)
            glEnable(GL_DEPTH_TEST)
            glDepthFunc(GL_LEQUAL)
            glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
            
            glEnable(GL_LIGHTING)
            glEnable(GL_LIGHT0)
            glEnable(GL_NORMALIZE)
            glEnable(GL_COLOR_MATERIAL)
            
            glLightfv(GL_LIGHT0, GL_POSITION, [0.5, 1.0, 0.8, 0.0])
            glLightfv(GL_LIGHT0, GL_AMBIENT, [0.1, 0.1, 0.12, 1.0])
            glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.5, 0.5, 0.55, 1.0])
            
            glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
            glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.35, 0.28, 0.28, 1.0])
            glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 48.0)
            
            self.vbo_vertices = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertices)
            glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)
            
            self.vbo_normals = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals)
            glBufferData(GL_ARRAY_BUFFER, self.normals.nbytes, self.normals, GL_STATIC_DRAW)
            
            self.vbo_faces = glGenBuffers(1)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vbo_faces)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.faces.nbytes, self.faces, GL_STATIC_DRAW)
            
            self.region, self.hemi, self.sulcus_mask, self.sulcus_phase = self._compute_regions_and_mask()
            self.vertex_colors = self._generate_cyber_colors()
            
            self.vbo_colors = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_colors)
            glBufferData(GL_ARRAY_BUFFER, self.vertex_colors.nbytes, self.vertex_colors, GL_STATIC_DRAW)
            
            self.glow_colors = np.zeros((self.num_vertices, 4), dtype=np.float32)
            self.vbo_glow = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_glow)
            glBufferData(GL_ARRAY_BUFFER, self.glow_colors.nbytes, self.glow_colors, GL_DYNAMIC_DRAW)
            
            self.start_time = time.time()
            self.pulse_timer = QTimer(self)
            self.pulse_timer.timeout.connect(self.update)
            self.pulse_timer.start(33)
            
            self.gl_ready = True
            print(f"✅ Cyber Brain inicializado ({self.num_faces} caras)")
        except Exception as e:
            print(f"❌ Error initializeGL: {e}")
            self.gl_ready = False

    def _compute_regions_and_mask(self):
        v = self.vertices
        n = len(v)
        ap = v[:, 2]
        si = v[:, 1]
        lr = v[:, 0]

        CB_TOP, CB_MID, SYLVIAN, TEMP_LR = 0.10, 0.20, -0.10, 0.25
        OCC_AP, CEREB_SI, CEREB_AP, STEM_LR, MID_T = -0.55, -0.45, -0.35, 0.15, 0.018

        region = np.ones(n, dtype=np.int32)
        cb = CB_MID + (CB_TOP - CB_MID) * np.clip(si, 0.0, 1.0)

        cerebelo = (si < CEREB_SI) & (ap < CEREB_AP) & (np.abs(lr) > STEM_LR)
        bulbo = (si < CEREB_SI) & (np.abs(lr) <= STEM_LR) & (ap < 0.10)
        occipital = (ap < OCC_AP) & (si > CEREB_SI)
        temporal = (si < SYLVIAN) & (np.abs(lr) > TEMP_LR) & (ap > OCC_AP + 0.15) & (si > CEREB_SI)
        frontal = (ap > cb) & ~temporal

        region[frontal] = 0
        region[occipital] = 3
        region[temporal] = 2
        region[cerebelo] = 4
        region[bulbo] = 5

        hemi = np.sign(lr).astype(np.int32)
        fr = region[self.faces]
        dif = (fr[:,0] != fr[:,1]) | (fr[:,1] != fr[:,2]) | (fr[:,0] != fr[:,2])
        borde = np.zeros(n, dtype=bool)
        borde[self.faces[dif].ravel()] = True
        
        mid = (np.abs(lr) < MID_T) & (si > -0.55)
        self.mid_mask = mid
        mask = np.maximum(borde.astype(np.float32), mid.astype(np.float32))
        phase = (ap + si + lr) * 6.0
        return region, hemi, mask, phase.astype(np.float32)

    def _generate_cyber_colors(self):
        base_human = np.array([0.80, 0.52, 0.50], dtype=np.float32)
        tintes = {
            0: (0.05, 0.00, 0.00), 1: (0.00, 0.02, 0.04), 2: (0.04, -0.02, 0.00),
            3: (-0.02, 0.00, 0.03), 4: (0.00, 0.03, 0.00), 5: (0.02, 0.00, 0.02),
        }
        self.lobe_rgb = np.array([np.clip(base_human + np.array(tintes[i], dtype=np.float32), 0, 1) for i in range(6)], dtype=np.float32)
        HEMI_DIM = 0.82
        colors = np.zeros((self.num_vertices, 4), dtype=np.float32)
        base = self.lobe_rgb[self.region]
        noise = (0.035 * np.sin(self.vertices[:,0]*9 + self.vertices[:,1]*7 + self.vertices[:,2]*11) +
                 0.020 * np.sin(self.vertices[:,0]*23 - self.vertices[:,1]*17 + self.vertices[:,2]*29))
        dim = np.where(self.hemi >= 0, 1.0, HEMI_DIM)[:, None]
        colors[:, :3] = np.clip((base + noise[:, None]) * dim, 0.0, 1.0)
        colors[:, 3] = 1.0
        return colors

    def _update_glow(self, elapsed):
        flow = 0.35 + 0.65 * np.sin(elapsed * 6.5 - self.sulcus_phase * 1.6)
        spark = (np.sin(elapsed * 13.0 + self.sulcus_phase * 3.1) > 0.975)
        inten = np.clip(self.sulcus_mask * (flow + 0.8 * spark), 0.0, 1.2)
        inten = inten ** 1.4
        warm = np.array([1.0, 0.78, 0.82], dtype=np.float32)
        seam = np.clip(warm * 1.15 + 0.15, 0.0, 1.0)
        seam = np.where(self.mid_mask[:, None], np.array([0.95, 0.95, 1.0], dtype=np.float32), seam)
        glow = np.zeros((self.num_vertices, 4), dtype=np.float32)
        glow[:, :3] = seam * inten[:, None]
        glow[:, 3] = np.clip(inten, 0.0, 1.0) * 0.9
        return glow

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w / max(1, h), 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        if not self.gl_ready or not self.is_loaded:
            return
        try:
            elapsed = time.time() - self.start_time
            glDisable(GL_BLEND)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()
            glTranslatef(0.0, 0.0, self.zoom)
            glRotatef(self.rotation_x, 1.0, 0.0, 0.0)
            glRotatef(self.rotation_y, 0.0, 1.0, 0.0)
            
            import math
            glLightfv(GL_LIGHT0, GL_POSITION, [math.sin(elapsed * 0.6), 0.9, math.cos(elapsed * 0.6), 0.0])
            
            glEnable(GL_LIGHTING)
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_NORMAL_ARRAY)
            glEnableClientState(GL_COLOR_ARRAY)
            
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertices)
            glVertexPointer(3, GL_FLOAT, 0, None)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals)
            glNormalPointer(GL_FLOAT, 0, None)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_colors)
            glColorPointer(4, GL_FLOAT, 0, None)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vbo_faces)
            glDrawElements(GL_TRIANGLES, self.num_faces * 3, GL_UNSIGNED_INT, None)
            
            glow = self._update_glow(elapsed)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_glow)
            glBufferSubData(GL_ARRAY_BUFFER, 0, glow.nbytes, glow)
            glColorPointer(4, GL_FLOAT, 0, None)
            glDisable(GL_LIGHTING)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)
            glDrawElements(GL_TRIANGLES, self.num_faces * 3, GL_UNSIGNED_INT, None)
            
            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_NORMAL_ARRAY)
            glDisableClientState(GL_COLOR_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
            glDisable(GL_BLEND)
            glEnable(GL_LIGHTING)
        except Exception as e:
            print(f"⚠️ Error paintGL: {e}")

    def mousePressEvent(self, event):
        self.last_mouse_pos = (event.position().x(), event.position().y())

    def mouseMoveEvent(self, event):
        if self.last_mouse_pos:
            dx = event.position().x() - self.last_mouse_pos[0]
            dy = event.position().y() - self.last_mouse_pos[1]
            self.rotation_y += dx * 0.5
            self.rotation_x += dy * 0.5
            self.last_mouse_pos = (event.position().x(), event.position().y())
            self.update()

    def wheelEvent(self, event):
        self.zoom += event.angleDelta().y() * 0.01
        self.zoom = max(-10.0, min(-1.5, self.zoom))
        self.update()

    def cleanup(self):
        if self.vbo_vertices: glDeleteBuffers(1, [self.vbo_vertices])
        if self.vbo_normals: glDeleteBuffers(1, [self.vbo_normals])
        if self.vbo_faces: glDeleteBuffers(1, [self.vbo_faces])
        if self.vbo_colors: glDeleteBuffers(1, [self.vbo_colors])
        if self.vbo_glow: glDeleteBuffers(1, [self.vbo_glow])


class MainWindow(QMainWindow):
    send_message_signal = Signal(str)
    mic_toggle_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neural Brain Mapper v2.0 (3D Active)")
        self.setMinimumSize(1400, 800)
        self.setStyleSheet("background-color: #05070A;")
        self._init_ui()
        self._apply_styles()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # PANEL 1: CHAT
        self.chat_panel = QFrame()
        self.chat_panel.setObjectName("PanelChat")
        chat_layout = QVBoxLayout(self.chat_panel)
        
        chat_title = QLabel("NEURAL INTERFACE")
        chat_title.setObjectName("StatTitle")
        chat_layout.addWidget(chat_title)

        self.chat_history = QTextEdit()
        self.chat_history.setObjectName("ChatHistory")
        self.chat_history.setReadOnly(True)
        chat_layout.addWidget(self.chat_history)

        self.thinking_label = QLabel("⟨ Analizando patrones neurales... ⟩")
        self.thinking_label.setObjectName("ThinkingLabel")
        self.thinking_label.setAlignment(Qt.AlignCenter)
        self.thinking_label.hide()
        chat_layout.addWidget(self.thinking_label)

        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setObjectName("ChatInput")
        self.chat_input.setPlaceholderText("Escribe tu consulta neural...")
        self.chat_input.returnPressed.connect(self._on_send_clicked)
        
        self.send_btn = QPushButton("ENVIAR")
        self.send_btn.setObjectName("SendButton")
        self.send_btn.clicked.connect(self._on_send_clicked)
        
        input_layout.addWidget(self.chat_input, 4)
        input_layout.addWidget(self.send_btn, 1)
        chat_layout.addLayout(input_layout)

        # PANEL 2: CEREBRO 3D
        self.brain_panel = QFrame()
        self.brain_panel.setObjectName("PanelBrain")
        brain_layout = QVBoxLayout(self.brain_panel)
        brain_layout.setContentsMargins(0, 0, 0, 0)

        self.brain_visualizer = BrainVisualizer3D()
        brain_layout.addWidget(self.brain_visualizer, stretch=1)
        
        mode_text = "Motor 3D PyOpenGL Activo" if self.brain_visualizer.is_loaded else "MODO FALLBACK (Sin archivo .stl)"
        color = "#00FF9D" if self.brain_visualizer.is_loaded else "#FF3B3B"
        self.brain_status = QLabel(f"Estado: <span style='color:{color}; font-weight:bold;'>{mode_text}</span>")
        self.brain_status.setObjectName("BrainStatus")
        self.brain_status.setAlignment(Qt.AlignCenter)
        brain_layout.addWidget(self.brain_status)

        # PANEL 3: ESTADÍSTICAS
        self.stats_panel = QFrame()
        self.stats_panel.setObjectName("PanelStats")
        stats_layout = QVBoxLayout(self.stats_panel)

        stats_title = QLabel("BIOMETRIC TELEMETRY")
        stats_title.setObjectName("StatTitle")
        stats_layout.addWidget(stats_title)

        self.wave_bars = {}
        for wave in ["Alpha", "Beta", "Theta", "Delta"]:
            label = QLabel(f"{wave} Waves")
            label.setObjectName("StatLabel")
            stats_layout.addWidget(label)
            bar = QProgressBar()
            bar.setObjectName("NeuroProgressBar")
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            stats_layout.addWidget(bar)
            self.wave_bars[wave] = bar

        stats_layout.addSpacing(24)
        
        region_title = QLabel("ACTIVE REGIONS")
        region_title.setObjectName("StatTitle")
        region_title.setStyleSheet("color: #00E5FF; margin-top: 10px;")
        stats_layout.addWidget(region_title)

        self.region_labels = {}
        for region in ["Frontal", "Parietal", "Temporal", "Occipital"]:
            r_layout = QHBoxLayout()
            r_label = QLabel(region)
            r_label.setObjectName("StatLabel")
            r_val = QLabel("0.0%")
            r_val.setObjectName("StatValue")
            r_val.setAlignment(Qt.AlignRight)
            r_layout.addWidget(r_label)
            r_layout.addWidget(r_val)
            stats_layout.addLayout(r_layout)
            self.region_labels[region] = r_val

        stats_layout.addStretch()
        main_layout.addWidget(self.chat_panel, stretch=2)
        main_layout.addWidget(self.brain_panel, stretch=5)
        main_layout.addWidget(self.stats_panel, stretch=2)

    def _apply_styles(self):
        fallback_qss = """
            QMainWindow { background-color: #05070A; }
            #PanelChat, #PanelBrain, #PanelStats { 
                background-color: #0D1117; border: 1px solid #21262D; border-radius: 16px; 
            }
            #StatTitle { color: #8B949E; font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: 1px; font-weight: bold; margin-bottom: 10px;}
            #StatLabel { color: #8B949E; font-family: 'Inter', sans-serif; font-size: 13px; }
            #StatValue { color: #00E5FF; font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: bold; }
            #ChatHistory { background-color: transparent; border: 1px solid #21262D; border-radius: 8px; padding: 10px; color: #E6EDF3; font-size: 14px; }
            #ChatInput { background-color: #161B22; border: 1px solid #21262D; border-radius: 8px; padding: 12px; color: #E6EDF3; }
            #ChatInput:focus { border: 1px solid #00E5FF; }
            #SendButton { background-color: #00E5FF; color: #05070A; border: none; border-radius: 8px; padding: 12px 20px; font-weight: bold; }
            #SendButton:hover { background-color: #33EAFF; }
            #BrainStatus { color: #8B949E; font-size: 13px; margin-top: 10px; }
            #NeuroProgressBar { border: 1px solid #21262D; border-radius: 4px; background-color: #161B22; }
            #NeuroProgressBar::chunk { background: linear-gradient(90deg, #B026FF, #00E5FF); border-radius: 3px; }
            #ThinkingLabel { color: #8B949E; font-style: italic; font-size: 12px; margin: 5px 0; }
        """
        QApplication.instance().setStyleSheet(fallback_qss)

    def _on_send_clicked(self):
        text = self.chat_input.text().strip()
        if text:
            self.chat_input.clear()
            self.thinking_label.show()
            self.send_message_signal.emit(text)

    def append_chat_message(self, message):
        self.thinking_label.hide()
        role = message.role if hasattr(message, 'role') else Role.USER
        content = message.content if hasattr(message, 'content') else str(message)
        
        if role == Role.USER:
            html = f'<div style="text-align: right; margin: 8px 0;"><span style="background-color: #238636; color: white; padding: 8px 12px; border-radius: 12px 12px 0 12px; display: inline-block;">{content}</span></div>'
        else:
            html = f'<div style="text-align: left; margin: 8px 0;"><span style="background-color: #1f6feb; color: white; padding: 8px 12px; border-radius: 12px 12px 12px 0; display: inline-block;">{content}</span></div>'
        
        self.chat_history.append(html)
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())

    def update_brain_stats(self, waves, regions):
        import time
        wave_map = {"Alpha": waves.alpha, "Beta": waves.beta, "Theta": waves.theta, "Delta": waves.delta}
        for name, bar in self.wave_bars.items():
            max_val = 30.0 if name == "Beta" else 15.0
            bar.setValue(min(100, int((wave_map[name] / max_val) * 100)))

        region_map = {r.name.split()[0]: r.activation_level for r in regions}
        for name, label in self.region_labels.items():
            if "[ACTIVA]" not in label.text():
                val = region_map.get(name, 0.0)
                label.setText(f"{val*100:.1f}%")

        # Solo sobrescribe el estado si no hay una activación reciente (6 s de bloqueo)
        if time.time() > getattr(self, "_activation_until", 0.0):
            status_color = "#00FF9D" if self.brain_visualizer.is_loaded else "#FF3B3B"
            status_text = "SINCRONIZADO" if self.brain_visualizer.is_loaded else "ERROR 3D"
            self.brain_status.setText(f"Estado: <span style='color:{status_color}; font-weight:bold;'>{status_text}</span>")

    def handle_brain_activation(self, result):
        import time
        self._activation_until = time.time() + 6.0  # La telemetría no pisa el feedback 6 s

        # Iluminar la región dominante en el panel derecho
        for name, label in self.region_labels.items():
            if name == result.dominant_region:
                label.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 16px;")
                label.setText(f"{result.activation_level*100:.1f}% [ACTIVA]")
            else:
                label.setStyleSheet("color: #8B949E; font-weight: normal; font-size: 14px;")

        # Cambiar el estado emocional en el panel del cerebro
        if result.emotional_state == "Calm":
            state_color = "#00FF9D"
        elif result.emotional_state == "Stressed":
            state_color = "#FF3B3B"
        else:
            state_color = "#00E5FF"

        self.brain_status.setText(f"Estado: <span style='color:{state_color}; font-weight:bold;'>{result.emotional_state.upper()}</span> | Región: {result.dominant_region}")

class MainWindowFull(MainWindow):
    def __init__(self):
        super().__init__()
        self._upgrade_chat()

    def _upgrade_chat(self):
        vl = self.chat_panel.layout()
        self.chat_tabs = QTabWidget()
        self.results_view = QTextEdit()
        self.results_view.setObjectName("ChatHistory")
        self.results_view.setReadOnly(True)
        vl.replaceWidget(self.chat_history, self.chat_tabs)
        self.chat_tabs.addTab(self.chat_history, "ENTREVISTA")
        self.chat_tabs.addTab(self.results_view, "RESULTADOS")
        self.mic_btn = QPushButton("MIC")
        self.mic_btn.setFixedWidth(50)
        self.mic_btn.setToolTip("Activar microfono")
        self.mic_btn.clicked.connect(self._on_mic_clicked)
        for i in range(vl.count()):
            it = vl.itemAt(i)
            if it.layout() is not None and it.layout().indexOf(self.send_btn) >= 0:
                it.layout().addWidget(self.mic_btn)
                break
        self.mic_status = QLabel("")
        self.mic_status.setAlignment(Qt.AlignCenter)
        vl.addWidget(self.mic_status)

    def _on_mic_clicked(self):
        self.mic_toggle_requested.emit()

    def set_listening_state(self, listening):
        if listening:
            self.mic_btn.setText("STOP")
            self.mic_btn.setStyleSheet('background-color: #00FF9D; color: #05070A; border-radius: 8px; font-weight: bold;')
            self.mic_status.setText('<span style="color:#00FF9D; font-weight:bold;">● ESCUCHANDO...</span>')
        else:
            self.mic_btn.setText("MIC")
            self.mic_btn.setStyleSheet('background-color: #FF3B3B; color: white; border-radius: 8px; font-weight: bold;')
            self.mic_status.setText('<span style="color:#8B949E;">Micrófono listo</span>')

    def append_analysis_result(self, result):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        linea = ('<p style="color:#8B949E;">[' + ts + '] '
                 + '<span style="color:#00E5FF; font-weight:bold;">' + result.emotional_state.upper() + '</span> | '
                 + 'Region: <b>' + result.dominant_region + '</b> | '
                 + 'Activacion: ' + format(result.activation_level * 100, '.1f') + '%</p>')
        self.results_view.append(linea)

    def append_chat_message(self, message):
        role = message.role if hasattr(message, "role") else Role.USER
        content = message.content if hasattr(message, "content") else str(message)
        if role == Role.USER:
            html = '<div style="text-align: right; margin: 8px 0;"><span style="background-color: #238636; color: white; padding: 8px 12px; border-radius: 12px 12px 0 12px; display: inline-block;">' + content + '</span></div>'
        else:
            html = '<div style="text-align: left; margin: 8px 0;"><span style="background-color: #1f6feb; color: white; padding: 8px 12px; border-radius: 12px 12px 12px 0; display: inline-block;">' + content + '</span></div>'
        self.chat_history.append(html)
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())


def _upgrade_chat_v2(self):
    vl = self.chat_panel.layout()
    if self.chat_history.parentWidget() is not self.chat_tabs:
        vl.replaceWidget(self.chat_history, self.chat_tabs)
    if self.chat_tabs.count() == 0:
        self.chat_tabs.addTab(self.chat_history, "ENTREVISTA")
        self.chat_tabs.addTab(self.results_view, "RESULTADOS")
    if self.mic_btn.parent() is None:
        vl.addWidget(self.mic_btn)
    self.mic_btn.setText("MIC")
    self.mic_btn.setStyleSheet("background-color: #FF3B3B; color: white; border-radius: 8px; font-weight: bold;")
    self.mic_btn.show()

MainWindowFull._upgrade_chat = _upgrade_chat_v2
print("PATCH MIC V2 ACTIVO")


def _upgrade_chat_v3(self):
    vl = self.chat_panel.layout()
    if not hasattr(self, "chat_tabs"):
        self.chat_tabs = QTabWidget()
    if not hasattr(self, "results_view"):
        self.results_view = QTextEdit()
        self.results_view.setObjectName("ChatHistory")
        self.results_view.setReadOnly(True)
    if self.chat_history.parentWidget() is not self.chat_tabs:
        vl.replaceWidget(self.chat_history, self.chat_tabs)
    if self.chat_tabs.count() == 0:
        self.chat_tabs.addTab(self.chat_history, "ENTREVISTA")
        self.chat_tabs.addTab(self.results_view, "RESULTADOS")
    if not hasattr(self, "mic_btn"):
        self.mic_btn = QPushButton("MIC")
        self.mic_btn.setFixedWidth(50)
        self.mic_btn.clicked.connect(self._on_mic_clicked)
    if self.mic_btn.parent() is None:
        placed = False
        for i in range(vl.count()):
            it = vl.itemAt(i)
            if it.layout() is not None and it.layout().indexOf(self.send_btn) >= 0:
                it.layout().addWidget(self.mic_btn)
                placed = True
                break
        if not placed:
            vl.addWidget(self.mic_btn)
    if not hasattr(self, "mic_status"):
        self.mic_status = QLabel("")
        self.mic_status.setAlignment(Qt.AlignCenter)
        vl.addWidget(self.mic_status)
    self.mic_btn.setText("MIC")
    self.mic_btn.setStyleSheet("background-color: #FF3B3B; color: white; border-radius: 8px; font-weight: bold;")
    self.mic_btn.show()

MainWindowFull._upgrade_chat = _upgrade_chat_v3
print("PATCH MIC V3 ACTIVO")
