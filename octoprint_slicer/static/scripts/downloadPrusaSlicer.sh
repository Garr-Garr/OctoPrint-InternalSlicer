# This script is to download PrusaSlicer on OctoPi OS

# Move to the home directory
cd $HOME

# Create a folder for PrusaSlicer
mkdir $HOME/PrusaSlicer-2.7.1

# Download PrusaSlicer
wget https://github.com/prusa3d/PrusaSlicer/releases/download/version_2.7.1/PrusaSlicer-2.7.1+linux-armv7l-GTK2-202312121430.tar.bz2

# Extract PrusaSlicer
tar -xvf PrusaSlicer-2.7.1+linux-armv7l-GTK2-202312121430.tar.bz2 -C $HOME/PrusaSlicer-2.7.1 --strip-components=1

# Remove the downloaded file
rm PrusaSlicer-2.7.1+linux-armv7l-GTK2-202312121430.tar.bz2

# Change permissions to the PrusaSlicer program
chmod a+x $HOME/PrusaSlicer-2.7.1/prusa-slicer
