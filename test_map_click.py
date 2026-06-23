import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from ui.page_live_map import LiveMapPage

app = QApplication(sys.argv)
page = LiveMapPage()
page.show()

def trigger_js():
    page.map_view.page().runJavaScript('console.log("FLY_TO:10.0,20.0");')
    print("JS triggered.")

def catch_signal(lat, lon):
    print(f"SUCCESS: Signal caught! {lat}, {lon}")
    app.quit()

page.fly_command_requested.connect(catch_signal)
QTimer.singleShot(2000, trigger_js)
QTimer.singleShot(4000, app.quit)

app.exec_()
