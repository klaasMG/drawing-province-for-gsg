from PIL import Image, ImageDraw
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QGraphicsView, QGraphicsScene,
                             QGraphicsPixmapItem, QWidget, QVBoxLayout, QHBoxLayout, QAbstractItemView,
                             QListWidget, QPushButton)
from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
import numpy as np
import sys
import queue
import threading

Image.MAX_IMAGE_PIXELS = None
draw_to_compute_thread = queue.Queue(maxsize=4096)
compute_to_image_render_thread = queue.Queue(maxsize=4096)
shutdown_queue = queue.Queue(maxsize=16)
thread_finished_send = queue.Queue(maxsize=32)
province_id = 1
province_id_max = 1


def extract_rgb_divmod(color_24bit):
    blue = color_24bit % 256
    color_24bit //= 256
    green = color_24bit % 256
    color_24bit //= 256
    red = color_24bit % 256
    return red, green, blue


class MainWindow(QMainWindow):
    def __init__(self, map_path):
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

    def closeEvent(self, event):
        self.draw_widget.stop()
        self.thread = QThread()
        self.worker = Shutdown_Thread()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.threads_finished.connect(self.on_worker_finished)

        self.thread.start()
        event.ignore()

    def on_worker_finished(self, shut_down_finished):
        if shut_down_finished == "done":
            self.thread.quit()
            self.close()


