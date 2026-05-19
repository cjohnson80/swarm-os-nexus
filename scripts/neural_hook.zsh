# Neural Shell Hook for Swarm OS
# Source this file in your ~/.zshrc

command_not_found_handler() {
    local cmd="$1"
    shift
    local args=("$@")
    
    # Run the default behavior or just print an error
    echo "zsh: command not found: $cmd"
    
    # Trigger the Neural Shell to suggest a fix
    /home/chrisj/.native-agent/venv/bin/python3 /home/chrisj/.native-agent/scripts/neural_shell.py "$cmd ${args[*]}"
    
    # Return 127 as per standard command not found
    return 127
}
