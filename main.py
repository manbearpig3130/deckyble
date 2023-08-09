## Standard imports
import asyncio, threading, json, queue, os, time, datetime, requests

## Set environment variables so soudndevice can find devices
os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"
os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/run/user/1000/bus"

## Third party imports
import sounddevice as sd
import websockets, numpy
import pymumble_py3 as pymumble
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from lxml import etree

## local imports
import decky_plugin
from settings import SettingsManager
from steam_deck_input import SteamDeckInput
from mumble_client import CustomMumble
from helpful_functions import mumble_ping, mono_to_stereo, catch_errors, ServerConnection

## Decky Plugin env variables
settingsDir = os.environ["DECKY_PLUGIN_SETTINGS_DIR"]
deckyHomeDir = os.environ["DECKY_HOME"]
loggingDir = "/home/deck/homebrew/logs/mumble/"


async def send_update(websocket, path, thing=None):
    Plugin.clients.setdefault('default', set()).add(websocket)
    try:
        while True:  # Keep listening for messages
            message = await websocket.recv()
            data = json.loads(message)
            decky_plugin.logger.info(f"GOT A TERGID UPDATE!!! {message}")
            if data['type'] == 'join':  # If the client wants to join a channel
                Plugin.clients.setdefault(data['channel'], set()).add(websocket)
    except websockets.ConnectionClosed as e:
        decky_plugin.logger.info(f"CLOSED THE TERGIDS {e}")
    finally:
        for clients in Plugin.clients.values():
            clients.discard(websocket)

