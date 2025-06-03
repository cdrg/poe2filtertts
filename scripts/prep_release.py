"""
Make .zip files of TTS soundpack directories for uploading with a github release.
"""

import os
import sys
import argparse
import shutil

def main():
    '''
    Make .zip files of TTS soundpack directories for uploading with a github release.

    TODO: First, verify all soundpack dirs versus the template file?

    Warning: Existing .zip files with the same name in the output directory will be overwritten.

    Returns:
        (int): 0 on success, 1 on error
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputdir", help="the input directory containing soundpack dirs", default=os.getcwd())
    parser.add_argument("-o", "--outputdir", help="the output directory to write zips to", default=os.path.join(os.path.expanduser("~"), "ttszips"))
    args: argparse.Namespace = parser.parse_args()

    if not os.path.exists(args.inputdir):
        print(f"Error: input directory '{args.inputdir}' does not exist.")
        return 1
    
    if not os.path.exists(args.outputdir):
        os.makedirs(args.outputdir, mode=0o755, exist_ok=True)
    
    soundpackdirs: list[str] = [name for name in os.listdir(args.inputdir) 
                                if os.path.isdir(os.path.join(args.inputdir, name)) 
                                and os.path.isdir(os.path.join(args.inputdir, name, "sounds"))]
    for soundpackdir in soundpackdirs:
        soundpackdir_path: str = os.path.join(args.inputdir, soundpackdir)
       
        zip_path: str = os.path.join(args.outputdir, f"{soundpackdir}.zip")

        shutil.make_archive(base_name=zip_path, format='zip', root_dir=soundpackdir_path)
        print(f"Created zip '{zip_path}' from soundpack dir '{soundpackdir_path}'")

if __name__ == "__main__":
    sys.exit(main())