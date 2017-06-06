import paramiko
import io
import time
import atexit
import getpass
import os
import _thread

# ==============================
#   Initialize the SSH objects
# ==============================
password = getpass.getpass("Enter SSH password: ")
try:
	player = paramiko.SSHClient()
	player.load_system_host_keys()
	player.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	player.connect("24.49.174.95", username="root", password=password, port=2001)

	master = paramiko.SSHClient()
	master.load_system_host_keys()
	master.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	master.connect("24.49.174.95", username="root", password=password, port=2002)
except Exception as e:
	print(e)
	print("Invalid authentication.")
	os._exit(1)

p_transport = player.get_transport()
p_session = p_transport.open_session()
p_session.setblocking(0)
p_session.get_pty()
p_session.invoke_shell()

# ========================
#    Control functions
# ========================
# -- Globals --
songPlaying = False
engineState = {
	"active": False,
	"bigRange": False
}
playSession = None

def startEngine(sliding=False, bigRange=False):
	global engineState
	print("Starting engine...")

	p_session.send("cd c++;\n./engine {} {}\n".format(int(not sliding), int(bigRange)))
	engineState["active"] = True
	engineState["bigRange"] = bigRange

	# Give it time to set up
	time.sleep(4)

	print("Engine started.\n")

def stopEngine():
	global engineState

	print("Terminating engine...")
	p_session.send("\x03")
	engineState["active"] = False
	print("Engine terminated.\n")

def playSong(songName, bigRange=False, finishCB=lambda: None):
	global songPlaying
	global playSession

	m_transport = master.get_transport()
	m_session = m_transport.open_session()
	m_session.get_pty()
	playSession = m_session

	print("Playing {}.".format(songName))
	m_session.exec_command("cd python; python midiplayer{}.py {}".format("2" if bigRange else "", songName))

	songPlaying = True
	_thread.start_new_thread(waitSong, (m_session, finishCB, ))

def stopSong():
	global songPlaying
	global playSession

	if not playSession: return

	playSession.send("\x03")
	playSession = None

def waitSong(m_session, cb):
	global songPlaying

	# Block until song is over
	while not m_session.exit_status_ready():
		time.sleep(0.1)

	print("Song finished.\n")
	cb()
	songPlaying = False

def getSongs():
	m_transport = master.get_transport()
	m_session = m_transport.open_session()
	m_session.get_pty()

	m_session.exec_command("ls songs | grep .dat")

	contents = bytes()
	while not m_session.exit_status_ready():
		if m_session.recv_ready():
			data = m_session.recv(1024)
			while data:
				contents += data
				data = m_session.recv(1024)

	songs = []
	for line in contents.split(b"\n"):
		line = line.decode("utf-8").rstrip("\r")
		if line:	# there's an empty line usually
			songs.append(line.replace(".dat", ""))

	return songs

@atexit.register
def exit():
	stopEngine()

# =================
#    Main logic
# =================
def main():
	print()
	print("Song choices:")
	print("-------------")
	print("\n".join(getSongs()))
	print()

	songName, bigRange = input("Enter song name: "), (input("16 bit serial comm? (t/f): ").lower() == "t")
	print()

	startEngine(sliding=False, bigRange=bigRange)
	playSong(songName, bigRange=bigRange)

	while songPlaying:
		time.sleep(0.1)


if __name__ == "__main__":
	main()
