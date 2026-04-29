from checkip import find_ip_from_mac
from time import sleep

class Camera:
    __camera_ip = None
    __mac_address = None
    
    def __init__(self, mac_address):
        self.__mac_address = mac_address
        self.__camera_ip = self.get_ip()
        
    

    def get_ip(self):
        while not self.__camera_ip:
            try:
                camera_ip = find_ip_from_mac(self.__mac_address)
                if camera_ip:
                    return camera_ip
                sleep(2)
            except KeyboardInterrupt:
                print("Ip search stopped by user.")
                return None
        return self.__camera_ip


    