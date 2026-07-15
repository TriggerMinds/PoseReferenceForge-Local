from PySide6 import QtWidgets, QtCore


class PropertiesPanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)

        # Joint info group
        grp_joint = QtWidgets.QGroupBox("Selected Joint")
        joint_layout = QtWidgets.QFormLayout(grp_joint)
        self.lbl_joint_id = QtWidgets.QLabel("None")
        self.lbl_state = QtWidgets.QLabel("—")
        self.lbl_confidence = QtWidgets.QLabel("—")
        self.lbl_position = QtWidgets.QLabel("—")
        self.lbl_depth = QtWidgets.QLabel("—")
        joint_layout.addRow("Joint:", self.lbl_joint_id)
        joint_layout.addRow("State:", self.lbl_state)
        joint_layout.addRow("Confidence:", self.lbl_confidence)
        joint_layout.addRow("Position:", self.lbl_position)
        joint_layout.addRow("Depth:", self.lbl_depth)

        self.btn_lock = QtWidgets.QPushButton("Lock Joint")
        self.btn_reset = QtWidgets.QPushButton("Reset Joint")
        joint_layout.addRow(self.btn_lock)
        joint_layout.addRow(self.btn_reset)

        layout.addWidget(grp_joint)

        # Depth controls
        grp_depth = QtWidgets.QGroupBox("Depth Adjustment")
        depth_layout = QtWidgets.QVBoxLayout(grp_depth)
        self.depth_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.depth_slider.setRange(-100, 100)
        self.depth_slider.setValue(0)
        depth_layout.addWidget(QtWidgets.QLabel("Move closer / farther"))
        depth_layout.addWidget(self.depth_slider)
        layout.addWidget(grp_depth)

        # Warnings
        grp_warnings = QtWidgets.QGroupBox("Warnings")
        warnings_layout = QtWidgets.QVBoxLayout(grp_warnings)
        self.warnings_list = QtWidgets.QListWidget()
        warnings_layout.addWidget(self.warnings_list)
        layout.addWidget(grp_warnings)

        layout.addStretch()

    def set_joint_info(self, joint_id: str, state: str, confidence: float, x: float, y: float, z: float):
        self.lbl_joint_id.setText(joint_id)
        self.lbl_state.setText(state)
        self.lbl_confidence.setText(f"{confidence:.3f}")
        self.lbl_position.setText(f"({x:.1f}, {y:.1f}, {z:.1f})")
        self.lbl_depth.setText(f"{z:.1f}")

    def clear_joint(self):
        self.lbl_joint_id.setText("None")
        self.lbl_state.setText("—")
        self.lbl_confidence.setText("—")
        self.lbl_position.setText("—")
        self.lbl_depth.setText("—")

    def add_warning(self, msg: str):
        self.warnings_list.addItem(msg)

    def clear_warnings(self):
        self.warnings_list.clear()
