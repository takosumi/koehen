#(C) 2022 Takosumi
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import font
from os import path
import sys
import platform
import wave
import numpy as np
import pyworld as pw
import unvocs as uv
import pyaudio
import json
import threading
import winreg
import ctypes as ct
import struct
from PIL import Image, ImageTk

from matplotlib import cbook
from matplotlib.figure import Figure
from matplotlib.backend_bases import NavigationToolbar2
#matplotlibのツールチップを日本語化
NavigationToolbar2.toolitems = (
    ("Home", "最初の表示に戻す", "home", "home"),
    ("Back", "1つ前の表示に戻す", "back", "back"),
    ("Forward", "1つ後の表示に戻す", "forward", "forward"),
    (None, None, None, None),
    ("Pan",
     "左ドラッグで移動, 右ドラッグで拡大縮小\n"
     "x/yで軸を固定, Ctrlで縦横比を固定",
     "move", "pan"),
    ("Zoom", "選択範囲を拡大\nx/yで軸を固定", "zoom_to_rect", "zoom"),
    ("Subplots", "表示の設定", "subplots", "configure_subplots"),
    (None, None, None, None),
    ("Save", "画像を保存", "filesave", "save_figure")
)

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
#matplotlibのツールバーの内容を上書き
#参考：https://qiita.com/belre/items/0cf05baa8e4bf8eaac3b
class NavigationToolbar(NavigationToolbar2Tk):
    toolitems = [t for t in NavigationToolbar2Tk.toolitems if t[0] in ("Pan", "Zoom","Back","Forward","Home")]
    #カーソルの座標を省略
    def set_message(self, s):
        pass
    #ダークモードに対応
    def __init__(self, canvas, window, *, pack_toolbar=True):
        self.window = window
        Frame.__init__(self, master=window, borderwidth=2,
                          width=int(canvas.figure.bbox.width), height=50)
        self._buttons = {}
        for text, tooltip_text, image_file, callback in self.toolitems:
            if text is None:
                self._Spacer()
            else:
                if app.button_text3.get() != "ライトモード":
                    self._buttons[text] = button = self._Button(
                        text,
                        str(cbook._get_data_path(f"images/{image_file}.png")),
                        toggle=callback in ["zoom", "pan"],
                        command=getattr(self, callback),
                    )
                else:
                    self._buttons[text] = button = self._Button(
                        text,
                        image_file,
                        toggle=callback in ["zoom", "pan"],
                        command=getattr(self, callback),
                    )
                if tooltip_text is not None:
                    ToolTip.createToolTip(button, tooltip_text)
        self._label_font = font.Font(root=window, size=10)
        label = Label(master=self, font=self._label_font,
                         text="\N{NO-BREAK SPACE}\n\N{NO-BREAK SPACE}")
        label.pack(side=RIGHT)

        self.message = StringVar(master=self)
        self._message_label = Label(master=self, font=self._label_font,
                                       textvariable=self.message)
        self._message_label.pack(side=RIGHT)
        NavigationToolbar2.__init__(self, canvas)
        if pack_toolbar:
            self.pack(side=BOTTOM, fill=X)
        if app.button_text3.get() == "ライトモード":
            self["bg"] = "#424242"
            for item in self.winfo_children():
                item["bg"] = "#424242"
                item["activebackground"] = "#222222"

    def _set_image_for_button(self, button):
        if button._image_file is None:
            return
        size = button.winfo_pixels("18p")
        if app.button_text3.get() != "ライトモード":
            with Image.open(button._image_file.replace(".png", "_large.png")
                            if size > 24 else button._image_file) as im:
                image = ImageTk.PhotoImage(im.resize((size, size)), master = self)
        else:
            if size > 24:
                darkmode_path = path.dirname(sys.argv[0]) + "\\images\\" + button._image_file + "_dark_large.png"
            else:
                darkmode_path = path.dirname(sys.argv[0]) + "\\images\\" + button._image_file + "_dark.png"
            with Image.open(darkmode_path) as im:
                image = ImageTk.PhotoImage(im.resize((size, size)), master = self)
        button.configure(image = image, height = "18p", width = "18p")
        button._ntimage = image

    def _Button(self, text, image_file, toggle, command):
        if not toggle:
            b = Button(master = self, text = text, command = command)
        else:
            var = IntVar(master = self)
            b = Checkbutton(
                master = self, text = text, command = command,
                indicatoron = False, variable = var)
            b.var = var
            if app.button_text3.get() == "ライトモード":
                b["selectcolor"] = "#222222"
        b._image_file = image_file
        if image_file is not None:
            self._set_image_for_button(b)
        else:
            b.configure(font = self._label_font)
        b.pack(side = LEFT)
        return b

    def _rescale(self):
        for widget in self.winfo_children():
            if isinstance(widget, (Button, Checkbutton)):
                if hasattr(widget, "_image_file"):
                    self._set_image_for_button(widget)
                else:
                    pass
            elif isinstance(widget, Frame):
                widget.configure(height="22p", pady="1p")
                widget.pack_configure(padx="4p")
            elif isinstance(widget, Label):
                pass
            else:
                _log.warning("Unknown child class %s", widget.winfo_class)
        self._label_font.configure(size=10)
#Windowsがダークモードかcheck
regpath = r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize"
try:
    regkey = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, regpath)
    regdata, regtype = winreg.QueryValueEx(regkey, "AppsUseLightTheme")
    winreg.CloseKey(regkey)
except Exception:
    regdata = 1
#windowsのバージョンを確認
version_data = platform.version()
build_number = int(version_data[version_data.rfind(".") + 1:len(version_data)])

root = Tk()
root.tk.call("source", path.dirname(sys.argv[0]) + "\\theme\\black.tcl")

#Windowsがダークモードの時にタイトルバーを黒色にする
#参考：https://gist.github.com/Olikonsti/879edbf69b801d8519bf25e804cec0aa
def dark_title_bar(window):
    window.update()
    if build_number >= 18362:
        if build_number >= 19041:
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        else:
            DWMWA_USE_IMMERSIVE_DARK_MODE = 19
        set_window_attribute = ct.windll.dwmapi.DwmSetWindowAttribute
        get_parent = ct.windll.user32.GetParent
        hwnd = get_parent(window.winfo_id())
        rendering_policy = DWMWA_USE_IMMERSIVE_DARK_MODE
        value = 2
        value = ct.c_int(value)
        set_window_attribute(hwnd, rendering_policy, ct.byref(value), ct.sizeof(value))

if regdata == 0:
    dark_title_bar(root)

root.title("こえへん！powered by UNVOCS")
style = ttk.Style()
style.configure("Sash", sashthickness = 6)
style.configure("mainframe.TFrame", relief = "sunken")
style.configure("editor_window.TFrame", background = "#424242")

#waveファイル読み込み用の関数
#参考：https://www.wizard-notes.com/entry/python/hack-wave-read
WAVE_FORMAT_PCM        = 0x0001
WAVE_FORMAT_IEEE_FLOAT = 0x0003
class Waveread_float(wave.Wave_read):
    def _read_fmt_chunk(self, chunk):
        try:
            wFormatTag, self._nchannels, self._framerate, dwAvgBytesPerSec, wBlockAlign = struct.unpack_from("<HHLLH", chunk.read(14))
        except struct.error:
            raise EOFError from None
        if wFormatTag == WAVE_FORMAT_PCM or wFormatTag == WAVE_FORMAT_IEEE_FLOAT:
            self.wFormatTag = int(wFormatTag)
            try:
                sampwidth = struct.unpack_from("<H", chunk.read(2))[0]
            except struct.error:
                raise EOFError from None
            self._sampwidth = (sampwidth + 7) // 8
            if not self._sampwidth:
                raise Error("bad sample width")
        else:
            raise Error("unknown format: %r" % (wFormatTag,))
        if not self._nchannels:
            raise Error("bad # of channels")
        self._framesize = self._nchannels * self._sampwidth
        self._comptype = "NONE"
        self._compname = "not compressed"
        
    def getformatid(self):
        return self.wFormatTag

def waveread(filename, mode):
    wf = Waveread_float(filename)
    n_bytes = wf.getsampwidth()
    channel = wf.getnchannels()
    if channel > 2:
        log_insert("[エラー] チャンネル数が3以上のファイルには対応していません。")
        return 1
    framerate = wf.getframerate()
    n_frames = wf.getnframes()
    format_id = wf.getformatid()
    if framerate != app.sample_rate_menu.num:
        log_insert("[エラー] 読み込むファイルの周波数(" + str(framerate) + "Hz)が規定値(" + str(app.sample_rate_menu.num) + "Hz)と異なります。")
        return 1
    else:
        buffer = wf.readframes(n_frames)
        if n_bytes == 1:
            signal = (np.frombuffer(buffer, dtype = "uint8") - 128).astype(np.float64)/128.0
        elif n_bytes == 2:
            signal = np.frombuffer(buffer, dtype = "int16").astype(np.float64)/32768.0
        elif n_bytes == 3:
            data = [unpack("<i", bytearray([0]) + buffer[n_bytes * k:n_bytes * (k + 1)])[0] for k in range(n_frames)]
            signal = np.array(data, dtype="int32").astype(np.float64)/2147483648.0
        elif n_bytes == 4 and format_id == WAVE_FORMAT_PCM:
            signal = np.array(data, dtype="int32").astype(np.float64)/2147483648.0
        elif n_bytes == 4 and format_id == WAVE_FORMAT_IEEE_FLOAT:
            signal = np.frombuffer(buffer, dtype = "float32").astype(np.float64)
        elif n_bytes == 8 and format_id == WAVE_FORMAT_IEEE_FLOAT:
            signal = np.frombuffer(buffer, dtype = "float64")
        else:
            log_insert("[エラー] このフォーマットは読み込めません。\nサポートされているフォーマット：8bit、16bit、24bit、32bit int、32bit float、64bit float")
            return 1
        if mode == 0:
            if channel == 2:
                signal = np.ascontiguousarray((signal[::2] + signal[1::2])/2)
            return signal, framerate
        elif mode == 1:
            if channel == 2:
                signal_l = np.ascontiguousarray(signal[::2])
                signal_r = np.ascontiguousarray(signal[1::2])
                return signal_l, signal_r, framerate, channel, n_bytes
            else:
                return signal, None, framerate, channel, n_bytes

