from PIL import Image , ImageDraw , ImageOps
from PyQt5.QtWidgets import (QApplication , QMainWindow , QFileDialog , QGraphicsView , QGraphicsScene ,
    QGraphicsPixmapItem , QWidget , QVBoxLayout , QHBoxLayout , QAbstractItemView , QListWidget , QPushButton)
from PyQt5.QtCore import Qt , QObject , QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
import numpy as np
import sys
import queue

draw_to_compute_thread = queue.Queue()
compute_to_image_render_thread = queue.Queue()

def extract_rgb_divmod(color_24bit):
    #getting a rgb valeus from the id
    blue = color_24bit % 256
    color_24bit //= 256
    green = color_24bit % 256
    color_24bit //= 256
    red = color_24bit % 256
    return red, green, blue

class MainWindow(QMainWindow):
    def __init__(self , map_path):
        super().__init__()
        
        central = QWidget()
        self.map_path = map_path
        self.draw_widget = MyDrawWindow(self.map_path)
        size = self.draw_widget.get_size()
        self.leftside = ProvinceSettings(size)
        layout = QHBoxLayout(central)
        layout.addWidget(self.leftside)
        layout.addWidget(self.draw_widget)
        
        self.setCentralWidget(central)


class MyDrawWindow(QGraphicsView):
    def __init__(self , map_path):
        super().__init__()
        self.tool = "free hand"
        self.using_tool = False
        self.points_send = []
        self.map_path = map_path
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        pixmap = QPixmap(map_path)
        self.size_check = Image.open(map_path).size
        draw_to_compute_thread.put(("queue init",self.size_check))
        self.original_pixmap = QPixmap(map_path)
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        
        self.drawing_pixmap = QPixmap(self.original_pixmap.size())
        self.drawing_pixmap.fill(Qt.transparent)
        self.drawing_item = QGraphicsPixmapItem(self.drawing_pixmap)
        self.scene.addItem(self.drawing_item)
        
        self.fitInView(self.drawing_item , Qt.KeepAspectRatio)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setFocusPolicy(Qt.StrongFocus)
        self.thread = QThread()
        self.worker = ComputeThread()
        self.worker.moveToThread(self.thread)
        
        self.thread.started.connect(self.worker.run)
        self.worker.compute_to_draw_thread.connect(self.on_worker_finished)# start werk als thread start
        
        self.thread.start()
    
    def wheelEvent(self , event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        delta = event.angleDelta().y()
        zoom_factor = zoom_in_factor if delta > 0 else zoom_out_factor
        self.scale(zoom_factor , zoom_factor)
    
    def on_worker_finished(self , data):
        print("[MyDrawWindow] Worker finished:" , data)
    
    def mousePressEvent(self , event):
        if event.button() == Qt.LeftButton:
            self.using_tool = True
            self.point_pressed = self.mapToScene(event.pos())
            self.points_send.append(self.point_pressed)
            if len(self.points_send) > 1:
                self.points_send.pop(0)
            draw_to_compute_thread.put((self.tool , (self.points_send, 1)))
    
    def mouseMoveEvent(self , event):
        if self.using_tool:
            self.point_pressed = self.mapToScene(event.pos())
            self.points_send.append(self.point_pressed)
            if len(self.points_send) > 2:
                self.points_send.pop(0)
            draw_to_compute_thread.put((self.tool ,(self.points_send, 1)))
    
    def mouseReleaseEvent(self , event):
        if event.button() == Qt.LeftButton:
            self.using_tool = False
    
    def get_size(self):
        return self.width()


class ProvinceSettings(QWidget):
    def __init__(self , size):
        super().__init__()
        self.setFixedWidth(size)
        layout = QVBoxLayout(self)
        self.new_province = QPushButton("new province")
        self.save_button = QPushButton("save")
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.item = ["province:1"]
        self.list_widget.addItems(self.item)
        layout.addWidget(self.new_province)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.save_button)


