import decky_plugin, hid

class SteamDeckInput:
    def __init__(self):
        decky_plugin.logger.info("Starting sdinput init")
        self.device = None
        self.on = True
        for d in hid.enumerate():
            decky_plugin.logger.info(d)
            if d['vendor_id'] == 0x28DE and d['product_id'] == 0x1205 and d['interface_number'] == 2:
                decky_plugin.logger.info("Found the input tergid")
                self.device = hid.device()
                self.device.open_path(d['path'])
                decky_plugin.logger.info(self.device)
                self.previous_L5 = False
                self.current_L5 = False
                self.previous_L4 = False
                self.current_L4 = False
                self.previous_R4 = False
                self.current_R4 = False
                self.previous_R5 = False
                self.current_R5 = False
                self.fart = ""
                self.previous_fart = ""
                break
        
        if not self.device:
            decky_plugin.logger.info("Couldn't find Steam Deck controller device")
            raise Exception("Couldn't find Steam Deck controller device")
    
    def close(self):
        decky_plugin.logger.info("closing device")
        self.on = False
        self.device.close()
        
    def update(self):
        try:
            if self.on:
                data = self.device.read(64)
            
                # Update previous button state
                self.previous_L5 = self.current_L5
                self.previous_R5 = self.current_R5
                self.previous_L4 = self.current_L4
                self.previous_R4 = self.current_R4
                self.previous_fart = self.fart

                # Check the most significant bit of the 10th byte for the L5 button state
                self.current_L5 = bool(data[9] & 0b10000000)
                self.current_R5 = bool(data[10])
                if data[13] == 2:
                    self.current_L4 = True
                elif data[13] == 4:
                    self.current_R4 = True
                elif data[13] == 0:
                    self.current_L4 = False
                    self.current_R4 = False
                    
                if self.previous_L5 == False and self.current_L5 == True:
                    decky_plugin.logger.info("L5 button was just pressed")
                    self.fart = "L5"

                if self.previous_L5 == True and self.current_L5 == False:
                    decky_plugin.logger.info("L5 button was just released")
                    self.fart = ""

                if self.previous_R5 == False and self.current_R5 == True:
                    decky_plugin.logger.info("R5 button was just pressed")
                    self.fart = "R5"

                if self.previous_R5 == True and self.current_R5 == False:
                    decky_plugin.logger.info("R5 button was just released")
                    self.fart = ""

                if self.previous_L4 == False and self.current_L4 == True:
                    decky_plugin.logger.info("L4 button was just pressed")
                    self.fart = "L4"

                if self.previous_L4 == True and self.current_L4 == False:
                    decky_plugin.logger.info("L4 button was just released")
                    self.fart = ""

                if self.previous_R4 == False and self.current_R4 == True:
                    decky_plugin.logger.info("R4 button was just pressed")
                    self.fart = "R4"

                if self.previous_R4 == True and self.current_R4 == False:
                    decky_plugin.logger.info("R4 button was just released")
                    self.fart = ""

                return self.fart

        except Exception as e:
            decky_plugin.logger.info("CUPPA Fucked?")
            decky_plugin.logger.info(e)
            self.on = False
            self.close()