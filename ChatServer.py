import socket
import sys
import threading
import Channel
import User
import time
import argparse

class Server:
    SERVER_CONFIG = {"MAX_CONNECTIONS": 15}

    HELP_MESSAGE = ""

    WELCOME_MESSAGE = "\n> Welcome to eduChat! Please enter your username:\n".encode('utf8')

    def __init__(self, host=socket.gethostbyname('localhost'), port=50000, allowReuseAddress=True, timeout=3):
        self.address = (host, port)
        self.channels = {} # Channel Name -> Channel
        self.users_channels_map = {} # User Name -> Channel Name
        self.client_thread_list = [] # A list of all threads that are either running or have finished their task.
        self.users = [] # A list of all the users who are connected to the server.
        self.wasUsers = []
        self.exit_signal = threading.Event()
        self.version = "Server v1.0"
        self.rules = "Server Rule: Be kind to one-another. Respect one-another, especially operators\n"
        self.bannedUsers = []
        self.compTime = time.asctime(time.localtime(time.time()))

        with open("users.txt") as f:
            for line in f:
                if len(line) < 4:
                    continue
                line = line.split(" ")
                tempUser = User.User("")
                tempUser.username = line[0]
                tempUser.nickname = line[1]
                tempUser.password = line[2]
                tempUser.usertype = line[3]
                self.wasUsers.append(tempUser)
        f.close()

        with open("bannedUsers.txt") as f:
            for line in f:
                self.bannedUsers.append(line)

        try:
            self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as errorMessage:
            sys.stderr.write("Failed to initialize the server. Error - {0}\n".format(errorMessage))
            raise

        self.serverSocket.settimeout(timeout)

        if allowReuseAddress:
            self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.serverSocket.bind(self.address)
        except socket.error as errorMessage:
            sys.stderr.write("Failed to bind to address {0} on port {1}. Error - {2}\n".format(self.address[0], self.address[1], errorMessage))
            raise

    def start_listening(self, defaultGreeting="\n> Welcome to eduChat. Please enter your username:\n"):
        self.serverSocket.listen(Server.SERVER_CONFIG["MAX_CONNECTIONS"])
        try:
            while not self.exit_signal.is_set():
                try:
                    print("Waiting for a client to establish a connection\n")
                    clientSocket, clientAddress = self.serverSocket.accept()
                    print("Connection established with IP address {0} and port {1}\n".format(clientAddress[0], clientAddress[1]))
                    user = User.User(clientSocket)
                    self.users.append(user)
                    self.wasUsers.append(user)
                    self.welcome_user(user)
                    clientThread = threading.Thread(target=self.client_thread, args=(user,))
                    clientThread.start()
                    self.client_thread_list.append(clientThread)
                except socket.timeout:
                    pass
        except KeyboardInterrupt:
            self.exit_signal.set()

        for client in self.client_thread_list:
            if client.is_alive():
                client.join()

    def welcome_user(self, user):
        user.socket.sendall(Server.WELCOME_MESSAGE)

    def client_thread(self, user, size=4096):
        username = user.socket.recv(size).decode('utf8')

        while len(username.split(" ")) > 1:
            user.socket.send("Invalid Syntax: Username cannot have spaces\nRe-Enter username\n".encode("utf8"))
            username = user.socket.recv(size).decode('utf8')


        x = 0

        for u in self.wasUsers:
            if u.username == username and u.password != "@":
                user.socket.send("This username is password-protected. Please enter your password\n".encode("utf8"))
                while True:
                    password = user.socket.recv(size).decode('utf8')
                    if u.password == password:
                        user.nickname = u.nickname
                        user.password = u.password
                        user.usertype = u.usertype
                        print(user.usertype)
                        del self.wasUsers[x]
                        break
                    else:
                        user.socket.send("Invalid password. Please enter your password\n".encode("utf8"))
            x += 1
        user.username = username

        welcomeMessage = '\n> Welcome {0}, type /help for a list of helpful commands\n\n'.format(user.username).encode('utf8')
        user.socket.sendall(welcomeMessage)

        if username in self.bannedUsers:
            self.remove_user(user)
            user.socket.send("/quituser\n".encode("utf8"))

        while True:
            chatMessage = user.socket.recv(size).decode('utf8')

            if self.exit_signal.is_set():
                break

            if not chatMessage:
                break

            self.save(user.username, chatMessage)

            if user.username in self.users_channels_map:
                channelName = self.users_channels_map[user.username]
                channelObject = self.channels[channelName]

            userIsOp = False
            if "op" == user.usertype:
                userIsOp = True


            stringAfter = chatMessage.split(" ", 1)

            if len(stringAfter) > 1:
                stringAfter = stringAfter[1]
            else:
                stringAfter = ""

            if '/quit' in chatMessage:
                self.quit(user)
                break

            elif '/list' in chatMessage:
                self.list_all_channels(user)

            elif '/ping' in chatMessage:
                user.socket.send("SERVER RESPONSE: /PONG".encode("utf8"))

            elif '/help' in chatMessage:
                self.help(user)

            elif '/join' in chatMessage:
                self.join(user, chatMessage)

            elif '/knock' in chatMessage:
                try:
                    tempChannel = self.channels[stringAfter]
                    tempChannel.broadcast_message(user.username + " is requesting access to join the channel. Use [/invite " + user.username + "]\n")
                    user.socket.send(("You have requested to join " + stringAfter + "\n").encode("utf8"))
                except:
                    user.socket.send((stringAfter + " does not exist\n").encode("utf8"))

            elif '/time' in chatMessage:
                localtime = time.asctime(time.localtime(time.time()))
                user.socket.send(("Current Server Time: " + localtime + "\n").encode("utf8"))

            elif '/info' in chatMessage:
                localtime = time.asctime(time.localtime(time.time()))
                user.socket.send(("Current Server Time: " + localtime + "\n").encode("utf8"))
                user.socket.send(("Sever Compilation Time: " + self.compTime + "\n").encode("utf8"))
                user.socket.send(self.rules.encode("utf8"))
                user.socket.send(("HOST: " + self.address[0] + "\n").encode("utf8"))
                user.socket.send(("PORT: " + str(self.address[1]) + "\n").encode("utf8"))


            elif '/userhost' in chatMessage:
                checkUsers = stringAfter.split(" ")
                usersOn = []
                userHostMessage = "The following users are online:\n"
                for u in self.users:
                    if u.username in checkUsers:
                        usersOn.append(u)

                if len(usersOn) > 0:
                    for u in usersOn:
                        ip = str(u.socket.getpeername()[0])
                        port = str(u.socket.getpeername()[1])
                        userHostMessage += u.username + "--> IP: " + ip + ", PORT: " + port + "\n"
                else:
                    userHostMessage = "No users found\n"

                user.socket.send(userHostMessage.encode("utf8"))
            elif '/version' in chatMessage:
                user.socket.send(self.version.encode("utf8"))

            elif '/pass' in chatMessage:
                user.password = stringAfter
                passMessage = "Your new password is " + stringAfter + "\n"

                if stringAfter == "":
                    passMessage = "Password disabled\n"
                    user.password = "@"

                user.socket.send(passMessage.encode("utf8"))

            elif '/rules' in chatMessage:
                user.socket.send(self.rules.encode("utf8"))

            elif '/die' in chatMessage:
                if not userIsOp:
                    user.socket.send("You do not have enough privileges to shutdown the server\n".encode("utf8"))
                else:
                    user.socket.sendall("/squit".encode("utf8"))
                    self.server_shutdown()

            elif '/oper' in chatMessage:
                userExists = False
                if not userIsOp:
                    user.socket.send("You do not have enough privileges to make someone an operator\n".encode("utf8"))
                else:
                    for u in self.wasUsers:
                        if u.username == stringAfter:
                            userExists = True
                            u.usertype = "op"
                            user.socket.send((stringAfter + " now has operator privileges\n").encode("utf8"))

                    for u in self.users:
                        if u.username == stringAfter:
                            u.usertype = "op"
                            u.socket.send((user.username + " has given you operator privileges\n").encode("utf8"))

                    if not userExists:
                        user.socket.send((stringAfter + " does not exist").encode("utf8"))

            elif '/kill' in chatMessage:
                if not userIsOp:
                    user.socket.send("You do not have enough privileges to ban someone\n".encode("utf8"))
                else:
                    userExists = False
                    for killUser in self.users:
                        if killUser.username == stringAfter:
                            userExists = True
                            self.bannedUsers.append(killUser.username)
                            f = open("bannedUsers.txt", "w")
                            f.write(killUser.username)
                            f.close()
                            user.socket.send((stringAfter + " has been removed from the server\n").encode("utf8"))
                            self.remove_user(killUser)
                            killUser.socket.sendall("/quituser".encode("utf8"))
                            killUser.socket.close()


                    if not userExists:
                        user.socket.send((stringAfter + " does not exist\n").encode("utf8"))

            elif '/wallops' in chatMessage:
                if not userIsOp:
                    user.socket.send("You do not have enough privileges to send a broadcast message to operators\n".encode("utf8"))
                else:
                    for u in self.users:
                        if u.usertype == "op":
                            u.socket.send(("Operator Message from " + user.username + ": " + stringAfter + "\n").encode("utf8"))
                    user.socket.send("Message succesfully sent to all operators currently online\n".encode("utf8"))

            elif '/kick' in chatMessage:
                if not userIsOp:
                    user.socket.send("You do not have enough privileges to kick someone\n".encode("utf8"))
                else:
                    userExists = False
                    for kickUser in self.users:
                        if kickUser.username == stringAfter:
                            if kickUser.username in self.users_channels_map:
                                kickUser.socket.send("You have been kicked out from the channel\n".encode("utf8"))
                                self.remove_user(kickUser)
                                userExists = True
                            else:
                                userExists = True
                                user.socket.send((kickUser.username + " does not belong to any channel\n").encode("utf8"))


                    if not userExists:
                        user.socket.send((stringAfter + " does not exist\n").encode("utf8"))

            elif '/silence' in chatMessage:
                if not userIsOp:
                    user.socket.send("You do not have enough privileges to silence someone\n".encode("utf8"))
                else:
                    userExists = False
                    silenceMessage = ""
                    for u in self.users:
                        if u.username == stringAfter:
                            userExists = True
                            u.silenced = not u.silenced
                            if u.silenced:
                                silenceMessage = stringAfter + " have been silenced\n"
                            else:
                                silenceMessage = stringAfter + " have been unsilenced\n"

                    if not userExists:
                        silenceMessage = stringAfter + " does not exist\n"

                    user.socket.send(silenceMessage.encode("utf8"))

            elif '/whowas' in chatMessage:
                whoWasMessage = "History of users in the server:\n"
                for user in self.wasUsers:
                    whoWasMessage += user.username
                    if user.usertype == "op":
                        whoWasMessage += "+"
                    whoWasMessage += "\n"
                user.socket.send(whoWasMessage.encode("utf8"))

            elif '/part' in chatMessage:
                user.socket.send("You have departed the channel\n".encode("utf8"))
                self.channels[self.users_channels_map[user.username]].remove_user_from_channel(user)
                del self.users_channels_map[user.username]


            elif '/userip' in chatMessage:
                userIpMessage = stringAfter + " does not exist\n"
                for userIp in self.users:
                    if userIp.username == stringAfter:
                        userIpMessage = stringAfter + "'s IP: " + str(userIp.socket.getpeername()[0]) + "\n"
                        userIpMessage += stringAfter + "'s PORT: " + str(userIp.socket.getpeername()[1]) + "\n"
                        break

                user.socket.send(userIpMessage.encode("utf8"))

            elif '/privmsg' in chatMessage:
                userExists = False
                try:
                    username = stringAfter.split(" ", 1)[0]
                    prvmsg = stringAfter.split(" ", 1)[1] + "\n"

                    for msgUser in self.users:
                        if msgUser.username == username:
                            userExists = True
                            if msgUser.status == "Online":
                                user.socket.send(("Private Message sent to " + msgUser.username + ": " + prvmsg).encode("utf8"))
                                msgUser.socket.send(("Private Message from " + user.username + ": " + prvmsg).encode("utf8"))
                            else:
                                user.socket.send((msgUser.username + " is away: " + msgUser.status + "\n").encode("utf8"))

                    if not userExists:
                        user.socket.send((username + " does not exist\n").encode("utf8"))

                except:
                    user.socket.send("Invalid Syntax: /msg [USERNAME] [MESSAGE]\n".encode("utf8"))

            elif '/notice' in chatMessage:
                userExists = False
                try:
                    username = stringAfter.split(" ", 1)[0]
                    prvmsg = stringAfter.split(" ", 1)[1] + "\n"

                    for msgUser in self.users:
                        if msgUser.username == username:
                            userExists = True
                            user.socket.send(("Private Message sent to " + msgUser.username + ": " + prvmsg).encode("utf8"))
                            msgUser.socket.send(("Private Message from " + user.username + ": " + prvmsg).encode("utf8"))

                    if not userExists:
                        user.socket.send((username + " does not exist\n").encode("utf8"))

                except:
                    user.socket.send("Invalid Syntax: /msg [USERNAME] [MESSAGE]\n".encode("utf8"))

            elif user.username not in self.users_channels_map:
                user.socket.send("Please join a channel to access that command\n".encode("utf8"))

            elif '/away' in chatMessage:
                try:
                    newStatus = chatMessage.split(" ", 1)[1]
                    awayMessage = user.username + " is away: " + newStatus + "\n"
                    user.status = newStatus

                except:
                    awayMessage = user.username + " is Online!\n"
                    user.status = "Online"

                channelObject.broadcast_message(awayMessage)

            elif '/whois' in chatMessage:
                whoIsMessage = "Users in " + channelName + ":\n"
                for user in channelObject.users:
                    whoIsMessage += user.username
                    if user.usertype == "op":
                        whoIsMessage += "+"
                    whoIsMessage += "\n"
                user.socket.send(whoIsMessage.encode("utf8"))

            elif '/who' in chatMessage:
                whoMessage = ""
                for user in channelObject.users:
                    if stringAfter in user.username:
                        whoMessage += user.username + "\n"

                if whoMessage == "" or stringAfter == "":
                    whoMessage = "No user matching " + stringAfter + "\n"
                else:
                    whoMessage = "Users who match " + stringAfter + ":\n" + whoMessage

                user.socket.send(whoMessage.encode("utf8"))

            elif '/invite' in chatMessage:
                userExists = False

                try:
                    userInvite = stringAfter.split(" ", 1)[0]

                    for u in self.users:
                        if u.username == userInvite:
                            userExists = True
                            userInviteObject = u
                            userInviteObject.socket.send((user.username + " has sent you an invitation to [/join " + channelObject.channel_name + "]\n").encode("utf8"))
                            userInviteObject.invitationRequired = True
                            channelObject.usersAllowed.append(userInviteObject.username)
                            for user in channelObject.users:
                                channelObject.usersAllowed.append(user.username)

                        if not userExists:
                            inviteMessage = userInvite + " does not exist\n"
                        else:
                            inviteMessage = "Invitation successfully sent to " + userInvite + "\n"
                except:
                    inviteMessage = "Invalid Syntax: /invite [USERNAME]\n"

                user.socket.send(inviteMessage.encode("utf8"))

            elif '/nick' in chatMessage:
                if stringAfter != "":
                    user.nickname = stringAfter
                    nickMessage = "Your nickname has been changed to " + stringAfter + "\n"
                else:
                    nickMessage = "Invalid Syntax: /nick [NICKNAME]\n"
                user.socket.send(nickMessage.encode("utf8"))

            elif '/setname' in chatMessage:
                userExists = False
                for u in self.wasUsers:
                    if u.username == stringAfter:
                        user.socket.send((stringAfter + " already exists. Please pick a different one\n").encode("utf8"))
                        userExists = True
                        break
                if len(stringAfter.split(" ", 1)) == 1:
                    if not userExists:
                        prevUsername = user.username
                        username = stringAfter
                        user.username = username
                        if prevUsername in self.users_channels_map:
                            self.users_channels_map[username] = channelName
                            del self.users_channels_map[prevUsername]
                            setnameMessage = prevUsername + "'s username is now " + username + "\n|" + channelObject.get_all_users_in_channel()
                            self.broadcast_message(setnameMessage, "IMPORTANT:")
                        else:
                            user.socket.send(("You are now " + username + "\n").encode("utf8"))
                else:
                    user.socket.send("Invalid Syntax: /setname [USERNAME]\n".encode("utf8"))

            elif '/ison' in chatMessage:
                checkUsers = stringAfter.split(" ")
                usersOn = []
                isonMessage = "The following users are online:\n"
                for u in self.users:
                    if u.username in checkUsers:
                        usersOn.append(u.username)

                if len(usersOn) > 0:
                    for u in usersOn:
                        isonMessage += u + "\n"
                else:
                    isonMessage = "None users found\n"

                user.socket.send(isonMessage.encode("utf8"))

            elif '/topic' in chatMessage:
                if not userIsOp:
                    user.socket.send("You do not have enough privileges to set the topic\n".encode("utf8"))
                else:
                    channelObject.topic = stringAfter

                    if stringAfter == "":
                        channelObject.topic = "NONE"
                        channelObject.broadcast_message("This channel does not has a topic\n", "IMPORTAT: ")
                    else:
                        channelObject.broadcast_message("This channel's topic is now " + stringAfter.upper() + "\n", "IMPORTAT: ")

            else:
                if not user.silenced:
                    self.send_message(user, chatMessage + '\n')
                else:
                    user.socket.send("Message not sent. You have been silenced\n".encode("utf8"))











        if self.exit_signal.is_set():
            user.socket.sendall('/squit'.encode('utf8'))

        user.socket.close()

    def quit(self, user):
        user.socket.send('/quit'.encode('utf8'))
        self.remove_user(user)


    def list_all_channels(self, user):
        if len(self.channels) == 0:
            chatMessage = "No rooms available. Create your own by typing /join [channel_name]\n".encode('utf8')
            user.socket.sendall(chatMessage)
        else:
            chatMessage = '\n\nCurrent channels available are: \n'
            for channel in self.channels:
                chatMessage += "    \n" + channel + ": " + str(len(self.channels[channel].users)) + " user(s)"
            chatMessage += "\n"
            user.socket.sendall(chatMessage.encode('utf8'))

    def help(self, user):
        Server.HELP_MESSAGE = "AWAY – Set their status to away\nHELP – Gives a full list of available commands and how to use them\nINFO – Gives more detailed information about the server\nINVITE – Invites someone to the channel. Makes the channel “invitation only”\nISON – Returns the users that are on the server as a comma-separated list\nJOIN – Joins a channel\nKNOCK – Requests to join a channel\nLIST – Lists all the channels available\nNICK – Sets your nickname\nNOTICE – Send a private message to a person no matter if they’re away\nPART – Leave the current channel\nPASS – Set your password. Log back in to your account\nPING – Ping the server to test connection. The server responds with PONG\nPRIVMSG – Send a private message to anyone who is not away\nQUIT – Leave the server\nRULES – Request the rules of the server\nSETNAME – Change your username\nTIME – Know the current time of the server\nUSERHOST – Returns information such as IP and Port of the comma-separated usernames\nUSERIP – Returns IP and Port of the given username\nUSERS – Returns all the users in the channel\nVERSION – Returns the version of the server\nWHO – Searches for users who are currently online that match the string after\nWHOIS – Returns online users from the given comma-separated usernames\nWHOWAS – Returns all the users ever created\n\n"
        if user.usertype == "op":
            Server.HELP_MESSAGE += "OPERATOR PRIVILEGES:\nDIE – Shuts down the server\nKICK – Kicks someone out from a channel\nKILL – Bans the user. This username will no longer be able to connect to the server\nOPER – Make someone an operator\nSILENCE – Silence someone, their messages will not be sent\nTOPIC – Set the topic of the channel\nWALLOPS – Send a message to all operators in the server.\n\n"

        user.socket.send(Server.HELP_MESSAGE.encode("utf8"))


    def join(self, user, chatMessage):
        isInSameRoom = False
        isAllowed = True

        if len(chatMessage.split()) >= 2:
            channelName = chatMessage.split()[1]

            if channelName in self.channels:
                if self.channels[channelName].invitationRequired:
                    if user in self.channels[channelName].usersAllowed:
                        isAllowed = True
                    else:
                        isAllowed = False

            if isAllowed:
                if user.username in self.users_channels_map: # Here we are switching to a new channel.
                    if self.users_channels_map[user.username] == channelName:
                        user.socket.sendall("\n> You are already in channel: {0}\n".format(channelName).encode('utf8'))
                        isInSameRoom = True
                    else: # switch to a new channel
                        oldChannelName = self.users_channels_map[user.username]
                        self.channels[oldChannelName].remove_user_from_channel(user) # remove them from the previous channel

                if not isInSameRoom:
                    if not channelName in self.channels:
                        newChannel = Channel.Channel(channelName)
                        self.channels[channelName] = newChannel

                    self.channels[channelName].users.append(user)
                    self.channels[channelName].welcome_user(user.username)
                    self.users_channels_map[user.username] = channelName
            else:
                user.socket.sendall("\n> You don't have permission to join the channel\n".encode('utf8'))
        else:
            self.help(user)

    def send_message(self, user, chatMessage):
        if user.username in self.users_channels_map:
            self.channels[self.users_channels_map[user.username]].broadcast_message(chatMessage, "{0}: ".format(user.username))
        else:
            chatMessage = """\n> You are currently not in any channels:

Use /list to see a list of available channels.
Use /join [channel name] to join a channel.\n\n""".encode('utf8')

            user.socket.sendall(chatMessage)

    def remove_user(self, user):
        if user.username in self.users_channels_map:
            self.channels[self.users_channels_map[user.username]].remove_user_from_channel(user)
            del self.users_channels_map[user.username]
            print("Client: {0} has left\n".format(user.username))

    def server_shutdown(self):
        print("Shutting down chat server.\n")
        self.serverSocket.close()


    def broadcast_message(self, broadcastMessage, who):
        for channel in self.channels:
            self.channels[channel].broadcast_message(broadcastMessage, who)

    def save(self, username, chatMessage):
        f = open("users.txt", "w")
        for user in self.wasUsers:
            f.write(user.username + " " + user.nickname + " " + user.password + " " + user.usertype + " " + "\n")

        f.close()

        f = open("channels.txt", "w")

        for channel in self.channels:
            tempChannelObject = self.channels[channel]
            f.write(tempChannelObject.channel_name + "\n")

        f.close()

        f = open("chatLog.txt", "a+")
        localtime = time.asctime(time.localtime(time.time()))
        f.write(username + " -- " + str(localtime) + ": " + chatMessage + "\n")

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--hostname", dest="hostname", help="Manually set the server's hostname")
    parser.add_argument("-p", "--port", dest="serverport", help="Manually set the server's port")
    parser.add_argument("-c", "--config file", dest="configFile", help="Specify the name of the configuration file")
    args = parser.parse_args()
    host = "127.0.0.1"
    port = 50000

    if (args.hostname and args.serverport):
        host = args.hostname
        port = int(args.serverport)

    chatServer = Server(host, port)

    print("\nListening on port {0}".format(chatServer.address[1]))
    print("Waiting for connections...\n")
    chatServer.start_listening()
    chatServer.server_shutdown()

if __name__ == "__main__":
    main()