#ツールチップ(matplotlib内部の関数を転用)
class ToolTip:
    @staticmethod
    def createToolTip(widget, text):
        toolTip = ToolTip(widget)
        def enter(event):
            toolTip.showtip(text)
        def leave(event):
            toolTip.hidetip()
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        if self.widget.winfo_class() == "TLabel":
            x = x + self.widget.winfo_rootx()
            y = y + self.widget.winfo_rooty() - self.widget.winfo_height()
        else:
            x = x + self.widget.winfo_rootx() + 27
            y = y + self.widget.winfo_rooty()
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        try:
            # For Mac OS
            tw.tk.call("::tk::unsupported::MacWindowStyle",
                       "style", tw._w,
                       "help", "noActivates")
        except TclError:
            pass
        if app.button_text3.get() == "ダークモード":
            label = Label(tw, text=self.text, justify=LEFT, relief = SOLID,
                          borderwidth=1)
        elif app.button_text3.get() == "ライトモード":
            label = Label(tw, text=self.text, justify=LEFT, relief = SOLID,
                          borderwidth=1, background = "#525252", foreground = "#ffffff")
        label.pack(ipadx = 1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

def log_insert(text):
    app.log.logarea["state"] = "normal"
    app.log.logarea.insert("end", "\n" + text)
    app.log.logarea["state"] = "disabled"

def gaussian(a, x, c, s):
    return a * np.exp(-((x - c) ** 2)/(2 * (s ** 2)))

def original_spectrum(a, c, s):
    i = [0] * 513
    for k in range(513):
        for j in range(len(c)):
            i[k] = i[k] + gaussian(a[j], k, c[j], s[j])
    return i

class log:
    def __init__(self, mainframe):
        self.logarea = Text(mainframe, height = 10)
        self.ys = ttk.Scrollbar(mainframe, orient = "vertical", command = self.logarea.yview)
        self.logarea["yscrollcommand"] = self.ys.set
        self.logarea.insert("1.0", "汎用声質変換ソフト「こえへん！」Ver.beta1\n(C)Takosumi 2022\nここにログが表示されます。")
        self.logarea["state"] = "disabled"

class rightwindow:
    def __init__(self, mainframe, a, sample_rate):
        self.var1 = StringVar()
        self.var1.set("現在の変換データ：(データなし)")
        self.border = ""
        self.border_final = ""
        self.average = ""
        self.average_final = ""
        self.a = ""
        self.a_final = ""
        self.i = ""
        self.u = ""
        self.e = ""
        self.o = ""
        self.file_path = ""
        self.flag = 0
        self.framerate = 0
        self.subframe = ttk.Frame(mainframe)
        self.subframe.grid(column = a, row = 1, sticky = (N, W, E, S))
        self.subframe2 = ttk.Frame(mainframe)
        self.subframe2.grid(column = a, row = 2, sticky = (N, W, E, S))
        self.label_a = ttk.Label(self.subframe, text = "あ")
        self.label_i = ttk.Label(self.subframe, text = "い")
        self.label_u = ttk.Label(self.subframe, text = "う")
        self.label_e = ttk.Label(self.subframe, text = "え")
        self.label_o = ttk.Label(self.subframe, text = "お")
        self.label_a.grid(column = 0, row = 1)
        self.label_i.grid(column = 0, row = 2)
        self.label_u.grid(column = 0, row = 3)
        self.label_e.grid(column = 0, row = 4)
        self.label_o.grid(column = 0, row = 5)
        self.button = open_button_set(self.subframe)
        self.button.button1.button.grid(column = 1, row = 1)
        self.button.button1.filelabel.grid(column = 2, row = 1)
        self.button.button2.button.grid(column = 1, row = 2)
        self.button.button2.filelabel.grid(column = 2, row = 2)
        self.button.button3.button.grid(column = 1, row = 3)
        self.button.button3.filelabel.grid(column = 2, row = 3)
        self.button.button4.button.grid(column = 1, row = 4)
        self.button.button4.filelabel.grid(column = 2, row = 4)
        self.button.button5.button.grid(column = 1, row = 5)
        self.button.button5.filelabel.grid(column = 2, row = 5)
        self.button.button1.filename.trace_add("write", self.check_signal)
        self.button.button2.filename.trace_add("write", self.check_signal)
        self.button.button3.filename.trace_add("write", self.check_signal)
        self.button.button4.filename.trace_add("write", self.check_signal)
        self.button.button5.filename.trace_add("write", self.check_signal)
        self.file_name_import_button = ttk.Button(self.subframe, text = "ファイル名読込", command = self.file_import, width = "12")
        self.file_name_import_button.grid(column = 1, row = 6)
        self.record_button = ttk.Button(self.subframe, text = "ファイル名保存", command = self.record, width = "12")
        self.record_button.state(["disabled"])
        self.record_button.grid(column = 2, row = 6)
        self.division_button = ttk.Button(self.subframe, text = "分割位置推定", command = lambda:self.division_estimate(sample_rate), width = "12")
        self.division_button.state(["disabled"])
        self.division_button.grid(column = 1, row = 7)
        self.edit_button = ttk.Button(self.subframe, text = "手動補正", command = lambda:self.open_editor_window(mainframe), width = "12")
        self.edit_button.state(["disabled"])
        self.edit_button.grid(column = 2, row = 7)
        self.change_data_label2 = ttk.Label(self.subframe2, textvariable = self.var1, anchor = "w")
        self.change_data_label2.grid(column = 1, columnspan = 2, row = 0)
        self.import_button = ttk.Button(self.subframe2, text = "変換データ読込", command = self.json_import)
        self.import_button.grid(column = 1, row = 1, sticky = (E))
        self.export_button = ttk.Button(self.subframe2, text = "変換データ保存", command = self.export)
        self.export_button.state(["disabled"])
        self.export_button.grid(column = 2, row = 1, sticky = (W))
        self.subframe2.columnconfigure(1, weight = "1")
        self.subframe2.columnconfigure(2, weight = "1")

    def check_signal(self, *args):
        if (self.button.button1.filename.get() != "" and self.button.button2.filename.get() != "" and self.button.button3.filename.get() != "" and self.button.button4.filename.get() != "" and self.button.button5.filename.get() != ""):
            self.division_button.state(["!disabled"])
            self.record_button.state(["!disabled"])

    def division_estimate(self, sample_rate):
        if self.button.button1.framerate == self.button.button2.framerate == self.button.button3.framerate == self.button.button4.framerate == self.button.button5.framerate:
            self.border, self.average, self.a, self.i, self.u, self.e, self.o = uv.estimate_division_pos(self.button.button1.signal, self.button.button2.signal, self.button.button3.signal, self.button.button4.signal, self.button.button5.signal, sample_rate)
            self.average_final = self.average
            self.border_final = self.border
            self.a_final = self.a
            self.division_button.state(["disabled"])
            self.edit_button.state(["!disabled"])
            self.export_button.state(["!disabled"])
            self.framerate = self.button.button1.framerate
            self.var1.set("現在の変換データ：上より推定")
        else:
            log_insert("[エラー] 各ファイルの周波数が一致していません。")

    def open_editor_window(self, mainframe):
        self.editor = editor(mainframe, self.a, self.i, self.u, self.e, self.o, self.border)
        self.update_button = ttk.Button(self.editor.frame1, text = "決定", command = self.update)
        self.update_button.grid(column = 1, row = 17, sticky = (N))
        self.editor.frame1.rowconfigure(17, weight = 1)
        self.editor.t.grab_set()
        self.editor.t.focus_set()
        root.wait_window(self.editor.t)

    def update(self):
        self.border = [self.editor.entry1.x, self.editor.entry2.x, self.editor.entry3.x, self.editor.entry4.x, self.editor.entry5.x, self.editor.entry6.x, self.editor.entry7.x, self.editor.entry8.x]
        self.average = uv.average_calculate(self.border, self.a)
        self.border_final = self.border
        self.average_final = self.average
        self.a_final = self.a
        self.var1.set("現在の変換データ：上より推定")
        self.export_button.state(["!disabled"])
        self.editor.t.destroy()

    def file_import(self):
        self.filename = filedialog.askopenfilename(title = "開く", filetypes = [("JSON", ".json")])
        if len(self.filename) != 0:
            with open(self.filename) as self.f:
                try:
                    self.data = json.load(self.f)
                    self.file_import1(self.data, "a", "i", "u", "e", "o")
                except (TypeError, KeyError):
                    log_insert("[エラー] データ形式が誤っています。")

    def file_import1(self, data, a, i, u, e, o):
            if data[a] != "":
                if path.isfile(data[a]):
                    if not(type(waveread(data[a], 0)) is int):
                        self.button.button1.file_path = data[a]
                        self.button.button1.filename.set(path.basename(data[a]))
                        self.button.button1.signal, self.button.button1.framerate = waveread(data[a], 0)
                        ToolTip.createToolTip(self.button.button1.filelabel, path.basename(data[a]))
                else:
                    log_insert("[警告] ファイル " + data[a] + " が見つかりませんでした。")
            if data[i] != "":
                if path.isfile(data[i]):
                    if not(type(waveread(data[i], 0)) is int):
                        self.button.button2.file_path = data[i]
                        self.button.button2.filename.set(path.basename(data[i]))
                        self.button.button2.signal, self.button.button2.framerate = waveread(data[i], 0)
                        ToolTip.createToolTip(self.button.button2.filelabel, path.basename(data[i]))
                else:
                    log_insert("[警告] ファイル " + data[i] + " が見つかりませんでした。")
            if data[u] != "":
                if path.isfile(data[u]):
                    if not(type(waveread(data[u], 0)) is int):
                        self.button.button3.file_path = data[u]
                        self.button.button3.filename.set(path.basename(data[u]))
                        self.button.button3.signal, self.button.button3.framerate = waveread(data[u], 0)
                        ToolTip.createToolTip(self.button.button3.filelabel, path.basename(data[u]))
                else:
                    log_insert("[警告] ファイル " + data[u] + " が見つかりませんでした。")
            if data[e] != "":
                if path.isfile(data[e]):
                    if not(type(waveread(data[e], 0)) is int):
                        self.button.button4.file_path = data[e]
                        self.button.button4.filename.set(path.basename(data[e]))
                        self.button.button4.signal, self.button.button4.framerate = waveread(data[e], 0)
                        ToolTip.createToolTip(self.button.button4.filelabel, path.basename(data[e]))
                else:
                    log_insert("[警告] ファイル " + data[e] + " が見つかりませんでした。")
            if data[o] != "":
                if path.isfile(data[o]):
                    if not(type(waveread(data[o], 0)) is int):
                        self.button.button5.file_path = data[o]
                        self.button.button5.filename.set(path.basename(data[o]))
                        self.button.button5.signal, self.button.button5.framerate = waveread(data[o], 0)
                        ToolTip.createToolTip(self.button.button5.filelabel, path.basename(data[o]))
                else:
                    log_insert("[警告] ファイル " + data[o] + " が見つかりませんでした。")

    def record(self):
        self.filename = filedialog.asksaveasfilename(title = "ファイル名保存", filetypes = [("JSON", ".json")], defaultextension = "json")
        if len(self.filename) != 0:
            self.data = {"a":self.button.button1.file_path, "i":self.button.button2.file_path, "u":self.button.button3.file_path, "e":self.button.button4.file_path, "o":self.button.button5.file_path}
            try:
                with open(self.filename, "w") as self.f:
                    json.dump(self.data, self.f, indent = 4, ensure_ascii = False)
                log_insert("ファイル名を" + self.filename + "に保存しました。")
            except (AttributeError, PermissionError):
                log_insert("ファイル" + self.filename + "を上書きできません。\n他のプログラムが使用中の可能性があります。")

    def json_import(self):
        self.filename = filedialog.askopenfilename(title = "開く", filetypes = [("JSON", ".json")])
        if len(self.filename) != 0:
                self.json_import1(self.filename)

    def json_import1(self, filename):
        with open(filename) as self.f:
            try:
                self.data = json.load(self.f)
                self.border_final = self.data["border"]
                self.average_final = self.data["average"]
                self.a_final = np.array(self.data["a"])
                self.framerate = int(self.data["framerate"])
                self.file_path = filename
                self.var1.set("現在の変換データ：" + path.basename(filename))
                self.export_button.state(["disabled"])
            except (TypeError, KeyError):
                log_insert("[エラー] データ形式が誤っています。")

    def export(self):
        self.filename = filedialog.asksaveasfilename(title = "変換データ保存", filetypes = [("JSON", ".json")], defaultextension = "json")
        if len(self.filename) != 0:
            self.data = {"border":self.border, "average":self.average, "a":self.a.tolist(), "framerate":self.framerate}
            try:
                with open(self.filename, "w") as self.f:
                    json.dump(self.data, self.f, indent = 4, ensure_ascii = False)
                log_insert("変換データを" + self.filename + "に保存しました。")
            except (AttributeError, PermissionError):
                log_insert("ファイル" + self.filename + "を上書きできません。\n他のプログラムが使用中の可能性があります。")

class rightwindow2(rightwindow):
    def __init__(self, mainframe, a, sample_rate):
        super().__init__(mainframe, a, sample_rate)
        self.secondframe = ttk.Frame(mainframe)
        self.secondframe.grid(column = a, row = 1, sticky = (N, W, E, S))
        self.original_border = [33, 45, 88, 125, 185, 215, 245, 310]
        self.original_average = [40, 1, 40, 5, 0.01, 0.01, 0.01, 0.02, 0.01]
        self.estimated_spec = original_spectrum([self.original_average[0]/1000000, self.original_average[1]/1000000, self.original_average[2]/1000000, self.original_average[3]/1000000, self.original_average[4]/1000000, self.original_average[5]/1000000, self.original_average[6]/1000000, self.original_average[7]/1000000, self.original_average[8]/1000000],
            [(self.original_border[0])/3, (self.original_border[1] + self.original_border[0])/2, (self.original_border[2] + self.original_border[1])/2, (self.original_border[3] + self.original_border[2])/2, (self.original_border[4] + self.original_border[3])/2, (self.original_border[5] + self.original_border[4])/2, (self.original_border[6] + self.original_border[5])/2, (self.original_border[7] + self.original_border[6])/2, (512 + self.original_border[7])/2],
            [(self.original_border[0])/3, (self.original_border[1] - self.original_border[0])/4, (self.original_border[2] - self.original_border[1])/4, (self.original_border[3] - self.original_border[2])/4, (self.original_border[4] - self.original_border[3])/4, (self.original_border[5] - self.original_border[4])/4, (self.original_border[6] - self.original_border[5])/4, (self.original_border[7] - self.original_border[6])/4, (512 - self.original_border[7])/4])
        self.average2 = uv.average_calculate(self.original_border, self.estimated_spec)
        self.edit_window_button = ttk.Button(self.secondframe, text = "編集ウインドウを開く", command = lambda: self.open_voice_editor_window(mainframe, self.original_border, self.original_average, self.estimated_spec))
        self.edit_window_button.grid(column = 0, row = 0, sticky = (E, W))
        self.param_save_button = ttk.Button(self.secondframe, text = "音声パラメータ保存", command = self.original_voice_parameter_save)
        self.param_save_button.grid(column = 0, row = 1, sticky = (E, W))
        self.param_save_button = ttk.Button(self.secondframe, text = "音声パラメータ読込", command = self.original_voice_parameter_import)
        self.param_save_button.grid(column = 0, row = 2, sticky = (E, W))
        self.subframe.tkraise()

    def open_voice_editor_window(self, mainframe, b, a, s):
        self.original_voice_editor = original_voice_editor(mainframe, b, a, s)
        self.update_button = ttk.Button(self.original_voice_editor.frame1, text = "決定", command = self.original_voice_update)
        self.update_button.grid(column = 1, row = 18, columnspan = 3, sticky = (N))
        self.original_voice_editor.frame1.rowconfigure(18, weight = 1)
        self.original_voice_editor.t.grab_set()
        self.original_voice_editor.t.focus_set()
        root.wait_window(self.original_voice_editor.t)

    def original_voice_update(self):
        self.original_border = [self.original_voice_editor.entry1.x, self.original_voice_editor.entry2.x, self.original_voice_editor.entry3.x, self.original_voice_editor.entry4.x, self.original_voice_editor.entry5.x, self.original_voice_editor.entry6.x, self.original_voice_editor.entry7.x, self.original_voice_editor.entry8.x]
        self.original_average = [self.original_voice_editor.entry11.num, self.original_voice_editor.entry12.num, self.original_voice_editor.entry13.num, self.original_voice_editor.entry14.num, self.original_voice_editor.entry15.num, self.original_voice_editor.entry16.num, self.original_voice_editor.entry17.num, self.original_voice_editor.entry18.num, self.original_voice_editor.entry19.num]
        self.estimated_spec = self.original_voice_editor.spec
        self.average2 = uv.average_calculate(self.original_border, self.original_voice_editor.spec)
        self.var1.set("現在の変換データ：人工的に作成")
        self.export_button.state(["!disabled"])
        self.original_voice_editor.t.destroy()

    def original_voice_parameter_import(self):
        self.filename = filedialog.askopenfilename(title = "開く", filetypes = [("JSON", ".json")])
        if len(self.filename) != 0:
            with open(self.filename) as self.f:
                try:
                    self.data = json.load(self.f)
                    self.original_border = self.data["original_border"]
                    self.original_average = self.data["original_average"]
                    self.estimated_spec = original_spectrum([self.original_average[0]/1000000, self.original_average[1]/1000000, self.original_average[2]/1000000, self.original_average[3]/1000000, self.original_average[4]/1000000, self.original_average[5]/1000000, self.original_average[6]/1000000, self.original_average[7]/1000000, self.original_average[8]/1000000],
                        [(self.original_border[0])/3, (self.original_border[1] + self.original_border[0])/2, (self.original_border[2] + self.original_border[1])/2, (self.original_border[3] + self.original_border[2])/2, (self.original_border[4] + self.original_border[3])/2, (self.original_border[5] + self.original_border[4])/2, (self.original_border[6] + self.original_border[5])/2, (self.original_border[7] + self.original_border[6])/2, (512 + self.original_border[7])/2],
                        [(self.original_border[0])/3, (self.original_border[1] - self.original_border[0])/4, (self.original_border[2] - self.original_border[1])/4, (self.original_border[3] - self.original_border[2])/4, (self.original_border[4] - self.original_border[3])/4, (self.original_border[5] - self.original_border[4])/4, (self.original_border[6] - self.original_border[5])/4, (self.original_border[7] - self.original_border[6])/4, (512 - self.original_border[7])/4])
                    self.average2 = self.data["average"]
                except (TypeError, KeyError):
                    log_insert("[エラー] データ形式が誤っています。")

    def original_voice_parameter_save(self):
        self.filename = filedialog.asksaveasfilename(title = "音声パラメータ保存", filetypes = [("JSON", ".json")], defaultextension = "json")
        if len(self.filename) != 0:
            self.data = {"original_border":self.original_border, "original_average":self.original_average, "average":self.average2}
            try:
                with open(self.filename, "w") as self.f:
                    json.dump(self.data, self.f, indent = 4, ensure_ascii = False)
                log_insert("音声パラメータを" + self.filename + "に保存しました。")
            except (AttributeError, PermissionError):
                log_insert("ファイル" + self.filename + "を上書きできません。\n他のプログラムが使用中の可能性があります。")

    def export(self):
        self.filename = filedialog.asksaveasfilename(title = "変換データ保存", filetypes = [("JSON", ".json")], defaultextension = "json")
        if len(self.filename) != 0:
            if self.var1.get() == "現在の変換データ：上より推定":
                self.data = {"border":self.border, "average":self.average, "a":self.a.tolist(), "framerate":self.framerate}
            elif self.var1.get() == "現在の変換データ：人工的に作成":
                self.data = {"border":self.original_border, "average":self.average2, "a":self.estimated_spec, "framerate":app.sample_rate_menu.num}
            try:
                with open(self.filename, "w") as self.f:
                    json.dump(self.data, self.f, indent = 4, ensure_ascii = False)
                log_insert("変換データを" + self.filename + "に保存しました。")
            except (AttributeError, PermissionError):
                log_insert("ファイル" + self.filename + "を上書きできません。\n他のプログラムが使用中の可能性があります。")

class open_button_set:
    def __init__(self, mainframe):
        self.button1 = open_button(mainframe)
        self.button2 = open_button(mainframe)
        self.button3 = open_button(mainframe)
        self.button4 = open_button(mainframe)
        self.button5 = open_button(mainframe)

class open_button:
    def __init__(self, mainframe):
        self.file_path = ""
        self.filename = StringVar()
        self.filename.set("")
        self.button = ttk.Button(mainframe, text = "開く", command = self.file_read, width = "12")
        self.filelabel = ttk.Label(mainframe, textvariable = self.filename)
        self.signal = None
        self.framerate = None

    def file_read(self):
        self.file_path = filedialog.askopenfilename(title = "音声ファイルを開く", filetypes = [("wave", ".wav")])
        if len(self.file_path) != 0:
            self.file_read1(self.file_path)

    def file_read1(self, file_path):
        if not(type(waveread(file_path, 0)) is int):
            self.filename.set(path.basename(file_path))
            self.signal, self.framerate = waveread(file_path, 0)
            ToolTip.createToolTip(self.filelabel, self.filename.get())

class open_button2(open_button):
    def file_read1(self, file_path):
        if not(type(waveread(file_path, 1)) is int):
            self.filename.set(path.basename(file_path))
            self.signal_l, self.signal_r, self.framerate, self.n_channel, self.n_bytes = waveread(file_path, 1)
            ToolTip.createToolTip(self.filelabel, self.filename.get())

class abstract_editor:
    def __init__(self, mainframe, b):
        global regdata
        self.t = Toplevel(mainframe)
        self.t.wm_attributes("-toolwindow", "True")
        if regdata == 0:
            dark_title_bar(self.t)
        if app.button_text3.get() == "ライトモード":
            self.t.configure(background = "#424242")
        self.frame = ttk.Frame(self.t)
        self.frame1 = ttk.Frame(self.t)
        self.frame.grid(column = 0, row = 0)
        self.frame1.grid(column = 1, row = 0, sticky = (N))
        if app.button_text3.get() == "ライトモード": 
            self.fig = Figure(facecolor = "#424242")
        else:
            self.fig = Figure()
        self.ax = self.fig.add_subplot(1,1,1)
        if app.button_text3.get() == "ライトモード":
            self.ax.set_facecolor("#525252")
            self.ax.spines["top"].set_color("#ffffff")
            self.ax.spines["bottom"].set_color("#ffffff")
            self.ax.spines["left"].set_color("#ffffff")
            self.ax.spines["right"].set_color("#ffffff")
            self.ax.tick_params(axis = "x", colors ="#ffffff")
            self.ax.tick_params(axis = "y", colors = "#ffffff")
        self.graph = FigureCanvasTkAgg(self.fig, self.frame)
        self.graph.get_tk_widget().pack()
        self.toolbar = NavigationToolbar(self.graph, self.frame)
        self.entry1 = entryAndLine(self.frame1, self.ax, self.graph, 1, 2, b[0])
        self.entry2 = entryAndLine(self.frame1, self.ax, self.graph, 1, 4, b[1])
        self.entry3 = entryAndLine(self.frame1, self.ax, self.graph, 1, 6, b[2])
        self.entry4 = entryAndLine(self.frame1, self.ax, self.graph, 1, 8, b[3])
        self.entry5 = entryAndLine(self.frame1, self.ax, self.graph, 1, 10, b[4])
        self.entry6 = entryAndLine(self.frame1, self.ax, self.graph, 1, 12, b[5])
        self.entry7 = entryAndLine(self.frame1, self.ax, self.graph, 1, 14, b[6])
        self.entry8 = entryAndLine(self.frame1, self.ax, self.graph, 1, 16, b[7])
        self.label1 = ttk.Label(self.frame1, text = "分割位置1")
        self.label2 = ttk.Label(self.frame1, text = "分割位置2")
        self.label3 = ttk.Label(self.frame1, text = "分割位置3")
        self.label4 = ttk.Label(self.frame1, text = "分割位置4")
        self.label5 = ttk.Label(self.frame1, text = "分割位置5")
        self.label6 = ttk.Label(self.frame1, text = "分割位置6")
        self.label7 = ttk.Label(self.frame1, text = "分割位置7")
        self.label8 = ttk.Label(self.frame1, text = "分割位置8")
        self.label1.grid(column = 1, row = 1)
        self.label2.grid(column = 1, row = 3)
        self.label3.grid(column = 1, row = 5)
        self.label4.grid(column = 1, row = 7)
        self.label5.grid(column = 1, row = 9)
        self.label6.grid(column = 1, row = 11)
        self.label7.grid(column = 1, row = 13)
        self.label8.grid(column = 1, row = 15)

        self.entry1.s.bind("<FocusIn>", lambda event: self.change_black_to_red(self.entry1))
        self.entry1.s.bind("<FocusOut>", lambda event: self.change_red_to_black(self.entry1))
        self.entry1.xcoords.trace_add("write", lambda *args: self.slide(self.entry1))
        self.entry2.s.bind("<FocusIn>", lambda event: self.change_black_to_red(self.entry2))
        self.entry2.s.bind("<FocusOut>", lambda event: self.change_red_to_black(self.entry2))
        self.entry2.xcoords.trace_add("write", lambda *args: self.slide(self.entry2))
        self.entry3.s.bind("<FocusIn>", lambda event: self.change_black_to_red(self.entry3))
        self.entry3.s.bind("<FocusOut>", lambda event: self.change_red_to_black(self.entry3))
        self.entry3.xcoords.trace_add("write", lambda *args: self.slide(self.entry3))
        self.entry4.s.bind("<FocusIn>", lambda event: self.change_black_to_red(self.entry4))
        self.entry4.s.bind("<FocusOut>", lambda event: self.change_red_to_black(self.entry4))
        self.entry4.xcoords.trace_add("write", lambda *args: self.slide(self.entry4))
        self.entry5.s.bind("<FocusIn>", lambda event: self.change_black_to_red(self.entry5))
        self.entry5.s.bind("<FocusOut>", lambda event: self.change_red_to_black(self.entry5))
        self.entry5.xcoords.trace_add("write", lambda *args: self.slide(self.entry5))
        self.entry6.s.bind("<FocusIn>", lambda event: self.change_black_to_red(self.entry6))
        self.entry6.s.bind("<FocusOut>", lambda event: self.change_red_to_black(self.entry6))
        self.entry6.xcoords.trace_add("write", lambda *args: self.slide(self.entry6))
        self.entry7.s.bind("<FocusIn>", lambda event: self.change_black_to_red(self.entry7))
        self.entry7.s.bind("<FocusOut>", lambda event: self.change_red_to_black(self.entry7))
        self.entry7.xcoords.trace_add("write", lambda *args: self.slide(self.entry7))
        self.entry8.s.bind("<FocusIn>", lambda event: self.change_black_to_red(self.entry8))
        self.entry8.s.bind("<FocusOut>", lambda event: self.change_red_to_black(self.entry8))
        self.entry8.xcoords.trace_add("write", lambda *args: self.slide(self.entry8))

        self.entry1.s.bind("<FocusIn>", lambda event:self.get_border(0, self.entry2.x, self.entry1), "+")
        self.entry2.s.bind("<FocusIn>", lambda event:self.get_border(self.entry1.x, self.entry3.x, self.entry2), "+")
        self.entry3.s.bind("<FocusIn>", lambda event:self.get_border(self.entry2.x, self.entry4.x, self.entry3), "+")
        self.entry4.s.bind("<FocusIn>", lambda event:self.get_border(self.entry3.x, self.entry5.x, self.entry4), "+")
        self.entry5.s.bind("<FocusIn>", lambda event:self.get_border(self.entry4.x, self.entry6.x, self.entry5), "+")
        self.entry6.s.bind("<FocusIn>", lambda event:self.get_border(self.entry5.x, self.entry7.x, self.entry6), "+")
        self.entry7.s.bind("<FocusIn>", lambda event:self.get_border(self.entry6.x, self.entry8.x, self.entry7), "+")
        self.entry8.s.bind("<FocusIn>", lambda event:self.get_border(self.entry7.x, 0, self.entry8), "+")

    def slide(self, a):
        if a.xcoords.get().isdecimal():
            a.x = int(a.xcoords.get())
            if a.bottom_num <= a.x < a.top_num:
                a.line.remove()
                a.line = self.ax.axvline(a.x, color = "red")
                self.graph.draw()

    def change_black_to_red(self, a):
        a.x = int(a.xcoords.get())
        a.line.remove()
        a.line = self.ax.axvline(a.x, color = "red")
        self.graph.draw()

    def change_red_to_black(self, a):
        if a.x >= a.top_num:
            a.x = a.top_num - 1
        elif a.x <= a.bottom_num:
            a.x = a.bottom_num
        a.xcoords.set(a.x)
        a.line.remove()
        if app.button_text3.get() == "ライトモード":
            a.line = self.ax.axvline(a.x, color = "white")
        else:
            a.line = self.ax.axvline(a.x, color = "black")
        self.graph.draw()

    def get_border(self, a, b, c):
        if (a != 0):
            c.bottom_num = a + 1
        if (b != 0):
            c.top_num = b

class editor(abstract_editor):
    def __init__(self, mainframe, spec1, spec2, spec3, spec4, spec5, b):
        super().__init__(mainframe, b)
        self.t.title("分割位置の修正")
        self.ax.plot(spec1, color = "deepskyblue", zorder = 1)
        self.ax.plot(spec2, color = "orange", zorder = 1)
        self.ax.plot(spec3, color = "lawngreen", zorder = 1)
        self.ax.plot(spec4, color = "crimson", zorder = 1)
        self.ax.plot(spec5, color = "magenta", zorder = 1)

class original_voice_editor(abstract_editor):
    def __init__(self, mainframe, b, a, e):
        super().__init__(mainframe, b)
        self.t.title("スペクトル包絡データの作成")
        self.frame1.rowconfigure(0, weight = 1)
        self.frame1.rowconfigure(17, weight = 1)
        self.frame2 = ttk.Frame(self.frame1)
        self.frame2.grid(column = 2, row = 0, rowspan = 18, sticky = (N, S))
        self.entry11 = original_voice_param(self.frame2, 2, 1, a[0])
        self.entry12 = original_voice_param(self.frame2, 2, 3, a[1])
        self.entry13 = original_voice_param(self.frame2, 2, 5, a[2])
        self.entry14 = original_voice_param(self.frame2, 2, 7, a[3])
        self.entry15 = original_voice_param(self.frame2, 2, 9, a[4])
        self.entry16 = original_voice_param(self.frame2, 2, 11, a[5])
        self.entry17 = original_voice_param(self.frame2, 2, 13, a[6])
        self.entry18 = original_voice_param(self.frame2, 2, 15, a[7])
        self.entry19 = original_voice_param(self.frame2, 2, 17, a[8])
        self.label11 = ttk.Label(self.frame2, text = "値1")
        self.label12 = ttk.Label(self.frame2, text = "値2")
        self.label13 = ttk.Label(self.frame2, text = "値3")
        self.label14 = ttk.Label(self.frame2, text = "値4")
        self.label15 = ttk.Label(self.frame2, text = "値5")
        self.label16 = ttk.Label(self.frame2, text = "値6")
        self.label17 = ttk.Label(self.frame2, text = "値7")
        self.label18 = ttk.Label(self.frame2, text = "値8")
        self.label19 = ttk.Label(self.frame2, text = "値9")
        self.label11.grid(column = 2, row = 0, columnspan = 2)
        self.label12.grid(column = 2, row = 2, columnspan = 2)
        self.label13.grid(column = 2, row = 4, columnspan = 2)
        self.label14.grid(column = 2, row = 6, columnspan = 2)
        self.label15.grid(column = 2, row = 8, columnspan = 2)
        self.label16.grid(column = 2, row = 10, columnspan = 2)
        self.label17.grid(column = 2, row = 12, columnspan = 2)
        self.label18.grid(column = 2, row = 14, columnspan = 2)
        self.label19.grid(column = 2, row = 16, columnspan = 2)
        self.entry11.var.trace_add("write", lambda *args: self.update(self.entry11))
        self.entry12.var.trace_add("write", lambda *args: self.update(self.entry12))
        self.entry13.var.trace_add("write", lambda *args: self.update(self.entry13))
        self.entry14.var.trace_add("write", lambda *args: self.update(self.entry14))
        self.entry15.var.trace_add("write", lambda *args: self.update(self.entry15))
        self.entry16.var.trace_add("write", lambda *args: self.update(self.entry16))
        self.entry17.var.trace_add("write", lambda *args: self.update(self.entry17))
        self.entry18.var.trace_add("write", lambda *args: self.update(self.entry18))
        self.entry19.var.trace_add("write", lambda *args: self.update(self.entry19))
        self.spec = e
        self.spec_line, = self.ax.plot(self.spec, color = "deepskyblue", zorder = 1)

    def spectrum_estimate(self):
        self.spec =  original_spectrum([self.entry11.num/1000000, self.entry12.num/1000000, self.entry13.num/1000000, self.entry14.num/1000000, self.entry15.num/1000000, self.entry16.num/1000000, self.entry17.num/1000000, self.entry18.num/1000000, self.entry19.num/1000000],
                [self.entry1.x/3, (self.entry2.x + self.entry1.x)/2, (self.entry3.x + self.entry2.x)/2, (self.entry4.x + self.entry3.x)/2, (self.entry5.x + self.entry4.x)/2, (self.entry6.x + self.entry5.x)/2, (self.entry7.x + self.entry6.x)/2, (self.entry8.x + self.entry7.x)/2, (512 + self.entry8.x)/2],
                [self.entry1.x/3, (self.entry2.x - self.entry1.x)/4, (self.entry3.x - self.entry2.x)/4, (self.entry4.x - self.entry3.x)/4, (self.entry5.x - self.entry4.x)/4, (self.entry6.x - self.entry5.x)/4, (self.entry7.x - self.entry6.x)/4, (self.entry8.x - self.entry7.x)/4, (512 - self.entry8.x)/4])

    def update(self, a):
        self.a = a.var.get()
        try:
            a.num = float(self.a)
            if a.num < a.bottom_num:
                a.num = a.buttom_num
            self.spectrum_estimate()
            self.spec_line.set_ydata(self.spec)
            self.graph.draw()
        except ValueError:
            pass

    def slide(self, a):
        if a.xcoords.get().isdecimal():
            a.x = int(a.xcoords.get())
            if a.bottom_num <= a.x < a.top_num:
                a.line.remove()
                a.line = self.ax.axvline(a.x, color = "red")
                self.spectrum_estimate()
                self.spec_line.set_ydata(self.spec)
                self.graph.draw()

class entryAndLine:
    def __init__(self, root, ax, graph, b, c, a):
        self.xcoords = StringVar()
        self.xcoords.set(a)
        self.x = a
        self.bottom_num = 0
        self.top_num = 512
        if app.button_text3.get() == "ライトモード":
            self.line = ax.axvline(a, color="white", zorder = 2)
        else:
            self.line = ax.axvline(a, color="black", zorder = 2)
        self.s = ttk.Spinbox(root, from_ = self.bottom_num, to = self.top_num, increment = 1, textvariable = self.xcoords)
        self.s.grid(column = b, row = c, padx = 3, pady = 3)

class original_voice_param:
    def __init__(self, mainframe, a, b, c):
        self.label = ttk.Label(mainframe, text = "E-6")
        self.var = StringVar()
        self.num = c
        self.var.set(self.num)
        self.bottom_num = 0
        self.top_num = 100
        self.s = ttk.Spinbox(mainframe, from_ = self.bottom_num, to = self.top_num, increment = 0.01, textvariable = self.var)
        self.s.grid(column = a, row = b, pady = 3)
        self.label.grid(column = a + 1, row = b, padx = 3)
        self.s.bind("<FocusOut>", self.display_update)
        self.var.trace_add("write", self.update)

    def update(self, *args):
        self.a = self.var.get()
        if self.a.isdecimal():
            self.num = int(self.a)
            if self.num < self.bottom_num:
                self.num = self.bottom_num

    def display_update(self, event):
        self.var.set(self.num)

class sample_rate_menu:
    def __init__(self, mainframe):
        self.var = StringVar()
        self.var.set(16000)
        self.num = 16000
        self.label = ttk.Label(mainframe, text = "サンプリング周波数", anchor = "e")
        self.entry = ttk.Combobox(mainframe, textvariable = self.var, width = 10)
        self.entry["values"] = ("16000","44100")
        self.label.grid(column = 1, row = 0, sticky = (E, W))
        self.entry.grid(column = 2, row = 0)
        self.entry.bind("<FocusOut>", self.display_update)
        self.var.trace_add("write", self.num_update)

    def num_update(self, *args):
        self.a = self.var.get()
        if self.a.isdecimal():
            self.num = int(self.a)
            if self.num < 1:
                self.num = 1

    def display_update(self, event):
        self.var.set(self.num)

class aperiodicity_transfer_menu:
    def __init__(self, mainframe):
        self.var = StringVar()
        self.var.set(0.60)
        self.num = 0.60
        self.bottom_num = 0.10
        self.top_num = 1.00
        self.entry = ttk.Spinbox(mainframe, from_ = self.bottom_num, to = self.top_num, increment = 0.01, textvariable = self.var, width = 12)
        self.label = ttk.Label(mainframe, text = "非周期指標の変換係数")
        self.label.grid(column = 0, row = 0)
        self.entry.grid(column = 1, row = 0)
        self.entry.bind("<FocusOut>", self.display_update)
        self.var.trace_add("write", self.num_update)

    def num_update(self, *args):
        self.a = self.var.get()
        try:
            self.num = float(self.a)
            if self.num > self.top_num:
                self.num = self.top_num
            elif self.num < self.bottom_num:
                self.num = self.bottom_num
        except ValueError:
            pass

    def display_update(self, event):
        self.var.set(self.num)

class volume_menu:
    def __init__(self, mainframe):
        self.var = StringVar()
        self.var.set(1.0)
        self.num = 1.0
        self.bottom_num = 0.01
        self.top_num = 2.0
        self.entry = ttk.Spinbox(mainframe, from_ = self.bottom_num, to = self.top_num, increment = 0.01, textvariable = self.var, width = 12)
        self.label = ttk.Label(mainframe, text = "出力音量")
        self.label.grid(column = 2, row = 0)
        self.entry.grid(column = 3, row = 0)
        self.entry.bind("<FocusOut>", self.display_update)
        self.var.trace_add("write", self.num_update)

    def num_update(self, *args):
        self.a = self.var.get()
        try:
            self.num = float(self.a)
            if self.num > self.top_num:
                self.num = self.top_num
            elif self.num < self.bottom_num:
                self.num = self.bottom_num
        except ValueError:
            pass

    def display_update(self, event):
        self.var.set(self.num)

class convert_method_menu:
    def __init__(self, mainframe):
        self.label = ttk.Label(mainframe, text = "変換先話者データの作成方法：", anchor = "e")
        self.var = StringVar()
        self.entry = ttk.Combobox(mainframe, textvariable = self.var, width = 13)
        self.entry["values"] = ["音声ファイルから", "本ソフトで作成"]
        self.entry.state(["readonly"])
        self.label.grid(column = 0, row = 0, pady = 3, sticky = (E, W))
        self.entry.grid(column = 1, row = 0, pady = 3)

class frequency_transfer_menu:
    def __init__(self, mainframe):
        self.label = ttk.Label(mainframe, text = "基本周波数の変換方法：")
        self.var = StringVar()
        self.entry = ttk.Combobox(mainframe, textvariable = self.var, width = 13)
        self.entry["values"] = ("比例変換", "オクターブ変換")
        self.entry.state(["readonly"])
        self.label.grid(column = 0, row = 0)
        self.entry.grid(column = 1, row = 0, sticky = (W))
        mainframe.columnconfigure(1, weight = 1)

class frequency_transfer_linear:
    def __init__(self, mainframe):
        self.label1 = ttk.Label(mainframe, text = "(変換前基本周波数)×")
        self.label2 = ttk.Label(mainframe, text = "＋")
        self.var1 = StringVar()
        self.var2 = StringVar()
        self.num1 = 1.0
        self.num2 = 0
        self.var1.set(self.num1)
        self.var2.set(self.num2)
        self.bottom_num1 = 0
        self.top_num1 = 10
        self.bottom_num2 = -1000
        self.top_num2 = 1000
        self.entry1 = ttk.Spinbox(mainframe, from_ = self.bottom_num1, to = self.top_num1, increment = 0.01, textvariable = self.var1, width = 12)
        self.entry2 = ttk.Spinbox(mainframe, from_ = self.bottom_num2, to = self.top_num2, increment = 0.01, textvariable = self.var2, width = 12)
        self.label1.grid(column = 0, row = 0, pady = 3)
        self.entry1.grid(column = 1, row = 0, pady = 3)
        self.label2.grid(column = 2, row = 0, pady = 3)
        self.entry2.grid(column = 3, row = 0, pady = 3)
        self.entry1.bind("<FocusOut>", self.display_update1)
        self.var1.trace_add("write", self.update1)
        self.entry2.bind("<FocusOut>", self.display_update2)
        self.var2.trace_add("write", self.update2)

    def update1(self, *args):
        self.a = self.var1.get()
        try:
            self.num1 = float(self.a)
            if self.num1 < self.bottom_num1:
                self.num1 = self.bottom_num1
        except ValueError:
            pass

    def display_update1(self, event):
        self.var1.set(self.num1)

    def update2(self, *args):
        self.a = self.var2.get()
        try:
            self.num2 = float(self.a)
            if self.num2 < self.bottom_num2:
                self.num2 = self.bottom_num2
        except ValueError:
            pass

    def display_update2(self, event):
        self.var2.set(self.num2)

class frequency_transfer_octave:
    def __init__(self, mainframe):
        self.label1 = ttk.Label(mainframe, text = "変換前基本周波数より12分の")
        self.label2 = ttk.Label(mainframe, text = "オクターブ上")
        self.var = StringVar()
        self.num = 0
        self.var.set(self.num)
        self.bottom_num = -100
        self.top_num = 100
        self.entry = ttk.Spinbox(mainframe, from_ = self.bottom_num, to = self.top_num, increment = 1, textvariable = self.var, width = 12)
        self.label1.grid(column = 0, row = 0, pady = 3)
        self.entry.grid(column = 1, row = 0, pady = 3)
        self.label2.grid(column = 2, row = 0, pady = 3)
        self.entry.bind("<FocusOut>", self.display_update)
        self.var.trace_add("write", self.update)

    def update(self, *args):
        self.a = self.var.get()
        if self.a.isdecimal():
            self.num = int(self.a)
            if self.num < self.bottom_num:
                self.num = self.bottom_num

    def display_update(self, event):
        self.var.set(self.num)

class voice_changer:
    def __init__(self, root):
        self.bak1 = ""
        self.bak2 = ""
        self.result = []
        self.button_text1 = StringVar()
        self.button_text2 = StringVar()
        self.button_text1.set("変換開始")
        self.button_text2.set("変換")
        self.button_text3 = StringVar()
        self.button_text3.set("ダークモード")
        self.entry_text1 = StringVar()
        self.entry_text1.set("デフォルトの入力デバイス")
        self.entry_text2 = StringVar()
        self.entry_text2.set("デフォルトの出力デバイス")
        self.entry_text3 = StringVar()
        self.entry_text3.set("デフォルトのAPI")
        self.entry_text4 = StringVar()
        self.entry_text4.set("1")
        self.save_mode = IntVar()
        self.save_mode.set(0)
        self.flag = 0
        self.frame_length = 1024 * 8
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.device_get()

        self.topframe = ttk.Frame(root, padding = 3)
        self.topframe.grid(column = 0, row = 0, sticky = (N, W, E, S))
        self.mode_change_button = ttk.Button(self.topframe, textvariable = self.button_text3, command = self.mode_change)
        self.mode_change_button.grid(column = 0, row = 0)
        self.sample_rate_menu = sample_rate_menu(self.topframe)
        self.topframe.columnconfigure(1, weight = 1)

        self.p1 = ttk.Panedwindow(root, orient = HORIZONTAL)
        self.p1.grid(column = 0, row = 1, sticky = (N,W,E,S))
        self.mainframe1 = ttk.Frame(root, padding = "3", style = "mainframe.TFrame")
        self.mainframe2 = ttk.Frame(root, padding = "3", style = "mainframe.TFrame")
        self.p1.add(self.mainframe1, weight = 1)
        self.p1.add(self.mainframe2, weight = 3)

        self.realtime_voice_change_button = ttk.Button(self.mainframe1, textvariable = self.button_text1, command = self.voice_change)
        self.file_open_button = open_button2(self.mainframe2)
        self.file_open_button.filename.trace_add("write", self.button_update)
        self.file_convert_button = ttk.Button(self.mainframe2, textvariable = self.button_text2, command = self.file_change)
        self.file_convert_button.state(["disabled"])
        self.input_channel_label = ttk.Label(self.mainframe1, text = "入出力チャンネル数", anchor = "e")
        self.input_channel_menu = ttk.Combobox(self.mainframe1, textvariable = self.entry_text4, width = 1)
        self.input_channel_menu["values"] = [1, 2]
        self.input_channel_menu.state(["readonly"])
        self.label_realtime_voice_change = ttk.Label(self.mainframe1, text = "リアルタイム声質変換")
        self.label_file_change = ttk.Label(self.mainframe2, text = "音声ファイルを変換")
        self.label_realtime_voice_change.grid(column = 0, row = 0, columnspan = 2)
        self.realtime_voice_change_button.grid(column = 0, row = 1, columnspan = 2)
        self.input_channel_label.grid(column = 0, row = 2, sticky = (N, S, E, W))
        self.input_channel_menu.grid(column = 1, row = 2, sticky = (W))
        self.label_file_change.grid(column = 0, columnspan = 2, row = 0)
        self.file_open_button.button.grid(column = 0, row = 1)
        self.file_open_button.filelabel.grid(column = 1, row = 1)
        self.file_convert_button.grid(column = 0, columnspan = 2, row = 2)
        self.mainframe1.columnconfigure(0, weight = 1)
        self.mainframe1.columnconfigure(1, weight = 1)
        self.mainframe2.columnconfigure(1, weight = 1)

        self.topframe1 = ttk.Frame(root, padding = "3")
        self.topframe1.grid(column = 0, row = 2, sticky = (N,W,E,S))
        self.input_api_label = ttk.Label(self.topframe1, text = "API")
        self.input_api_select = ttk.Combobox(self.topframe1, textvariable = self.entry_text3, width = 20)
        self.input_api_select["values"] = self.input_api_list
        self.input_api_select.state(["readonly"])
        self.input_api_select.bind("<<ComboboxSelected>>", self.input_device_label_change)
        self.input_device_label = ttk.Label(self.topframe1, text = "入力デバイス")
        self.input_device_select = ttk.Combobox(self.topframe1, textvariable = self.entry_text1, width = 35)
        self.input_device_select["values"] = self.input_device_display_list
        self.input_device_select.state(["readonly"])
        self.output_device_label = ttk.Label(self.topframe1, text = "出力デバイス")
        self.output_device_select = ttk.Combobox(self.topframe1, textvariable = self.entry_text2, width = 35)
        self.output_device_select["values"] = self.output_device_display_list
        self.output_device_select.state(["readonly"])
        self.device_update = ttk.Button(self.topframe1, text = "更新", command = self.device_get2, width = 5)
        self.input_api_label.grid(column = 0, row = 0, rowspan = 2)
        self.input_api_select.grid(column = 1, row = 0, rowspan = 2)
        self.input_device_label.grid(column = 2, row = 0)
        self.input_device_select.grid(column = 3, row = 0)
        self.output_device_label.grid(column = 2, row = 1)
        self.output_device_select.grid(column = 3, row = 1)
        self.device_update.grid(column = 4, row = 0, padx = 3, rowspan = 2)

        self.topframe2 = ttk.Frame(root, padding = "3")
        self.topframe2.grid(column = 0, row = 3, sticky = (N, W, E, S))
        self.aperiod_menu = aperiodicity_transfer_menu(self.topframe2)
        self.volume_menu = volume_menu(self.topframe2)

        self.topframe3 = ttk.Frame(root, padding = "3")
        self.topframe3.grid(column = 0, row = 4, sticky = (N, W, E, S))
        self.freq_transfer_menu = frequency_transfer_menu(self.topframe3)
        self.freq_transfer_menu.entry.current(0)
        self.freq_transfer_menu.entry.bind("<<ComboboxSelected>>", self.frame_change)

        self.bottomframe3 = ttk.Frame(self.topframe3)
        self.bottomframe3.grid(column = 0, columnspan = 2, row = 1, sticky = (N, W, E, S))
        self.freq_transfer_octave = frequency_transfer_octave(self.bottomframe3)

        self.bottomframe2 = ttk.Frame(self.topframe3)
        self.bottomframe2.grid(column = 0, columnspan = 2, row = 1, sticky = (N, W, E, S))
        self.freq_transfer_linear = frequency_transfer_linear(self.bottomframe2)

        self.p = ttk.Panedwindow(root, orient = HORIZONTAL)
        self.p.grid(column = 0, row = 5, sticky = (N,W,E,S))
        self.leftframe = ttk.Frame(self.p, padding = "3", style = "mainframe.TFrame")
        self.rightframe = ttk.Frame(self.p, padding = "3", style = "mainframe.TFrame")
        self.p.add(self.leftframe, weight = 1)
        self.p.add(self.rightframe, weight = 1)

        self.label_title_leftcolumn = ttk.Label(self.leftframe, text = "変換元話者")
        self.label_title_rightcolumn = ttk.Label(self.rightframe, text = "変換先話者")
        self.label_title_leftcolumn.grid(column = 0, row = 0)
        self.label_title_rightcolumn.grid(column = 0, row = 0)
        self.rightwindow1 = rightwindow(self.leftframe, 0, self.sample_rate_menu.num)
        self.rightwindow2 = rightwindow2(self.rightframe, 0, self.sample_rate_menu.num)

        self.leftframe.columnconfigure(0, weight = 1)
        self.rightframe.columnconfigure(0, weight = 1)
        self.rightwindow1.subframe.columnconfigure(2, weight = 1)
        self.rightwindow2.subframe.columnconfigure(2, weight = 1)

        self.bottomframe1 = ttk.Frame(root, padding = "3")
        self.bottomframe1.grid(column = 0, row = 6, sticky = (N, W, E, S))
        self.convert_method_menu = convert_method_menu(self.bottomframe1)
        self.convert_method_menu.entry.current(0)
        self.convert_method_menu.entry.bind("<<ComboboxSelected>>", self.frame_change2)
        self.bottomframe1.columnconfigure(0, weight = 1)

        self.logframe = ttk.Frame(root, padding = "0")
        self.logframe.grid(column = 0, row = 7, sticky = (N,E,W,S))
        self.log = log(self.logframe)
        self.log.logarea.grid(column = 0, row = 0, sticky = (N,E,W,S))
        self.log.ys.grid(column = 1, row = 0, sticky = (N,W,E,S))
        self.logframe.columnconfigure(0, weight = 1)
        self.logframe.rowconfigure(0, weight = 1)

        root.columnconfigure(0, weight = 1)
        root.rowconfigure(7, weight = 1)

    def device_get(self):
        self.input_api_list = []
        self.input_api_list.append("デフォルトのAPI")
        self.input_api_index_list = []
        self.input_device_list = []
        self.input_device_index_list = []
        self.output_device_list = []
        self.output_device_index_list = []
        self.input_device_display_list = ["デフォルトの入力デバイス"]
        self.input_device_index_current = [self.audio.get_default_input_device_info()["index"]]
        self.output_device_display_list = ["デフォルトの出力デバイス"]
        self.output_device_index_current = [self.audio.get_default_output_device_info()["index"]]
        self.cut_pos_input = []
        self.cut_pos_output = []
        self.cut_pos_input.append(0)
        self.cut_pos_output.append(0)
        self.num_cut_pos_input = 0
        self.num_cut_pos_output = 0
        for j in range(self.audio.get_host_api_count()):
            self.num_input_device = 0
            self.num_output_device = 0
            for k in range(self.audio.get_host_api_info_by_index(j)["deviceCount"]):
                if self.audio.get_device_info_by_host_api_device_index(j, k)["maxInputChannels"] != 0:
                    self.num_input_device = self.num_input_device + 1
                    self.input_device_list.append(self.audio.get_device_info_by_host_api_device_index(j, k)["name"])
                    self.input_device_index_list.append(self.audio.get_device_info_by_host_api_device_index(j, k)["index"])
                if self.audio.get_device_info_by_host_api_device_index(j, k)["maxOutputChannels"] != 0:
                    self.num_output_device = self.num_output_device + 1
                    self.output_device_list.append(self.audio.get_device_info_by_host_api_device_index(j, k)["name"])
                    self.output_device_index_list.append(self.audio.get_device_info_by_host_api_device_index(j, k)["index"])
            self.num_cut_pos_input = self.num_cut_pos_input + self.num_input_device
            self.num_cut_pos_output = self.num_cut_pos_output + self.num_output_device
            self.cut_pos_input.append(self.num_cut_pos_input)
            self.cut_pos_output.append(self.num_cut_pos_output)
            if self.num_input_device != 0 and self.num_output_device != 0:
                self.input_api_list.append(self.audio.get_host_api_info_by_index(j)["name"])
                self.input_api_index_list.append(self.audio.get_host_api_info_by_index(j)["index"])
            if self.audio.get_host_api_info_by_index(j)["index"] == self.audio.get_default_host_api_info()["index"]:
                self.input_api_index_list.insert(0, self.audio.get_default_host_api_info()["index"])

    def device_get2(self):
        self.device_get()
        self.input_api_select.current(0)
        self.input_device_label_change(0)

    def mode_change(self):
        global style
        global root
        self.bak3 = []
        self.bak3.append(self.input_api_select.current())
        self.bak3.append(self.input_device_select.current())
        self.bak3.append(self.output_device_select.current())
        self.bak3.append(self.sample_rate_menu.entry.current())
        self.bak3.append(self.convert_method_menu.entry.current())
        self.bak3.append(self.freq_transfer_menu.entry.current())
        self.bak3.append(self.input_channel_menu.current())
        if self.button_text3.get() == "ダークモード":
            style.theme_use("black")
            style.configure("TSpinbox", fieldbackground = "#525252", foreground = "#ffffff")
            style.configure("TCombobox", fieldbackground = "#525252", foreground = "#ffffff")
            style.configure("Sash", sashthickness = 6)
            style.configure("mainframe.TFrame", relief = "sunken")
            style.configure("TButton", anchor = "center")
            self.log.logarea.configure(background = "#525252", foreground = "#ffffff", selectbackground = "#4a6984", selectforeground = "#ffffff")
            root.option_add("*TCombobox*Listbox.background", "#525252")
            root.option_add("*TCombobox*Listbox.foreground", "#ffffff")
            root.option_add("*TCombobox*Listbox.selectBackground", "#4a6984")
            root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
            self.button_text3.set("ライトモード")
        elif self.button_text3.get() == "ライトモード":
            style.theme_use("vista")
            self.log.logarea.configure(background = "systemWindow", foreground = "systemWindowText", selectbackground = "systemHighlight", selectforeground = "systemHighlightText")
            root.option_add("*TCombobox*Listbox.background", "systemWindow")
            root.option_add("*TCombobox*Listbox.foreground", "systemWindowText")
            root.option_add("*TCombobox*Listbox.selectBackground", "systemHighlight")
            root.option_add("*TCombobox*Listbox.selectForeground", "systemHighlightText")
            self.button_text3.set("ダークモード")
        #combobox widgetを強制的に再生成(プルダウンリスト部分の色設定を反映させる為)
        del self.input_api_select, self.input_device_select, self.output_device_select, self.sample_rate_menu, self.convert_method_menu, self.freq_transfer_menu, self.input_channel_menu
        self.input_api_select = ttk.Combobox(self.topframe1, textvariable = self.entry_text3, width = 20)
        self.input_api_select["values"] = self.input_api_list
        self.input_api_select.state(["readonly"])
        self.input_api_select.bind("<<ComboboxSelected>>", self.input_device_label_change)
        self.input_api_select.grid(column = 1, row = 0, rowspan = 2)
        self.input_api_select.current(self.bak3[0])
        self.input_device_select = ttk.Combobox(self.topframe1, textvariable = self.entry_text1, width = 35)
        self.input_device_select["values"] = self.input_device_display_list
        self.input_device_select.state(["readonly"])
        self.input_device_select.grid(column = 3, row = 0)
        self.input_device_select.current(self.bak3[1])
        self.output_device_select = ttk.Combobox(self.topframe1, textvariable = self.entry_text2, width = 35)
        self.output_device_select["values"] = self.output_device_display_list
        self.output_device_select.state(["readonly"])
        self.output_device_select.grid(column = 3, row = 1)
        self.output_device_select.current(self.bak3[2])
        self.sample_rate_menu = sample_rate_menu(self.topframe)
        self.sample_rate_menu.entry.current(self.bak3[3])
        self.convert_method_menu = convert_method_menu(self.bottomframe1)
        self.convert_method_menu.entry.bind("<<ComboboxSelected>>", self.frame_change2)
        self.convert_method_menu.entry.current(self.bak3[4])
        self.freq_transfer_menu = frequency_transfer_menu(self.topframe3)
        self.freq_transfer_menu.entry.bind("<<ComboboxSelected>>", self.frame_change)
        self.freq_transfer_menu.entry.current(self.bak3[5])
        self.input_channel_menu = ttk.Combobox(self.mainframe1, textvariable = self.entry_text4, width = 1)
        self.input_channel_menu["values"] = [1, 2]
        self.input_channel_menu.state(["readonly"])
        self.input_channel_menu.grid(column = 1, row = 2, sticky = (W))
        self.input_channel_menu.current(self.bak3[6])

    def input_device_label_change(self, event):
        self.b = self.input_api_select.current()
        if self.b == 0:
            self.input_device_display_list = ["デフォルトの入力デバイス"]
            self.input_device_index_current = [self.audio.get_default_input_device_info()["index"]]
            self.output_device_display_list = ["デフォルトの出力デバイス"]
            self.output_device_index_current = [self.audio.get_default_output_device_info()["index"]]
        else:
            self.input_device_display_list = self.input_device_list[self.cut_pos_input[self.input_api_index_list[self.b]]:self.cut_pos_input[self.input_api_index_list[self.b] + 1]]
            self.input_device_index_current = self.input_device_index_list[self.cut_pos_input[self.input_api_index_list[self.b]]:self.cut_pos_input[self.input_api_index_list[self.b] + 1]]
            self.output_device_display_list = self.output_device_list[self.cut_pos_output[self.input_api_index_list[self.b]]:self.cut_pos_output[self.input_api_index_list[self.b] + 1]]
            self.output_device_index_current = self.output_device_index_list[self.cut_pos_output[self.input_api_index_list[self.b]]:self.cut_pos_output[self.input_api_index_list[self.b] + 1]]
        self.input_device_select["values"] = self.input_device_display_list
        self.input_device_select.current(0)
        self.output_device_select["values"] = self.output_device_display_list
        self.output_device_select.current(0)

    def voice_change(self):
        if self.rightwindow1.var1.get() != "現在の変換データ：(データなし)" and self.rightwindow2.var1.get() != "現在の変換データ：(データなし)":
            self.mode_change_button.state(["disabled"])
            if self.rightwindow2.var1.get() == "現在の変換データ：人工的に作成":
                if self.rightwindow1.framerate == self.sample_rate_menu.num:
                    self.voice_change2()
                else:
                    log_insert("[エラー] 変換元話者の変換データの周波数(" + str(self.rightwindow1.framerate) + "Hz)と現在の規定値(" + str(self.sample_rate_menu.num) + "Hz)が一致していません。")
            else:
                if self.rightwindow1.framerate == self.rightwindow2.framerate == self.sample_rate_menu.num:
                    self.voice_change2()
                else:
                    log_insert("[エラー] 変換元話者の変換データの周波数(" + str(self.rightwindow1.framerate) + "Hz) 、変換先話者の変換データの周波数(" + str(self.rightwindow2.framerate) + "Hz)、現在の規定値(" + str(self.sample_rate_menu.num) + "Hz)が一致していません。")
        else:
            if self.rightwindow1.var1.get() == "現在の変換データ：(データなし)":
                log_insert("[エラー] 変換元話者の変換データがありません。")
            if self.rightwindow2.var1.get() == "現在の変換データ：(データなし)":
                log_insert("[エラー] 変換先話者の変換データがありません。")

    def voice_change2(self):
        if self.flag == 0:
            self.flag = 1
            self.button_text1.set("変換停止")
            self.input_api_select.state(["disabled"])
            self.input_device_select.state(["disabled"])
            self.output_device_select.state(["disabled"])
            self.device_update.state(["disabled"])
            self.audio = pyaudio.PyAudio()
            try:
                if self.audio.is_format_supported(rate = self.sample_rate_menu.num,
                            input_device = self.input_device_index_current[self.input_device_select.current()],
                            input_channels = int(self.entry_text4.get()),
                            input_format = pyaudio.paInt16):
                    try:
                        if self.audio.is_format_supported(rate = self.sample_rate_menu.num,
                                output_device = self.output_device_index_current[self.output_device_select.current()],
                                output_channels = int(self.entry_text4.get()),
                                output_format = pyaudio.paInt16):
                            self.stream = self.audio.open(format = pyaudio.paInt16,
                                channels = int(self.entry_text4.get()),
                                rate = self.sample_rate_menu.num,
                                frames_per_buffer = self.frame_length,
                                input=True,
                                output=True,
                                input_device_index = self.input_device_index_current[self.input_device_select.current()],
                                output_device_index = self.output_device_index_current[self.output_device_select.current()],
                                stream_callback = self.callback)
                    except ValueError as e:
                        if e.args[0] == "Invalid sample rate":
                            log_insert("[エラー] 現在の周波数(" + str(self.sample_rate_menu.num) + "Hz)がOS側の周波数の設定と異なっています。\nコントロールパネル>ハードウェアとサウンド>サウンドからデバイスのプロパティを開き、周波数の設定を変更してください。")
                        else:
                            log_insert("[エラー] 出力デバイスが現在の音声形式(" + str(self.sample_rate_menu.num) + "Hz/16bit/" + self.entry_text4.get() + "チャンネル)に対応していません。")
                        self.flag = 0
                        self.button_text1.set("変換開始")
                        self.audio.terminate()
                        self.input_api_select.state(["!disabled"])
                        self.input_device_select.state(["!disabled"])
                        self.output_device_select.state(["!disabled"])
                        self.device_update.state(["!disabled"])
            except ValueError as e:
                if e.args[0] == "Invalid sample rate":
                    log_insert("[エラー] 現在の周波数(" + str(self.sample_rate_menu.num) + "Hz)がOS側の周波数の設定と異なっています。\nコントロールパネル>ハードウェアとサウンド>サウンドからデバイスのプロパティを開き、周波数の設定を変更してください。")
                else:
                    log_insert("[エラー] 入力デバイスが現在の音声形式(" + str(self.sample_rate_menu.num) + "Hz/16bit/" + self.entry_text4.get() + "チャンネル)に対応していません。")
                self.flag = 0
                self.button_text1.set("変換開始")
                self.audio.terminate()
                self.input_api_select.state(["!disabled"])
                self.input_device_select.state(["!disabled"])
                self.output_device_select.state(["!disabled"])
                self.device_update.state(["!disabled"])
        elif self.flag == 1:
            self.flag = 0
            self.button_text1.set("変換開始")
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()
            self.input_api_select.state(["!disabled"])
            self.input_device_select.state(["!disabled"])
            self.output_device_select.state(["!disabled"])
            self.device_update.state(["!disabled"])
            self.mode_change_button.state(["!disabled"])

    def callback(self, in_data, frame_count, time_info, status):
        if self.entry_text4.get() == "2":
            self.spec_mat_l, self.aperiod_mat_l, self.f0_l = self.voice_convert(np.ascontiguousarray(np.frombuffer(in_data, dtype = "int16").astype(np.float64)[::2]/32768.0))
            self.new_f0_l = self.freq_convert(self.f0_l)
            if not(type(self.new_f0_l) is int):
                self.out_data_l = pw.synthesize(self.new_f0_l, self.spec_mat_l, self.aperiod_mat_l, self.sample_rate_menu.num)
                self.spec_mat_r, self.aperiod_mat_r, self.f0_r = self.voice_convert(np.ascontiguousarray(np.frombuffer(in_data, dtype = "int16").astype(np.float64)[1::2]/32768.0))
                self.new_f0_r = self.freq_convert(self.f0_r)
                if not(type(self.new_f0_r) is int):
                    self.out_data_r = pw.synthesize(self.new_f0_r, self.spec_mat_r, self.aperiod_mat_r, self.sample_rate_menu.num)
                    self.out_data = np.empty(len(self.out_data_l) + len(self.out_data_r), dtype = "float64")
                    self.out_data[::2] = self.out_data_l * 32768.0 * self.volume_menu.num
                    self.out_data[1::2] = self.out_data_r * 32768.0 * self.volume_menu.num
                    return (self.out_data.astype(np.int16).tobytes(), pyaudio.paContinue)
        else:
            self.spec_mat, self.aperiod_mat, self.f0 = self.voice_convert(np.frombuffer(in_data, dtype = "int16").astype(np.float64)/32768.0)
            self.new_f0 = self.freq_convert(self.f0)
            if not(type(self.new_f0) is int):
                self.out_data = pw.synthesize(self.new_f0, self.spec_mat, self.aperiod_mat, self.sample_rate_menu.num) * 32768.0 * self.volume_menu.num
                return (self.out_data.astype(np.int16).tobytes(), pyaudio.paContinue)

    def file_change(self):
        if self.rightwindow1.var1.get() != "現在の変換データ：(データなし)" and self.rightwindow2.var1.get() != "現在の変換データ：(データなし)":
            self.mode_change_button.state(["disabled"])
            if self.rightwindow2.var1.get() == "現在の変換データ：人工的に作成":
                if self.rightwindow1.framerate == self.sample_rate_menu.num == self.file_open_button.framerate:
                    self.filename = filedialog.asksaveasfilename(title = "保存", filetypes = [("Wave", ".wav")], defaultextension = "wav")
                    if len(self.filename) != 0:
                        self.thread1 = threading.Thread(target = self.run)
                        self.thread1.start()
                else:
                    log_insert("[エラー] 変換元話者の変換データの周波数(" + str(self.rightwindow1.framerate) + "Hz) 、変換する音声ファイルの周波数(" + str(self.file_open_button.framerate) + "Hz)、規定値(" + str(self.sample_rate_menu.num) + "Hz)が一致していません。")
            else:
                if self.rightwindow1.framerate == self.rightwindow2.framerate == self.file_open_button.framerate:
                    self.filename = filedialog.asksaveasfilename(title = "保存", filetypes = [("Wave", ".wav")], defaultextension = "wav")
                    if len(self.filename) != 0:
                        self.thread1 = threading.Thread(target = self.run)
                        self.thread1.start()
                else:
                    log_insert("[エラー] 変換元話者の音声ファイルの周波数(" + str(self.rightwindow1.framerate) + "Hz) 、変換先話者の音声ファイルの周波数(" + str(self.rightwindow2.framerate) + "Hz)、変換する音声ファイルの周波数(" + str(self.file_open_button.framerate) + "Hz)が一致していません。")
        else:
            if self.rightwindow1.var1.get() == "現在の変換データ：(データなし)":
                log_insert("[エラー] 変換元話者の変換データがありません。")
            if self.rightwindow2.var1.get() == "現在の変換データ：(データなし)":
                log_insert("[エラー] 変換先話者の変換データがありません。")

    def run(self):
        self.volume_menu.entry.state(["disabled"])
        if self.file_open_button.n_channel == 1:
            self.spec_mat, self.aperiod_mat, self.f0 = self.voice_convert(self.file_open_button.signal_l)
            self.new_f0 = self.freq_convert(self.f0)
            if not(type(self.new_f0) is int):
                self.out_data = pw.synthesize(self.new_f0, self.spec_mat, self.aperiod_mat, self.file_open_button.framerate) * 32768.0 * self.volume_menu.num
            else:
                self.volume_menu.entry.state(["!disabled"])
                self.mode_change_button.state(["!disabled"])
                return 1
        elif self.file_open_button.n_channel == 2:
            self.spec_mat_l, self.aperiod_mat_l, self.f0_l = self.voice_convert(self.file_open_button.signal_l)
            self.new_f0_l = self.freq_convert(self.f0_l)
            if not(type(self.new_f0_l) is int):
                self.out_data_l = pw.synthesize(self.new_f0_l, self.spec_mat_l, self.aperiod_mat_l, self.file_open_button.framerate) * 32768.0 * self.volume_menu.num
                self.spec_mat_r, self.aperiod_mat_r, self.f0_r = self.voice_convert(self.file_open_button.signal_r)
                self.new_f0_r = self.freq_convert(self.f0_r)
                if not(type(self.new_f0_r) is int):
                    self.out_data_r = pw.synthesize(self.new_f0_r, self.spec_mat_r, self.aperiod_mat_r, self.file_open_button.framerate) * 32768.0 * self.volume_menu.num
                    self.out_data = np.empty(len(self.out_data_l) + len(self.out_data_r), dtype = "float64")
                    self.out_data[::2] = self.out_data_l
                    self.out_data[1::2] = self.out_data_r
                else:
                    self.volume_menu.entry.state(["!disabled"])
                    self.mode_change_button.state(["!disabled"])
                    return 1
            else:
                self.volume_menu.entry.state(["!disabled"])
                self.mode_change_button.state(["!disabled"])
                return 1
        try:
            self.f = wave.open(self.filename, "wb")
            self.f.setnchannels(self.file_open_button.n_channel)
            self.f.setsampwidth(2)
            self.f.setframerate(self.sample_rate_menu.num)
            self.f.writeframes(self.out_data.astype(np.int16).tobytes())
            self.f.close()
            log_insert("変換が完了しました。ファイルのパスは" + self.filename + "です。")
        except (AttributeError, PermissionError):
            log_insert("ファイル" + self.filename + "を上書きできません。\n他のプログラムが使用中の可能性があります。")
        finally:
            self.volume_menu.entry.state(["!disabled"])
            self.mode_change_button.state(["!disabled"])

    def voice_convert(self, a):
            if self.rightwindow2.var1.get() == "現在の変換データ：人工的に作成":
                self.result = uv.voice_convert(a, self.rightwindow1.average_final, self.rightwindow1.border_final, self.rightwindow2.estimated_spec, self.rightwindow2.original_border, self.sample_rate_menu.num, self.aperiod_menu.num)
            else:
                self.result = uv.voice_convert(a, self.rightwindow1.average_final, self.rightwindow1.border_final, self.rightwindow2.a_final, self.rightwindow2.border_final, self.sample_rate_menu.num, self.aperiod_menu.num)
            return self.result

    def frame_change(self, event):
        self.mode_change_button.state(["disabled"])
        if self.freq_transfer_menu.var.get() == "比例変換":
            self.bottomframe2.tkraise()
        elif self.freq_transfer_menu.var.get() == "オクターブ変換":
            self.bottomframe3.tkraise()
        self.mode_change_button.state(["!disabled"])

    def frame_change2(self, event):
        self.mode_change_button.state(["disabled"])
        self.bak1 = self.rightwindow2.var1.get()
        if self.convert_method_menu.var.get() == "音声ファイルから":
            self.rightwindow2.subframe.tkraise()
            if self.bak1 == "現在の変換データ：人工的に作成":
                if self.bak2 != "":
                    self.rightwindow2.var1.set(self.bak2)
                    if self.bak2 == "現在の変換データ：上より推定":
                        self.rightwindow2.export_button.state(["!disabled"])
                    else:
                        self.rightwindow2.export_button.state(["disabled"])
        elif self.convert_method_menu.var.get() == "本ソフトで作成":
            self.rightwindow2.secondframe.tkraise()
            if self.bak1 != "現在の変換データ：人工的に作成":
                if self.bak1 == "現在の変換データ：(データなし)" or self.bak1 == "現在の変換データ：上より推定":
                    self.rightwindow2.var1.set("現在の変換データ：人工的に作成")
                    self.rightwindow2.export_button.state(["!disabled"])
                self.bak2 = self.bak1
        self.mode_change_button.state(["!disabled"])

    def freq_convert(self, a):
        self.new_a = []
        self.f = 0
        for j in range(len(a)):
            if a[j] == 0:
                self.new_a.append(0.0)
            else:
                if self.freq_transfer_menu.var.get() == "比例変換":
                    self.b = a[j] * self.freq_transfer_linear.num1 + self.freq_transfer_linear.num2
                    if self.b < 0:
                        self.f = 1
                    else:
                        self.new_a.append(self.b)
                elif self.freq_transfer_menu.var.get() == "オクターブ変換":
                    self.new_a.append(a[j] * (2 ** (self.freq_transfer_octave.num/12)))
        if self.f == 0:
            return np.array(self.new_a)
        else:
            log_insert("[エラー] 変換後の基本周波数がマイナスになりました。\n変換係数を変更してもう一度試してください。")
            return 1

    def button_update(self, *args):
        self.file_convert_button.state(["!disabled"])

    def save_values(self):
        self.confirm_window = Toplevel(root)
        self.confirm_window.title("終了の確認")
        self.confirm_window.wm_attributes("-toolwindow", "True")
        if regdata == 0:
            dark_title_bar(self.confirm_window)
        self.confirm_frame = ttk.Frame(self.confirm_window, padding = 3)
        self.confirm_frame.grid(column = 0, row = 0, sticky = (N, W, E, S))
        self.confirm_message = ttk.Label(self.confirm_frame, text = "終了前に、現在の入力内容を保存しますか？")
        self.confirm_message.grid(column = 0, row = 0, columnspan = 2)
        self.yes_button = ttk.Button(self.confirm_frame, text = "はい", command = self.save)
        self.no_button = ttk.Button(self.confirm_frame, text = "いいえ", command = self.quit)
        self.yes_button.grid(column = 0, row = 1, pady = 3)
        self.no_button.grid(column = 1, row = 1, pady = 3)
        self.confirm_frame.columnconfigure(0, weight = 1)
        self.confirm_frame.columnconfigure(1, weight = 1)
        self.yes_button.focus()
        self.confirm_window.grab_set()
        self.confirm_window.focus_set()
        root.wait_window(self.confirm_window)

    def save(self):
        self.save_data = {}
        self.save_data.update(left_a = self.rightwindow1.button.button1.file_path)
        self.save_data.update(left_i = self.rightwindow1.button.button2.file_path)
        self.save_data.update(left_u = self.rightwindow1.button.button3.file_path)
        self.save_data.update(left_e = self.rightwindow1.button.button4.file_path)
        self.save_data.update(left_o = self.rightwindow1.button.button5.file_path)
        self.save_data.update(right_a = self.rightwindow2.button.button1.file_path)
        self.save_data.update(right_i = self.rightwindow2.button.button2.file_path)
        self.save_data.update(right_u = self.rightwindow2.button.button3.file_path)
        self.save_data.update(right_e = self.rightwindow2.button.button4.file_path)
        self.save_data.update(right_o = self.rightwindow2.button.button5.file_path)
        self.save_data.update(left_parameter_file = self.rightwindow1.file_path)
        self.save_data.update(right_parameter_file = self.rightwindow2.file_path)
        self.save_data.update(file_for_convert = self.file_open_button.file_path)
        self.save_data.update(sample_rate = self.sample_rate_menu.num)
        self.save_data.update(aperiodicity_transfer_rate = self.aperiod_menu.num)
        self.save_data.update(volume = self.volume_menu.num)
        self.save_data.update(frequency_transfer_parameter_1 = self.freq_transfer_linear.num1)
        self.save_data.update(frequency_transfer_parameter_2 = self.freq_transfer_linear.num2)
        self.save_data.update(frequency_transfer_parameter_3 = self.freq_transfer_octave.num)
        self.save_data.update(original_voice_border_parameter = self.rightwindow2.original_border)
        self.save_data.update(original_voice_average_parameter = self.rightwindow2.original_average)
        self.save_data.update(original_average = self.rightwindow2.average2)
        self.save_data.update(estimated_spec = self.rightwindow2.estimated_spec)
        with open(path.dirname(sys.argv[0]) + "\\" + "Latest.json", "w") as self.f:
            json.dump(self.save_data, self.f, indent = 4, ensure_ascii = False)
        self.quit()

    def quit(self):
        self.confirm_window.destroy()
        root.destroy()

app = voice_changer(root)

if regdata == 0:
    app.mode_change()

if path.isfile(path.dirname(sys.argv[0]) + "\\" + "Latest.json"):
    with open(path.dirname(sys.argv[0]) + "\\" + "Latest.json") as f:
        try:
            load_data = json.load(f)
            app.sample_rate_menu.num = load_data["sample_rate"]
            app.sample_rate_menu.var.set(load_data["sample_rate"])
            app.aperiod_menu.num = load_data["aperiodicity_transfer_rate"]
            app.aperiod_menu.var.set(load_data["aperiodicity_transfer_rate"])
            app.volume_menu.num = load_data["volume"]
            app.volume_menu.var.set(load_data["volume"])
            app.freq_transfer_linear.num1 = load_data["frequency_transfer_parameter_1"]
            app.freq_transfer_linear.var1.set(load_data["frequency_transfer_parameter_1"])
            app.freq_transfer_linear.num2 = load_data["frequency_transfer_parameter_2"]
            app.freq_transfer_linear.var2.set(load_data["frequency_transfer_parameter_2"])
            app.freq_transfer_octave.num = load_data["frequency_transfer_parameter_3"]
            app.freq_transfer_octave.var.set(load_data["frequency_transfer_parameter_3"])
            app.rightwindow1.file_import1(load_data, "left_a", "left_i", "left_u", "left_e", "left_o")
            app.rightwindow2.file_import1(load_data, "right_a", "right_i", "right_u", "right_e", "right_o")
            if load_data["left_parameter_file"] != "":
                if path.isfile(load_data["left_parameter_file"]):
                    app.rightwindow1.json_import1(load_data["left_parameter_file"])
                else:
                    log_insert("[警告] ファイル" + load_data["left_parameter_file"] + "が見つかりませんでした。")
            if load_data["right_parameter_file"] != "":
                if path.isfile(load_data["right_parameter_file"]):
                    app.rightwindow2.json_import1(load_data["right_parameter_file"])
                else:
                    log_insert("[警告] ファイル" + load_data["right_parameter_file"] + "が見つかりませんでした。")
            app.rightwindow2.original_border = load_data["original_voice_border_parameter"]
            app.rightwindow2.original_average = load_data["original_voice_average_parameter"]
            app.rightwindow2.average2 = load_data["original_average"]
            app.rightwindow2.estimated_spec = load_data["estimated_spec"]
            if load_data["file_for_convert"] != "":
                if path.isfile(load_data["file_for_convert"]):
                    app.file_open_button.file_read1(load_data["file_for_convert"])
                else:
                    log_insert("[警告] ファイル" + load_data["file_for_convert"] + "が見つかりませんでした。")
        except (TypeError, KeyError):
            log_insert("[警告] データ形式が誤っています。")
else:
    log_insert("[警告] 前回終了した時のデータが見つかりません。(この警告は、初回起動時にも表示されます)")

root.iconbitmap(path.dirname(sys.argv[0]) + "\\images\\Koehen-Logo.ico")
root.minsize(width = 400, height = 550)
root.protocol("WM_DELETE_WINDOW", app.save_values)
root.mainloop()