# External Data Representation - Client-Server Programming using Protocol Buffers and MongoDB Atlas

This project is a distributed application composed of a server implemented in TypeScript and an interactive Python client. The system allows the management (CRUD) of a movie catalog using the "sample_mflix" dataset hosted on MongoDB Atlas. Communication between the endpoints is done through pure TCP sockets with binary serialization via Protocol Buffers.

## TypeScript Server

The server acts as the processing and persistence core of the system. It is responsible for managing TCP connections, decoding binary requests from the client, executing queries on MongoDB Atlas, and returning properly sanitized responses.

* **Protocol:** TCP (Transmission Control Protocol) with structured messages via Protocol Buffers (Proto3).
* **Features:** Operation routing, semantic data validation, BSON type sanitization, and resilient error handling.

### How to Compile and Run (Locally)

1.  **Dependency Installation:**
    In the root of the server folder, run:
    ```bash
    npm install
    ```

2.  **Environment Setup:**
    * Locate the `env.example` file.
    * Rename it to `.env`.
    * Fill the `MONGO_URI` variable with your MongoDB Atlas connection string.
    * Define the `PORT` (defaults to 3000).

3.  **Initialization:**
    To run the server in development mode with auto-reload:
    ```bash
    npm run dev
    ```

### Libraries Used in the Server

* **mongodb:** Driver for connection and data manipulation in MongoDB Atlas.
* **protobufjs:** Loads .proto files and performs serialization/deserialization of binary messages.
* **net:** Native Node.js module used to create the TCP socket server.
* **dotenv:** Environment variable manager for credential protection.
* **tsx:** High-speed TypeScript executor that allows running the project without prior manual compilation.

---

## Python Client

The client is an interactive command-line interface (CLI) based on a REPL loop. It allows the operator to interact with the server through simple commands, abstracting all the complexity of assembling binary packets and the TCP network flow.

* **Protocol:** TCP (using the native socket library) and Protocol Buffers to ensure compatibility with the server.

### Setup and Start (Locally)

1.  **Virtual Environment Creation (venv):**
    ```bash
    python3 -m venv venv
    ```

2.  **venv Activation:**
    ```bash
    source venv/bin/activate
    ```

3.  **Dependency Installation:**
    ```bash
    pip install protobuf
    ```

4.  **Execution:**
    ```bash
    python3 main.py
    ```

### Available Commands in the Terminal

| Command | Description |
| :--- | :--- |
| `LSACT` | Lists movies based on a specific actor (e.g., "Harrison Ford"). |
| `LSCATG` | Lists movies by category/genre (e.g., "Action", "Fantasy"). Includes validation for allowed categories. |
| `READ` | Fetches and displays the complete details of a movie via its unique ID. |
| `CREATE` | Starts the flow for creating a new record (prompts for title, year, cast, plot, etc). |
| `UPDATE` | Allows partial mutation of an existing record, choosing which field to change. |
| `DELETE` | Physically removes a movie from the database via its ID. |
| `EXIT` | Closes the connection and shuts down the interactive terminal. |

### Libraries Used in the Client

* **socket:** Native Python library for low-level communication via TCP/IP network.
* **protobuf:** To decode and encode binary messages following the contract defined in the .proto file.

---
## Running with Docker (Containerized Environment)

If you prefer not to install Node.js dependencies or manage Python virtual environments locally, you can run the entire system using Docker. This approach guarantees an isolated, consistent environment, automatically handling network resolution between the client and the server.

### Prerequisites
* Docker and Docker Compose installed on your machine.
* The `.env` file properly configured inside the `serverTS` directory (with your `MONGO_URI`).

### How to Start and Interact

1. **Build and start the infrastructure in the background:**

   Run the following command in the root directory of the project (where the `docker-compose.yml` is located):
   ```bash
   docker compose up -d --build
   ```
2. **Access the Interactive Client:**

    Since the client is a REPL (Read-Eval-Print Loop) requiring interactive keyboard input, it runs continuously in the background. To interact with it, you must attach your terminal to the client container:
    ```bash
    docker attach xdr_client
    ```
    *After running this command, press Enter and the xdr-cli> prompt will appear.*
