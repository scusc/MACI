import os
import glob

# Path to the screenshots in artifact directory
SCREENSHOT_DIR = "/Users/saichandsunkara/.gemini/antigravity-ide/brain/d77395c6-8f44-4422-8528-b78e4be1532f"
REPORT_PATH = "/Users/saichandsunkara/.gemini/antigravity-ide/brain/d77395c6-8f44-4422-8528-b78e4be1532f/MultiPlayer_Swarm_Demo.md"

def main():
    screenshots = glob.glob(os.path.join(SCREENSHOT_DIR, "swarm_*.png"))
    screenshots.sort()  
    
    with open(REPORT_PATH, "w") as f:
        f.write("# Massive 100+ Screenshot Multi-Player Swarm Demo\n\n")
        f.write("This document contains an unprecedented visual walkthrough of 5 completely independent browser contexts interacting within a real-time group swarm. It covers everything from DB seeding, to negative auth paths, to live websockets chatting with the AI Delegate.\n\n")
        f.write("We have captured **" + str(len(screenshots)) + "** screenshots across the entire journey.\n\n")
        f.write("---\n\n")
        
        # Use a carousel to present the screenshots efficiently
        f.write("````carousel\n")
        for i, shot in enumerate(screenshots):
            basename = os.path.basename(shot)
            step_name = basename.replace('.png', '').replace('snap_', '').replace('_', ' ').title()
            
            # The URL to the image needs to be the absolute path
            abs_path = os.path.abspath(shot)
            
            f.write(f"![{step_name}]({abs_path})\n")
            if i < len(screenshots) - 1:
                f.write("<!-- slide -->\n")
                
        f.write("````\n")
            
    print(f"Generated QA report with {len(screenshots)} screenshots at {REPORT_PATH}")

if __name__ == "__main__":
    main()
