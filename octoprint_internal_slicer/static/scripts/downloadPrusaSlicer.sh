# This script is to download PrusaSlicer v2.7.2 on OctoPi OS and then install CPULimit to limit the CPU usage of PrusaSlicer

# Move to the home directory
cd /home/pi

# Create a folder for PrusaSlicer (if it doesn't already exist)
mkdir /home/pi/slicers

# Download PrusaSlicer
wget -P /home/pi/slicers https://github.com/Garr-R/PrusaSlicer-ARM.AppImage/releases/download/v2.7.2/PrusaSlicer-version_2.7.2-armhf.AppImage

# Change permissions to the PrusaSlicer program
chmod a+x /home/pi/slicers/PrusaSlicer-version_2.7.2-armhf.AppImage

# Download and install CPULimit
sudo apt-get -fqy install cpulimit

# Get the path to the user's Python3 site-packages directory
#site_packages=$(python3 -m site --user-site)

# Append the remaining path to the end of it
#path="$site_packages/octoprint_internal_slicer/static/installation"

#sudo dpkg -i $path/cpulimit_2.8-1_armhf.deb