3. **Detaching Safely:**

    To exit the terminal without killing the client container, do not type EXIT. Instead, use the Docker escape sequence:

    Press Ctrl + P, followed by Ctrl + Q.




## Usage Examples
```bash
# LSACT command
xdr-cli> LSACT
actor name (first letters capitalized): Harrison Ford
[+] success. returned records: 25

[*] record 1
    id        : 573a1397f29313caabce68f6
    title     : star wars: episode iv - a new hope (1977)
    type      : movie
    genres    : action, adventure, fantasy
    cast      : mark hamill, harrison ford, carrie fisher, peter cushing
    directors : george lucas
    plot      : luke skywalker joins forces with a jedi knight, a cocky pilot, a wookiee and two droids to save the universe from the empires world-destroying battle-station, while also attempting to rescue princess leia from the evil darth vader.

[*] record 2
    id        : 573a1397f29313caabce77d9
    title     : star wars: episode v - the empire strikes back (1980)
    type      : movie
    genres    : action, adventure, fantasy
    cast      : mark hamill, harrison ford, carrie fisher, billy dee williams
    directors : irvin kershner
    plot      : after the rebels have been brutally overpowered by the empire on their newly established base, luke skywalker takes advanced jedi training with master yoda, while his friends are pursued by darth vader as part of his plan to capture luke.

# LSCATG command
xdr-cli> LSCATG          
target category: action
[+] success. returned records: 50

[*] record 1
    id        : 573a1390f29313caabcd5293
    title     : the perils of pauline (1914)
    type      : movie
    genres    : action
    cast      : pearl white, crane wilbur, paul panzer, edward josè
    directors : louis j. gasnier, donald mackenzie
    plot      : young pauline is left a lot of money when her wealthy uncle dies. however, her uncles secretary has been named as her guardian until she marries, at which time she will officially take ...

[*] record 2
    id        : 573a1391f29313caabcd68d0
    title     : from hand to mouth (1919)
    type      : movie
    genres    : comedy, short, action
    cast      : harold lloyd, mildred davis, 'snub' pollard, peggy cartwright
    directors : alfred j. goulding, hal roach
    plot      : a penniless young man tries to save an heiress from kidnappers and help her secure her inheritance.

# READ command
xdr-cli> READ
target id: 573a1392f29313caabcd9cfb
[+] success. returned records: 1

[*] record 1
    id        : 573a1392f29313caabcd9cfb
    title     : tarzan the ape man (1932)
    type      : movie
    genres    : action, adventure, romance
    cast      : johnny weissmuller, neil hamilton, c. aubrey smith, maureen osullivan
    directors : w.s. van dyke
    plot      : a trader and his daughter set off in search of the fabled graveyard of the elephants in deepest africa, only to encounter a wild man raised by apes.


# CREATE command
xdr-cli> CREATE
movie title: external data representation programming       
release year: 2026
type (movie/series): movie
genres (comma separated): fantasy
cast (comma separated): Allan                       
directors (comma separated): L33tSh4rk
plot: a story of a lot of programming using XDR    
[+] success. returned records: 1

[*] record 1
    id        : 6a03e4a5ffecfc0cd5e9a066
    title     : external data representation programming (2026)
    type      : movie
    genres    : fantasy
    cast      : allan
    directors : l33tsh4rk
    plot      : a story of a lot of programming using xdr


# UPDATE command
xdr-cli> UPDATE
target id for mutation: 6a03e4a5ffecfc0cd5e9a066
available fields: TITLE, YEAR, TYPE, GENRES, CAST, DIRECTORS, PLOT
enter the field you want to change: GENRES
new genres (comma separated): mystery, drama
[+] success. returned records: 1

[*] record 1
    id        : 6a03e4a5ffecfc0cd5e9a066
    title     : external data representation programming (2026)
    type      : movie
    genres    : mystery, drama
    cast      : allan
    directors : l33tsh4rk
    plot      : a story of a lot of programming using xdr

# DELETE command
xdr-cli> DELETE
target id for annihilation: 6a03e4a5ffecfc0cd5e9a066
[+] success. returned records: 0

# testing DELETE (with deleted movie ID)
xdr-cli> READ
target id: 6a03e4a5ffecfc0cd5e9a066
[-] operation failed: movie not found
```

---
