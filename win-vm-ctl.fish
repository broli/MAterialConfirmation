#!/usr/bin/env fish
# Toggle libvirt and network daemons for the Windows deployment VM

# Internal Help Function
function _show_help
    echo "Usage: ./win-vm-ctl.fish [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start   - Enable background services for the Windows VM"
    echo "  stop    - Disable the Windows VM environment to free up resources"
    echo "  toggle  - (Default) Toggle the services on or off depending on current state"
    echo "  help    - Show this help message"
    echo ""
end

# Parse arguments
set -l action "toggle"
if test (count $argv) -gt 0
    switch $argv[1]
        case "start"
            set action "start"
        case "stop"
            set action "stop"
        case "toggle"
            set action "toggle"
        case "help" "-h" "--help"
            _show_help
            return 0
        case "*"
            echo "Error: Unknown argument '$argv[1]'"
            _show_help
            return 1
    end
end

# Determine current state
set -l is_running 0
if systemctl is-active --quiet libvirtd.service; or systemctl is-active --quiet virtqemud.service
    set is_running 1
end

# Resolve "toggle" action to either "start" or "stop"
if test "$action" = "toggle"
    if test $is_running -eq 1
        set action "stop"
    else
        set action "start"
    end
end

# Execute the requested action
if test "$action" = "stop"
    if test $is_running -eq 0
        echo "Services are already stopped."
        return 0
    end
    
    echo "=================================================="
    echo "Disabling Windows VM environment to free up resources..."
    echo "=================================================="
    
    # Stop daemons and their associated systemd sockets
    sudo systemctl stop libvirtd.service libvirtd.socket libvirtd-ro.socket libvirtd-admin.socket 2>/dev/null
    sudo systemctl stop virtqemud.service virtqemud.socket virtqemud-ro.socket virtqemud-admin.socket 2>/dev/null
    sudo systemctl stop virtnetworkd.service virtnetworkd.socket 2>/dev/null
    
    # Clean up the virtual network bridge if it exists
    if ip link show virbr0 >/dev/null 2>&1
        echo "Removing virtual network bridge (virbr0)..."
        sudo ip link set dev virbr0 down
        sudo ip link delete virbr0
    end
    
    echo "✓ Windows deployment background services terminated successfully."
    
else if test "$action" = "start"
    if test $is_running -eq 1
        echo "Services are already running."
        return 0
    end
    
    echo "=================================================="
    echo "Enabling background services for Windows VM deployment..."
    echo "=================================================="
    
    # Start the relevant daemons
    # This safely attempts to start traditional monolithic libvirtd or modular daemons
    sudo systemctl start libvirtd.service 2>/dev/null
    sudo systemctl start virtqemud.service virtnetworkd.service 2>/dev/null
    
    echo "✓ Libvirt services are now active."
    echo "✓ Ready to launch Windows deployment environment."
end