class MyDrawWindow(QGraphicsView):
    def __init__(self, map_path):
        super().__init__()
        self.tool = "free hand"
        self.using_tool = False
        self.points_send = []
        self.map_path = map_path
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        pixmap = QPixmap(map_path)
        self.size_check = Image.open(map_path).size
        draw_to_compute_thread.put(("queue init", self.size_check))
        self.original_pixmap = QPixmap(map_path)
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)

        # ---- FIX: create drawing pixmap with explicit width/height
        w = self.original_pixmap.width()
        h = self.original_pixmap.height()
        self.drawing_pixmap = QPixmap(w, h)
        self.drawing_pixmap.fill(Qt.transparent)
        self.drawing_item = QGraphicsPixmapItem(self.drawing_pixmap)
        self.scene.addItem(self.drawing_item)

        # ensure layering: drawing on top
        self.pixmap_item.setZValue(0)
        self.drawing_item.setZValue(1)

        # set scene rect and initial view
        self.scene.setSceneRect(0, 0, w, h)
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.setDragMode(QGraphicsView.NoDrag)
        self.setFocusPolicy(Qt.StrongFocus)
        self.thread = QThread()
        self.worker = ComputeThread()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.compute_to_draw_thread.connect(self.on_worker_finished)

        self.thread.start()
        self.worker1 = Image_draw_thread(w, h)
        threading.Thread(target=self.worker1.run, daemon=True).start()

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        delta = event.angleDelta().y()
        zoom_factor = zoom_in_factor if delta > 0 else zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

    def on_worker_finished(self, return_data):
        tool, data = return_data
        if data is None:
            return
        points, colour = data
        if isinstance(colour, tuple):
            red, green, blue = colour
        else:
            red, green, blue = 255, 0, 0

        # convert points that may be tuples (already pixel coords from compute thread)
        def to_xy(p):
            if p is None:
                return None
            if hasattr(p, "x") and hasattr(p, "y"):
                return int(p.x()), int(p.y())
            return int(p[0]), int(p[1])

        point1 = to_xy(points[0])
        point2 = to_xy(points[1]) if points and points[1] is not None else None

        if point1 is None:
            return

        w = self.drawing_pixmap.width()
        h = self.drawing_pixmap.height()
        # bounds-check
        if not (0 <= point1[0] < w and 0 <= point1[1] < h):
            # out of bounds -> ignore
            return

        painter = QPainter(self.drawing_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setPen(QPen(QColor(int(red or 0), int(green or 0), int(blue or 0), 255), 2))
        painter.drawPoint(point1[0], point1[1])
        if point2 is not None and (0 <= point2[0] < w and 0 <= point2[1] < h):
            painter.drawLine(point1[0], point1[1], point2[0], point2[1])
        painter.end()
        self.drawing_item.setPixmap(self.drawing_pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.using_tool = True
            # ---- FIX: convert scene coords to pixmap/item coords
            scene_pt = self.mapToScene(event.pos())
            pix_pt = self.pixmap_item.mapFromScene(scene_pt)
            x = int(pix_pt.x()); y = int(pix_pt.y())
            w = self.original_pixmap.width(); h = self.original_pixmap.height()
            if not (0 <= x < w and 0 <= y < h):
                # outside image, ignore
                return
            self.point_pressed = pix_pt
            self.points_send.append(self.point_pressed)
            if len(self.points_send) > 2:
                self.points_send.pop(0)
            # debug
            print("press", x, y, "-> send")
            global province_id
            draw_to_compute_thread.put((self.tool, (self.points_send, province_id)))

    def mouseMoveEvent(self, event):
        if self.using_tool:
            scene_pt = self.mapToScene(event.pos())
            pix_pt = self.pixmap_item.mapFromScene(scene_pt)
            x = int(pix_pt.x()); y = int(pix_pt.y())
            w = self.original_pixmap.width(); h = self.original_pixmap.height()
            if not (0 <= x < w and 0 <= y < h):
                return
            self.point_pressed = pix_pt
            self.points_send.append(self.point_pressed)
            if len(self.points_send) > 2:
                self.points_send.pop(0)
            print("move", x, y, "-> send")
            global province_id
            draw_to_compute_thread.put((self.tool, (self.points_send, province_id)))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.using_tool = False

    def get_size(self):
        return self.width()

    def stop(self):
        # send shutdown signal
        try:
            shutdown_queue.put_nowait("shut down")
        except:
            pass


class Shutdown_Thread(QObject):
    threads_finished = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        shutdown_queue.put("shut down")
        threads_shutdown = 0
        while threads_shutdown < 2:
            try:
                message = thread_finished_send.get(timeout=0.5)
                if message == "finished_thread":
                    threads_shutdown += 1
            except queue.Empty:
                continue
        self.threads_finished.emit("done")


class ProvinceSettings(QWidget):
    def __init__(self, size):
        super().__init__()
        self.setFixedWidth(size)
        layout = QVBoxLayout(self)
        self.new_province = QPushButton("new province")
        self.new_province.clicked.connect(self.increase_prov_id)
        self.save_button = QPushButton("save")
        self.save_button.clicked.connect(self.send_save)
        self.list_widget = QListWidget()
        # adjust signature: signal gives (current, previous)
        self.list_widget.currentItemChanged.connect(self.set_province_id)
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.item = ["province : 1"]
        self.list_widget.addItems(self.item)
        layout.addWidget(self.new_province)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.save_button)

    def increase_prov_id(self):
        global province_id, province_id_max
        province_id_max += 1
        province_id = province_id_max
        self.list_widget.addItem(f"province : {province_id_max}")

    def set_province_id(self, current, previous=None):
        if current is None:
            return
        global province_id
        prov_id_to = current.text()
        prov_id_to = prov_id_to.split(":")[1].strip()
        province_id = int(prov_id_to)

    def send_save(self):
        draw_to_compute_thread.put(("save", "data not needed"))


class ComputeThread(QObject):
    compute_to_draw_thread = pyqtSignal(tuple)

    def __init__(self):
        super().__init__()
        self.compute_image = np.array([], dtype=np.uint32)
        self.last_pid = 1
        self.running = True

    def run(self):
        while self.running:
            try:
                data_get = draw_to_compute_thread.get(timeout=0.1)
                tool, data = data_get
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
                    tool, data = self.free_hand(tool, point1, point2, pid)
                    self.last_pid = pid
                elif tool == "queue init":
                    size_aray_x, size_aray_y = data
                    self.compute_image = np.zeros((size_aray_y, size_aray_x), dtype=np.uint32)
                elif tool == "save":
                    data = None
                compute_to_image_render_thread.put((tool, data))
                self.compute_to_draw_thread.emit((tool, data))
            except queue.Empty:
                continue

            # non-blocking shutdown check
            try:
                msg = shutdown_queue.get_nowait()
                if msg == "shut down":
                    self.stop()
                    thread_finished_send.put("finished_thread")
            except queue.Empty:
                pass

    def free_hand(self, tool, point1, point2, pid):
        if pid is not None or point1 is not None:
            if pid is not None:
                red, green, blue = extract_rgb_divmod(pid)
            else:
                red, green, blue = 0, 0, 0
            # point1 is a QPointF from GUI (mapped to pix coords) — safe conversion
            if hasattr(point1, "x") and hasattr(point1, "y"):
                point1_x = int(point1.x())
                point1_y = int(point1.y())
            else:
                point1_x, point1_y = int(point1[0]), int(point1[1])

            # bounds-check before writing into compute_image
            if self.compute_image.size != 0:
                h, w = self.compute_image.shape
                if 0 <= point1_x < w and 0 <= point1_y < h:
                    self.compute_image[point1_y, point1_x] = pid

            if point2 is not None and self.last_pid == pid:
                if hasattr(point2, "x") and hasattr(point2, "y"):
                    point2_x = int(point2.x())
                    point2_y = int(point2.y())
                else:
                    point2_x, point2_y = int(point2[0]), int(point2[1])
                # draw bresenham into compute_image (quick bounds-safe)
                self.bresenham_octant0(point2_y, point2_x, point1_y, point1_x, pid)
                point2 = (point2_x, point2_y)
            else:
                point2 = None
            point1 = (point1_x, point1_y)
        else:
            red, green, blue = None, None, None
        return tool, ((point1, point2), (red, green, blue))

    def bresenham_octant0(self, dy, dx, offset_y, offset_x, pid):
        dy = dy - offset_y
        dx = dx - offset_x
        octant = self.octant_for_transform(dy, dx)
        if octant == "failed to get one" or isinstance(octant, str):
            dy = abs(dy)
            dx = abs(dx)
            if dx > dy:
                dy, dx = dx, dy

            D = 2 * dy - dx
            y = 0

            for x in range(dx + 1):
                send_y, send_x = self.from_octant_to_transform(octant, y, x)
                send_y, send_x = send_y + offset_y, send_x + offset_x
                # bounds-check
                if 0 <= send_y < self.compute_image.shape[0] and 0 <= send_x < self.compute_image.shape[1]:
                    self.compute_image[send_y, send_x] = pid
                if D > 0:
                    y += 1
                    D -= 2 * dx
                D += 2 * dy

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

    def from_octant_to_transform(self, octant, y, x):
        if octant == 0:
            y, x = y, x
        elif octant == 1:
            y, x = x, y
        elif octant == 2:
            y, x = x, -y
        elif octant == 3:
            y, x = y, -x
        elif octant == 4:
            y, x = -y, -x
        elif octant == 5:
            y, x = -x, -y
        elif octant == 6:
            y, x = -x, y
        elif octant == 7:
            y, x = -y, x
        return y, x

    def stop(self):
        self.running = False


class Image_draw_thread():
    def __init__(self, w, h):
        # keep image same size as pixmap (avoid coordinate mismatch)
        self.draw_image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.running = True

    def run(self):
        while self.running:
            try:
                tool, data = compute_to_image_render_thread.get(timeout=0.1)
                if tool == "free hand":
                    points, colour = data
                    point1, point2 = points
                    red, green, bleu = colour
                    # bounds-safe putpixel
                    w, h = self.draw_image.size
                    if point1 is not None and 0 <= point1[0] < w and 0 <= point1[1] < h:
                        self.draw_image.putpixel(point1, (int(red or 0), int(green or 0), int(bleu or 0)))
                    if point2 is not None:
                        draw = ImageDraw.Draw(self.draw_image)
                        draw.line((point1[0], point1[1], point2[0], point2[1]), fill=(int(red or 0), int(green or 0), int(bleu or 0)), width=1)
                if tool == "save":
                    self.draw_image.save("map_image.png", format="png")
            except queue.Empty:
                pass

            # non-blocking shutdown check
            try:
                msg = shutdown_queue.get_nowait()
                if msg == "shut down":
                    self.stop()
                    thread_finished_send.put("finished_thread")
            except queue.Empty:
                pass

    def stop(self):
        self.running = False


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        map_path = QFileDialog.getOpenFileName(None, "Select Map Image", "", "Images (*.png *.jpg *.bmp)")[0]
        if map_path:
            window = MainWindow(map_path)
            window.show()
            sys.exit(app.exec_())
        else:
            print("[main] No file selected. Exiting.")
    except Exception as e:
        import traceback
        print("Exception during startup:", e)
        traceback.print_exc()
