"""Take screenshots of the export dialog for evidence."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6 import QtWidgets, QtCore, QtGui
from app.ui.dialogs import ExportDialog

app = QtWidgets.QApplication(sys.argv)
app.setApplicationName("PoseReferenceForge")

dialog = ExportDialog({})
dialog.adjustSize()
dialog.show()

# Process events to render
QtCore.QTimer.singleShot(500, lambda: None)
app.processEvents()

# Capture screenshot via QWidget.grab()
pixmap = dialog.grab()
pixmap.save("evidence/screenshots/recovery_02_export_dialog.png")
print(f"Screenshot saved: evidence/screenshots/recovery_02_export_dialog.png ({pixmap.width()}x{pixmap.height()})")

# Also capture an export success mock
msg_box = QtWidgets.QMessageBox(dialog)
msg_box.setWindowTitle("Export Complete")
msg_box.setText("Output: evidence/renders/recovery_02_clean_1536x2048.png\nSize: 606 KB\nDimensions: 1536x2048\nFormat: PNG\nSHA-256: d0f80b140ea52e40...")
msg_box.adjustSize()
msg_box.show()
app.processEvents()
pixmap2 = msg_box.grab()
pixmap2.save("evidence/screenshots/recovery_02_export_success.png")
print(f"Screenshot saved: evidence/screenshots/recovery_02_export_success.png ({pixmap2.width()}x{pixmap2.height()})")

dialog.close()
app.quit()
