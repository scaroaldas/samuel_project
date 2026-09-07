# ui/main_window.py
import sys
import os
import numpy as np

from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QTextEdit, QLineEdit, QPushButton, QLabel, 
                               QProgressBar, QFrame, QApplication)
from PySide6.QtCore import Qt, Signal, QFile, QTextStream
from PySide6.QtGui import QFont
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from OpenGL.GL import *
from OpenGL.GLU import *

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from corebackend_skeleton import ChatMessage, Role, BrainWaveData, BrainRegion
except ImportError:
    pass 

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
        
        # Buffers
        self.vbo_vertices = None
        self.vbo_normals = None
        self.vbo_faces = None
        self.vbo_colors = None
        self.vbo_glow = None        # 🟣 NUEVO: buffer dinámico para luz morada
        self.num_faces = 0
        self.num_vertices = 0
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        stl_path = os.path.join(base_dir, "assets", "brain_anatomy.stl")
        
        if not os.path.exists(stl_path):
            print("⚠️ STL no encontrado")
            return
            
        try:
            import trimesh
            mesh = trimesh.load(stl_path, force='mesh', process=True)
            print(f"📊 Malla original: {len(mesh.faces)} caras")
            
            try:
                mesh = mesh.simplify_quadric_decimation(face_count=45000)
                print(f"✅ Malla decimada a {len(mesh.faces)} caras")
            except Exception:
                print("⚠️ Decimación no disponible")
            
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
            print(f"❌ Error STL: {e}")

    def initializeGL(self):
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
            glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 20.0)
            
            # VBOs estáticos
            self.vbo_vertices = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_vertices)
            glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            
            self.vbo_normals = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_normals)
            glBufferData(GL_ARRAY_BUFFER, self.normals.nbytes, self.normals, GL_STATIC_DRAW)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            
            self.vbo_faces = glGenBuffers(1)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vbo_faces)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.faces.nbytes, self.faces, GL_STATIC_DRAW)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
            
            self.vertex_colors = self._generate_cyber_colors()
            self.vbo_colors = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_colors)
            glBufferData(GL_ARRAY_BUFFER, self.vertex_colors.nbytes, self.vertex_colors, GL_STATIC_DRAW)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            
            # 🟣 NUEVO: VBO dinámico para la banda morada (se actualiza cada frame)
            self.glow_colors = np.zeros((self.num_vertices, 4), dtype=np.float32)
            self.vbo_glow = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_glow)
            glBufferData(GL_ARRAY_BUFFER, self.glow_colors.nbytes, self.glow_colors, GL_DYNAMIC_DRAW)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            
            # Timer pulso
            from PySide6.QtCore import QTimer
            import time
            self.start_time = time.time()
            self.pulse_timer = QTimer(self)
            self.pulse_timer.timeout.connect(self.update)
            self.pulse_timer.start(33)
            
            self.gl_ready = True
            print(f"✅ Cyber Brain inicializado ({self.num_faces} caras, {self.num_vertices} vértices)")
            
        except Exception as e:
            print(f"❌ Error initializeGL: {e}")
            self.gl_ready = False

    def _generate_cyber_colors(self):
        """Colores: gris oscuro mate con variación orgánica."""
        colors = np.zeros((self.num_vertices, 4), dtype=np.float32)
        
        for i in range(self.num_vertices):
            v = self.vertices[i]
            base = 0.12 + 0.06 * np.sin(v[0] * 8 + v[1] * 6 + v[2] * 10)
            tint = 0.02 * np.sin(v[1] * 12 + v[2] * 9)
            
            colors[i, 0] = max(0.05, min(0.25, base + tint))
            colors[i, 1] = max(0.05, min(0.25, base + tint * 0.8))
            colors[i, 2] = max(0.06, min(0.28, base + tint * 0.5 + 0.02))
            colors[i, 3] = 1.0
        
        return colors

    def _update_glow(self, elapsed):
        """🟣 NUEVO: Calcula la banda morada que recorre los lóbulos de ida y vuelta."""
        # Frontera móvil en eje X: viaja de -0.9 a +0.9 (ida y vuelta)
        frontier = 0.9 * np.sin(elapsed * 0.8)
        # Distancia de cada vértice a la frontera
        dist = np.abs(self.vertices[:, 0] - frontier)
        # Banda suave (grosor ~0.18 unidades) con caída cuadrática
        band = np.clip(1.0 - dist / 0.18, 0.0, 1.0) ** 2
        # Pulso rápido sobre la banda (latido)
        pulse = 0.7 + 0.3 * np.sin(elapsed * 5.0)
        inten = band * pulse

        glow = np.zeros((self.num_vertices, 4), dtype=np.float32)
        glow[:, 0] = inten * 0.75   # Rojo medio
        glow[:, 1] = inten * 0.08   # Verde casi nulo
        glow[:, 2] = inten * 1.0    # Azul pleno => MORADO fluorescente
        glow[:, 3] = inten
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
            import time
            elapsed = time.time() - self.start_time
            pulse = 0.7 + 0.3 * np.sin(elapsed * 3.0)
            
            # Reset estados críticos al inicio
            glDisable(GL_BLEND)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glLineWidth(1.0)
            glPointSize(1.0)
            glDisable(GL_POINT_SMOOTH)
            
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()
            
            glTranslatef(0.0, 0.0, self.zoom)
            glRotatef(self.rotation_x, 1.0, 0.0, 0.0)
            glRotatef(self.rotation_y, 0.0, 1.0, 0.0)
            
            # === CAPA 1: Superficie sólida gris oscura ===
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
            
            # 🟣 NUEVO === CAPA 1.5: Banda morada de energía fluyendo ===
            glow = self._update_glow(elapsed)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_glow)
            glBufferSubData(GL_ARRAY_BUFFER, 0, glow.nbytes, glow)
            glColorPointer(4, GL_FLOAT, 0, None)
            
            glDisable(GL_LIGHTING)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)  # aditivo = glow
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glDrawElements(GL_TRIANGLES, self.num_faces * 3, GL_UNSIGNED_INT, None)
            glDisable(GL_BLEND)
            glEnable(GL_LIGHTING)
            
            # Restaurar puntero de color al VBO base para las capas siguientes
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo_colors)
            glColorPointer(4, GL_FLOAT, 0, None)
            
            # === CAPA 2: Circuitos naranjas ===
            glDisable(GL_LIGHTING)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            
            glColor4f(1.0 * pulse, 0.45 * pulse, 0.0, 0.7 * pulse)
            glLineWidth(1.2)
            glDrawElements(GL_TRIANGLES, self.num_faces * 3, GL_UNSIGNED_INT, None)
            
            glColor4f(1.0 * pulse, 0.3 * pulse, 0.0, 0.25 * pulse)
            glLineWidth(3.0)
            glDrawElements(GL_TRIANGLES, self.num_faces * 3, GL_UNSIGNED_INT, None)
            
            # === CAPA 3: Nodos de energía ===
            glDisableClientState(GL_NORMAL_ARRAY)
            glDisableClientState(GL_COLOR_ARRAY)
            glEnable(GL_POINT_SMOOTH)
            
            glPointSize(3.5)
            glColor4f(1.0, 0.5 * pulse, 0.1, 0.85 * pulse)
            glDrawArrays(GL_POINTS, 0, self.num_vertices)
            
            glPointSize(1.8)
            glColor4f(1.0, 0.8 * pulse, 0.3, 1.0 * pulse)
            glDrawArrays(GL_POINTS, 0, self.num_vertices)
            
            # === RESET FINAL CRÍTICO ===
            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_NORMAL_ARRAY)
            glDisableClientState(GL_COLOR_ARRAY)
            
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
            
            glDisable(GL_BLEND)
            glDisable(GL_POINT_SMOOTH)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glLineWidth(1.0)
            glPointSize(1.0)
            glEnable(GL_LIGHTING)
            
        except Exception as e:
            print(f"⚠️ Error paintGL: {e}")
            try:
                glDisableClientState(GL_VERTEX_ARRAY)
                glDisableClientState(GL_NORMAL_ARRAY)
                glDisableClientState(GL_COLOR_ARRAY)
                glBindBuffer(GL_ARRAY_BUFFER, 0)
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
                glDisable(GL_BLEND)
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            except:
                pass

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
        """Limpieza explícita de recursos GPU al cerrar."""
        if self.vbo_vertices:
            glDeleteBuffers(1, [self.vbo_vertices])
        if self.vbo_normals:
            glDeleteBuffers(1, [self.vbo_normals])
        if self.vbo_faces:
            glDeleteBuffers(1, [self.vbo_faces])
        if self.vbo_colors:
            glDeleteBuffers(1, [self.vbo_colors])
        if self.vbo_glow:                    # 🟣 NUEVO
            glDeleteBuffers(1, [self.vbo_glow])


