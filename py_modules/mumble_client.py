import pymumble_py3 as pymumble
from pymumble_py3 import mumble_pb2
import decky_plugin
from google.protobuf.json_format import MessageToDict

class CustomMumble(pymumble.Mumble):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server_sync_message = None
        self.on_comment_update = None  # Initialize the callback to None
        self.received_server_sync = False

    def set_comment_update_callback(self, callback):
        """Set the callback that will be called when a comment is updated."""
        self.on_comment_update = callback
    
    def get_control_socket(self):
        decky_plugin.logger.info(f"Getting control socket")
        decky_plugin.logger.info(f"{type(self.control_socket)}")
        return self.control_socket
    
    def remove_comment_update_callback(self):
        self.on_comment_update = None
    
    def comment_updated(self, user, comment):
        """Call the comment update callback, if it's set."""
        if self.on_comment_update:
            self.on_comment_update(user, comment)
    
    def callback_user_updated(self, user, message):
        # Call the original method to ensure the user's state is updated correctly
        super().callback_user_updated(user, message)
        
        # Then, add your own logic to capture the user's comment
        if message.HasField('comment'):
            user['comment'] = message.comment

    def dispatch_control_message(self, message_type, message):
        super().dispatch_control_message(message_type, message)

        if message_type == pymumble.constants.PYMUMBLE_MSG_TYPES_SERVERSYNC:
            mess = mumble_pb2.ServerSync()
            mess.ParseFromString(message)
            self.server_sync_message = mess
            self.received_server_sync = True
        elif message_type == pymumble.constants.PYMUMBLE_MSG_TYPES_CODECVERSION:
            mess = mumble_pb2.CodecVersion()
            mess.ParseFromString(message)
            #decky_plugin.logger.info(f"Codec version: {mess}")
            if mess.opus:
                #decky_plugin.logger.info(f"Opus: {mess.opus}")
                self.codec = "Opus"
            else:
                self.codec = "CELT"
        elif message_type == pymumble.constants.PYMUMBLE_MSG_TYPES_USERSTATE:
            mess = mumble_pb2.UserState()
            mess.ParseFromString(message)
            decky_plugin.logger.info(f"User state: {mess}")
            if mess.HasField('comment'):
                user = self.users[mess.session]
                user['comment'] = mess.comment
                self.comment_updated(user, mess.comment)
        elif message_type == pymumble.constants.PYMUMBLE_MSG_TYPES_SERVERCONFIG:
            mess = mumble_pb2.ServerConfig()
            mess.ParseFromString(message)
            try:
                #decky_plugin.logger.info(f"Server config: {mess}")
                #decky_plugin.logger.info(f"{type(mess)}")
                self.server_info = MessageToDict(mess)
                #decky_plugin.logger.info(f"{self.server_info}")
            except Exception as e:
                decky_plugin.logger.info(f"ass fuck: {e}")
        elif message_type == pymumble.constants.PYMUMBLE_MSG_TYPES_VERSION:
            #self.tls_version = self.get_control_socket().version()
            try:
                self.cipher = self.get_control_socket().cipher()
                self.cipher_info = {'suite': self.cipher[0], 'cipher_version': self.cipher[1], 'bits': self.cipher[2]}
                #decky_plugin.logger.info(f"TLS info: {self.tls_version}")
                decky_plugin.logger.info(f"cipher info: {self.cipher}")
            except Exception as e:
                decky_plugin.logger.info(f"farts ARSE {e}")
            mess = mumble_pb2.Version()
            mess.ParseFromString(message)
            decky_plugin.logger.info(f"Version info: {mess}")
            self.server_version_info = MessageToDict(mess)
                