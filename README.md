# File System API

An API for performing basic operations (create, read, update, delete) on files
in a file system. The app has a root directory passed in via an environment
variable, and all file system operations will be done relative to that directory.

### How to run the api without Docker

You will need to:
1. Install Python 3.10.8 (using a tool such as Homebrew, pyenv, or asdf)
2. (Optional) Set up a virtualenv and source it using `python3 -m venv venv && source venv/bin/activate`
3. Intall dependencies using `python3 -m pip install requirements.txt`
4. Run the server using `run_server.sh`

### How to run the app with Docker

Once you have Docker set up locally, you just need to run `docker compose up` and it will:
1. Build the latest image
2. Run that image, binding to port 8000
3. Display logs to the console

### Testing that the server is working

Once you have set up the api with or without Docker, you can test that the
API is working by doing the following:
1. Hit the server on port 8000 such as `curl -D- http://127.0.0.1:8000/`. It should return an empty list of files.
2. Add a file to the `root_directory` by running `echo "hi" > root_directory/foo.txt`
3. Repeat step (1) to see the new file listed
4. Run `curl -D- http://127.0.0.1:8000/foo.txt` to see the file contents
