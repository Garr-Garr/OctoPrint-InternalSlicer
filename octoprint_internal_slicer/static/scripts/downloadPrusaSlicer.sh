# This script is to download PrusaSlicer v2.6.1 on OctoPi OS and then install CPULimit to limit the CPU usage of PrusaSlicer

# Move to the home directory
cd $HOME

# Create a folder for PrusaSlicer (if it doesn't already exist)
mkdir $HOME/slicers

# Download PrusaSlicer
wget -P $HOME/slicers https://github.com/Garr-Garr/PrusaSlicer-ARM.AppImage/releases/download/v2.6.1/PrusaSlicer-version_2.6.1-armhf.AppImage

# Change permissions to the PrusaSlicer program
chmod a+x $HOME/slicers/PrusaSlicer-version_2.6.1-armhf.AppImage

# Download and install CPULimit
#sudo apt-get -fqy install cpulimit

# Get the path to the user's Python3 site-packages directory
#site_packages=$(python3 -m site --user-site)

# Append the remaining path to the end of it
#path="$site_packages/octoprint_internal_slicer/static/installation"

#sudo dpkg -i $path/cpulimit_2.8-1_armhf.deb

### Steps for Debian bookworm & the latest version of PrusaSlicer
### (for manual entry)
### Tested using:
### 2024-03-14_2024-03-12-octopi-bookworm-armhf-lite-1.1.0

#cd $HOME
#mkdir $HOME/slicers
#wget -P $HOME/slicers https://github.com/Garr-Garr/PrusaSlicer-ARM.AppImage/releases/download/v2.7.2/PrusaSlicer-version_2.7.2-armhf.AppImage
#chmod a+x $HOME/slicers/PrusaSlicer-version_2.7.2-armhf.AppImage

#sudo apt-get install -y git cmake libboost-dev libboost-regex-dev libboost-filesystem-dev \
#libboost-thread-dev libboost-log-dev libboost-locale-dev libcurl4-openssl-dev build-essential \
#pkg-config libtbb-dev zlib1g-dev libcereal-dev libeigen3-dev libnlopt-cxx-dev \
#libudev-dev libopenvdb-dev libboost-iostreams-dev libgmpxx4ldbl libnlopt-dev \
#libdbus-1-dev imagemagick libgtk2.0-dev libgtk-3-dev libwxgtk3.0-gtk3-dev fuse libfuse2