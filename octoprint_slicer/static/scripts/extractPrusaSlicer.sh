# This script is to download PrusaSlicer on OctoPi OS

# Move to the home directory
cd /home/pi

# Create a folder for PrusaSlicer
mkdir /home/pi/PrusaSlicer-2.4.2

# Extract PrusaSlicer
tar -xvf /home/pi/oprint/lib/python3.7/site-packages/octoprint_slicer/static/slicer/PrusaSlicer-2.4.2+linux-armv7l-GTK2-202204251109.tar.bz2 -C /home/pi/PrusaSlicer-2.4.2 --strip-components=1

# Remove the downloaded file
rm /home/pi/oprint/lib/python3.7/site-packages/octoprint_slicer/static/slicer/PrusaSlicer-2.4.2+linux-armv7l-GTK2-202204251109.tar.bz2

# Change permissions to the PrusaSlicer program
chmod a+x /home/pi/PrusaSlicer-2.4.2/prusa-slicer
