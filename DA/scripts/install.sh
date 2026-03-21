#!/bin/bash
# Install DeepAgents - makes 'da' available system-wide
set -e

DA_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Create/update venv
if [ ! -d "$DA_DIR/.venv" ]; then
    python3 -m venv "$DA_DIR/.venv"
fi

"$DA_DIR/.venv/bin/pip" install -e "$DA_DIR" -q

# Create symlink in ~/bin
mkdir -p "$HOME/bin"
cat > "$HOME/bin/da" << EOF
#!/bin/bash
exec "$DA_DIR/.venv/bin/da" "\$@"
EOF
chmod +x "$HOME/bin/da"

# Create ~/.da directory
mkdir -p "$HOME/.da"

# Copy config if not exists
if [ ! -f "$HOME/.da/config.yaml" ]; then
    cp "$DA_DIR/config.yaml" "$HOME/.da/config.yaml"
fi

echo "DeepAgents installed."
echo "  Binary: ~/bin/da"
echo "  Config: ~/.da/config.yaml"
echo "  Ensure ~/bin is in your PATH"