class ComputeThread(QObject):
    compute_to_draw_thread = pyqtSignal(tuple)
    def __init__(self):
        super().__init__()
        self.compute_image = np.array([],dtype=np.uint32)
    def run(self):
        while True:
            try:
                tool , data = draw_to_compute_thread.get(timeout=0.1)
                if tool == "free hand":
                    if len(data) == 2:
                        points, pid = data
                        if len(points) == 2:
                            point1, point2 = points
                        else:
                            point1 = points[0]
                            point2 = None
                    else:
                        point1 = None
                        point2 = None
                        pid = None
                    tool,data = self.free_hand(tool , point1 , point2 , pid)
                elif tool == "queue init":
                    size_aray_x , size_aray_y= data
                    self.compute_image = np.zeros((size_aray_y, size_aray_x), dtype=np.uint32)
                compute_to_image_render_thread.put((tool , data))
                self.compute_to_draw_thread.emit((tool,data))
            except queue.Empty:
                continue
    
    def free_hand(self , tool , point1 , point2 , pid):
        if pid is not None or point1 is not None:
            if pid is not None:
                red , green , blue = extract_rgb_divmod(pid)
            else:
                red , green , blue = 0 , 0 , 0  # fallback colour
            point1_x = int(point1.x())
            point1_y = int(point1.y())
        
            self.compute_image[point1_y,point1_x] = pid
            if point2 is not None:
                point2_x = int(point2.x())
                point2_y = int(point2.y())
                
                
        else:
            red, green, blue = None, None, None
        return tool , (point1 , point2 , (red, green, blue))
    
    def bresenham_octant0(self, dy , dx ,offset_y ,offset_x ,pid):
        """
        Returns list of (x, y) points for a line starting at (0, 0)
        ending at (dx, dy) where dx >= dy >= 0 (octant 0).
        """
        dy = dy - offset_y
        dx = dx - offset_x
        octant = self.octant_for_transform(dy, dx)
        points = []
        if octant == "failed to get one" or isinstance(octant,str):
            dy = abs(dy)
            dx = abs(dx)
            if dx > dy:
                dy , dx = dx , dy
            
            D = 2 * dy - dx
            y = 0
            
            for x in range(dx + 1):
                send_y, send_x = self.from_octant_to_transform(octant,y,x)
                send_y, send_x = send_y + offset_y, send_x + offset_x
                self.compute_image[send_y, send_x] = pid
                if D > 0:
                    y += 1
                    D -= 2 * dx
                D += 2 * dy
        return points
    def octant_for_transform(self, dy, dx):
        octant = "failed to get one"
        if dx > 0 and dy > 0:
            if dy > dx:
                octant = 1
            elif dy < dx:
                octant = 0
        elif dx < 0 > dy:
            if dy > abs(dx):
                octant = 3
            elif dy < abs(dx):
                octant = 2
        elif dx < 0 and dy < 0:
            if abs(dy) > abs(dx):
                octant = 5
            elif abs(dy) < abs(dx):
                octant = 4
        elif dy < 0 > dx:
            if abs(dy) > dx:
                octant = 7
            elif abs(dy) < dx:
                octant = 6
        return octant
    def from_octant_to_transform(self,octant, y, x):
        if octant == 0:
            y, x = y, x
        elif octant == 1:
            y, x = x, y
        elif octant == 2:
            y, x = x, -y
        elif octant == 3:
            y, x =  y, -x
        elif octant == 4:
            y, x = -y, -x
        elif octant == 5:
            y, x = -x, -y
        elif octant == 6:
            y, x = -x, y
        elif octant == 7:
            y, x = -y, x
        return y, x

app = QApplication(sys.argv)
map_path = QFileDialog.getOpenFileName(None , "Select Map Image" , "" , "Images (*.png *.jpg *.bmp)")[0]
if map_path:
    window = MainWindow(map_path)
    window.show()
    sys.exit(app.exec_())
else:
    print("[main] No file selected. Exiting.")