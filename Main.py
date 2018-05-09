import tkinter as tk
from tkinter import messagebox
import ChatClient as client
import BaseDialog as dialog
import BaseEntry as entry
import threading
import argparse

class SocketThreadedTask(threading.Thread):
    def __init__(self, socket, logFile, **callbacks):
        threading.Thread.__init__(self)
        self.socket = socket
        self.callbacks = callbacks
        self.logFile = logFile

    def run(self):
        while True:
            try:
                message = self.socket.receive()

                if '/quituser' in message:
                    self.callbacks['clear_chat_window']()
                    self.callbacks['update_chat_window']('\n> You have been disconnected from the server\n')
                    self.socket.disconnect()
                elif message == '/squit':
                    self.callbacks['clear_chat_window']()
                    self.callbacks['update_chat_window']('\n> The server was forcibly shutdown. No further messages are able to be sent\n')
                    self.socket.disconnect()
                elif 'joined' in message or 'username is now' in message:
                    split_message = message.split('|')
                    print(split_message)
                    self.callbacks['clear_chat_window']()
                    self.callbacks['update_chat_window'](split_message[0])
                    self.callbacks['update_user_list'](split_message[1])
                elif 'left' in message:
                    self.callbacks['update_chat_window'](message)
                    self.callbacks['remove_user_from_list'](message.split(' ')[2])
                else:
                    if self.logFile != "":
                        f = open(self.logFile, "a")
                        f.write(message)
                        f.close()
                    self.callbacks['update_chat_window'](message)
            except OSError:
                break

class ChatDialog(dialog.BaseDialog):
    def body(self, master):
        tk.Label(master, text="Enter host:").grid(row=0, sticky="w")
        tk.Label(master, text="Enter port:").grid(row=1, sticky="w")

        self.hostEntryField = entry.BaseEntry(master, placeholder="Example: 127.0.0.1")
        self.portEntryField = entry.BaseEntry(master, placeholder="Example: 50000")

        self.hostEntryField.grid(row=0, column=1)
        self.portEntryField.grid(row=1, column=1)
        return self.hostEntryField

    def validate(self):
        host = str(self.hostEntryField.get())

        try:
            port = int(self.portEntryField.get())

            if(port >= 0 and port < 65536):
                self.result = (host, port)
                return True
            else:
                tk.messagebox.showwarning("Error", "The port number has to be between 0 and 65535 -- inclusive")
                return False
        except ValueError:
            tk.messagebox.showwarning("Error", "The port number has to be an integer")
            return False

