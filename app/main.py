import sys
import os

# Ensure the repo root is on sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from PySide6 import QtWidgets
from app.ui.main_window import MainWindow
from app.config.settings import Settings


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("PoseReferenceForge")
    app.setOrganizationName("PoseReferenceForge")
    app.setApplicationVersion("1.0.0-dev")

    # Initialize settings
    Settings.get()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
