#!/usr/bin/env python3
"""Write a private FS-UAE profile for the batting prototype and optionally run it."""
import argparse,os,pathlib,shutil,subprocess
R=pathlib.Path(__file__).resolve().parents[2];O=R/'build/little-league'
def configure(rom):
 rom=pathlib.Path(rom).resolve()
 if not rom.is_file():raise SystemExit('Kickstart path does not exist')
 adf=O/'Little-League-SmallMig-Batting.adf'
 if not adf.is_file():raise SystemExit('Build the batting ADF first')
 config=O/'Batting.fs-uae'
 config.write_text(f'''[fs-uae]
base_dir = {O/'fs-uae'}
amiga_model = A1200
cpu = 68EC020
chip_memory = 2048
fast_memory = 0
kickstart_file = {rom}
floppy_drive_0 = {adf}
floppy_drive_0_sounds = 0
writable_floppy_images = 0
joystick_port_1 = keyboard
keyboard_key_space = action_joy_1_fire_button
fullscreen = 0
window_width = 960
window_height = 768
video_sync = off
''')
 return config
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--kickstart',default=os.environ.get('AMIGA_KICKSTART'));p.add_argument('--write-config',action='store_true');a=p.parse_args()
 if not a.kickstart:p.error('Supply --kickstart or AMIGA_KICKSTART')
 config=configure(a.kickstart);print(config)
 if not a.write_config:
  exe=shutil.which('fs-uae')
  if not exe:p.error('FS-UAE executable was not found')
  subprocess.run([exe,str(config)],check=True)