class Plugin:
    server_stop_event = asyncio.Event()
    ###########################################################################
    ##             Special plugin functions, called by Decky                 ##
    ##                   _main    _unload    _migration                      ##
    ###########################################################################
    # Asyncio-compatible long-running code, executed in a task when the plugin is loaded. This is the main entry point for the plugin.
    async def _main(self):
        ## Set up all the class variables
        self.logger = decky_plugin.logger
        self.server_stop_event = asyncio.Event()
        self.clients = {}
        self.muted_users = []
        self.settings = SettingsManager(name='settings', settings_directory=settingsDir)
        self.settings.read()
        self.mumble = None
        self.muted = False
        self.deafened = False
        self.connected = False
        self.publicServers = []
        self.stream = None
        self.audio_queue = queue.Queue()
        self.savedServers = self.settings.getSetting("savedServers", [])
        decky_plugin.logger.info(f"saved servers: {self.savedServers}")
        self.messages = []
        self.selected_recipient = { 'ID': 0, 'name': "Channel" }
        self.probe = None
        self.probing = False
        self.broadcastAfter = self.settings.getSetting("broadcastAfter", 50)
        self.silenceBelow = self.settings.getSetting("silenceBelow", 20)
        self.transmit_mode = self.settings.getSetting("transmitMode", 0)   ## 'always-on' or 'push-to-talk' or 'activity'
        self.broadcast_timer = None
        self.BROADCAST_TIMEOUT = self.settings.getSetting("BROADCAST_TIMEOUT", 5)  # Timeout in seconds
        self.selected_input_device = sd.default.device[0]
        self.selected_output_device = sd.default.device[1]
        self.selected_api_input = sd.query_hostapis()[sd.default.hostapi]
        self.selected_api_input['index'] = sd.default.hostapi
        self.selected_api_output = sd.query_hostapis()[sd.default.hostapi]
        self.selected_api_output['index'] = sd.default.hostapi
        self.apis = sd.query_hostapis()
        devices = sd.query_devices()
        self.allDevices = devices
        self.inlist = [dev for dev in devices if dev['max_input_channels'] > 0]
        self.outlist = [dev for dev in devices if dev['max_output_channels'] > 0]
        self.input_handler = None
        self.ptt_key = 'R5'
        self.ig_ptt_key = 'Up'
        self.ptt_enabled = False
        if self.transmit_mode == 1:
            self.transmitting = False
        else:
            self.transmitting = True
        
        ## Set the currently selected server to the last server used, or the first server in the list if there is no last server
        lastServer = self.settings.getSetting("currentServer", None)
        decky_plugin.logger.info(f"CONNECTION: {lastServer}")
        decky_plugin.logger.info(f"len saved servers: {len(self.savedServers)}")
        if lastServer is None and len(self.savedServers) > 0:
            try:
                # self.connection = ServerConnection(**self.savedServers[0])
                await self.setCurrentServer(self.savedServers[0]['label'])
                decky_plugin.logger.info(f"CONNECTION SET: {self.connection}")
                #decky_plugin.logger.info(f"CONNECTION: {self.connection}")
            except Exception as e:
                decky_plugin.logger.info(f"Failed to load connection: {e}")
        elif lastServer is not None and len(self.savedServers) > 0:
            decky_plugin.logger.info(f"CONNECTION FART CUNTS: {lastServer}")
            await self.setCurrentServer(self, lastServer['label'])
        
        ## Set up the side loop in a separate thread
        self.side_loop = threading.Thread(target=self.sideloop, args=(self,))
        self.side_loop.start()

        ## Set up the websocket server
        try:
            async with websockets.serve(lambda websocket, path: send_update(websocket, path, thing=self), "localhost", 8765):
                await Plugin.server_stop_event.wait()
        except Exception as e:
            decky_plugin.logger.info("Failed to start websocket server")
            decky_plugin.logger.info(e)
            return
        
    # Function called first during the unload process, utilize this to handle your plugin being removed
    async def _unload(self):
        decky_plugin.logger.info("Goodbye asshats!")
        if self.connected:
            self.leave_server()
            self.muted_users = []
        if self.input_handler is not None:
            self.input_handler.close()
            self.input_handler = None
        self.server_stop_event.set()
        self.side_loop.join()
        if self.stream is not None:
            self.stream.stop()
        pass

    # Migrations that should be performed before entering `_main()`.
    async def _migration(self):
        decky_plugin.logger.info("Migrating")
        decky_plugin.migrate_logs(os.path.join(decky_plugin.DECKY_USER_HOME,
                                               ".config", "decky-template", "template.log"))
        decky_plugin.migrate_settings(
            os.path.join(decky_plugin.DECKY_HOME, "settings", "template.json"),
            os.path.join(decky_plugin.DECKY_USER_HOME, ".config", "decky-template"))
        decky_plugin.migrate_runtime(
            os.path.join(decky_plugin.DECKY_HOME, "template"),
            os.path.join(decky_plugin.DECKY_USER_HOME, ".local", "share", "decky-template"))
        
    ###########################################################################
    ##                     Various important functions                       ##
    ###########################################################################
    ## sideloop is a loop which is kind of the main loop, but not really.
    ## It's used to check if the user is transmitting, and to send audio level data when the soudn settings page is open
    @catch_errors
    def sideloop(self):
        decky_plugin.logger.info("STARTED SIDE TERGISON LLOOOOPP")
        while True:
            if self.input_handler is not None:
                if self.transmit_mode == 1 and self.ptt_enabled:
                    if self.input_handler.update() == self.ptt_key and self.ptt_enabled:
                        self.transmitting = True
                    else:
                        self.transmitting = False
                
                elif self.transmit_mode == 1 and self.ptt_enabled == False and self.input_handler is not None:
                    self.input_handler.close()
                    self.input_handler = None
            elif self.input_handler is None and self.ptt_enabled:
                if self.transmit_mode == 1:
                    self.input_handler = SteamDeckInput()

            if 'audio_level' in self.clients:
                if len(self.clients['audio_level']) > 0:
                    self.probing = True
                else:
                    self.probing = False
                    if self.probe:
                        self.probe.stop()
                    self.probe = None
            if self.probing:         
                if 'audio_level' in self.clients:
                    if not self.probe:
                        self.logger.info("ALIEN PROBE?")
                        self.open_probing_stream(self)
            time.sleep(0.01)

    ## Sends a message to the websocket server which signals the frontend that it should update/refresh
    async def broadcast_update(self, message=None, channel='default', reason='Turds', data=None, username=None):
        ## If message is included, it will send the message string to the frontend as well
        if message is not None:
            self.logger.info(f"SENDING MESSAGE UPDATE {message}")
            for websocket in self.clients.get(channel, []):
                try:
                    await websocket.send(json.dumps({'type': 'message', 'actor': self.mumble.users[message.actor]['name'], 'message': message.message, 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))
                except Exception as e:
                    decky_plugin.logger.info("Failed to send message")
                    decky_plugin.logger.info(e)
        
        ## If the username is included, update the frontend to say this user is transmitting
        elif username is not None:
            #decky_plugin.logger.info(f"sending transmission data {username['name']}")
            for websocket in self.clients.get('default', []):
                try:
                    await websocket.send(json.dumps({'type': 'user_transmitting', 'username': username['name']}))
                except Exception as e:
                    decky_plugin.logger.error(f"Failed to send update: {e}")

        ## General purpose update
        else:
            for websocket in self.clients.get(channel, []):
                try:
                    response = await websocket.send(json.dumps({'type': 'update', 'reason': reason}))
                    #decky_plugin.logger.info(f"TERGID RESPONSE?? {response}")
                except Exception as e:
                    decky_plugin.logger.info("Failed to send update")
                    decky_plugin.logger.info(e)

    async def send_text_message_to_server(self, msg=None):
        if msg is not None:
            self.mumble.my_channel().send_text_message(msg)

    async def send_text_message_to_user(self, usersession=None, msg=None):
        decky_plugin.logger.info(f"FUCKTARD MCJUICE, {usersession}, {msg}")
        if msg is not None:
            self.mumble.users[usersession].send_text_message(msg)
            self.messages.append(json.dumps({'type': 'message', 'actor': self.connection.username, 'message': msg, 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))

    ## Function for connecting to a server. Uses the details of the 'currently selected' server
    async def connect_server(self):
        self.logger.info(f"GENERAL ASS FACE {self.connection}")
        if not self.connected and self.connection is not None:
            decky_plugin.logger.info(f"Connecting to server")
            try:
                self.open_audio_stream(self)
                decky_plugin.logger.info(f"Connecting to server: {str(self.connection.host)}:{self.connection.port} Tokens: {self.connection.tokens}")
                self.mumble = CustomMumble(self.connection.host, self.connection.username, port=int(self.connection.port), certfile=None, keyfile=None, password=self.connection.password, tokens=self.connection.tokens)
                self.mumble.set_receive_sound(True)
                self.messages = []

                loop = asyncio.get_running_loop()
                self.mumble.set_application_string("Steam Deck Mumble Plugin")
                await loop.run_in_executor(None, self.mumble.start)

                self.mumble.is_ready()
                if self.muted:
                    self.mumble.users.myself.mute()
                if self.deafened:
                    self.mumble.users.myself.deafen()

                for u in self.mumble.users:
                    self.mumble.users[u]['volume'] = 100
                
                channels_and_users = await self.get_channels_and_users(self)
                decky_plugin.logger.info(f"{self.mumble.users}")
                decky_plugin.logger.info(f"{channels_and_users}")
                self.connected = True
                self.messages.append(json.dumps({'type': 'message', 'actor': 'Server', 'message': str(self.mumble.server_sync_message.welcome_text), 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))
                
                ## Set up callbacks to do things when stuff happens
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, partial(self.sound_received_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_USERCREATED, partial(self.user_added_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_USERUPDATED, partial(self.user_updated_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_USERREMOVED, partial(self.user_removed_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELCREATED, partial(self.channel_added_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELUPDATED, partial(self.channel_updated_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELREMOVED, partial(self.channel_removed_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, partial(self.message_received_handler, self))
                self.mumble.callbacks.add_callback(pymumble.constants.PYMUMBLE_CLBK_DISCONNECTED, partial(self.disconnected_handler, self))
                self.mumble.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_ACLRECEIVED, self.acl_received_handler)
                self.mumble.set_comment_update_callback(self.comment_updated_handler)
                
                await self.broadcast_update(self, reason="Connected to server")
                decky_plugin.logger.info(f"Connected")
                decky_plugin.logger.info("Welcome message:")
                decky_plugin.logger.info(self.mumble.server_sync_message.welcome_text)
                return channels_and_users
            
            except Exception as e:
                decky_plugin.logger.info("Failed to connect to server")
                decky_plugin.logger.info(e)
                users = []
                return users
        elif self.connected:
            decky_plugin.logger.info(f"Already connected")
            channels_and_users = await self.get_channels_and_users(self)
            return channels_and_users
        else:
            decky_plugin.logger.info(f"No server selected")
            return False

    ## Thread which handles playback of received audio
    @catch_errors
    def audio_playback_thread(self):
        try:
            device_info = sd.query_devices(self.selected_output_device, 'output')
            output_sample_rate = device_info['default_samplerate']
            self.logger.info(f"Tergis fart {self.selected_input_device}, {output_sample_rate}")
            with sd.OutputStream(samplerate=48000, device=self.selected_output_device, dtype=numpy.int16, channels=2, blocksize=32768) as stream:
                while True:
                    vol, audio_data = self.audio_queue.get()
                    if audio_data is None:
                        break  # Exit the loop if we get a None item in the queue
                    
                    ## Set the volume based on the user's volume setting
                    vol = vol / 100.0
                    audio_data = (audio_data * vol).astype(numpy.int16)
                    stream.write(audio_data)

        except Exception as e:
            self.logger.info(f"Bad luck tergis {e}")

    ## Function for opening the audio stream
    @catch_errors
    def open_audio_stream(self):
        CHUNK = 1920
        CHANNELS = 1
        RATE = 48000
        frame_duration = CHUNK / RATE
        MAX_DATA_BYTES = 4000
        min_level = 175
        max_level = 500000

        def input_callback(in_data, frame_count, time_info, status):
            if self.transmit_mode == 0 and self.connected and not self.muted and self.transmitting:
                try:
                    # Directly send raw PCM audio data
                    self.mumble.sound_output.add_sound(in_data.tobytes())
                    asyncio.run(self.broadcast_update(self, username=self.mumble.users.myself))
                except Exception as e:
                    decky_plugin.logger.info(f"Failed to send audio: {e}")
            if self.transmit_mode == 1 and not self.muted and self.transmitting:
                try:
                    self.mumble.sound_output.add_sound(in_data.tobytes())
                    asyncio.run(self.broadcast_update(self, username=self.mumble.users.myself))
                except Exception as e:
                    decky_plugin.logger.info(f"Failed to send audio (PTT MODE): {e}")

            if self.transmit_mode == 2 and not self.muted and self.connected:
                try:
                    volume_norm = numpy.linalg.norm(in_data) * 10
                    volume_norm = numpy.clip(volume_norm, min_level, max_level)
                    volume_percent = ((volume_norm - min_level) / (max_level - min_level)) * 100
                    if volume_percent > self.broadcastAfter:
                        if volume_percent > self.silenceBelow:
                            decky_plugin.logger.info(f"Sending audio {volume_percent}")
                            self.mumble.sound_output.add_sound(in_data.tobytes())
                            asyncio.run(self.broadcast_update(self, username=self.mumble.users.myself))
                            self.broadcast_timer = time.time()  # Reset the timer
                    elif self.broadcast_timer is not None:
                        if time.time() - self.broadcast_timer > self.BROADCAST_TIMEOUT:
                            self.broadcast_timer = None  # Stop the timer
                        else:
                            # Keep broadcasting until the timer runs out
                            self.mumble.sound_output.add_sound(in_data.tobytes())
                            asyncio.run(self.broadcast_update(self, username=self.mumble.users.myself))
                    elif volume_percent < self.silenceBelow:
                        self.broadcast_timer = None  # Stop the timer immediately
                except Exception as e:
                    decky_plugin.logger.info(f"Failed to send audio (ACTIVITY MODE): {e}")
        try:
            self.stream = sd.InputStream(
                            channels=CHANNELS,
                            samplerate=RATE,
                            device=self.selected_input_device,
                            blocksize=CHUNK,
                            dtype='int16',
                            callback=input_callback)
            
            self.stream.start()
            self.playback_thread = threading.Thread(target=self.audio_playback_thread, args=(self,))
            self.playback_thread.start()
            self.logger.info("Started Audio")
        except Exception as e:
            self.logger.info(e)

    ## Opens the probing stream. This is the audio stream which is used to check the audio level when the sound settings page is open
    @catch_errors
    def open_probing_stream(self):
        if True:
            self.logger.info("PROBE NOT CONNECTED FART")
            def probe_callback(in_data, frame_count, time_info, status):
                min_level = 175
                max_level = 500000
                self.volume_norm = numpy.linalg.norm(in_data) * 10
                self.volume_norm = numpy.clip(self.volume_norm, min_level, max_level)
                self.volume_percent = ((self.volume_norm - min_level) / (max_level - min_level)) * 100
                asyncio.run(self.check_audio_level(self))
            try:
                decky_plugin.logger.info("STARTING PROBER?! ")
                self.probe = sd.InputStream(channels=1, samplerate=48000, device=self.selected_input_device, blocksize=1920, dtype='int16', callback=probe_callback)
                self.probe.start()
                self.probing = True
                decky_plugin.logger.info(f"STARTed PROBER?! {self.probing}, {self.probe}")
            except Exception as e:
                self.logger.info(e)
    
    @catch_errors
    async def check_audio_level(self):
        if 'audio_level' in self.clients:
            if len(self.clients['audio_level']) > 0:
                for websocket in self.clients.get('audio_level', []):
                    await websocket.send(json.dumps({'type': 'audio_level_update', 'data': int(self.volume_percent)}))

    @catch_errors
    async def leave_server(self):
        decky_plugin.logger.info(f"leaving server")
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.mumble.stop)
            decky_plugin.logger.info(f"Left Server?")
            await self.broadcast_update(self)
            users=[]
            self.connected = False
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELCREATED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELUPDATED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELREMOVED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_USERCREATED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_USERUPDATED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_USERREMOVED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_DISCONNECTED)
            self.mumble.callbacks.reset_callback(pymumble.constants.PYMUMBLE_CLBK_ACLRECEIVED)
            self.mumble.remove_comment_update_callback()
            #await self.broadcast_update(self)
            self.stream.stop()
            self.audio_queue.put((None, None))
            self.playback_thread.join()
            return users
        except Exception as e:
            decky_plugin.logger.info(f"fucked")
            decky_plugin.logger.info(e)
            return False
        
    async def move_to_channel(self, channelName):
        decky_plugin.logger.info(f"Moving to channel {channelName}")
        try:
            c = self.get_channel_by_name(self, channelName)
            c.move_in()
            await self.broadcast_update(self)
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Turgidson?")
            decky_plugin.logger.info(e)
    
    @catch_errors
    def query_public_servers(self):
        listurl = f"https://publist.mumble.info/v1/list"
        r = requests.get(listurl)
        #decky_plugin.logger.info(f"requests {r.content}")
        # Check if the request was successful
        if r.status_code == 200:
            # Parse the XML response
            root = etree.fromstring(r.content)
            # Iterate through the server elements to extract the server information
            for server in root.findall('server'):
                name = server.get('name')
                ca = server.get('ca')
                continent_code = server.get('continent_code')
                country = server.get('country')
                country_code = server.get('country_code')
                ip = server.get('ip')
                port = server.get('port')
                region = server.get('region')
                url = server.get('url')
                # Do something with the server information (e.g., add to a list or print)
                decky_plugin.logger.info(f"Server Name: {name}, IP: {ip}, Port: {port}, URL: {url}")
                self.publicServers.append({'name': name, 'ip': ip, 'port': port, 'url': url, 'country': country, 'country_code': country_code, 'ping': 999 })
        else:
            decky_plugin.logger.info("Failed to fetch the public server list.")


    async def notify_clients(self, server_data, websocket):
        message = {'type': 'pingupdate', 'data': server_data}
        await websocket.send(json.dumps(message))
    
    # @catch_errors
    # def pingPublicServers(self, main_event_loop):
    #     with ThreadPoolExecutor() as executor:
    #         for s in self.publicServers:
    #             decky_plugin.logger.info(f"Pinging {s['name']}")
    #             try:
    #                 future = executor.submit(mumble_ping, s['ip'], int(s['port']))
    #                 r = future.result()
    #                 decky_plugin.logger.info(f"pinged {r}")
    #                 s['ping'] = r['ping']
    #                 for websocket in self.clients.get('default', []):
    #                     self.notify_clients(self, s, websocket)
    #             except Exception as e:
    #                 decky_plugin.logger.info(f"Failed to ping {s['name']}")
    #                 decky_plugin.logger.info(e)

    @catch_errors
    def pingPublicServers(self, main_event_loop):
        for s in self.publicServers:
            decky_plugin.logger.info(f"Pinging {s['name']}")
            try:
                r = mumble_ping(s['ip'], int(s['port']))
                decky_plugin.logger.info(f"pinged {r}")
                s['ping'] = r['ping']
                s['users'] = r['users']
                s['max_users'] = r['max_users']
                for websocket in self.clients.get('default', []):
                    coroutine_obj = self.notify_clients(self, s, websocket)
                    asyncio.run_coroutine_threadsafe(coroutine_obj, main_event_loop)
            except Exception as e:
                decky_plugin.logger.info(f"Failed to ping {s['name']}")
                decky_plugin.logger.info(e)


    ###########################################################################
    ##                Functions for handling Mumble Callbacks                ##
    ###########################################################################
    ## When sound is received, this function is called. It adds the sound to the queue for playback by the audio_playback_thread
    @catch_errors
    def sound_received_handler(self, user, soundchunk):
        decky_plugin.logger.info(f"Sound received {user}")
        try:
            if not self.deafened and user['name'] not in self.muted_users:
                asyncio.run(self.broadcast_update(self, username=user))
                device_info = sd.query_devices(self.selected_output_device, 'output')
                stereo_data = mono_to_stereo(soundchunk.pcm)
                self.audio_queue.put((user['volume'], stereo_data))
        except Exception as e:
            decky_plugin.logger.error(f"Failed to handle sound received: {e}")

    def user_added_handler(self, user):
        decky_plugin.logger.info(f"user added: {user}")
        self.messages.append(json.dumps({'type': 'message', 'actor': 'Server', 'message': f"{user['name']} joined", 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))
        self.mumble.users[user['session']]['volume'] = 100
        asyncio.run(self.broadcast_update(self, reason="User added"))

    def user_updated_handler(self, user, changes):
        decky_plugin.logger.info(f"user changed: {user} {changes}")
        asyncio.run(self.broadcast_update(self, reason="User updated"))

    def user_removed_handler(self, user, event):
        decky_plugin.logger.info(f"user removed: {user} {event}")
        self.messages.append(json.dumps({'type': 'message', 'actor': 'Server', 'message': f"{user['name']} left", 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))
        if user['name'] == self.connection.username:
            asyncio.run(self.broadcast_update(self, reason="Kicked"))
            asyncio.run(self.leave_server(self))
        asyncio.run(self.broadcast_update(self, reason="User removed"))

    def channel_added_handler(self, channel):
        decky_plugin.logger.info(f"channel added: {channel}")
        asyncio.run(self.broadcast_update(self, reason="Channel added"))

    def channel_updated_handler(self, channel, changes):
        decky_plugin.logger.info(f"channel updated: {channel} {changes}")
        asyncio.run(self.broadcast_update(self, reason="Channel updated"))
    
    def channel_removed_handler(self, channel):
        decky_plugin.logger.info(f"channel removed: {channel}")
        asyncio.run(self.broadcast_update(self, reason="Channel removed"))
    
    def message_received_handler(self, message):
        decky_plugin.logger.info(f"Received message: {message}")
        self.messages.append(json.dumps({'type': 'message', 'actor': self.mumble.users[message.actor]['name'], 'message': message.message, 'time': str(datetime.datetime.now().strftime("%H:%M:%S"))}))
        decky_plugin.logger.info(f"messages array: {self.messages}")
        asyncio.run(self.broadcast_update(self, message=message))

    def disconnected_handler(self):
        decky_plugin.logger.info(f"Disconnected from server")
        asyncio.run(self.broadcast_update(self))
        asyncio.run(self.leave_server(self))

    @catch_errors
    def comment_updated_handler(self, comment):
        decky_plugin.logger.info(f"comment updated {comment}")

    @catch_errors
    def acl_received_handler(event):
        try:
            decky_plugin.logger.info(f"acl received ")
            decky_plugin.logger.info(f"acl received {event}")

            for group in event.groups:
                if event.group.name == "admin":
                    decky_plugin.logger.info(f"IN TERGID admin group{[user for user in group.add]}")
        except Exception as e:
            decky_plugin.logger.info(f"Failed to handle acl received: {e}")

        # # Check if our user is in the 'admin' group
        # for group in acl.groups:
        #     if group.name == "admin" and self.mumble.users.myself['name'] in group.members:
        #         self.logger.info(f"User is admin")
        #         return True
        
        # self.logger.info(f"User is NOT A TERGID admin")
        # return False


    ###########################################################################
    ##                      Getter and Setter functions                      ##
    ##                Most of these are called by the frontend               ##
    ###########################################################################                    
    async def get_default_input(self):
        return {"ID": self.p.get_default_input_device_info()["index"], "name": self.p.get_default_input_device_info()["name"]}

    async def get_default_output(self):
        return {"ID": self.p.get_default_output_device_info()['index'], "name": self.p.get_default_output_device_info()['name']}
    
    async def get_transmit_mode(self):
        if self.transmit_mode == 0:
            return {'ID': self.transmit_mode, 'name': 'always-on'}
        if self.transmit_mode == 1:
            return {'ID': self.transmit_mode, 'name': 'push-to-talk'}
        if self.transmit_mode == 2:
            return {'ID': self.transmit_mode, 'name': 'activity'}
    
    async def set_transmit_mode(self, mode=0):
        decky_plugin.logger.info(f"set to {mode}")
        self.transmit_mode = mode
        if mode == 0:
            self.transmitting = True
        elif mode == 1:
            self.transmitting = False
        self.settings.setSetting("transmitMode", mode)
        #await self.broadcast_update(self)
        return self.transmit_mode

    async def get_users_list(self):
        decky_plugin.logger.info(f"Getting users list")
        users = [{'name': user['name'], 'muted': self.check_user_muted(self, user), 'ID': user['session']} for user in self.mumble.users.values()]
        decky_plugin.logger.info(f"Got users list: {users}")
        return users

    async def settings_read(self):
        decky_plugin.logger.info('Reading settings')
        return self.settings.read()
    
    async def settings_commit(self):
        decky_plugin.logger.info('Saving settings')
        return self.settings.commit()
    
    async def settings_getSetting(self, key: str, defaults):
        return self.settings.getSetting(key, defaults)
    
    @catch_errors
    async def settings_setSetting(self, key: str, value):
       decky_plugin.logger.info(f"trying to fart: {key}, {value}")
       return self.settings.setSetting(key, value)
    
    @catch_errors
    async def saveServer(self, address, port, username, label, password, tokens):
        # if tokens is not None:
        #     tokens = tokens.split()
        server = ServerConnection(address, port, username, password, label, tokens)
        for i in self.savedServers:
            if i['label'] == label:
                self.logger.info(f"Already exists. updating...: {server}")
                self.savedServers.remove(i)
                self.savedServers.append(server.to_json())
                return self.settings.setSetting("savedServers", self.savedServers)
        self.logger.info(f"saving server: {server}")
        self.savedServers.append(server.to_json())
        await self.setCurrentServer(self, label)
        return self.settings.setSetting("savedServers", self.savedServers)
    
    @catch_errors
    async def getCurrentServer(self):
        self.logger.info("getting current server details")
        if self.connection is not None:
            return self.connection.to_json()
        return False
    
    @catch_errors
    async def setCurrentServer(self, serverLabel):
        self.logger.info("setting current server details")
        for serv in self.savedServers:
            if serv['label'] == serverLabel:
                self.connection = ServerConnection(**serv)
                self.logger.info(self.connection)
                return self.settings.setSetting("currentServer", self.connection.to_json())
        return False
    
    @catch_errors
    async def getServers(self):
        decky_plugin.logger.info(f"Get servers: {self.savedServers}")
        decky_plugin.logger.info(f"type: {type(self.savedServers)}")
        return self.savedServers
    
    @catch_errors
    async def deleteServer(self, serverLabel):
        decky_plugin.logger.info(f"Removing server: {serverLabel}")
        for i in self.savedServers:
            if serverLabel in i['label']:
                self.savedServers.remove(i)
                return self.settings.setSetting("savedServers", self.savedServers)
        return False
    
    async def pingServer(self, ip, port):
        ping = mumble_ping(str(ip), int(port))
        self.logger.info(f"ping: {str(ping)}")
        return ping

    async def mute(self):
        decky_plugin.logger.info(f"Muting self")
        #self.check_if_admin(self, self.mumble.my_channel())
        
        try:
            if self.connected:
                self.mumble.users.myself.mute()
                self.muted = True
                await self.broadcast_update(self)
            else:
                self.muted = True
        except Exception as e:
            decky_plugin.logger.info(f"Turgidson?")
            decky_plugin.logger.info(e)
        
        #threads = threading.enumerate()
        #decky_plugin.logger.info(f"Threads: {str(threads)}")
        #await asyncio.sleep(0.1)
        #for thread in threads:
        #    decky_plugin.logger.info(f"Thread name: {thread.getName()}, Thread ID: {thread.ident}")
        decky_plugin.logger.info(f"Muted: {self.muted}")
        return True

    async def unmute(self):
        decky_plugin.logger.info(f"Unmuting self")
        try:
            if self.connected:
                self.mumble.users.myself.unmute()
                self.muted = False
                await self.broadcast_update(self)
            else:
                self.muted = False
        except Exception as e:
            decky_plugin.logger.info(f"Turgidson fart?")
            decky_plugin.logger.info(e)
        return True

    async def deafen(self):
        decky_plugin.logger.info(f"Deafening self")
        try:
            if self.connected:
                self.mumble.users.myself.deafen()
                self.deafened = True
                self.muted = True
                await self.broadcast_update(self)
                return True
            else:
                self.deafened = True
                self.muted = True
                return True
        except Exception as e:
            decky_plugin.logger.info(f"Turgidson?")
            decky_plugin.logger.info(e)

    async def undeafen(self):
        decky_plugin.logger.info(f"undeafening self")
        try:
            if self.connected:
                self.mumble.users.myself.undeafen()
                self.deafened = False
                await self.broadcast_update(self)
                return True
            else:
                self.deafened = False
                return True

        except Exception as e:
            decky_plugin.logger.info(f"Turgidson fart?")
            decky_plugin.logger.info(e)
    
    async def get_channels_and_users(self):
        channels_and_users = {}
        decky_plugin.logger.info(f"Connected: {self.connected}")

        if self.connected:
            for channel in self.mumble.channels:
                channel_obj = self.mumble.channels[channel]
                channels_and_users[channel_obj["name"]] = {
                    "users": {}
                }
                for user in channel_obj.get_users():
                    channels_and_users[channel_obj["name"]]["users"][user["name"]] = {
                        "muted": self.check_user_muted(self, user),
                        "ID": user['session'],
                        "volume": user['volume']
                    }
            return channels_and_users
        else:
            return {}
    
    @catch_errors
    async def mute_user(self, userName):
        self.muted_users.append(userName)
        self.logger.info(f"Muted users CUP OF TURD: {self.muted_users}")
        return self.muted_users
    
    async def unmute_user(self, userName):
        self.muted_users.remove(userName)
        self.logger.info(f"Muted users CUP OF UNTURD: {self.muted_users}")
        return self.muted_users

    async def get_muted_users(self):
        self.logger.info(f"Muted users GOT TURDS: {self.muted_users}")
        return self.muted_users
            
    async def getConnected(self):
        return self.connected
    
    async def getDeafened(self):
        return self.deafened
    
    async def getMuted(self):
        return self.muted
    
    async def getUsername(self):
        return self.connection.username
    
    @catch_errors
    async def setUserVolume(self, user, volume):
        self.logger.info(f"Setting user volume: {user}, {volume}")
        for u in self.mumble.users:
            if self.mumble.users[u]['name'] == user:
                self.mumble.users[u]['volume'] = volume
                return self.mumble.users[u]['volume']
    
    async def getUserVolume(self, user):
        self.logger.info(f"Getting user volume ASS1: {user}")
        for u in self.mumble.users:
            if self.mumble.users[u]['name'] == user:
                self.logger.info(f"Getting user volume: {user}")
                self.logger.info(f"{self.mumble.users[u]['volume']}")
                return self.mumble.users[u]['volume']
        return 0
    
    async def getMessagesArray(self):
        self.logger.info(self.messages)
        return self.messages
    
    def check_user_muted(self, user):
        if 'self_mute' in user:
            return user['self_mute']
        else:
            return False

    async def get_selected_recipient(self):
        decky_plugin.logger.info(f"got selected recipient")
        return self.selected_recipient
    
    async def set_selected_recipient(self, ID=int, name=str):
        decky_plugin.logger.info(f"Eatign a cup of , {ID}, {name}")
        self.selected_recipient = { 'ID': ID, 'name': name }
        return True

    async def setBroadcastAfter(self, value=int):
        try:
            self.broadcastAfter = value
            decky_plugin.logger.info(value)
            self.settings.setSetting("broadcastAfter", value)
            for websocket in self.clients.get('audio_level', []):
                await websocket.send(json.dumps({'type': 'broadcastAfter_update', 'value': value }))
            return True
        except Exception as e:
            return False
    
    async def getbroadcastAfter(self):
        return self.broadcastAfter
    
    async def setTransmitting(self, value=True):
        self.transmitting = value
        return self.transmitting
    
    async def setsilenceBelow(self, value=int):
        try:
            self.silenceBelow = value
            decky_plugin.logger.info(value)
            self.settings.setSetting("silenceBelow", value)
            for websocket in self.clients.get('audio_level', []):
                await websocket.send(json.dumps({'type': 'silenceBelow_update', 'value': value }))

            return True
        except Exception as e:
            return False
    
    async def getTimeout(self):
        return self.BROADCAST_TIMEOUT
    
    async def setTimeout(self, value=int):
        try:
            self.BROADCAST_TIMEOUT = value
            decky_plugin.logger.info(value)
            self.settings.setSetting("BROADCAST_TIMEOUT", value)
            for websocket in self.clients.get('audio_level', []):
                await websocket.send(json.dumps({'type': 'timeout_update', 'value': value }))
            return True
        except Exception as e:
            return False
    
    async def getsilenceBelow(self):
        return self.silenceBelow
    
    async def setInputDevice(self, device=int):
        try:
            self.selected_input_device = device
            self.logger.info(f"Selected input device: {self.selected_input_device}")
            if self.probing:
                self.probing = False
                if self.probe:
                    self.probe.stop()
                self.probe = None
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting input device: {e}")
            return False

    async def setOutputDevice(self, device=int):
        try:
            self.selected_output_device = device
            decky_plugin.logger.info(f"Selected output device: {self.selected_output_device}")
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting output device: {e}")
            return False
        
    async def setAPI(self, api=int):
        try:
            self.selected_api_input = self.apis[api]
            self.selected_api_input['index'] = api
            decky_plugin.logger.info(f"Selected INPUT API: {self.selected_api_input}")
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting API device: {e}")
            return False
        
    async def setAPI_output(self, api=int):
        try:
            self.selected_api_output = self.apis[api]
            self.selected_api_output['index'] = api
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting API device: {e}")
            return False
    
    async def get_api(self):
        for index, i in enumerate(self.apis):
            if i['name'] == self.selected_api_input['name']:
                turdname = i['name']
                turddex = index
        return {'ID': turddex, 'name': turdname}
    
    async def get_api_output(self):
        decky_plugin.logger.info(f"The Selected API FETUS is: {self.selected_api_output}")
        for index, i in enumerate(self.apis):
            if i['name'] == self.selected_api_output['name']:
                turdname = i['name']
                turddex = index
        return {'ID': turddex, 'name': turdname}
    
    async def get_apis(self):
        try:
            formatted_input_apis = [{'ID': index, 'name': api['name'] } for index, api in enumerate(self.apis)]
            return formatted_input_apis
        except Exception as e:
            decky_plugin.logger.info(f"CUPPA MCFUCKED {e}")
    
    def get_channel_by_name(self, channel_name):
        for channel in self.mumble.channels:
            if self.mumble.channels[channel]["name"] == channel_name:
                return self.mumble.channels[channel]
        return None
    
    async def setPushToTalkKey(self, key="R5"):
        try:
            self.ptt_key = key
            decky_plugin.logger.info(f"Set ppt key {key}")
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting ptt key: {e}")
            return False
    
    @catch_errors
    async def getPushToTalkKey(self):
        decky_plugin.logger.info(f"TERDINOOS KEY IS {self.ptt_key}")
        if self.ptt_key == "R4":
            return {'ID': 0, 'name': 'R4'}
        if self.ptt_key == "L4":
            return {'ID': 1, 'name': 'L4'}
        if self.ptt_key == "R5":
            return {'ID': 2, 'name': 'R5'}
        if self.ptt_key == "L5":
            return {'ID': 3, 'name': 'L5'}
    
    @catch_errors
    async def setInGamePushToTalkKey(self, key="Up"):
        try:
            self.ig_ptt_key = key
            decky_plugin.logger.info(f"Set ppt key {key}")
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting ptt key: {e}")
            return False
    
    @catch_errors
    async def getInGamePushToTalkKey(self):
        decky_plugin.logger.info(f"TERDINOOS KEY IS {self.ig_ptt_key}")
        if self.ig_ptt_key == "A":
            return {'ID': 0, 'name': 'A'}
        if self.ig_ptt_key == "B":
            return {'ID': 1, 'name': 'B'}
        if self.ig_ptt_key == "X":
            return {'ID': 2, 'name': 'X'}
        if self.ig_ptt_key == "Y":
            return {'ID': 3, 'name': 'Y'}
        if self.ig_ptt_key == "L1":
            return {'ID': 4, 'name': 'L1'}
        if self.ig_ptt_key == "L2":
            return {'ID': 5, 'name': 'L2'}
        if self.ig_ptt_key == "L3":
            return {'ID': 6, 'name': 'L3'}
        if self.ig_ptt_key == "R1":
            return {'ID': 7, 'name': 'R1'}
        if self.ig_ptt_key == "R2":
            return {'ID': 8, 'name': 'R2'}
        if self.ig_ptt_key == "R3":
            return {'ID': 9, 'name': 'R3'}
        if self.ig_ptt_key == "Select":
            return {'ID': 10, 'name': 'Select'}
        if self.ig_ptt_key == "Start":
            return {'ID': 11, 'name': 'Start'}
        if self.ig_ptt_key == "Up":
            return {'ID': 12, 'name': 'Up'}
        if self.ig_ptt_key == "Down":
            return {'ID': 13, 'name': 'Down'}
        if self.ig_ptt_key == "Left":
            return {'ID': 14, 'name': 'Left'}
        if self.ig_ptt_key == "Right":
            return {'ID': 15, 'name': 'Right'}
    
    @catch_errors
    async def setPTTEnabled(self, value=True):
        try:
            self.ptt_enabled = value
            decky_plugin.logger.info(f"Set ppt {value}")
            return True
        except Exception as e:
            decky_plugin.logger.info(f"Error setting ptt: {e}")
            return False
    
    @catch_errors
    async def getPTTEnabled(self):
        return self.ptt_enabled

    async def get_input_devices(self):
        decky_plugin.logger.info(f"The inlist is here: {len(self.inlist)}")
        newlist = []
        for i in self.inlist:
            if i['hostapi'] == self.selected_api_input['index']:
                newlist.append(i)
        formatted_input_devices = [{'ID': device['index'], 'name': device['name']} for index, device in enumerate(newlist)]
        decky_plugin.logger.info(f"formatted_input_devices TERDS: {formatted_input_devices}")
        return formatted_input_devices
    
    async def get_output_devices(self):
        newlist = []
        for i in self.outlist:
            if i['hostapi'] == self.selected_api_output['index']:
                newlist.append(i)
        formatted_output_devices = [{'ID': device['index'], 'name': device['name']} for index, device in enumerate(newlist)]
        return formatted_output_devices
    
    async def get_selected_output(self):
        decky_plugin.logger.info(f"The Selected OUTPUT FETUS is: {self.selected_output_device}")
        for i in self.outlist:
            if i['index'] == self.selected_output_device:
                turdname = i['name']
        return {'ID': self.selected_output_device, 'name': turdname}
    
    async def get_selected_input(self):
        decky_plugin.logger.info(f"The Selected INPUT TERGINOOS is: {self.selected_input_device}")
        
        for i in self.inlist:
            if i['index'] == self.selected_input_device:
                turdname = i['name']
        decky_plugin.logger.info({'ID': self.selected_input_device, 'name': turdname})
        return {'ID': self.selected_input_device, 'name': turdname}
    
    @catch_errors
    async def set_comment(self, comment):
        self.logger.info(f"Setting comment: {comment}")
        self.mumble.users.myself.comment(comment)
        return comment
    
    @catch_errors
    async def kick_user(self, user):
        self.logger.info(f"Kicking user: {user}")
        for u in self.mumble.users:
            if self.mumble.users[u]['name'] == user:
                try:
                    self.mumble.users[u].kick()
                    return True
                except Exception as e:
                    self.logger.info(f"Error kicking user {user}: {e}")
        return False
    
    @catch_errors
    async def get_comment(self, user):
        for u in self.mumble.users:
            if self.mumble.users[u]['name'] == user:
                self.logger.info(f"Getting user comment: {user}")
                try:
                    self.logger.info(f"{self.mumble.users[u]['comment']}")
                    return self.mumble.users[u]['comment']
                except Exception as e:
                    self.logger.info(f"Error getting user comment: {e}")
                    return ""
        return ""
    
    @catch_errors
    def check_if_admin(self, channel):
        # Fetch the ACL for the channel
        try:
            self.mumble.channels[0].request_acl()
            self.mumble.my_channel().acl.request_group_update(group_name='admin')
            self.logger.info(f"requested ACL")
        except Exception as e:
            self.logger.info(f"Error requesting ACL: {e}")

    @catch_errors
    async def getInfo(self):
        info = self.connection.to_json()
        decky_plugin.logger.info(f"info: {info}")
        moreInfo = mumble_ping(info['host'], int(info['port']))
        mergedInfo = {**info, **moreInfo, **self.mumble.server_info, **self.mumble.server_version_info, **self.mumble.cipher_info, 'codec': self.mumble.codec}
        decky_plugin.logger.info(f"mergedInfo: {mergedInfo}")
        return mergedInfo
    
    @catch_errors
    async def getPublicServers(self):
        self.query_public_servers(self)
        pingThread = threading.Thread(target=self.pingPublicServers, args=(self, asyncio.get_event_loop()))
        pingThread.start()
        return self.publicServers
