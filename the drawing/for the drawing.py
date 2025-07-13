import os
import queue
import shutil
import sys
from io import StringIO
from PIL import Image, ImageDraw, ImageOps
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QFileDialog,
    QGraphicsPixmapItem, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QCheckBox, QListWidget, QAbstractItemView
)

#do not use in nay online application we trust the provider of the image as it is the user itself
Image.MAX_IMAGE_PIXELS = None
#creating a way to send each draw to the thread
drawing_queue = queue.Queue()
#for the province id that is used
province_id = 1
province_id_max = 1
#for the deleting the temporary map used
delete_file_list = []

def iMage_expend(iMage_pass,paint_point):
    #geting the width and height for indexing
    width ,height = iMage_pass.size
    paint_point_x, paint_point_y = paint_point
    left = top = right = bottom = 0
    #from width to index
    width_index = width - 1
    height_index = height - 1
    #cheking if and by how much the point is out of bounds
    if paint_point_x < 0:
        left = abs(paint_point_x)
    elif width_index < paint_point_x:
        right = paint_point_x - width_index

    if paint_point_y < 0:
        top = abs(paint_point_y)
    elif height_index < paint_point_y:
        bottom = paint_point_y - height_index
    #expanding the image
    expand = (left,top,right,bottom)
    iMage_pass = ImageOps.expand(image= iMage_pass,border=expand,fill=(0,0,0,0))
    return iMage_pass, expand

class ImageDrawingThread(QThread):
    def __init__(self):
        super().__init__()
        self.running = True
        self.provinces = {}
        self.paint_reqeust = 0
        self.save_reqeust = 0
    def run(self):
        while self.running:
            #trying to get the tool and do the action if the queue is empty
            try:
                data ,tool = drawing_queue.get(timeout=0.1)
                if (data, tool) != (None, None):
                    if tool == "add":
                        point1 , point2 , province_id_temporary = data
                        self.add(point1, point2,province_id_temporary)
                    if tool == "save":
                        self.save_provinces()
            except queue.Empty:
                continue
    def add(self,point1, point2,province_id_temporary):
        #if the province does exist do this
        if f"province_{province_id_temporary}" in self.provinces and f"metadata_{province_id_temporary}" in self.provinces:
            #using the id get the colour and getting the files from memory we use
            red, green, bleu = extract_rgb_divmod(province_id_temporary)
            meta_data = self.provinces[f"metadata_{province_id_temporary}"]
            province_file = self.provinces[f"province_{province_id_temporary}"]
            meta_data.seek(0)
            #getting the center of the map compared to the top left for translation
            meta_data_line_ignore = meta_data.readline()
            del meta_data_line_ignore
            province_map_center_txt = meta_data.readline()
            list_str_province_map_center_txt = province_map_center_txt.split(",")
            map_cent_x = list_str_province_map_center_txt[0]
            map_cent_y = list_str_province_map_center_txt[1]
            province_map_center = (int(map_cent_x), int(map_cent_y))
            #setting the point compared to the center of the top left of the image
            dist_point_to_map_center = (point1[0] - province_map_center[0],point1[1] - province_map_center[1])
            province_file, index_change = iMage_expend(province_file,dist_point_to_map_center)
            #adjusting for the change in image size
            dist_point_to_map_center = (dist_point_to_map_center[0] - index_change[0],dist_point_to_map_center[1] - index_change[1])
            province_map_center = (province_map_center[0] - index_change[0], province_map_center[1] - index_change[1])
            #writing the data to the files
            province_file.putpixel(dist_point_to_map_center,(red,bleu,green,255))
            meta_data.seek(0)
            meta_data.truncate(0)
            meta_data.seek(0)
            meta_data.write(f"0,0\n{province_map_center[0]},{province_map_center[1]}\n")
            meta_data.seek(0)
            #repeat step one with a line if there are 2 points
            if point2 is not None:
                line_origin = dist_point_to_map_center
                dist_point_to_map_center = (point2[0] - province_map_center[0], point2[1] - province_map_center[1])
                province_file,index_change1 = iMage_expend(province_file,dist_point_to_map_center)

                dist_point_to_map_center = (dist_point_to_map_center[0] - index_change1[0], dist_point_to_map_center[1] - index_change1[1])
                province_map_center = (province_map_center[0] - index_change1[0],province_map_center[1] - index_change1[1])
                draw = ImageDraw.Draw(province_file)
                draw.line((line_origin[0],line_origin[1],dist_point_to_map_center[0],dist_point_to_map_center[1]),fill=(red,bleu,green,255),width=1)
                meta_data.seek(0)
                meta_data.truncate(0)
                meta_data.seek(0)
                meta_data.write(f"0,0\n{province_map_center[0]},{province_map_center[1]}\n")
                meta_data.seek(0)
            self.provinces[f"metadata_{province_id_temporary}"] = meta_data
            self.provinces[f"province_{province_id_temporary}"] = province_file
        #if the province is new create it
        else:
            meta_data = StringIO()
            first_write = (0, 0)
            province_file = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
            red, green, bleu = extract_rgb_divmod(province_id_temporary)
            province_file.putpixel(xy=first_write,value=(red,green,bleu,255))
            first_line = f"{first_write[0]},{first_write[1]}\n{point1[0]},{point1[1]}\n"
            meta_data.write(first_line)
            meta_data.seek(0)
            self.provinces[f"metadata_{province_id_temporary}"] = meta_data
            self.provinces[f"province_{province_id_temporary}"] = province_file
        
    def save_provinces(self):
        # creating the saved provinces list and the directory
        saved_province = []
        os.makedirs("save" , exist_ok=True)
        for i , j in self.provinces.items():
            key_str = i
            file = j
            lst_prov_key = key_str.split("_")
            prov_key = lst_prov_key[1]
            # create province directory if it does not exist and checking the type to save it as the right file type
            os.makedirs("save",exist_ok=True)
            if prov_key not in saved_province:
                saved_province.append(prov_key)
                os.makedirs(f"save/province_{prov_key}" , exist_ok=True)
                print("add to save prov")
            if isinstance(file , Image.Image):
                file.save(f"province_image_{prov_key}.png" , format="png")
                shutil.move(f"province_image_{prov_key}.png" ,
                            f"save/province_{prov_key}/province_image_{prov_key}.png")
                print(f"saved image {prov_key}")
            else:
                text_file = file.getvalue()
                with open(f"province_metadata_{prov_key}.txt" , "w") as output_file:
                    output_file.write(text_file)
                shutil.move(f"province_metadata_{prov_key}.txt" ,
                            f"save/province_{prov_key}/province_metadata_{prov_key}.txt")
                print(f"saved image {prov_key}")
        num_id = len(self.provinces) / 2
        map_image = Image.new("RGBA" , (13500 , 6750) , (0 , 0 , 0 , 0))
        p = 1
        while p < num_id:
            province = self.provinces[f"province_{p}"]
            meta_data = self.provinces[f"metadata_{p}"]
            discard = meta_data.readline()
            paste_point = meta_data.readline()
            del discard
            paste_point_lst = paste_point.split(",")
            x_paste = paste_point_lst[0]
            y_paste = paste_point_lst[1]
            map_image.paste(province , (x_paste , y_paste) , province)
            p += 1
        map_image.save("map_image_total.png" , format="png")
