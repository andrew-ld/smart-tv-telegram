import os
import socket
import time
import bot
import server


if __name__ == "__main__":
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("8.8.8.8", 53))
            sock.send(bytes(1))

        except socket.error:
            time.sleep(1)
            continue

        else:
            break

    if os.fork() == 0:
        bot.bot.main()

    else:
        server.server.main()
