from scapy.all import ARP, Ether, srp
import sys
from dotenv import load_dotenv
import time  # Required for the loop cooldown

load_dotenv()

# Define your target MAC address here (Use colons to separate segments)
target_mac = os.getenv("CAMERA_MAC")

def find_ip_from_mac(mac):
    # Specify the local subnet and the router's IP address range, left at the usual range for now
    target_ip_range = "192.168.0.0/24" 
    
    # 1. Create an ARP Request packet
    arp_request = ARP(pdst=target_ip_range)
    
    # 2. Create an Ethernet Frame to broadcast the request
    ether_frame = Ether(dst="ff:ff:ff:ff:ff:ff")
    
    # 3. Stack them into a combined packet (Ethernet + ARP)
    final_packet = ether_frame / arp_request
    
    # 4. Send the packet and wait for responses
    result = srp(final_packet, timeout=2, verbose=0)[0]

    # 5. Look through all the responses for the matching MAC address
    for sent_packet, received_packet in result:
        if received_packet.hwsrc.lower() == mac.lower():
            return received_packet.psrc

    return None

if __name__ == "__main__":
    current_ip = None
    cooldown_seconds = 5  # Set how long it waits before blasting the network again

    print(f"[*] Starting continuous search for MAC: {target_mac}")
    print("[*] Press Ctrl+C at any time to stop.\n")

    try:
        while not current_ip:
            # The end="" keeps the output on the same line for a cleaner look
            print(f"[*] Scanning 192.168.0.0/24... ", end="")
            
            # sys.stdout.flush() forces the terminal to print the above line immediately, 
            # before the scapy function freezes the script for 2 seconds waiting for replies
            sys.stdout.flush() 

            current_ip = find_ip_from_mac(target_mac)

            if current_ip:
                print("Found!")
                print(f"\n--------------------------------------------------")
                print(f"[+] SUCCESS: Device with MAC [{target_mac.upper()}] is at IP [{current_ip}]")
                print(f"--------------------------------------------------\n")
                print(f"You can now use the IP address [{current_ip}] to log into the camera via ONVIF Device Manager.")
            else:
                print(f"Not found. Retrying in {cooldown_seconds} seconds...")
                time.sleep(cooldown_seconds) # Pauses the script to prevent network flooding

    except KeyboardInterrupt:
        # This block catches the Ctrl+C command silently instead of throwing a massive red error
        print("\n\n[-] Search stopped.")
