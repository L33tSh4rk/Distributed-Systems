# P2P Architecture and File Transfer via UDP

Here are the implementations of two distributed systems built on top of the UDP protocol. The first is a P2P Chat with header formatting, and the second is a File Upload Server focused on high performance through Bitmap synchronization.

## UDP P2P Chat

A decentralized (Node-to-Node) chat system that enables message exchange with native support for custom commands. The protocol defines a binary packaging:

`[Type (1 byte)] + [Nick_Size (1 byte)] + [Nickname] + [Msg_Size (1 byte)] + [Message]`

The architecture strictly respects this protocol using exact C-structs. It is worth noting that the semantic validation of the content types (e.g., verifying if a sent URL actually starts with `http://`) is not handled at the code base. The design acts surgically at the Network/Transport layer, ensuring that bytes travel in the correct blocks, delegating the responsibility of handling content types to the Application layer (which was not the focus).

### How to Run

Open two different terminals on your machine (or on different machines on the same network) and run the node instances:

In Terminal 1:
```bash
python3 node1_p2p.py
```
In Terminal 2:
```bash
python3 node2_p2p.py
```
### Libraries Used

**socket:** Responsible for the base communication, configured with SOCK_DGRAM to shoot and catch datagrams on the network without the need for a prior connection session (connect/accept).  

**struct:** The heart of the custom transport layer. Used to pack and unpack strings into formatted bytes with size identifiers, enforcing Network Byte Order (Big-Endian !).  

**threading:** Concurrency tool that allows splitting the Node into two simultaneous flows: the Main Thread (which blocks waiting for user input) and the Daemon Thread (which listens to the network interface in an infinite loop in the background).  

**readline:** For terminal Quality of Life. It retrieves the Linux kernel buffer, saving the user's current typing and redrawing the terminal (sys.stdout.write) so that the arrival of a new message does not visually break the ongoing typing.  

**sys:** Used to control direct outputs (stdout.write and flush) and cleanups with Escape Codes (e.g., \033[2K).

---

### Available Commands

| Command | Description |
|---------|-----------|
| `<normal text>` | Sends a simple text message on the network (TIPO_NORMAL). |
| `!emoji <text>` | Changes the header to 0x02 and marks the packet as an EMOJI. |
| `!url <link>` | Changes the header to 0x03 for sending and marking URLs. |
| `!echo <text>` | Changes the header to 0x04, proving node activity. |
| `exit` | Interrupts the execution loop and shuts down the node's ports.|

### Usage Examples

```bash
=== UDP P2P CHAT ===
enter your nickname: user_1
enter local port to listen on (e.g.: 5001): 5001
enter destination ip (e.g.: 127.0.0.1): 127.0.0.1
enter destination port (e.g.: 5002): 5002

[!] node online. listening on port 5001.
[!] commands: type normally or start with !emoji, !url, !echo to change type.
p2p> hello
[user_2]: hello, how are you?
p2p> i am doing well!
[user_2 sent an EMOJI]: :D
p2p> !echo i am here
[ECHO from user_1]: i am here (active user)
p2p> !url google.com
[user_2 shared a URL]: google.com

p2p> exit

[!] shutting down p2p node...

```

---

# UDP File Upload Server

## File Upload via UDP (Bitmap Synchronization)

This system solves the UDP protocol's lack of reliability, order, and delivery guarantee. The protocol establishes communication demarcated by 6 types of packets (META, DATA, END, NACK, SUCCESS, FAIL).

The architectural differential of this implementation is the efficiency of the Bitmap Batch engine. Instead of implementing Stop-and-Wait based transfers (where the sender waits for the ACK of each packet, leaving the download choked and slow), the client shoots the packets using the Fire-and-Forget strategy.

The server uses disk pointers (seek) based on SeqNums to fit out-of-order data without corrupting the file. When the client signals that it has finished (END), the server calculates the holes (lost packets) using set logic and returns a single NACK packet with the list of what it lost. The client then resends only the corrupted blocks. The final integrity is compared using SHA-1 hashes.

### How to Run

In one terminal, bring up the server infrastructure:

```bash
python3 udp_server.py
```

In a second terminal, start sending the file by providing the path:
```bash
python3 udp_client.py /absolute/path/to/file.pdf
```

### Libraries Used

**socket:** Base module for UDP communication, highlighting the critical function sock.settimeout(), implemented to avoid infinite blocks (deadlocks) in case confirmation packets (like SUCCESS or END) get lost in the network.  

**struct:** Massive protocol operator. Packs short and long unsigned integers (!I, !Q, !H) ensuring that the byte counts of pointers and sequence numbers are mathematically perfect when read in C.  

**hashlib:** Cryptographic engine responsible for digesting blocks in memory (8192 bytes) and generating the end-to-end SHA-1 signature without swallowing the equipment's RAM.  

**math:** Used in the math.ceil function to round fractions up when discovering the actual size of the total number of blocks (1024-byte Chunks) of the file.  

**pathlib:** Object-oriented tool to create the destination folder (server_uploads) and extract information from the system's inodes without using os.path.  

**time:** Implementation of time.sleep() during the abrupt sending of packets to allow micro-breaths in the local network card buffer, preventing premature hardware discard.  

**random:** Used in the client to force the mathematical discard of a fixed percentage of packets on purpose, proving the NACK's resilience in recovering the file via bitmap.

---

### Packet Types (Upload UDP Protocol)

| Packet | Description |
|---------|-----------|
| `TIPO_META (1)` | Initial handshake. Sends File Size and Name to instantiate memory. |
| `TIPO_DATA (2)` | Live payload packet. Contains the SeqNum followed by up to 1024 bytes of raw file. |
| `TIPO_END (3)` | Informs that uploads are finished and carries the 20 bytes of the native SHA-1 key. |
| `TIPO_NACK (4)` | Server responds requesting the rescue only of the specific pieces it lost. |
| `TIPO_SUCCESS (5)` | Final closure validated by crossing the SHA-1 on both sides.|
| `TIPO_FAIL (6)` | Final closure rejected by crossing the SHA-1 on both sides. |

### Usage Example (Simulating Packet Loss)

Server Terminal (udp_server.py):
```bash
[*] p2p UDP server (batch/bitmap) listening on port 65432

[*] receiving A brief introduction to distributed systems.pdf (917969 bytes, 897 chunks)
[!] 856 packets missing.
[!] 717 packets missing.
[!] 581 packets missing.
[!] 440 packets missing.
[!] 307 packets missing.
[!] 172 packets missing.
[!] 40 packets missing.
[*] all blocks received. validating integrity...
[+] 100% integrity validated. success.
^C
[!] server shut down (SIGINT).

```

Client Terminal (udp_client.py):
```bash
python3 udp_client.py /home/l33tsh4rk/Downloads/A\ brief\ introduction\ to\ distributed\ systems.pdf

[*] calculating file SHA-1...
[*] starting file transfer: 897 packets...
[!] server requested recovery of 250 lost packets. resending...
[!] server requested recovery of 250 lost packets. resending...
[-] timeout. server did not respond. resending final packet (END)...
[!] server requested recovery of 250 lost packets. resending...
[-] timeout. server did not respond. resending final packet (END)...
[!] server requested recovery of 250 lost packets. resending...
[-] timeout. server did not respond. resending final packet (END)...
[!] server requested recovery of 250 lost packets. resending...
[-] timeout. server did not respond. resending final packet (END)...
[!] server requested recovery of 172 lost packets. resending...
[-] timeout. server did not respond. resending final packet (END)...
[!] server requested recovery of 40 lost packets. resending...
[+] server confirmed. 100% intact transfer.

```

---