from __future__ import annotations

import socket
import threading
import time
import webbrowser
from tkinter import BOTH, LEFT, X, Button, Label, Tk, messagebox

import uvicorn

from .web_app import app


HOST = "127.0.0.1"
PORT = 8787
URL = f"http://{HOST}:{PORT}"


def port_is_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((HOST, PORT)) == 0


class ValorantClipperWindow:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Valorant 高光剪辑")
        self.root.geometry("460x180")
        self.root.resizable(False, False)
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None

        self.status = Label(self.root, text="准备启动", anchor="w", font=("Microsoft YaHei UI", 11))
        self.status.pack(fill=X, padx=18, pady=(18, 8))

        hint = Label(
            self.root,
            text="本程序会在本机启动网页服务，然后用浏览器打开剪辑页面。",
            anchor="w",
            fg="#555555",
            font=("Microsoft YaHei UI", 9),
        )
        hint.pack(fill=X, padx=18)

        button_bar = Label(self.root)
        button_bar.pack(fill=BOTH, padx=14, pady=18)

        Button(button_bar, text="打开网页", width=12, command=self.open_web).pack(side=LEFT, padx=4)
        Button(button_bar, text="查看状态", width=12, command=self.show_status).pack(side=LEFT, padx=4)
        Button(button_bar, text="停止并退出", width=12, command=self.stop_and_exit).pack(side=LEFT, padx=4)

        self.root.protocol("WM_DELETE_WINDOW", self.stop_and_exit)

    def set_status(self, text: str) -> None:
        self.status.config(text=text)
        self.root.update_idletasks()

    def start_server(self) -> None:
        if port_is_open():
            self.set_status(f"已检测到服务运行中：{URL}")
            self.open_web()
            return

        config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()

        for _ in range(50):
            if port_is_open():
                self.set_status(f"运行中：{URL}")
                self.open_web()
                return
            time.sleep(0.1)

        self.set_status("启动失败")
        messagebox.showerror("Valorant 高光剪辑", "启动失败，请确认端口 8787 没有被占用。")

    def open_web(self) -> None:
        webbrowser.open(URL)

    def show_status(self) -> None:
        if port_is_open():
            messagebox.showinfo("Valorant 高光剪辑", f"当前状态：运行中\n地址：{URL}")
        else:
            messagebox.showwarning("Valorant 高光剪辑", "当前状态：未运行")

    def stop_and_exit(self) -> None:
        if self.server:
            self.server.should_exit = True
        self.root.after(250, self.root.destroy)

    def run(self) -> None:
        self.root.after(200, self.start_server)
        self.root.mainloop()


def main() -> None:
    ValorantClipperWindow().run()


if __name__ == "__main__":
    main()
