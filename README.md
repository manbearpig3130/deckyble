# Mumble Steam Deck Plugin

This repository is an attempt to create a Mumble VOIP client built into the Steam Deck interface. Don't browse the code if you're offendded by profanity until I actually start polishing it.

Pymumble is used in the Python backend to handle Mumble connections.

## Features:
- 3 different voice transmit modes: always-on, voice activity. push-to-talk (Kind of works)
- Save servers and connect from the server manager
- Select any Input or Output devices for audio
- Text chat

### To install:

 Make sure to read up on how the [Decky Template Repository](https://github.com/SteamDeckHomebrew/decky-plugin-template) is set up. 

The pre-requisites for this to work are:
-  A Steam Deck with Decky Loader installed
-  numpy installed on the Steam Deck
-  Your build machine needs pnpm installed

On your Steam Deck:
1. Install [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader)
2. You need to install numpy to your Steam Deck: `python -m pip install numpy`

On the build machine:
1. To install required Typescript packages, run: `pnpm i`
2. Python dependencies are installed to py_modules by running: `pip install -r requirements.txt --target py_modules/`
3. Edit the .env file with the SSH connection details to your Steam Deck
4. Run `make it` to build and install to your Steam Deck
5. It works maybe?


