import pymumble_py3 as pymumble
from pymumble_py3 import mumble_pb2
import decky_plugin

class CustomMumble(pymumble.Mumble):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server_sync_message = None
        self.on_comment_update = None  # Initialize the callback to None
        self.received_server_sync = False

    def set_comment_update_callback(self, callback):
        """Set the callback that will be called when a comment is updated."""
        self.on_comment_update = callback
    
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

    def dispatch_control_message(self, type, message):
        super().dispatch_control_message(type, message)

        if type == pymumble.constants.PYMUMBLE_MSG_TYPES_SERVERSYNC:
            mess = mumble_pb2.ServerSync()
            mess.ParseFromString(message)
            self.server_sync_message = mess
            self.received_server_sync = True
        elif type == pymumble.constants.PYMUMBLE_MSG_TYPES_USERSTATE:
            mess = mumble_pb2.UserState()
            mess.ParseFromString(message)
            decky_plugin.logger.info(f"User state: {mess}")
            if mess.HasField('comment'):
                user = self.users[mess.session]
                user['comment'] = mess.comment
                self.comment_updated(user, mess.comment)