class MainWindow(QMainWindow):
    send_message_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neural Brain Mapper v1.0")
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

        self.chat_panel = QFrame()
        self.chat_panel.setObjectName("PanelChat")
        chat_layout = QVBoxLayout(self.chat_panel)
        chat_layout.setContentsMargins(16, 16, 16, 16)
        
        chat_title = QLabel("NEURAL INTERFACE")
        chat_title.setObjectName("StatTitle")
        chat_layout.addWidget(chat_title)

        self.chat_history = QTextEdit()
        self.chat_history.setObjectName("ChatHistory")
        self.chat_history.setReadOnly(True)
        chat_layout.addWidget(self.chat_history)

        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setObjectName("ChatInput")
        self.chat_input.setPlaceholderText("Escribe tu consulta neural...")
        self.chat_input.returnPressed.connect(self._on_send_clicked)
        
        self.send_btn = QPushButton("ENVIAR")
        self.send_btn.setObjectName("SendButton")
        self.send_btn.clicked.connect(self._on_send_clicked)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.send_btn)
        chat_layout.addLayout(input_layout)

        self.brain_panel = QFrame()
        self.brain_panel.setObjectName("PanelBrain")
        brain_layout = QVBoxLayout(self.brain_panel)
        brain_layout.setContentsMargins(0, 0, 0, 0)

        self.brain_visualizer = BrainVisualizer3D()
        brain_layout.addWidget(self.brain_visualizer, stretch=1)
        
        mode_text = "Motor 3D PyOpenGL Activo" if self.brain_visualizer.is_loaded else "ERROR DE CARGA"
        color = "#00FF9D" if self.brain_visualizer.is_loaded else "#FF3B3B"
        self.brain_status = QLabel(f"Estado: <span style='color:{color}; font-weight:bold;'>{mode_text}</span>")
        self.brain_status.setObjectName("BrainStatus")
        self.brain_status.setAlignment(Qt.AlignCenter)
        brain_layout.addWidget(self.brain_status)

        self.stats_panel = QFrame()
        self.stats_panel.setObjectName("PanelStats")
        stats_layout = QVBoxLayout(self.stats_panel)
        stats_layout.setContentsMargins(16, 16, 16, 16)

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
        current_dir = os.path.dirname(os.path.abspath(__file__))
        qss_path = os.path.join(current_dir, "styles.qss")
        fallback_qss = """
            QMainWindow { background-color: #05070A; }
            #PanelChat, #PanelBrain, #PanelStats { 
                background-color: #0D1117; border: 1px solid #21262D; border-radius: 16px; 
            }
            #StatTitle { color: #8B949E; font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: 1px; font-weight: bold; }
            #StatLabel { color: #8B949E; font-family: 'Inter', sans-serif; font-size: 13px; }
            #StatValue { color: #00E5FF; font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: bold; }
            #ChatHistory { background-color: transparent; border: none; color: #E6EDF3; font-size: 14px; }
            #ChatInput { background-color: #161B22; border: 1px solid #21262D; border-radius: 8px; padding: 12px; color: #E6EDF3; }
            #ChatInput:focus { border: 1px solid #00E5FF; }
            #SendButton { background-color: #00E5FF; color: #05070A; border: none; border-radius: 8px; padding: 12px 20px; font-weight: bold; }
            #SendButton:hover { background-color: #33EAFF; }
            #BrainStatus { color: #8B949E; font-size: 13px; margin-top: 10px; }
            #NeuroProgressBar { border: 1px solid #21262D; border-radius: 4px; background-color: #161B22; }
            #NeuroProgressBar::chunk { background: linear-gradient(90deg, #B026FF, #00E5FF); border-radius: 3px; }
        """
        qss_file = QFile(qss_path)
        if qss_file.open(QFile.ReadOnly | QFile.Text):
            stream = QTextStream(qss_file)
            QApplication.instance().setStyleSheet(stream.readAll() + fallback_qss)
            qss_file.close()
        else:
            QApplication.instance().setStyleSheet(fallback_qss)

    def _on_send_clicked(self):
        text = self.chat_input.text().strip()
        if text:
            self.chat_input.clear()
            self.send_message_signal.emit(text)

    def append_chat_message(self, message):
        color = "#00E5FF" if hasattr(message, 'role') and message.role == Role.AI else "#E6EDF3"
        prefix = "IA" if hasattr(message, 'role') and message.role == Role.AI else "Tú"
        content = message.content if hasattr(message, 'content') else str(message)
        html = f'<p style="color:{color}; margin:8px 0;"><b>{prefix}:</b> {content}</p>'
        self.chat_history.append(html)
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())

    def update_brain_stats(self, waves, regions):
        wave_map = {"Alpha": waves.alpha, "Beta": waves.beta, "Theta": waves.theta, "Delta": waves.delta}
        for name, bar in self.wave_bars.items():
            max_val = 30.0 if name == "Beta" else 15.0
            bar.setValue(min(100, int((wave_map[name] / max_val) * 100)))

        region_map = {r.name.split()[0]: r.activation_level for r in regions}
        for name, label in self.region_labels.items():
            val = region_map.get(name, 0.0)
            label.setText(f"{val*100:.1f}%")
            
        status_color = "#00FF9D" if self.brain_visualizer.is_loaded else "#FF3B3B"
        status_text = "SINCRONIZADO" if self.brain_visualizer.is_loaded else "ERROR 3D"
        self.brain_status.setText(f"Estado: <span style='color:{status_color}; font-weight:bold;'>{status_text}</span>")