class ChatWindow(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        self.initUI(parent)

    def initUI(self, parent):
        self.messageTextArea = tk.Text(parent, bg="white smoke", state=tk.DISABLED, wrap=tk.WORD)
        self.messageTextArea.grid(row=0, column=0, columnspan=2, sticky="nsew")

        self.messageScrollbar = tk.Scrollbar(parent, orient=tk.VERTICAL, command=self.messageTextArea.yview)
        self.messageScrollbar.grid(row=0, column=3, sticky="ns")

        self.messageTextArea['yscrollcommand'] = self.messageScrollbar.set

        self.usersListBox = tk.Listbox(parent, bg="gray80")
        self.usersListBox.grid(row=0, column=4, padx=5, sticky="nsew")

        self.entryField = entry.BaseEntry(parent, placeholder="Type your message...", width=80)
        self.entryField.grid(row=1, column=0, padx=5, pady=10, sticky="we")

        self.send_message_button = tk.Button(parent, text="SEND", width=10, bg="#CACACA", activebackground="#CACACA")
        self.send_message_button.grid(row=1, column=1, padx=5, sticky="we")

    def update_chat_window(self, message):
        self.messageTextArea.configure(state='normal')
        self.messageTextArea.insert(tk.END, message)
        self.messageTextArea.configure(state='disabled')

    def update_user_list(self, user_message):
        users = user_message.split(' ')

        for user in users:
            if user not in self.usersListBox.get(0, tk.END):
                self.usersListBox.insert(tk.END, user)

    def remove_user_from_list(self, user):
        index = self.usersListBox.get(0, tk.END).index(user)
        self.usersListBox.delete(index)

    def clear_chat_window(self):
        if not self.messageTextArea.compare("end-1c", "==", "1.0"):
            self.messageTextArea.configure(state='normal')
            self.messageTextArea.delete('1.0', tk.END)
            self.messageTextArea.configure(state='disabled')

        if self.usersListBox.size() > 0:
            self.usersListBox.delete(0, tk.END)

    def send_message(self, **callbacks):
        message = self.entryField.get()
        self.set_message("")

        callbacks['send_message_to_server'](message)

    def set_message(self, message):
        self.entryField.delete(0, tk.END)
        self.entryField.insert(0, message)

    def bind_widgets(self, callback):
        self.send_message_button['command'] = lambda sendCallback = callback : self.send_message(send_message_to_server=sendCallback)
        self.entryField.bind("<Return>", lambda event, sendCallback = callback : self.send_message(send_message_to_server=sendCallback))
        self.messageTextArea.bind("<1>", lambda event: self.messageTextArea.focus_set())

class ChatGUI(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        self.initUI(parent)

        self.ChatWindow = ChatWindow(self.parent)

        self.clientSocket = client.Client()

        self.ChatWindow.bind_widgets(self.clientSocket.send)
        self.parent.protocol("WM_DELETE_WINDOW", self.on_closing)

    def initUI(self, parent):
        self.parent = parent
        self.parent.title("eduChat by Eduardo Morales")

        screenSizeX = self.parent.winfo_screenwidth()
        screenSizeY = self.parent.winfo_screenheight()

        frameSizeX = 800
        frameSizeY = 600

        framePosX = (screenSizeX - frameSizeX) / 2
        framePosY = (screenSizeY - frameSizeY) / 2

        self.parent.geometry('%dx%d+%d+%d' % (frameSizeX, frameSizeY, framePosX, framePosY))
        self.parent.resizable(True, True)

        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)

        self.mainMenu = tk.Menu(self.parent)
        self.parent.config(menu=self.mainMenu)

        self.subMenu = tk.Menu(self.mainMenu, tearoff=0)
        self.mainMenu.add_cascade(label='File', menu=self.subMenu)
        self.subMenu.add_command(label='Connect', command=self.connect_to_server)
        self.subMenu.add_command(label='Exit', command=self.on_closing)

    def connect_to_server(self, logFile = ""):
        if self.clientSocket.isClientConnected:
            tk.messagebox.showwarning("Info", "Already connected to the server")
            return

        dialogResult = ChatDialog(self.parent).result

        if dialogResult:
            self.clientSocket.connect(dialogResult[0], dialogResult[1])

            if self.clientSocket.isClientConnected:
                self.ChatWindow.clear_chat_window()
                SocketThreadedTask(self.clientSocket, logFile,
                                                      update_chat_window=self.ChatWindow.update_chat_window,
                                                      update_user_list=self.ChatWindow.update_user_list,
                                                      clear_chat_window=self.ChatWindow.clear_chat_window,
                                                      remove_user_from_list=self.ChatWindow.remove_user_from_list,).start()
            else:
                tk.messagebox.showwarning("Error", "Unable to connect to the server")



    def on_closing(self):
        if self.clientSocket.isClientConnected:
            self.clientSocket.send('/quit')

        self.parent.quit()
        self.parent.destroy()

    def connect_to_server_args(self, host, port, logFile = ""):
        self.clientSocket.connect(host, port)

        if self.clientSocket.isClientConnected:
            self.ChatWindow.clear_chat_window()
            SocketThreadedTask(self.clientSocket, logFile,
                               update_chat_window=self.ChatWindow.update_chat_window,
                               update_user_list=self.ChatWindow.update_user_list,
                               clear_chat_window=self.ChatWindow.clear_chat_window,
                               remove_user_from_list=self.ChatWindow.remove_user_from_list,).start()
        else:
            tk.messagebox.showwarning("Error", "Unable to connect to the server")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--hostname", dest="hostname", help="Manually set the server's hostname")
    parser.add_argument("-u", "--username", dest="username", help="Manually set your username")
    parser.add_argument("-p", "--port", dest="serverport", help="Manually set the server's port")
    parser.add_argument("-L", "--logs", dest="logs", help="Save conversation log to specified file")
    parser.add_argument("-c", "--config file", dest="configFile", help="Specify the name of the configuration file")
    args = parser.parse_args()

    root = tk.Tk()
    chatGUI = ChatGUI(root)

    logFile = ""
    arrayList = []
    host = ""
    port = 0


    if args.username:
        chatGUI.clientSocket.argsusername = args.username

    if args.logs:
        logFile = args.logs

    if args.hostname and args.serverport:
        host = args.hostname
        port = int(args.serverport)

    if args.configFile:
        with open(args.configFile) as f:
            for line in f:
                arrayList.append(line.split("\t")[1][:-1])
        print(arrayList)
        host = str(arrayList[0])
        port = int(arrayList[1])

        if arrayList[2] == "True":
            logFile = arrayList[4]

    if host != "" and port != 0:
        chatGUI.connect_to_server_args(host, port, logFile)

    root.mainloop()