def province_select(new_id, add_new):
    #change the province id we are drawing with
    global province_id, province_id_max
    if add_new:
        province_id_max += 1
        province_id = province_id_max
    else:
        province_id = new_id
    return province_id, province_id_max

def extract_rgb_divmod(color_24bit):
    #getting a rgb valeus from the id
    blue = color_24bit % 256
    color_24bit //= 256
    green = color_24bit % 256
    color_24bit //= 256
    red = color_24bit % 256
    return red, green, blue

class MyDrawWindow(QGraphicsView):
    def __init__(self, map_path):
        super().__init__()
        #the data for drawing
        self.province_id_last = None
        self.mouse_pressed = False
        self.last_paint_pos = None

        #creating the drawing scene and the background
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        one_colour_image = Image.open(map_path).convert(mode="RGB")
        palette = [
            150, 150, 150,
            0, 0, 0,
        ] + [0, 0, 0] * 254
        one_colour_image = one_colour_image.convert("P",palette=Image.ADAPTIVE,colors=2)
        one_colour_image.putpalette(palette)
        map_path = "use_image.png"
        one_colour_image.save(map_path,format="png")
        global delete_file_list
        delete_file_list.append(map_path)
        
        pixmap = QPixmap(map_path)
        self.original_pixmap = QPixmap(map_path)
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        
        self.drawing_pixmap = QPixmap(self.original_pixmap.size())
        self.drawing_pixmap.fill(Qt.transparent)
        self.drawing_item = QGraphicsPixmapItem(self.drawing_pixmap)
        self.scene.addItem(self.drawing_item)

        self.fitInView(self.drawing_item, Qt.KeepAspectRatio)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setFocusPolicy(Qt.StrongFocus)

        #starting the thread
        self.worker = ImageDrawingThread()
        self.worker.start()


    def draw_at_position(self, scene_pos):
        #using the id it sends the data where was drawn and the selected id
        global province_id
        if province_id != self.province_id_last:
            self.last_paint_pos = None
        item_pos = self.pixmap_item.mapFromScene(scene_pos)
        x = int(item_pos.x())
        y = int(item_pos.y())
        painter = QPainter(self.drawing_pixmap)
        red, green, bleu = extract_rgb_divmod(province_id)
        painter.setPen(QPen(QColor(red, green, bleu), 1))
        if self.last_paint_pos and self.last_paint_pos != item_pos:
            painter.drawLine(x, y, int(self.last_paint_pos.x()), int(self.last_paint_pos.y()))
            point2 = (int(self.last_paint_pos.x()), int(self.last_paint_pos.y()))
            self.start_worker((x,y),point2, province_id,"add")
        else:
            painter.drawPoint(x, y)
            self.start_worker((x,y),None,province_id,"add")
        painter.end()
        #drawing to the ui
        self.drawing_item.setPixmap(self.drawing_pixmap)
        self.last_paint_pos = item_pos
        self.province_id_last = province_id

    def start_worker(self, point1, point2,pid,tool):
        data = (point1,point2,pid)
        drawing_queue.put((data,tool))

    def on_worker_finished(self, updated_provinces,save):
        pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = True
            self.draw_at_position(self.mapToScene(event.pos()))

    def mouseMoveEvent(self, event):
        if self.mouse_pressed:
            self.draw_at_position(self.mapToScene(event.pos()))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed = False

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        delta = event.angleDelta().y()
        zoom_factor = zoom_in_factor if delta > 0 else zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - 100)
        elif event.key() == Qt.Key_Down:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + 100)
        elif event.key() == Qt.Key_Left:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - 100)
        elif event.key() == Qt.Key_Right:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + 100)
        elif event.key() == Qt.Key_Escape:
            self.parent().close()
        elif event.key() == Qt.Key_R:
            self.resetTransform()
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def get_size(self):
        return self.width()

