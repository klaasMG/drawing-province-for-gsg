from PIL import Image , ImageDraw , ImageOps
from PyQt5.QtWidgets import QApplication , QMainWindow , QFileDialog , QGraphicsView , QGraphicsScene , \
    QGraphicsPixmapItem , QWidget , QVBoxLayout , QHBoxLayout , QAbstractItemView , QListWidget , QPushButton
from PyQt5.QtCore import Qt , QObject , QThread
from PyQt5.QtGui import QPixmap
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
        
        self.thread.started.connect(self.worker.run)  # start werk als thread start
        
        self.thread.start()
    
    def wheelEvent(self , event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        delta = event.angleDelta().y()
        zoom_factor = zoom_in_factor if delta > 0 else zoom_out_factor
        self.scale(zoom_factor , zoom_factor)
    
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
    def __init__(self):
        super().__init__()
    
    def run(self):
        while True:
            try:
                tool , data = draw_to_compute_thread.get(timeout=0.1)
                if tool == "free hand":
                    if len(data) == 3:
                        point1 , point2 , pid = data
                    else:
                        point1, point2, pid = None,None,None
                    tool,data = self.free_hand(tool , point1 , point2 , pid)
                compute_to_image_render_thread.put((tool , data))
            except queue.Empty:
                continue
    
    def free_hand(self , tool , point1 , point2 , pid):
        if pid is not None:
            red , green , blue = extract_rgb_divmod(pid)
        else:
            red , green , blue = 0 , 0 , 0  # fallback colour
        return tool , (point1 , point2 , (red, green, blue))


app = QApplication(sys.argv)
map_path = QFileDialog.getOpenFileName(None , "Select Map Image" , "" , "Images (*.png *.jpg *.bmp)")[0]
if map_path:
    window = MainWindow(map_path)
    window.show()
    sys.exit(app.exec_())
else:
    print("[main] No file selected. Exiting.")