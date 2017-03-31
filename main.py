import paramiko
import time
import atexit
import getpass
import os

# ==============================
#   Initialize the SSH objects
# ==============================
password = getpass.getpass("Enter SSH password: ")
try:
	player = paramiko.SSHClient()
	player.load_system_host_keys()
	player.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	player.connect("96.60.14.197", username="root", password=password, port=2001)

	master = paramiko.SSHClient()
	master.load_system_host_keys()
	master.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	master.connect("96.60.14.197", username="root", password=password, port=2002)
except:
	print("Invalid authentication.")
	os._exit(1)

p_transport = player.get_transport()
p_session = p_transport.open_session()
p_session.setblocking(0)
p_session.get_pty()
p_session.invoke_shell()

m_transport = master.get_transport()
m_session = m_transport.open_session()
m_session.get_pty()

# ========================
#    Control functions
# ========================
def startEngine(sliding=False, bigRange=False):
	print("Starting engine...")

	p_session.send("cd c++;\n./engine {} {}\n".format(int(not sliding), int(bigRange)))

	# Give it time to set up
	time.sleep(4)

	print("Engine started.\n")

def stopEngine():
	print("Terminating engine...")
	p_session.send("\x03")
	print("Engine terminated.\n")

def playSong(songName, bigRange=False):
	print("Playing {}".format(songName))
	m_session.exec_command("cd python; python midiplayer{}.py {}".format("2" if bigRange else "", songName))

	# Block until song is over
	while not m_session.exit_status_ready():
		time.sleep(0.1)

	print("Song finished.\n")

def getSongs():
	pass

@atexit.register
def exit():
	stopEngine()

# =================
#    Main logic
# =================
songName, bigRange = input("Enter song name: "), (input("16 bit serial comm? (t/f): ").lower() == "t")
print()

startEngine(sliding=False, bigRange=bigRange)
playSong(songName, bigRange=bigRange)
stopEngine()
