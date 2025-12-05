import datetime
import os
import sys
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk
import cv2
import numpy as np


class QRCameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("QR Scanner")  # Tên app trên title bar
        self.root.geometry("1280x750")
        self.root.minsize(1200, 700)
        
        # Đặt icon cho cửa sổ (nếu file tồn tại)
        # Hỗ trợ cả chế độ phát triển và PyInstaller bundle
        if getattr(sys, 'frozen', False):
            # Chạy từ file .exe (PyInstaller)
            base_path = sys._MEIPASS
        else:
            # Chạy từ script Python
            base_path = os.path.dirname(__file__)
        
        icon_path = os.path.join(base_path, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass  # Bỏ qua nếu không set được icon

        # === PALETTE MÀU CÔNG NGHỆ NÂNG CAP ===
        self.bg_main = "#0a0e27"        # nền chính đậm hơn
        self.bg_panel = "#131829"       # nền card
        self.bg_card = "#0d1117"        # bên trong card
        self.bg_gradient_start = "#1a1f3a"
        self.bg_gradient_end = "#0f1419"
        self.accent_blue = "#60a5fa"    # xanh dương sáng
        self.accent_cyan = "#22d3ee"    # xanh cyan
        self.accent_purple = "#c084fc"  # tím pastel
        self.accent_green = "#34d399"   # xanh lá
        self.accent_yellow = "#fbbf24"  # vàng
        self.accent_red = "#f87171"     # đỏ
        self.text_primary = "#f1f5f9"
        self.text_secondary = "#cbd5e1"
        self.text_muted = "#94a3b8"
        self.border_color = "#1e293b"
        self.border_accent = "#334155"

        self.root.configure(bg=self.bg_main)

        # Camera
        self.cap = None
        self.is_running = False

        # Thư mục lưu QR
        self.output_dir = None

        # Ảnh đang hiển thị
        self.frame_tk = None

        # Lưu QR đã lưu để tránh trùng (trong session hiện tại)
        self.saved_codes = set()
        
        # Lưu danh sách mã QR đã có trong folder xuất (dựa trên nội dung)
        self.existing_qr_contents = set()
        
        # Thống kê
        self.qr_count = 0
        self.duplicate_count = 0
        self.session_start_time = None

        # Tùy chọn tăng cường ảnh
        self.use_enhance = tk.BooleanVar(value=True)
        
        # Animation variables
        self.pulse_alpha = 0
        self.pulse_direction = 1
        self.scan_line_y = 0
        self.scan_direction = 1
        self.gradient_offset = 0
        self.button_hover_scale = {}
        self.notification_queue = []
        self.current_notification = None
        self.particles = []  # For particle effects
        self.rainbow_offset = 0

        # Tạo style hiện đại
        self._setup_style()

        # Xây dựng giao diện
        self._build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Start animations
        self._start_animations()

    # ================== STYLE ==================

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Frame styles
        style.configure(
            "Tech.TFrame",
            background=self.bg_panel,
            borderwidth=0,
        )

        style.configure(
            "TechCard.TFrame",
            background=self.bg_card,
            borderwidth=0,
        )
        
        style.configure(
            "Main.TFrame",
            background=self.bg_main,
            borderwidth=0,
        )

        # Label styles
        style.configure(
            "Tech.TLabel",
            background=self.bg_panel,
            foreground=self.text_primary,
            font=("Segoe UI", 10),
        )
        
        style.configure(
            "TechSecondary.TLabel",
            background=self.bg_panel,
            foreground=self.text_secondary,
            font=("Segoe UI", 10),
        )

        style.configure(
            "TechMuted.TLabel",
            background=self.bg_panel,
            foreground=self.text_muted,
            font=("Segoe UI", 9),
        )

        style.configure(
            "TechTitle.TLabel",
            background=self.bg_main,
            foreground=self.accent_cyan,
            font=("Segoe UI", 22, "bold"),
        )

        style.configure(
            "TechSubTitle.TLabel",
            background=self.bg_main,
            foreground=self.text_muted,
            font=("Segoe UI", 10),
        )
        
        style.configure(
            "CardTitle.TLabel",
            background=self.bg_panel,
            foreground=self.text_primary,
            font=("Segoe UI", 11, "bold"),
        )
        
        style.configure(
            "StatValue.TLabel",
            background=self.bg_card,
            foreground=self.accent_cyan,
            font=("Segoe UI", 20, "bold"),
        )
        
        style.configure(
            "StatLabel.TLabel",
            background=self.bg_card,
            foreground=self.text_muted,
            font=("Segoe UI", 9),
        )

        style.configure(
            "TechBadge.TLabel",
            background=self.accent_green,
            foreground="#000000",
            font=("Segoe UI", 8, "bold"),
            padding=(8, 2),
        )

        # Button styles
        style.configure(
            "Tech.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=10,
            borderwidth=0,
            focusthickness=0,
        )

        style.configure(
            "TechToggle.TCheckbutton",
            background=self.bg_panel,
            foreground=self.text_secondary,
            font=("Segoe UI", 9),
        )

        style.map(
            "Tech.TButton",
            foreground=[("disabled", "#6b7280"), ("active", "#ffffff")],
        )

    # ================== UI ==================

    def _build_ui(self):
        # ----- HEADER -----
        header_container = tk.Frame(self.root, bg=self.bg_main)
        header_container.pack(fill=tk.X, padx=20, pady=(16, 10))
        
        # Gradient effect simulation with Canvas
        header_canvas = tk.Canvas(
            header_container, 
            height=80, 
            bg=self.bg_panel,
            highlightthickness=0,
            bd=0
        )
        header_canvas.pack(fill=tk.X)
        
        # Title section
        title_frame = ttk.Frame(header_canvas, style="Tech.TFrame")
        header_canvas.create_window(20, 15, anchor="nw", window=title_frame)

        self.title_label = ttk.Label(
            title_frame,
            text="⚡ BỘ NHẬN DIỆN QR AI VISION",
            style="TechTitle.TLabel",
        )
        self.title_label.pack(anchor="w")

        subtitle = ttk.Label(
            title_frame,
            text="Thị Giác Máy Tính Nâng Cao • Nhận Diện Thời Gian Thực • Xử Lý Nhiều QR",
            style="TechSubTitle.TLabel",
        )
        subtitle.pack(anchor="w", pady=(4, 0))
        
        # Badge
        badge_frame = ttk.Frame(header_canvas, style="Tech.TFrame")
        header_canvas.create_window(header_canvas.winfo_width(), 25, anchor="ne", window=badge_frame)
        
        badge = ttk.Label(
            badge_frame,
            text=" BETA v1.0 ",
            style="TechBadge.TLabel",
        )
        badge.pack(side=tk.RIGHT, padx=20)

        # ----- STATISTICS PANEL -----
        stats_container = tk.Frame(self.root, bg=self.bg_main)
        stats_container.pack(fill=tk.X, padx=20, pady=(0, 12))
        
        # Stats cards
        stats_frame = tk.Frame(stats_container, bg=self.bg_main)
        stats_frame.pack(fill=tk.X)
        
        # QR Count stat
        self.qr_stat_card = tk.Frame(
            stats_frame,
            bg=self.bg_card,
            highlightbackground=self.accent_cyan,
            highlightthickness=2,
        )
        self.qr_stat_card.pack(side=tk.LEFT, padx=(0, 10), ipadx=20, ipady=10)
        
        self.qr_count_label = ttk.Label(
            self.qr_stat_card,
            text="0",
            style="StatValue.TLabel",
        )
        self.qr_count_label.pack()
        
        qr_stat_desc = ttk.Label(
            self.qr_stat_card,
            text="Mã QR Đã Phát Hiện",
            style="StatLabel.TLabel",
        )
        qr_stat_desc.pack()
        
        # Status stat
        status_stat_card = tk.Frame(
            stats_frame,
            bg=self.bg_card,
            highlightbackground=self.accent_purple,
            highlightthickness=2,
        )
        status_stat_card.pack(side=tk.LEFT, padx=(0, 10), ipadx=20, ipady=10)
        
        self.status_icon_label = ttk.Label(
            status_stat_card,
            text="●",
            style="StatValue.TLabel",
            foreground=self.text_muted,
        )
        self.status_icon_label.pack()
        
        self.status_text_label = ttk.Label(
            status_stat_card,
            text="Chờ",
            style="StatLabel.TLabel",
        )
        self.status_text_label.pack()
        
        # Session time stat
        time_stat_card = tk.Frame(
            stats_frame,
            bg=self.bg_card,
            highlightbackground=self.accent_yellow,
            highlightthickness=2,
        )
        time_stat_card.pack(side=tk.LEFT, padx=(0, 10), ipadx=20, ipady=10)
        
        self.session_time_label = ttk.Label(
            time_stat_card,
            text="00:00",
            style="StatValue.TLabel",
        )
        self.session_time_label.pack()
        
        time_stat_desc = ttk.Label(
            time_stat_card,
            text="Thời Gian Phiên",
            style="StatLabel.TLabel",
        )
        time_stat_desc.pack()
        
        # Duplicate count stat
        duplicate_stat_card = tk.Frame(
            stats_frame,
            bg=self.bg_card,
            highlightbackground=self.accent_red,
            highlightthickness=2,
        )
        duplicate_stat_card.pack(side=tk.LEFT, ipadx=20, ipady=10)
        
        self.duplicate_count_label = ttk.Label(
            duplicate_stat_card,
            text="0",
            style="StatValue.TLabel",
            foreground=self.accent_red,
        )
        self.duplicate_count_label.pack()
        
        duplicate_stat_desc = ttk.Label(
            duplicate_stat_card,
            text="Mã QR Trùng",
            style="StatLabel.TLabel",
        )
        duplicate_stat_desc.pack()

        # ----- CONTROL BAR -----
        control_panel = tk.Frame(self.root, bg=self.bg_main)
        control_panel.pack(fill=tk.X, padx=20, pady=(0, 12))

        # Panel có border phát sáng
        container = tk.Frame(
            control_panel,
            bg=self.bg_panel,
            highlightbackground=self.border_accent,
            highlightthickness=2,
            bd=0,
        )
        container.pack(fill=tk.X)

        controls_inner = ttk.Frame(container, style="Tech.TFrame")
        controls_inner.pack(fill=tk.X, padx=15, pady=12)

        # Nút điều khiển
        btn_frame = ttk.Frame(controls_inner, style="Tech.TFrame")
        btn_frame.pack(side=tk.LEFT)
        
        self.btn_select_dir = ttk.Button(
            btn_frame,
            text="📁  Chọn Thư Mục Lưu",
            style="Tech.TButton",
            command=lambda: self._button_click_animation(self.choose_output_dir),
        )
        self.btn_select_dir.grid(row=0, column=0, padx=(0, 8), pady=0)
        self._color_button(self.btn_select_dir, self.border_accent, self.text_primary)

        self.btn_open_image = ttk.Button(
            btn_frame,
            text="🖼️  Mở Ảnh & Quét",
            style="Tech.TButton",
            command=lambda: self._button_click_animation(self.open_image_and_detect),
        )
        self.btn_open_image.grid(row=0, column=1, padx=(0, 8), pady=0)
        self._color_button(self.btn_open_image, self.accent_green, "#000000")

        self.btn_start = ttk.Button(
            btn_frame,
            text="📷  Bật Camera",
            style="Tech.TButton",
            command=lambda: self._button_click_animation(self.start_camera),
        )
        self.btn_start.grid(row=0, column=2, padx=(0, 8), pady=0)
        self._color_button(self.btn_start, self.accent_blue, "#000000")

        self.btn_reset = ttk.Button(
            btn_frame,
            text="🔄  Đặt Lại",
            style="Tech.TButton",
            command=lambda: self._button_click_animation(self.reset_app),
        )
        self.btn_reset.grid(row=0, column=3, padx=0, pady=0)
        self._color_button(self.btn_reset, self.accent_red, "#000000")

        # Bên phải: settings
        right_controls = ttk.Frame(controls_inner, style="Tech.TFrame")
        right_controls.pack(side=tk.RIGHT)
        
        self.dir_label = ttk.Label(
            right_controls,
            text="📂 Đầu ra: (tự tạo 'qr_output' nếu chưa đặt)",
            style="TechMuted.TLabel",
            justify="right",
        )
        self.dir_label.pack(anchor="e")

        enhance_chk = ttk.Checkbutton(
            right_controls,
            text="⚡ Bật Tăng Cường Ảnh (CLAHE + Làm Nét)",
            variable=self.use_enhance,
            style="TechToggle.TCheckbutton",
        )
        enhance_chk.pack(anchor="e", pady=(6, 0))

        # ----- MAIN CONTENT: LEFT VIDEO / RIGHT LOG -----
        main = tk.Frame(self.root, bg=self.bg_main)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))

        # Left card: video (60% width)
        video_outer = tk.Frame(
            main,
            bg=self.bg_panel,
            highlightbackground=self.accent_blue,
            highlightthickness=2,
        )
        video_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        video_header = ttk.Frame(video_outer, style="Tech.TFrame")
        video_header.pack(fill=tk.X, padx=15, pady=(12, 8))

        video_title = ttk.Label(
            video_header,
            text="📹 Camera / Trình Xem Ảnh",
            style="CardTitle.TLabel",
        )
        video_title.pack(side=tk.LEFT)

        video_subtitle = ttk.Label(
            video_header,
            text="Nhận diện trực tiếp với khung bao quanh",
            style="TechMuted.TLabel",
        )
        video_subtitle.pack(side=tk.LEFT, padx=(10, 0))

        # Separator line
        sep1 = tk.Frame(video_outer, height=1, bg=self.border_color)
        sep1.pack(fill=tk.X, padx=15)

        # Video card body with canvas overlay for scan line
        video_body = tk.Frame(video_outer, bg=self.bg_card, bd=0)
        video_body.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        
        # Create canvas for overlay effects
        self.video_canvas = tk.Canvas(
            video_body,
            bg="#000000",
            highlightthickness=0
        )
        self.video_canvas.pack(fill=tk.BOTH, expand=True)

        self.label_video = tk.Label(
            self.video_canvas, 
            bg="#000000",
            text="📷\n\nChưa có camera hoặc ảnh được tải\n\nNhấn 'Bật Camera' hoặc 'Mở Ảnh & Quét'",
            fg=self.text_muted,
            font=("Segoe UI", 12),
        )
        self.video_canvas.create_window(
            400, 300, 
            anchor='center',
            window=self.label_video,
            tags="video"
        )
        
        # Bind canvas resize
        self.video_canvas.bind('<Configure>', self._on_canvas_resize)

        # Right card: log (40% width)
        log_outer = tk.Frame(
            main,
            bg=self.bg_panel,
            highlightbackground=self.accent_purple,
            highlightthickness=2,
        )
        log_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_header = ttk.Frame(log_outer, style="Tech.TFrame")
        log_header.pack(fill=tk.X, padx=15, pady=(12, 8))

        log_title = ttk.Label(
            log_header,
            text="📋 Nhật Ký Sự Kiện",
            style="CardTitle.TLabel",
        )
        log_title.pack(side=tk.LEFT)

        log_sub = ttk.Label(
            log_header,
            text="Luồng hoạt động thời gian thực",
            style="TechMuted.TLabel",
        )
        log_sub.pack(side=tk.LEFT, padx=(10, 0))

        # Separator line
        sep2 = tk.Frame(log_outer, height=1, bg=self.border_color)
        sep2.pack(fill=tk.X, padx=15)

        # log body
        log_body = tk.Frame(log_outer, bg=self.bg_card, bd=0)
        log_body.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        scrollbar = tk.Scrollbar(log_body, bg=self.bg_card, troughcolor=self.bg_card)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_log = tk.Text(
            log_body,
            bg=self.bg_card,
            fg=self.text_secondary,
            insertbackground=self.accent_cyan,
            font=("Consolas", 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=8,
            pady=8,
            yscrollcommand=scrollbar.set,
        )
        self.text_log.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_log.yview)
        
        # Configure text tags for colored log messages
        self.text_log.tag_configure("success", foreground=self.accent_green)
        self.text_log.tag_configure("info", foreground=self.accent_cyan)
        self.text_log.tag_configure("warning", foreground=self.accent_yellow)
        self.text_log.tag_configure("error", foreground=self.accent_red)
        self.text_log.tag_configure("highlight", foreground=self.accent_purple)

        # ----- STATUS BAR -----
        status_bar = tk.Frame(
            self.root, 
            bg=self.bg_panel,
            highlightbackground=self.border_color,
            highlightthickness=1,
        )
        status_bar.pack(fill=tk.X, padx=20, pady=(0, 12))

        status_inner = tk.Frame(status_bar, bg=self.bg_panel)
        status_inner.pack(fill=tk.X, padx=12, pady=8)

        self.status_label = tk.Label(
            status_inner,
            text="● Sẵn Sàng",
            bg=self.bg_panel,
            fg=self.accent_green,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Footer info
        footer_info = tk.Label(
            status_inner,
            text="Được hỗ trợ bởi OpenCV & Python",
            bg=self.bg_panel,
            fg=self.text_muted,
            font=("Segoe UI", 8),
        )
        footer_info.pack(side=tk.RIGHT)

        # Welcome log with colored tags
        self._log_colored("🚀 Máy Quét QR AI Vision Đã Khởi Động", "success")
        self._log_colored("━" * 50, "info")
        self.log("📌 Hướng Dẫn Thiết Lập:")
        self.log("   1. (Tùy chọn) Chọn thư mục lưu cho ảnh QR")
        self.log("   2. Chọn: Mở File Ảnh HOẶC Bật Camera Trực Tiếp")
        self.log("   3. Mã QR sẽ được tự động phát hiện và lưu")
        self._log_colored("✨ Tăng Cường Ảnh: ĐÃ BẬT", "highlight")
        self._log_colored("━" * 50, "info")

    def _color_button(self, btn, bg, fg):
        # Tạo kiểu riêng cho từng nút bằng style name động
        style = ttk.Style()
        name = f"{id(btn)}.TButton"
        style.configure(
            name,
            background=bg,
            foreground=fg,
            borderwidth=0,
            focusthickness=0,
            focuscolor=bg,
            padding=8,
            relief="flat",
        )
        style.map(
            name,
            background=[("active", self._brighten(bg, 1.15))],
        )
        btn.configure(style=name)

    def _brighten(self, hex_color, factor):
        """Làm sáng màu hex một chút để hover đẹp hơn."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = min(int(r * factor), 255)
        g = min(int(g * factor), 255)
        b = min(int(b * factor), 255)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ================== TIỆN ÍCH ==================

    def set_status(self, text, color=None):
        if color is None:
            color = self.accent_cyan
        self.status_label.config(text=f"● {text}", fg=color)
        
        # Flash effect on status change
        original_bg = self.status_label.cget('background')
        self.status_label.config(background=self.border_color)
        self.root.after(150, lambda: self.status_label.config(background=original_bg))

    def log(self, msg):
        self._slide_in_log(msg)
    
    def _log_colored(self, msg, tag):
        """Log with color tag and animation: success, info, warning, error, highlight"""
        self._slide_in_log(msg, tag)
        
        # Show notification for important messages
        if tag == "success" and "Phát Hiện" in msg:
            self._show_notification("✅ Đã Phát Hiện Mã QR!", self.accent_green)
        elif tag == "error":
            self._show_notification("❌ Đã Xảy Ra Lỗi", self.accent_red)
    
    def _update_qr_count(self):
        """Update QR count display with animation"""
        old_count = int(self.qr_count_label.cget('text'))
        self._animate_count_up(self.qr_count_label, old_count, self.qr_count)
    
    def _on_canvas_resize(self, event):
        """Handle canvas resize for video label"""
        self.video_canvas.coords("video", event.width//2, event.height//2)

    def choose_output_dir(self):
        directory = filedialog.askdirectory(title="Chọn thư mục để lưu ảnh QR")
        if directory:
            self.output_dir = directory
            self.dir_label.config(text=f"📂 Đầu ra: {self.output_dir}")
            self._log_colored(f"📁 Đã cấu hình thư mục đầu ra: {self.output_dir}", "success")
            # Load danh sách mã QR đã có trong folder
            self._load_existing_qr_codes()
        else:
            self._log_colored("ℹ️ Chưa chọn thư mục. Sẽ tự tạo './qr_output'", "info")

    def ensure_output_dir(self):
        if self.output_dir is None:
            default_dir = os.path.join(os.getcwd(), "qr_output")
            if not os.path.exists(default_dir):
                os.makedirs(default_dir, exist_ok=True)
            self.output_dir = default_dir
            self.dir_label.config(text=f"📂 Đầu ra: {self.output_dir}")
            self._log_colored(f"📂 Đã tự tạo thư mục đầu ra: {self.output_dir}", "info")
            # Load danh sách mã QR đã có trong folder
            self._load_existing_qr_codes()
    
    def _get_metadata_file_path(self):
        """Lấy đường dẫn file metadata lưu thông tin mã QR"""
        if self.output_dir is None:
            return None
        return os.path.join(self.output_dir, ".qr_metadata.json")
    
    def _load_existing_qr_codes(self):
        """Load danh sách mã QR đã có trong folder từ file metadata"""
        self.existing_qr_contents.clear()
        
        if self.output_dir is None or not os.path.exists(self.output_dir):
            return
        
        metadata_file = self._get_metadata_file_path()
        
        # Đọc từ file metadata nếu có
        if metadata_file and os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    if 'qr_contents' in metadata:
                        self.existing_qr_contents = set(metadata['qr_contents'])
                        count = len(self.existing_qr_contents)
                        if count > 0:
                            self._log_colored(f"📋 Đã tải {count} mã QR từ folder xuất", "info")
            except Exception as e:
                self._log_colored(f"⚠️ Không thể đọc metadata: {str(e)}", "warning")
        
        # Quét lại các file ảnh trong folder để cập nhật (nếu cần)
        self._scan_folder_for_qr_codes()
    
    def _scan_folder_for_qr_codes(self):
        """Quét các file ảnh trong folder để tìm mã QR"""
        if self.output_dir is None or not os.path.exists(self.output_dir):
            return
        
        detector = cv2.QRCodeDetector()
        scanned_count = 0
        
        # Quét các file PNG trong folder
        for filename in os.listdir(self.output_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and filename.startswith('qr_'):
                file_path = os.path.join(self.output_dir, filename)
                try:
                    img = cv2.imread(file_path)
                    if img is None:
                        continue
                    
                    # Thử đọc mã QR từ ảnh
                    retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
                    if retval and decoded_info:
                        for content in decoded_info:
                            if content and content.strip():
                                self.existing_qr_contents.add(content.strip())
                                scanned_count += 1
                except Exception:
                    continue
        
        # Lưu lại metadata
        self._save_metadata()
        
        if scanned_count > 0:
            self._log_colored(f"🔍 Đã quét và tìm thấy {scanned_count} mã QR trong folder", "info")
    
    def _save_metadata(self):
        """Lưu metadata về mã QR vào file JSON"""
        if self.output_dir is None:
            return
        
        metadata_file = self._get_metadata_file_path()
        if metadata_file:
            try:
                metadata = {
                    'qr_contents': list(self.existing_qr_contents),
                    'last_updated': datetime.datetime.now().isoformat()
                }
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self._log_colored(f"⚠️ Không thể lưu metadata: {str(e)}", "warning")

    # ========== TĂNG CƯỜNG & LÀM NÉT ẢNH ==========

    def enhance_for_qr(self, frame):
        """
        Tăng cường QR:
        - Gray + CLAHE (tăng tương phản)
        - Unsharp mask (làm nét biên QR)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=1.0, sigmaY=1.0)
        sharp = cv2.addWeighted(gray, 1.6, blur, -0.6, 0)

        return sharp

    # ========== XỬ LÝ ẢNH FILE ==========

    def open_image_and_detect(self):
        if self.is_running:
            self._log_colored("⚠️ Đang dừng camera để xử lý file ảnh...", "warning")
            self.stop_camera()

        file_path = filedialog.askopenfilename(
            title="Mở ảnh",
            filetypes=(("File ảnh", "*.png;*.jpg;*.jpeg;*.bmp"), ("Tất cả file", "*.*")),
        )
        if not file_path:
            return

        self._log_colored(f"🖼️ Đang tải ảnh: {os.path.basename(file_path)}", "info")
        self.set_status("Đang xử lý ảnh...", self.accent_yellow)
        self.status_icon_label.config(text="⏳", foreground=self.accent_yellow)
        self.status_text_label.config(text="Đang xử lý...")

        img = cv2.imread(file_path)
        if img is None:
            messagebox.showerror("Lỗi", "Không thể đọc file ảnh.")
            self._log_colored("❌ Không thể đọc file ảnh", "error")
            self.set_status("Lỗi", self.accent_red)
            self.status_icon_label.config(text="✖", foreground=self.accent_red)
            self.status_text_label.config(text="Lỗi")
            return

        self.saved_codes.clear()
        self.qr_count = 0
        self.duplicate_count = 0
        self._update_qr_count()
        self.duplicate_count_label.config(text="0")
        
        # Load danh sách mã QR đã có trong folder
        self._load_existing_qr_codes()
        
        annotated = self.detect_and_save_from_frame(img)
        self.show_frame(annotated)
        self.set_status("Đã xử lý ảnh", self.accent_green)
        self.status_icon_label.config(text="✓", foreground=self.accent_green)
        self.status_text_label.config(text="Hoàn thành")
        self._log_colored("━" * 50, "info")

    # ========== CAMERA ==========

    def start_camera(self):
        if self.is_running:
            self.stop_camera()
            return

        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            messagebox.showerror("Lỗi", "Không thể mở camera. Vui lòng kiểm tra thiết bị của bạn.")
            self._log_colored("❌ Không thể mở thiết bị camera", "error")
            self.set_status("Lỗi camera", self.accent_red)
            self.status_icon_label.config(text="✖", foreground=self.accent_red)
            self.status_text_label.config(text="Lỗi")
            self.cap = None
            return

        self.is_running = True
        self.saved_codes.clear()
        self.qr_count = 0
        self.duplicate_count = 0
        self._update_qr_count()
        self.duplicate_count_label.config(text="0")
        self.session_start_time = datetime.datetime.now()
        
        # Load danh sách mã QR đã có trong folder
        self._load_existing_qr_codes()
        
        self.btn_start.config(text="⏹️  Dừng Camera")
        self._color_button(self.btn_start, self.accent_red, "#000000")
        
        self._log_colored("━" * 50, "info")
        self._log_colored("🎥 Camera Đã Bật - Nhận Diện Trực Tiếp Hoạt Động", "success")
        self.log("   → Đưa mã QR vào ống kính camera")
        self.log("   → Mã QR được phát hiện sẽ tự động lưu")
        
        self.set_status("Camera Hoạt Động", self.accent_green)
        self.status_icon_label.config(text="●", foreground=self.accent_green)
        self.status_text_label.config(text="Hoạt động")

        self._update_session_time()
        self.update_frame()

    def stop_camera(self):
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.btn_start.config(text="📷  Bật Camera")
        self._color_button(self.btn_start, self.accent_blue, "#000000")
        
        self.set_status("Camera Đã Dừng", self.text_muted)
        self.status_icon_label.config(text="●", foreground=self.text_muted)
        self.status_text_label.config(text="Chờ")
        
        self._log_colored("🛑 Camera đã dừng", "warning")
        self._log_colored("━" * 50, "info")

    def update_frame(self):
        if not self.is_running or self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            self._log_colored("❌ Không thể đọc khung hình từ camera", "error")
            self.stop_camera()
            return

        frame = cv2.flip(frame, 1)

        annotated = self.detect_and_save_from_frame(frame)
        self.show_frame(annotated)

        self.root.after(30, self.update_frame)
    
    def _update_session_time(self):
        """Update session time display"""
        if self.is_running and self.session_start_time:
            elapsed = datetime.datetime.now() - self.session_start_time
            minutes = int(elapsed.total_seconds() // 60)
            seconds = int(elapsed.total_seconds() % 60)
            self.session_time_label.config(text=f"{minutes:02d}:{seconds:02d}")
            self.root.after(1000, self._update_session_time)

    def show_frame(self, frame, max_size=(720, 520)):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        
        # Get actual canvas size
        canvas_w = self.video_canvas.winfo_width()
        canvas_h = self.video_canvas.winfo_height()
        
        if canvas_w > 1 and canvas_h > 1:
            max_w, max_h = canvas_w - 20, canvas_h - 20
        else:
            max_w, max_h = max_size
        
        scale = min(max_w / w, max_h / h, 1.0)
        new_w, new_h = int(w * scale), int(h * scale)
        if scale != 1.0:
            rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)

        img_pil = Image.fromarray(rgb)
        img_tk = ImageTk.PhotoImage(img_pil)

        self.label_video.config(image=img_tk, text="")
        self.label_video.image = img_tk
        self.frame_tk = img_tk
        
        # Center the video label in canvas
        if canvas_w > 1 and canvas_h > 1:
            self.video_canvas.coords("video", canvas_w//2, canvas_h//2)

    # ========== NHẬN DIỆN & LƯU QR ==========

    def detect_and_save_from_frame(self, frame):
        frame_for_detect = frame
        if self.use_enhance.get():
            frame_for_detect = self.enhance_for_qr(frame)

        detector = cv2.QRCodeDetector()
        points = None
        decoded_info = None

        try:
            retval, decoded_info, points, straight_qrcodes = detector.detectAndDecodeMulti(
                frame_for_detect
            )
            if not retval:
                points = None
        except Exception:
            data, points = detector.detectAndDecode(frame_for_detect)
            if data == "" or points is None:
                points = None
            else:
                decoded_info = [data]

        if points is None:
            return frame

        pts = np.array(points, dtype=np.float32)
        if pts.ndim == 2:
            pts = pts[np.newaxis, :, :]

        self.ensure_output_dir()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        for idx, qr_pts in enumerate(pts):
            qr_pts = qr_pts.reshape(-1, 2).astype(int)
            xs, ys = qr_pts[:, 0], qr_pts[:, 1]
            min_x, max_x = xs.min(), xs.max()
            min_y, max_y = ys.min(), ys.max()

            pad = 10
            x1 = max(min_x - pad, 0)
            y1 = max(min_y - pad, 0)
            x2 = min(max_x + pad, frame.shape[1])
            y2 = min(max_y + pad, frame.shape[0])
            if x2 <= x1 or y2 <= y1:
                continue

            roi = frame[y1:y2, x1:x2].copy()

            content = None
            if decoded_info is not None and idx < len(decoded_info):
                content = decoded_info[idx].strip()

            # Kiểm tra trùng lặp dựa trên nội dung mã QR
            is_duplicate = False
            duplicate_reason = ""
            
            if content:
                # Kiểm tra trong session hiện tại
                if content in self.saved_codes:
                    is_duplicate = True
                    duplicate_reason = "đã được phát hiện trong phiên này"
                # Kiểm tra trong folder xuất
                elif content in self.existing_qr_contents:
                    is_duplicate = True
                    duplicate_reason = "đã tồn tại trong folder xuất"
            else:
                # Nếu không đọc được nội dung, dùng key dựa trên vị trí
                key = f"{min_x}_{min_y}_{max_x}_{max_y}"
                if key in self.saved_codes:
                    is_duplicate = True
                    duplicate_reason = "đã được phát hiện trong phiên này (không đọc được nội dung)"
            
            if is_duplicate:
                # Mã QR trùng - hiển thị thông báo và không lưu
                self.duplicate_count += 1
                self.duplicate_count_label.config(text=str(self.duplicate_count))
                self._log_colored(f"⚠️ MÃ QR TRÙNG LẶP - Không lưu", "warning")
                if content:
                    self._log_colored(f"   💬 Nội dung: {content}", "warning")
                else:
                    self._log_colored(f"   💬 Nội dung: <không đọc được>", "warning")
                self._log_colored(f"   📌 Lý do: {duplicate_reason}", "warning")
                self.log("")
                
                # Hiển thị thông báo popup
                self._show_notification("⚠️ Mã QR Trùng Lặp!", self.accent_yellow)
                
                # Vẽ khung màu vàng/cam để báo trùng
                cv2.polylines(frame, [qr_pts], True, (0, 165, 255), 3)  # Màu cam
                for (x, y) in qr_pts:
                    cv2.circle(frame, (x, y), 5, (0, 255, 255), -1)  # Màu vàng
            else:
                # Mã QR mới - lưu vào
                if content:
                    self.saved_codes.add(content)
                    self.existing_qr_contents.add(content)
                else:
                    key = f"{min_x}_{min_y}_{max_x}_{max_y}"
                    self.saved_codes.add(key)
                
                self.qr_count += 1
                self._update_qr_count()
                
                filename = f"qr_{timestamp}_{idx+1}.png"
                save_path = os.path.join(self.output_dir, filename)
                cv2.imwrite(save_path, roi)
                
                # Lưu metadata
                self._save_metadata()
                
                self._log_colored(f"✅ Mã QR #{self.qr_count} Đã Phát Hiện & Lưu", "success")
                self.log(f"   📄 Tệp: {filename}")
                if content:
                    self._log_colored(f"   💬 Nội dung: {content}", "highlight")
                else:
                    self._log_colored(f"   💬 Nội dung: <trống hoặc không đọc được>", "warning")
                self.log("")
                
                # Create confetti effect at QR center
                center_x = (min_x + max_x) // 2
                center_y = (min_y + max_y) // 2
                self._create_confetti(center_x, center_y)
                
                # Vẽ khung màu xanh để báo thành công
                cv2.polylines(frame, [qr_pts], True, (250, 165, 96), 3)  # Blue-orange
                for (x, y) in qr_pts:
                    cv2.circle(frame, (x, y), 5, (238, 211, 34), -1)  # Cyan-yellow

        return frame

    # ========== KHÁC ==========

    def reset_app(self):
        self.stop_camera()
        self.label_video.config(
            image="",
            text="📷\n\nChưa có camera hoặc ảnh được tải\n\nNhấn 'Bật Camera' hoặc 'Mở Ảnh & Quét'",
            fg=self.text_muted,
            font=("Segoe UI", 12),
        )
        self.text_log.delete("1.0", tk.END)
        self.saved_codes.clear()
        self.qr_count = 0
        self.duplicate_count = 0
        self._update_qr_count()
        self.duplicate_count_label.config(text="0")
        self.session_start_time = None
        self.session_time_label.config(text="00:00")
        
        self._log_colored("🔄 Đã Đặt Lại Ứng Dụng", "warning")
        self._log_colored("━" * 50, "info")
        self.log("📌 Sẵn sàng cho phiên mới:")
        self.log("   • Mở file ảnh để quét")
        self.log("   • Hoặc bật nhận diện camera trực tiếp")
        self._log_colored("━" * 50, "info")
        
        self.set_status("Sẵn Sàng", self.accent_green)
        self.status_icon_label.config(text="●", foreground=self.text_muted)
        self.status_text_label.config(text="Chờ")

    def on_close(self):
        self.stop_camera()
        self.root.destroy()

    # ========== ANIMATIONS ==========
    
    def _button_click_animation(self, callback):
        """Animate button click before executing callback"""
        # Small delay for visual feedback
        self.root.after(50, callback)
    
    def _start_animations(self):
        """Start all animation loops"""
        self._animate_pulse()
        self._animate_gradient()
        self._animate_scan_line()
        self._animate_glow_borders()
        self._animate_rainbow_title()
        self._animate_particles()
    
    def _animate_pulse(self):
        """Pulsing animation for status indicator"""
        if self.is_running:
            # Calculate breathing effect (0.5 to 1.0)
            self.pulse_alpha += 0.03 * self.pulse_direction
            if self.pulse_alpha >= 1.0:
                self.pulse_alpha = 1.0
                self.pulse_direction = -1
            elif self.pulse_alpha <= 0.5:
                self.pulse_alpha = 0.5
                self.pulse_direction = 1
            
            # Apply pulsing to status icon
            intensity = int(self.pulse_alpha * 255)
            if self.is_running:
                color = f"#{intensity//4:02x}{intensity:02x}{intensity//4:02x}"  # Green pulse
                self.status_icon_label.config(foreground=color)
        
        self.root.after(50, self._animate_pulse)
    
    def _animate_gradient(self):
        """Animated gradient effect for header"""
        self.gradient_offset = (self.gradient_offset + 1) % 360
        
        # This creates a subtle color shift effect
        # We can apply this to various elements
        
        self.root.after(100, self._animate_gradient)
    
    def _animate_scan_line(self):
        """Scanning line animation in video area when camera is active"""
        if self.is_running and hasattr(self, 'video_canvas'):
            self.scan_line_y += 3 * self.scan_direction
            canvas_height = self.video_canvas.winfo_height()
            
            if canvas_height > 0:
                if self.scan_line_y >= canvas_height:
                    self.scan_line_y = canvas_height
                    self.scan_direction = -1
                elif self.scan_line_y <= 0:
                    self.scan_line_y = 0
                    self.scan_direction = 1
                
                # Draw scan line
                self.video_canvas.delete("scanline")
                self.video_canvas.create_line(
                    0, self.scan_line_y,
                    self.video_canvas.winfo_width(), self.scan_line_y,
                    fill=self.accent_cyan,
                    width=2,
                    tags="scanline"
                )
        
        self.root.after(30, self._animate_scan_line)
    
    def _animate_button_press(self, button):
        """Button press animation effect"""
        original_bg = button.cget('background')
        button.configure(relief='sunken')
        self.root.after(100, lambda: button.configure(relief='raised'))
    
    def _fade_in_widget(self, widget, current_alpha=0.0):
        """Fade in animation for widgets"""
        if current_alpha < 1.0:
            current_alpha += 0.1
            # Note: Tkinter doesn't support alpha directly, but we can simulate with color
            self.root.after(30, lambda: self._fade_in_widget(widget, current_alpha))
    
    def _slide_in_log(self, message, tag=None):
        """Slide in animation for log messages"""
        # Add a visual separator with animation
        self.text_log.insert(tk.END, "  ", tag)
        self.text_log.insert(tk.END, message + "\n", tag)
        self.text_log.see(tk.END)
        
        # Trigger a flash effect
        self.text_log.tag_configure("flash", background=self.accent_blue)
        if tag:
            self.root.after(100, lambda: self.text_log.tag_configure(tag, background=self.bg_card))
    
    def _bounce_stat(self, label):
        """Bounce animation for stat update"""
        original_font = label.cget('font')
        font_parts = original_font.split()
        
        # Increase size
        if len(font_parts) >= 2:
            size = int(font_parts[1])
            label.configure(font=(font_parts[0], size + 4, *font_parts[2:]))
            self.root.after(100, lambda: label.configure(font=original_font))
    
    def _show_notification(self, message, color):
        """Show animated notification popup"""
        self.notification_queue.append((message, color))
        if self.current_notification is None:
            self._process_notification_queue()
    
    def _process_notification_queue(self):
        """Process notification queue"""
        if len(self.notification_queue) == 0:
            self.current_notification = None
            return
        
        message, color = self.notification_queue.pop(0)
        
        # Create notification window
        notif = tk.Toplevel(self.root)
        notif.overrideredirect(True)  # Remove window decorations
        notif.configure(bg=color)
        
        label = tk.Label(
            notif,
            text=message,
            bg=color,
            fg="#000000",
            font=("Segoe UI", 11, "bold"),
            padx=20,
            pady=10
        )
        label.pack()
        
        # Position at top center
        notif.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - notif.winfo_width()) // 2
        y = self.root.winfo_y() + 100
        notif.geometry(f"+{x}+{y}")
        
        self.current_notification = notif
        
        # Fade out and destroy after 2 seconds
        self.root.after(2000, lambda: self._fade_out_notification(notif))
    
    def _fade_out_notification(self, notif):
        """Fade out notification"""
        try:
            notif.destroy()
        except:
            pass
        self.current_notification = None
        self._process_notification_queue()
    
    def _create_ripple_effect(self, widget, x, y):
        """Create ripple effect on click"""
        # This would require canvas overlay - simplified version
        pass
    
    def _animate_count_up(self, label, start, end, current=None):
        """Animate number counting up"""
        if current is None:
            current = start
        
        if current < end:
            current += 1
            label.config(text=str(current))
            self.root.after(50, lambda: self._animate_count_up(label, start, end, current))
        else:
            label.config(text=str(end))
            self._bounce_stat(label)
    
    def _animate_glow_borders(self):
        """Animated glow effect for card borders"""
        # This creates a pulsing glow effect on borders
        # We cycle through brightness levels
        
        if not hasattr(self, 'glow_intensity'):
            self.glow_intensity = 0.5
            self.glow_direction = 1
        
        self.glow_intensity += 0.01 * self.glow_direction
        
        if self.glow_intensity >= 1.0:
            self.glow_intensity = 1.0
            self.glow_direction = -1
        elif self.glow_intensity <= 0.5:
            self.glow_intensity = 0.5
            self.glow_direction = 1
        
        # Apply glow to stat cards when camera is running
        if self.is_running and hasattr(self, 'qr_stat_card'):
            intensity = int(self.glow_intensity * 255)
            glow_color = f"#{intensity//2:02x}{intensity:02x}{intensity:02x}"
            # Note: We can't easily change border color dynamically in tkinter
            # This is a placeholder for the concept
        
        self.root.after(50, self._animate_glow_borders)
    
    def _progress_bar_animation(self, progress=0):
        """Animated progress bar effect"""
        # This could be used for loading states
        pass
    
    def _shimmer_effect(self, widget):
        """Create a shimmer/shine effect across widget"""
        # This creates a moving highlight effect
        pass
    
    def _float_animation(self, widget, offset=0):
        """Create floating/hovering animation"""
        # Makes widget appear to float up and down
        import math
        offset = (offset + 1) % 360
        y_offset = int(math.sin(math.radians(offset * 2)) * 3)
        # Apply offset to widget placement
        self.root.after(30, lambda: self._float_animation(widget, offset))
    
    def _animate_rainbow_title(self):
        """Create rainbow effect on title"""
        import math
        
        self.rainbow_offset = (self.rainbow_offset + 2) % 360
        
        # Calculate RGB from HSV
        hue = self.rainbow_offset / 360.0
        
        # Convert HSV to RGB (simplified)
        if hue < 1/6:
            r, g, b = 1.0, hue*6, 0.0
        elif hue < 2/6:
            r, g, b = 2.0 - hue*6, 1.0, 0.0
        elif hue < 3/6:
            r, g, b = 0.0, 1.0, (hue - 2/6)*6
        elif hue < 4/6:
            r, g, b = 0.0, (4/6 - hue)*6, 1.0
        elif hue < 5/6:
            r, g, b = (hue - 4/6)*6, 0.0, 1.0
        else:
            r, g, b = 1.0, 0.0, (1.0 - hue)*6
        
        # Scale to 0-255 with good brightness
        r = int(r * 180 + 75)
        g = int(g * 180 + 75)
        b = int(b * 180 + 75)
        
        color = f"#{r:02x}{g:02x}{b:02x}"
        
        # Apply color to title (only when camera is active for performance)
        if self.is_running and hasattr(self, 'title_label'):
            try:
                self.title_label.config(foreground=color)
            except:
                pass
        
        self.root.after(50, self._animate_rainbow_title)
    
    def _animate_particles(self):
        """Animate particle effects"""
        # Update existing particles
        particles_to_remove = []
        
        for i, particle in enumerate(self.particles):
            particle['y'] -= particle['vy']
            particle['x'] += particle['vx']
            particle['life'] -= 1
            particle['alpha'] = particle['life'] / 30.0
            
            if particle['life'] <= 0:
                particles_to_remove.append(i)
            else:
                # Update particle on canvas
                if hasattr(self, 'video_canvas'):
                    try:
                        self.video_canvas.coords(
                            particle['id'],
                            particle['x'] - 3,
                            particle['y'] - 3,
                            particle['x'] + 3,
                            particle['y'] + 3
                        )
                        # Fade out
                        alpha_hex = int(particle['alpha'] * 255)
                        color = particle['color']
                        # Can't easily do alpha in tkinter, but we can change size
                        size = int(3 * particle['alpha'])
                        if size < 1:
                            size = 1
                        self.video_canvas.coords(
                            particle['id'],
                            particle['x'] - size,
                            particle['y'] - size,
                            particle['x'] + size,
                            particle['y'] + size
                        )
                    except:
                        particles_to_remove.append(i)
        
        # Remove dead particles
        for i in reversed(particles_to_remove):
            try:
                if hasattr(self, 'video_canvas'):
                    self.video_canvas.delete(self.particles[i]['id'])
                self.particles.pop(i)
            except:
                pass
        
        self.root.after(30, self._animate_particles)
    
    def _create_confetti(self, x, y):
        """Create confetti particles at position"""
        import random
        
        colors = [self.accent_cyan, self.accent_purple, self.accent_green, 
                  self.accent_yellow, self.accent_blue]
        
        # Create 15 particles
        for _ in range(15):
            if hasattr(self, 'video_canvas'):
                try:
                    color = random.choice(colors)
                    particle_id = self.video_canvas.create_oval(
                        x - 3, y - 3, x + 3, y + 3,
                        fill=color,
                        outline="",
                        tags="particle"
                    )
                    
                    self.particles.append({
                        'id': particle_id,
                        'x': x,
                        'y': y,
                        'vx': random.uniform(-3, 3),
                        'vy': random.uniform(2, 6),
                        'life': 30,
                        'alpha': 1.0,
                        'color': color
                    })
                except:
                    pass


if __name__ == "__main__":
    root = tk.Tk()
    app = QRCameraApp(root)
    root.mainloop()