class province_widget(QWidget):
    def __init__(self):
        super().__init__()
        #creating the list that holds all the province
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)

        self.item = ["province:1"]
        self.list_widget.addItems(self.item)
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)

        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def add_item(self):
        #adding a new province to the list depending on id
        global province_id
        self.item.append(f"province:{province_id}")
        self.list_widget.clear()
        self.list_widget.addItems(self.item)

    def on_selection_changed(self):
        #when the selection does change
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            item = selected_items[0].text()
            item_split = item.split(":")
            province_select(int(item_split[1]), False)

class setting_widget(QWidget):
    def __init__(self, size):
        #adding all to the settings window
        super().__init__()
        self.setFixedWidth(size)

        layout = QVBoxLayout()
        self.list_province = province_widget()

        make_new_province_button = QPushButton("new province")
        make_new_province_button.clicked.connect(self.new_province_clicked)
        layout.addWidget(make_new_province_button)

        sea_or_land = QCheckBox("sea province")
        layout.addWidget(sea_or_land)

        layout.addWidget(self.list_province)

        save_button = QPushButton("save")
        save_button.clicked.connect(self.save_file)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def new_province_clicked(self):
        province_select(974, True)
        self.list_province.add_item()
    def save_file(self):
        drawing_queue.put(((None),"save"))
        print("just in case")

class MainWindow(QMainWindow):
    def __init__(self, map_path):
        #adding everything to the main window
        super().__init__()
        self.setWindowTitle("Simple PyQt Window with QGraphicsView Zooming")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        self.map_path = map_path

        self.draw_widget = MyDrawWindow(self.map_path)
        size = self.draw_widget.get_size()
        self.leftside = setting_widget(size)

        layout.addWidget(self.leftside)
        layout.addWidget(self.draw_widget)
        self.resize(1920, 1440)
    def closeEvent(self, a0):
        global delete_file_list
        for i in delete_file_list:
            path = i
            os.remove(path=path)
        a0.accept()
#geting the image to draw to
app = QApplication(sys.argv)
map_path = QFileDialog.getOpenFileName(None, "Select Map Image", "", "Images (*.png *.jpg *.bmp)")[0]

if map_path:
    window = MainWindow(map_path)
    window.show()
    sys.exit(app.exec_())
else:
    print("[main] No file selected. Exiting.")