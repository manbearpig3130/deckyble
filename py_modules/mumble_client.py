import pymumble_py3 as pymumble
from pymumble_py3 import mumble_pb2

class CustomMumble(pymumble.Mumble):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server_sync_message = None

    def dispatch_control_message(self, type, message):
        super().dispatch_control_message(type, message)

        if type == pymumble.constants.PYMUMBLE_MSG_TYPES_SERVERSYNC:
            mess = mumble_pb2.ServerSync()
            mess.ParseFromString(message)
            self.server_sync_message = mess