# Desktop Automation Skill

Desktop automation skill for controlling mouse and keyboard to autonomously navigate and interact with the desktop, applications, and windows.

## Features

### Mouse Control

- **Move**: Move cursor to absolute or relative coordinates with optional smooth movement
- **Click**: Click at current position or specified coordinates (left, right, middle)
- **Press/Release**: Press or release mouse buttons independently
- **Scroll**: Scroll vertically or horizontally at current or specified position
- **Drag**: Drag mouse from one position to another while holding a button
- **Position**: Get current mouse cursor position

### Keyboard Control

- **Type**: Type text character by character (simulates real typing)
- **Write**: Write text instantly (faster but less realistic)
- **Press/Release**: Press or release keys independently
- **Tap**: Press and release a key in one action
- **Hotkey**: Press combination of keys simultaneously (e.g., Ctrl+C, Alt+Tab)

### Screen Operations

- **Capture**: Take screenshots of entire screen or specific regions
- **Size**: Get screen resolution/dimensions

### Utility

- **Wait**: Wait for specified duration (useful for timing automation)

## Tools

### Mouse Tools

#### `mouse_move`

Move the mouse cursor to absolute coordinates or relative to current position.

**Parameters:**

- `x` (number, required): X coordinate
- `y` (number, required): Y coordinate
- `absolute` (boolean, default: true): Whether coordinates are absolute (screen coordinates) or relative
- `duration` (number, default: 0): Duration of movement in seconds (for smooth movement)

#### `mouse_click`

Click the mouse button at current position or specified coordinates.

**Parameters:**

- `button` (string, default: "left"): Mouse button ("left", "right", "middle")
- `clicks` (number, default: 1): Number of clicks
- `x` (number, optional): X coordinate to click at
- `y` (number, optional): Y coordinate to click at
- `interval` (number, default: 0.1): Interval between clicks in seconds

#### `mouse_press`

Press down a mouse button (without releasing).

**Parameters:**

- `button` (string, default: "left"): Mouse button to press

#### `mouse_release`

Release a mouse button.

**Parameters:**

- `button` (string, default: "left"): Mouse button to release

#### `mouse_scroll`

Scroll the mouse wheel vertically or horizontally.

**Parameters:**

- `dx` (number, default: 0): Horizontal scroll amount (positive = right, negative = left)
- `dy` (number, default: 0): Vertical scroll amount (positive = up, negative = down)
- `x` (number, optional): X coordinate to scroll at
- `y` (number, optional): Y coordinate to scroll at

#### `mouse_drag`

Drag the mouse from one position to another while holding a button.

**Parameters:**

- `x1` (number, required): Starting X coordinate
- `y1` (number, required): Starting Y coordinate
- `x2` (number, required): Ending X coordinate
- `y2` (number, required): Ending Y coordinate
- `button` (string, default: "left"): Mouse button to hold during drag
- `duration` (number, default: 0.5): Duration of drag in seconds

#### `mouse_position`

Get the current mouse cursor position.

**Parameters:** None

### Keyboard Tools

#### `keyboard_type`

Type text character by character (simulates real typing).

**Parameters:**

- `text` (string, required): Text to type
- `interval` (number, default: 0.05): Interval between keystrokes in seconds

#### `keyboard_write`

Write text instantly (faster than type, but less realistic).

**Parameters:**

- `text` (string, required): Text to write

#### `keyboard_press`

Press a keyboard key (without releasing).

**Parameters:**

- `key` (string, required): Key to press (e.g., "a", "enter", "ctrl", "shift", "alt", "space", "tab", "esc", "backspace", "delete", "up", "down", "left", "right", "f1"-"f12")

#### `keyboard_release`

Release a keyboard key.

**Parameters:**

- `key` (string, required): Key to release

#### `keyboard_tap`

Press and release a keyboard key (single key press).

**Parameters:**

- `key` (string, required): Key to tap

#### `keyboard_hotkey`

Press a combination of keys simultaneously (e.g., Ctrl+C, Alt+Tab).

**Parameters:**

- `keys` (array of strings, required): List of keys to press simultaneously (e.g., ["ctrl", "c"] for Ctrl+C)

### Screen Tools

#### `screen_capture`

Capture a screenshot of the entire screen or a specific region.

**Parameters:**

- `x` (number, optional): Left coordinate of region to capture
- `y` (number, optional): Top coordinate of region to capture
- `width` (number, optional): Width of region to capture
- `height` (number, optional): Height of region to capture
- `save_path` (string, optional): File path to save screenshot (returns base64 if omitted)

#### `screen_size`

Get the screen size (resolution).

**Parameters:** None

### Utility Tools

#### `wait`

Wait for a specified duration (useful for timing automation).

**Parameters:**

- `seconds` (number, required): Number of seconds to wait

## Examples

### Basic Mouse Movement and Click

```python
# Move mouse to coordinates (100, 200)
mouse_move(x=100, y=200, absolute=True)

# Click at current position
mouse_click(button="left", clicks=1)

# Click at specific coordinates
mouse_click(button="left", x=500, y=300, clicks=2)
```

### Keyboard Typing

```python
# Type text character by character
keyboard_type(text="Hello, World!", interval=0.05)

# Write text instantly
keyboard_write(text="Quick text")

# Press hotkey (Ctrl+C)
keyboard_hotkey(keys=["ctrl", "c"])

# Press Enter
keyboard_tap(key="enter")
```

### Screen Capture

```python
# Capture full screen
screen_capture()

# Capture specific region
screen_capture(x=100, y=100, width=800, height=600)

# Save screenshot to file
screen_capture(save_path="/path/to/screenshot.png")
```

### Complex Automation Flow

```python
# Get screen size
screen_size()

# Move mouse smoothly
mouse_move(x=500, y=300, absolute=True, duration=0.5)

# Click
mouse_click(button="left")

# Type text
keyboard_type(text="Search query", interval=0.05)

# Press Enter
keyboard_tap(key="enter")

# Wait for page to load
wait(seconds=2)

# Take screenshot
screen_capture(save_path="/path/to/result.png")
```

## Dependencies

- `pynput>=1.7.6` - Cross-platform mouse and keyboard control
- `Pillow>=10.0.0` - Image processing for screenshots
- `mcp>=1.0.0` - Model Context Protocol support
- `pydantic>=2.0` - Data validation

## Platform Support

This skill uses `pynput` which supports:

- Windows
- macOS
- Linux (X11)

**Note**: On Linux, you may need to install additional dependencies:

- `python3-xlib` (for X11)
- Appropriate permissions for input device access

## Security Considerations

This skill provides full control over mouse and keyboard input. Use with caution:

- Only enable this skill in trusted environments
- Be aware that automation can interact with any application
- Consider using this skill in a controlled environment or sandbox
- Some applications may detect and block automation

## License

Part of the AlphaHuman Skills ecosystem.
