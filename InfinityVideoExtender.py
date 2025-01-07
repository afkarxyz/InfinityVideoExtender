import sys
import os
import subprocess
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QLabel, QFileDialog, 
                             QMessageBox, QTextEdit,
                             QTabWidget, QSpinBox, QProgressBar, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QSettings
from PyQt6.QtGui import QTextCursor, QDesktopServices, QIcon
import requests

class FFmpegDownloader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, save_path):
        super().__init__()
        self.save_path = save_path
        self.files = {
            'ffmpeg.exe': 'https://github.com/afkarxyz/FFmpeg-Xfade-GUI/releases/download/XfadeGUI/ffmpeg.exe',
            'ffprobe.exe': 'https://github.com/afkarxyz/FFmpeg-Xfade-GUI/releases/download/XfadeGUI/ffprobe.exe'
        }

    def run(self):
        try:
            bin_path = os.path.join(self.save_path, 'FFmpeg', 'bin')
            os.makedirs(bin_path, exist_ok=True)

            total_files = len(self.files)
            session = requests.Session()
            
            for index, (filename, url) in enumerate(self.files.items()):
                file_path = os.path.join(bin_path, filename)
                
                response = session.get(url, stream=True)
                total_size = int(response.headers.get('content-length', 0))
                
                base_progress = (index * 100) // total_files
                
                with open(file_path, 'wb') as f:
                    if total_size == 0:
                        f.write(response.content)
                    else:
                        downloaded = 0
                        for data in response.iter_content(chunk_size=1024*1024):
                            downloaded += len(data)
                            f.write(data)
                            file_progress = (downloaded / total_size) * (100 // total_files)
                            total_progress = int(base_progress + file_progress)
                            self.progress.emit(total_progress)

            session.close()
            self.finished.emit(True, f"FFmpeg files downloaded successfully to {bin_path}")
        except Exception as e:
            self.finished.emit(False, str(e))
            
class VideoExtenderWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, input_file, hours, minutes, times, ffmpeg_path):
        super().__init__()
        self.input_file = input_file
        self.hours = hours
        self.minutes = minutes
        self.times = times
        self.ffmpeg_path = ffmpeg_path

    def run(self):
        try:
            from subprocess import CREATE_NO_WINDOW
            
            ffprobe_path = os.path.join(self.ffmpeg_path, "ffprobe.exe")
            duration_cmd = [
                ffprobe_path, '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                self.input_file
            ]
            
            duration = float(subprocess.check_output(
                duration_cmd,
                creationflags=CREATE_NO_WINDOW
            ).decode().strip())
            
            if self.times > 0:
                repeat = self.times
            else:
                desired_seconds = (self.hours * 3600) + (self.minutes * 60)
                repeat = int((desired_seconds + duration - 1) / duration)
            
            concat_file = "concat.txt"
            with open(concat_file, 'w') as f:
                for _ in range(repeat):
                    f.write(f"file '{self.input_file}'\n")
            
            name, ext = os.path.splitext(self.input_file)
            if self.times > 0:
                output_file = f"{name}_{self.times}times{ext}"
            else:
                time_str = f"{self.hours}h{self.minutes}m" if self.minutes > 0 else f"{self.hours}h"
                output_file = f"{name}_{time_str}{ext}"
            
            ffmpeg_path = os.path.join(self.ffmpeg_path, "ffmpeg.exe")
            ffmpeg_cmd = [
                ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                output_file
            ]
            
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=CREATE_NO_WINDOW
            )
            
            for line in process.stdout:
                self.progress.emit(line.strip())
            
            process.wait()
            os.remove(concat_file)
            
            if process.returncode == 0:
                self.finished.emit(True, f"Video extended successfully and saved as {output_file}")
            else:
                self.finished.emit(False, "Error processing video")
                
        except Exception as e:
            self.finished.emit(False, str(e))

