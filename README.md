eduChat by Eduardo Morales
An un-encrypted and simple IRC Chat.
emora113@fiu.edu
5663249
------------------------------------------------------------------------------------



GETTING STARTED:
Download and unzip the eduChat.zip file on your Desktop.

HOW TO RUN THE SERVER AND CLIENT WITH PYTHON3:
1. Open the Terminal/Cmd app.
2. Navigate to the eduChat directory using cd.
3. Type "Python3 ChatServer.py" to run the Server.
4. Type "Python3 Main.py --arguments" to run the Client.

------------------------------------------------------------------------------------



IMPORTANT:
Arguments -h and -p must be used together : python3 Main.py -h 127.0.0.1 -p 50000
Argument -c will ignore any other arguments, except -u.


ChatServer.py -- SERVER ARGUMENTS:
-n hostName [Automatically connects to the IP address]
-p serverPort [Automatically connects on port]
-c configurationFile [Takes arguments from the configuration file] : python3 Main.py -c chatfile.conf


Main.py -- CLIENT ARGUMENTS:
-n hostName [Automatically connects to the IP address]
-p serverPort [Automatically connects on port]
-u yourUsername [Automatically sets the username] : python3 Main.py -u Eduardo
-L logFileName [ Automatically saves client log to the specified file] : python3 Main.py -L chatlog.txt


------------------------------------------------------------------------------------



DATABASE:
*bannedUsers.txt is the list of banned users.
*chatLog.txt keeps a log of all messages that go through the server. Not to be confused with the client chat log.
*channels.txt contains a list of channels.
users.txt is the database for the users.


------------------------------------------------------------------------------------


OPERATOR LOGIN INFO:
There exists an operator user named "admin".
Login with username "admin" to access the server as an operator.

ADMIN LOGIN INFORMATION:
USERNAME: admin
PASSWORD: password


------------------------------------------------------------------------------------



VERSIONING:
1.0 -- Released March 21st, 2018


------------------------------------------------------------------------------------



AUTHORS:
Eduardo Morales - Functionality in Python3
Francisco Ortega - UI in Tkinter Python


------------------------------------------------------------------------------------


ACKNOWLEDGEMENTS:
Written from the bottom of my heart. Took me a long time, but I learned a lot!