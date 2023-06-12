# This script is to download PrusaSlicer on OctoPi OS

# Move to the home directory
cd /home/pi

# Create a folder for PrusaSlicer
mkdir /home/pi/PrusaSlicer-2.4.2

# Download PrusaSlicer
wget https://github.com/prusa3d/PrusaSlicer/releases/download/version_2.4.2/PrusaSlicer-2.4.2+linux-armv7l-GTK2-202204251109.tar.bz2

# Extract PrusaSlicer
tar -xvf PrusaSlicer-2.4.2+linux-armv7l-GTK2-202204251109.tar.bz2 -C /home/pi/PrusaSlicer-2.4.2 --strip-components=1

# Remove the downloaded file
rm PrusaSlicer-2.4.2+linux-armv7l-GTK2-202204251109.tar.bz2

# Change permissions to the PrusaSlicer program
chmod a+x /home/pi/PrusaSlicer-2.4.2/prusa-slicer

# Notify the user that PrusaSlicer has been installed
echo ".........................................."
echo ".........................................."
echo ".........................................."
echo ".........................................."
echo "PrusaSlicer has been installed!"