class InfinityVideoExtender(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings('infinityvideoextender', 'Infinity Video Extender')
        self.initUI()
        
        self.setWindowTitle('Infinity Video Extender')
        icon_path = os.path.join(os.path.dirname(__file__), "infinity.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def normalize_path(self, path):
        if not path:
            return path
            
        normalized_path = os.path.normpath(path)
        
        if len(normalized_path) >= 2 and normalized_path[1] == ':':
            normalized_path = normalized_path[0].upper() + normalized_path[1:]
        
        return normalized_path

    def initUI(self):
        self.setWindowTitle('Infinity Video Extender')
        self.setFixedWidth(650)
        self.setFixedHeight(420)
        main_layout = QVBoxLayout()
        
        ffmpeg_layout = QHBoxLayout()
        ffmpeg_label = QLabel('FFmpeg Path:')
        ffmpeg_label.setFixedWidth(100)
        ffmpeg_layout.addWidget(ffmpeg_label)
        self.ffmpeg_path = QLineEdit()
        initial_ffmpeg_path = self.normalize_path(self.load_ffmpeg_path())
        self.ffmpeg_path.setText(initial_ffmpeg_path)
        self.ffmpeg_path.setClearButtonEnabled(True)
        self.ffmpeg_path.textChanged.connect(lambda text: self.save_ffmpeg_path(self.normalize_path(text)))
        
        self.get_ffmpeg_btn = QPushButton('Get FFmpeg')
        self.get_ffmpeg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.get_ffmpeg_btn.setFixedWidth(100)
        self.get_ffmpeg_btn.clicked.connect(self.download_ffmpeg)
        ffmpeg_layout.addWidget(self.ffmpeg_path)
        ffmpeg_layout.addWidget(self.get_ffmpeg_btn)
        main_layout.addLayout(ffmpeg_layout)

        video_layout = QHBoxLayout()
        video_label = QLabel('Video Path:')
        video_label.setFixedWidth(100)
        video_layout.addWidget(video_label)
        self.video_path = QLineEdit()
        self.video_path.setClearButtonEnabled(True)
        self.video_path.textChanged.connect(lambda text: self.video_path.setText(self.normalize_path(text)) if text else None)
        self.video_browse = QPushButton('Browse')
        self.video_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.video_browse.setFixedWidth(100)
        self.video_browse.clicked.connect(self.browse_video)
        video_layout.addWidget(self.video_path)
        video_layout.addWidget(self.video_browse)
        main_layout.addLayout(video_layout)

        duration_group = QGroupBox("Settings")
        duration_layout = QHBoxLayout()
        duration_layout.setContentsMargins(0, 0, 0, 8)
        duration_layout.setSpacing(10)

        hours_layout = QHBoxLayout()
        hours_layout.setSpacing(5)
        hours_label = QLabel('Hours:')
        hours_label.setFixedWidth(45)
        self.hours_input = QSpinBox()
        self.hours_input.setFixedWidth(70)
        self.hours_input.setRange(0, 1000)
        self.hours_input.setValue(1)
        hours_layout.addWidget(hours_label)
        hours_layout.addWidget(self.hours_input)
        duration_layout.addLayout(hours_layout)

        minutes_layout = QHBoxLayout()
        minutes_layout.setSpacing(5)
        minutes_label = QLabel('Minutes:')
        minutes_label.setFixedWidth(55)
        self.minutes_input = QSpinBox()
        self.minutes_input.setFixedWidth(70)
        self.minutes_input.setRange(0, 59)
        self.minutes_input.setValue(0)
        minutes_layout.addWidget(minutes_label)
        minutes_layout.addWidget(self.minutes_input)
        duration_layout.addLayout(minutes_layout)

        times_layout = QHBoxLayout()
        times_layout.setSpacing(5)
        times_label = QLabel('Times:')
        times_label.setFixedWidth(45)
        self.times_input = QSpinBox()
        self.times_input.setFixedWidth(70)
        self.times_input.setRange(0, 1000)
        self.times_input.setValue(0)
        times_layout.addWidget(times_label)
        times_layout.addWidget(self.times_input)
        duration_layout.addLayout(times_layout)

        self.times_input.valueChanged.connect(self.on_times_changed)
        self.hours_input.valueChanged.connect(self.on_duration_changed)
        self.minutes_input.valueChanged.connect(self.on_duration_changed)

        duration_group.setLayout(duration_layout)
        main_layout.addWidget(duration_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.tab_widget = QTabWidget()

        process_tab = QWidget()
        process_layout = QVBoxLayout()
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        process_layout.addWidget(self.log_output)

        start_btn_layout = QHBoxLayout()
        self.process_btn = QPushButton('Start Processing')
        self.process_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.process_btn.setFixedWidth(180)
        self.process_btn.clicked.connect(self.process_videos)
        start_btn_layout.addStretch()
        start_btn_layout.addWidget(self.process_btn)
        start_btn_layout.addStretch()
        process_layout.addLayout(start_btn_layout)

        process_tab.setLayout(process_layout)
        self.tab_widget.addTab(process_tab, "Process")

        about_tab = QWidget()
        about_layout = QVBoxLayout()
        about_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.setSpacing(10)

        title_label = QLabel("Infinity Video Extender")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: palette(text);")
        about_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        sections = [
            ("Check for Updates", "https://github.com/afkarxyz/InfinityVideoExtender/releases"),
            ("Report an Issue", "https://github.com/afkarxyz/InfinityVideoExtender/issues"),
            ("FFmpeg Documentation", "https://ffmpeg.org/documentation.html")
        ]

        for title, url in sections:
            section_widget = QWidget()
            section_layout = QVBoxLayout(section_widget)
            section_layout.setSpacing(5)
            section_layout.setContentsMargins(0, 0, 0, 0)

            label = QLabel(title)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            section_layout.addWidget(label)

            button = QPushButton("Click Here!")
            button.setFixedWidth(150)
            button.setStyleSheet("""
                QPushButton {
                    background-color: palette(button);
                    color: palette(button-text);
                    border: 1px solid palette(mid);
                    padding: 6px;
                    border-radius: 15px;
                }
                QPushButton:hover {
                    background-color: palette(light);
                }
                QPushButton:pressed {
                    background-color: palette(midlight);
                }
            """)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _, url=url: QDesktopServices.openUrl(QUrl(url)))
            section_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)

            about_layout.addWidget(section_widget)

        footer_label = QLabel("v1.0 January 2025 | Infinity Video Extender")
        footer_label.setStyleSheet("font-size: 11px; color: palette(text);")
        about_layout.addWidget(footer_label, alignment=Qt.AlignmentFlag.AlignCenter)

        about_tab.setLayout(about_layout)
        self.tab_widget.addTab(about_tab, "About")

        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

    def on_times_changed(self, value):
        if value > 0:
            self.hours_input.setValue(0)
            self.minutes_input.setValue(0)
            self.hours_input.setEnabled(False)
            self.minutes_input.setEnabled(False)
        else:
            self.hours_input.setEnabled(True)
            self.minutes_input.setEnabled(True)

    def on_duration_changed(self, value):
        if self.hours_input.value() > 0 or self.minutes_input.value() > 0:
            self.times_input.setValue(0)

    def load_ffmpeg_path(self):
        return self.settings.value('ffmpeg_path', '', str)

    def save_ffmpeg_path(self, path):
        self.settings.setValue('ffmpeg_path', path)
        self.settings.sync()

    def browse_video(self):
        video_formats = "Video Files ("
        formats = [
            "*.mp4", "*.avi", "*.mov", "*.mkv", "*.wmv", "*.flv", "*.webm", 
            "*.m4v", "*.mpg", "*.mpeg", "*.m2v", "*.m2ts", "*.mts", "*.ts", 
            "*.vob", "*.3gp", "*.3g2", "*.f4v", "*.asf", "*.rmvb", "*.rm", 
            "*.ogv", "*.mxf", "*.dv", "*.divx", "*.xvid", "*.mpv", "*.m2p", 
            "*.mp2", "*.mpeg2", "*.ogm"
        ]
        video_formats += " ".join(formats) + ")"
        file, _ = QFileDialog.getOpenFileName(self, 'Select Video File', '', video_formats)
        if file:
            normalized_path = self.normalize_path(file)
            self.video_path.setText(normalized_path)

    def download_ffmpeg(self):
        save_path = self.normalize_path(os.path.dirname(os.path.abspath(__file__)))
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.downloader = FFmpegDownloader(save_path)
        self.downloader.progress.connect(self.progress_bar.setValue)
        self.downloader.finished.connect(self.on_download_finished)
        self.downloader.start()

    def on_download_finished(self, success, message):
        self.progress_bar.setVisible(False)
        if success:
            ffmpeg_path = self.normalize_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'FFmpeg', 'bin'))
            self.ffmpeg_path.setText(ffmpeg_path)
            self.save_ffmpeg_path(ffmpeg_path)
            QMessageBox.information(self, 'Success', message)
        else:
            QMessageBox.critical(self, 'Error', f'Download failed: {message}')

    def process_videos(self):
        if not self.video_path.text():
            QMessageBox.warning(self, 'Warning', 'Please select a video file.')
            return

        ffmpeg_path = self.ffmpeg_path.text()
        if not os.path.exists(os.path.join(ffmpeg_path, "ffmpeg.exe")) or not os.path.exists(os.path.join(ffmpeg_path, "ffprobe.exe")):
            QMessageBox.warning(self, 'Warning', 'Invalid FFmpeg path. Please ensure both ffmpeg.exe and ffprobe.exe are present in the selected directory.')
            return

        hours = self.hours_input.value()
        minutes = self.minutes_input.value()
        times = self.times_input.value()
        input_file = self.video_path.text()
        
        self.worker = VideoExtenderWorker(input_file, hours, minutes, times, ffmpeg_path)
        self.worker.progress.connect(self.update_log)
        self.worker.finished.connect(self.on_process_finished)
        
        self.process_btn.setEnabled(False)
        self.process_btn.setText('Processing...')
        
        self.log_output.append(f"\nProcessing video: {input_file}")
        self.worker.start()

    def update_log(self, message):
        self.log_output.append(message)
        self.log_output.moveCursor(QTextCursor.MoveOperation.End)

    def on_process_finished(self, success, message):
        self.process_btn.setEnabled(True)
        self.process_btn.setText('Start Processing')

        if success:
            self.log_output.append(f"\nSuccess: {message}")
        else:
            self.log_output.append(f"\nError: {message}")
            QMessageBox.critical(self, 'Error', f'An error occurred: {message}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = InfinityVideoExtender()
    ex.show()
    sys.exit(app.exec())
