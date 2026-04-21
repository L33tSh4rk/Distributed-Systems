## Protocol Socket: Remote Terminal and Multi-Tenant Isolation

The project's UTF-8 ecosystem simulates a remote terminal infrastructure (similar to an FTP or Telnet server). It was designed under the Plain Text (Human-Readable) paradigm, where data travels encoded in UTF-8, with requests and responses delimited by line breaks (\n).

The implementation was coordinated to ensure architecture security:

**Session Isolation (Chroot Jail):** Each connection receives a virtual "prison" (Home Directory). It is impossible for users to navigate outside their folder or access third-party data, completely neutralizing Path Traversal vulnerabilities (CWE-22).

**Secure Authentication:** Passwords never travel in plain text. The client intercepts the credential, applies the cryptographic hash algorithm, and the server performs constant-time validation.

**Non-Blocking I/O:** Uses multiplexing via selectors, allowing multiple users to be connected and interacting simultaneously without one blocking another's thread.

---

### How to Compile and Run

Since Python is an interpreted language, there is no need for prior compilation (build). The project is plug-and-play, requiring only Python 3.9+ or higher installed on the machine.

Open a terminal and start the server. It will automatically create the folder infrastructure in /tmp/servidor_tcp and listen on port 65432:

```bash
python3 t-server.py
```

Open a second terminal (multiple terminals can be used to simulate various clients) and start the user interface:

```bash
python3 t-client.py
```

---

### Libraries Used

The system was built fully with the Python Standard Library (no pip install required).

**socket:** Low-level operating system interface for opening and manipulating TCP/IP connections.

**selectors:** Advanced tool for I/O multiplexing. Allows the server to monitor multiple sockets simultaneously without using heavy threads or processes.

**hashlib and hmac:** Used for generating the SHA-512 hash on the client side and for secure (timing-attack resistant) comparison on the server side via hmac.compare_digest.

**pathlib and shutil:** Object-oriented and secure manipulation of file system paths and inodes, essential for calculating the virtual "prisons".

---

### Users and Available Commands

The server's in-memory test database comes pre-populated with the following users:

```bash
admin (password: admin)

aluno (password: aluno)

hacker (password: hacker)
```

Upon connecting, the following commands are available:


| Comando | Descrição |
|---------|-----------|
| `CONNECT <user>, <password>` | Authenticates on the network and provisions the isolated directory. |
| `WHOAMI` | Returns the name of the user currently logged into the session. |
| `PWD` | Prints the current working directory (virtualized to omit the real Linux root). |
| `CHDIR <target>` | Navigates to a parent directory (..) or a specific subfolder (e.g., configs). |
| `GETDIRS` | Lists the subfolders present in the current directory.|
| `GETFILES` | Lists the files present in the current directory. |
| `HELP` | Displays the static help menu. |
| `EXIT` | Safely closes the TCP connection. |

### Usage Examples
Below is a simulation of how the terminal interacts with the server's state machine:

```bash
UTFclient-server> WHOAMI
servidor: ERROR : authentication required

UTFclient-server> CONNECT hacker, hacker
servidor: SUCCESS

UTFclient-server> WHOAMI
servidor: hacker

UTFclient-server> PWD
servidor: /

UTFclient-server> GETDIRS
[2 items found]:
  - methodologies
  - tools

UTFclient-server> CHDIR methodologies
servidor: SUCCESS

UTFclient-server> GETFILES
[2 items found]:
  - redteam_recon.md
  - osint_research.txt

UTFclient-server> CHDIR ../../../admin
servidor: ERROR - directory not found

UTFclient-server> EXIT
servidor: SUCCESS_EXIT
```

---

## Binary Protocol: High Performance and File Streaming

Unlike the UTF-8 ecosystem, the binary protocol abandons human readability in favor of machine efficiency. With no "line breaks" (\n) separating messages, communication occurs via packed raw bytes traveling in Network Byte Order (Big-Endian).

The architecture was designed to support file transfers (Upload/Download) without crashing the server. Its pillars are:

**Non-Blocking Streaming Engine (Chunking):** The server never loads an entire file into RAM. It uses a Finite State Machine that reads and sends the file in small blocks (4096-byte chunks) based on network card availability. Memory consumption remains strictly capped, whether the file is 10 KB or 50 GB.

**File Descriptor Leak Prevention:** A "Teardown" (Session Purge) routine ensures that if the client unplugs the network cable mid-download, the server's hard drive read pointer is closed immediately, preventing resource leaks in the Linux kernel.

**Big-Endian Validation:** Use of demarcated sizes in headers (unsigned int for file sizes, unsigned short for item counts) ensuring protocol synchronization.

---

### How to Run

Just like the text server, the binary environment is native to Python (3.9+) and does not require compilation.

In the first terminal, start the file server. It will create the jail in /tmp/servidor_tcp and wait for connections on port 65432:

```bash
python3 b-server.py
```

In the second terminal, start the interactive client to send and receive binary packets:

```bash
python3 b-client.py
```

Note: The client will automatically create a *client_downloads* folder in the current directory to save the received files.

---

###  Libraries Used

No external dependencies are needed, but the system relies on low-level libraries from the Standard Library:

**struct:** The backbone of this protocol. Used to convert complex Python data structures into exact byte representations (C-structs), using the formatters !BBB (for headers), !I (file size), and !H (item quantity).

**selectors:** Ensures the streaming engine handles multiple parallel uploads and downloads without blocking the main thread.

**logging:** Implemented on the server to persist all transactions, failures, and Path Traversal attack attempts in the physical server_binario.log file, ensuring 24/7 auditability.

---

### Commands and Usage

The binary environment operates as a shared flat directory. The CLI client translates your intentions into hexadecimal packets transparently:


| Comando | Descrição |
|---------|-----------|
| `ADDFILE <local_path>` | Reads a file from your computer and uploads it (block streaming) to the server. Accepts both relative and absolute paths. |
| `GETFILESLIST` | Queries the server and returns the list of all files currently available for download. |
| `GETFILE <filename>` | Requests a file from the server. The download is done securely and saved in the *client_downloads* folder. |
| `DELETE <filename>` | Physically removes the file from the server (via inode unlink). |
| `HELP` | Displays the syntax of valid commands. Resolved locally on the client to avoid network overhead.|
| `EXIT` | Disconnects and closes the client terminal. |



---

###  Usage Example

```bash
BINclient-server> ADDFILE /home/user/documents/secret_payload.bin
[*] sending secret_payload.bin (10485760 bytes)...
[*] upload completed.

BINclient-server> GETFILESLIST
[*] 3 files found:
  - saas_notes.txt
  - hashcat_commands.txt
  - secret_payload.bin

BINclient-server> GETFILE hashcat_commands.txt
[*] downloading hashcat_commands.txt (42 bytes)...
[*] download completed at /path/to/project/client_downloads/hashcat_commands.txt

BINclient-server> DELETE saas_notes.txt
[*] file saas_notes.txt deleted successfully.

BINclient-server> EXIT
[!] terminal closed.
```

---