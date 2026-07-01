#!/usr/bin/env fish

# Create the local windows_build directory if it doesn't exist
mkdir -p "/home/carlos/Projects/Antigravity/MAterialConfirmation/windows_build"

echo "Pulling the compiled Windows executable from the VM..."

# Use SCP to copy the .exe directly from the VM's dist folder into the local windows_build folder
scp work@192.168.122.216:"C:/Users/Work/Documents/GitHub/MAterialConfirmation/dist/*.exe" "/home/carlos/Projects/Antigravity/MAterialConfirmation/windows_build/"

echo "Successfully pulled the executable! It is now located in your local windows_build/ directory."
