#!/usr/bin/env fish
# Toggle libvirt and network daemons for the Windows deployment VM

# Internal Help Function
function _show_help
    echo "Usage: ./win-vm-ctl.fish [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start   - Enable background services for the Windows VM"
    echo "  stop    - Disable the Windows VM environment to free up resources"
    echo "  toggle  - Toggle the services on or off depending on current state"
    echo "  status  - (Default) Show status of services and networks"
    echo "  help    - Show this help message"
    echo ""
end

# Parse arguments
set -l action "status"
if test (count $argv) -gt 0
    switch $argv[1]
        case "start"
            set action "start"
        case "stop"
            set action "stop"
        case "toggle"
            set action "toggle"
        case "status"
            set action "status"
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
    
    # Stop the default network cleanly via virsh if it is running
    sudo virsh net-destroy default >/dev/null 2>&1
    
    # Stop daemons and their associated systemd sockets
    sudo systemctl stop libvirtd.service libvirtd.socket libvirtd-ro.socket libvirtd-admin.socket 2>/dev/null
    sudo systemctl stop virtqemud.service virtqemud.socket virtqemud-ro.socket virtqemud-admin.socket 2>/dev/null
    sudo systemctl stop virtnetworkd.service virtnetworkd.socket 2>/dev/null
    
    # Clean up the virtual network bridge if it exists (fallback)
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
    
    # Start the default network cleanly
    sudo virsh net-start default >/dev/null 2>&1
    
    echo "✓ Libvirt services are now active."
    echo "✓ Ready to launch Windows deployment environment."
    
else if test "$action" = "status"
    echo "=================================================="
    echo "Windows VM Environment Status"
    echo "=================================================="
    
    set -l libvirtd_status (systemctl is-active libvirtd.service 2>/dev/null; or echo "inactive")
    set -l virtqemud_status (systemctl is-active virtqemud.service 2>/dev/null; or echo "inactive")
    set -l virtnetworkd_status (systemctl is-active virtnetworkd.service 2>/dev/null; or echo "inactive")
    
    echo "Services:"
    echo "  libvirtd.service:     $libvirtd_status"
    echo "  virtqemud.service:    $virtqemud_status"
    echo "  virtnetworkd.service: $virtnetworkd_status"
    
    echo ""
    echo "Networks:"
    if test $virtnetworkd_status = "active"; or test $libvirtd_status = "active"
        # Run sudo virsh to avoid requiring a separate password if they already ran with sudo
        sudo virsh net-list --all 2>/dev/null; or echo "  (Permission denied or libvirtd error)"
    else
        echo "  (Libvirt services are not running)"
    end
end