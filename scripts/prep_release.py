"""
Make .zip files of TTS soundpack directories for uploading with a github release.
"""

import os
import sys
import argparse
import shutil

import ffmpeg

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
       
        zip_path: str = os.path.join(args.outputdir, soundpackdir)

        # Make a zip file of the soundpack directory
        shutil.make_archive(base_name=zip_path, format='zip', root_dir=soundpackdir_path)
        print(f"Created zip '{zip_path}'.zip from soundpack dir '{soundpackdir_path}'")

        # Make a preview audio file of the soundpack.
        # Github README.md only supports video embeds, so put the audio in a video container.
        preview_input_path: str = os.path.join(soundpackdir_path, "sounds/currency/chaos orb.mp3")
        preview_output_path: str = os.path.join(args.outputdir, soundpackdir + ".mp4")
        ffmpeg.input(preview_input_path).output(filename=preview_output_path).run(quiet=True, overwrite_output=True)
if __name__ == "__main__":
    sys.exit(main())