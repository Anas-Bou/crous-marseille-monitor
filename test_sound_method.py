#!/usr/bin/env python3
import os
import time
import logging
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def play_sound_notification():
    """Play a sound notification for 5 seconds - Manjaro compatible"""
    try:
        logging.info("🔊 Playing sound notification...")
        
        print("Trying speaker-test (sine wave tone)...")
        # Method 1: Use speaker-test to generate a tone
        try:
            subprocess.run(['speaker-test', '-t', 'sine', '-f', '1000', '-l', '1'], 
                          timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logging.info("✅ Sound notification completed (speaker-test)")
            return
        except Exception as e:
            print(f"speaker-test failed: {e}")
        
        print("Trying spd-say (text-to-speech)...")
        # Method 2: Use spd-say (text-to-speech)
        try:
            subprocess.run(['spd-say', 'Test notification sound'], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logging.info("✅ Sound notification completed (text-to-speech)")
            return
        except Exception as e:
            print(f"spd-say failed: {e}")
        
        print("Trying system sound files...")
        # Method 3: Use paplay with system sound files
        sound_files = [
            '/usr/share/sounds/freedesktop/stereo/message.oga',
            '/usr/share/sounds/gnome/default/alerts/drip.ogg',
        ]
        for sound_file in sound_files:
            try:
                if os.path.exists(sound_file):
                    print(f"Playing sound file: {sound_file}")
                    subprocess.run(['paplay', sound_file], 
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    logging.info(f"✅ Sound notification completed (sound file: {sound_file})")
                    return
                else:
                    print(f"Sound file not found: {sound_file}")
            except Exception as e:
                print(f"Failed to play {sound_file}: {e}")
                continue
        
        print("Trying system beep (likely won't work)...")
        # Method 4: Fallback - use system beep
        os.system('echo -e "\a"')
        time.sleep(0.5)
        os.system('echo -e "\a"')
        time.sleep(0.5)
        os.system('echo -e "\a"')
        logging.info("✅ Sound notification completed (system beep)")
        
    except Exception as e:
        logging.warning(f"Could not play sound: {e}")

if __name__ == "__main__":
    print("Testing Manjaro-compatible sound notification...")
    print("This will try multiple methods until one works")
    print("Starting in 3 seconds...")
    time.sleep(3)
    
    play_sound_notification()
    print("Test completed!")