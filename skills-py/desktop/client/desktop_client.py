"""
Desktop automation client using pynput for mouse and keyboard control.
"""

from __future__ import annotations

import base64
import io
import time
from typing import Any

try:
  from PIL import ImageGrab
  from pynput import keyboard, mouse  # type: ignore[import-untyped]
  from pynput.keyboard import Key
  from pynput.mouse import Button

  PYNPUT_AVAILABLE = True
except ImportError:
  PYNPUT_AVAILABLE = False
  # Create dummy classes for type checking when pynput is not available
  # Use different names to avoid redefinition errors
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
    from PIL import ImageGrab  # type: ignore[import-not-found]
    from pynput.keyboard import Key  # type: ignore[import-untyped]
    from pynput.mouse import Button  # type: ignore[import-untyped]
  else:
    # Runtime fallback classes
    class Button:  # type: ignore[no-redef]
      left = None
      right = None
      middle = None

    class Key:  # type: ignore[no-redef]
      enter = None
      esc = None
      tab = None
      space = None
      backspace = None
      delete = None
      up = None
      down = None
      left = None
      right = None
      ctrl = None
      alt = None
      shift = None
      cmd = None
      f1 = None
      f2 = None
      f3 = None
      f4 = None
      f5 = None
      f6 = None
      f7 = None
      f8 = None
      f9 = None
      f10 = None
      f11 = None
      f12 = None

    class ImageGrab:  # type: ignore[no-redef]
      @staticmethod
      def grab(*args: Any, **kwargs: Any) -> Any:  # noqa: ARG004
        raise ImportError("Pillow is not installed")


class DesktopClient:
  """Client for desktop automation using pynput."""

  def __init__(self) -> None:
    """Initialize the desktop client."""
    if not PYNPUT_AVAILABLE:
      raise ImportError(
        "pynput is not installed. Please install it with: pip install pynput Pillow"
      )
    self._mouse_controller = mouse.Controller()
    self._keyboard_controller = keyboard.Controller()

  # ---------------------------------------------------------------------------
  # Mouse Operations
  # ---------------------------------------------------------------------------

  def mouse_move(
    self, x: float, y: float, absolute: bool = True, duration: float = 0
  ) -> dict[str, Any]:
    """Move mouse cursor."""
    try:
      if absolute:
        if duration > 0:
          # Smooth movement
          current_x, current_y = self._mouse_controller.position
          steps = int(duration * 60)  # 60 steps per second
          if steps > 0:
            dx = (x - current_x) / steps
            dy = (y - current_y) / steps
            step_duration = duration / steps
            for _ in range(steps):
              current_x += dx
              current_y += dy
              self._mouse_controller.position = (int(current_x), int(current_y))
              time.sleep(step_duration)
          self._mouse_controller.position = (int(x), int(y))
        else:
          self._mouse_controller.position = (int(x), int(y))
      else:
        # Relative movement
        current_x, current_y = self._mouse_controller.position
        new_x = current_x + x
        new_y = current_y + y
        if duration > 0:
          steps = int(duration * 60)
          if steps > 0:
            dx = x / steps
            dy = y / steps
            step_duration = duration / steps
            for _ in range(steps):
              current_x += dx
              current_y += dy
              self._mouse_controller.position = (int(current_x), int(current_y))
              time.sleep(step_duration)
          self._mouse_controller.position = (int(new_x), int(new_y))
        else:
          self._mouse_controller.position = (int(new_x), int(new_y))

      return {"success": True, "position": self._mouse_controller.position}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def mouse_click(
    self,
    button: str = "left",
    clicks: int = 1,
    x: float | None = None,
    y: float | None = None,
    interval: float = 0.1,
  ) -> dict[str, Any]:
    """Click mouse button."""
    try:
      button_map = {"left": Button.left, "right": Button.right, "middle": Button.middle}
      btn = button_map.get(button, Button.left)

      if x is not None and y is not None:
        self._mouse_controller.position = (int(x), int(y))

      for _ in range(clicks):
        self._mouse_controller.click(btn, 1)
        if clicks > 1:
          time.sleep(interval)

      return {"success": True, "position": self._mouse_controller.position}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def mouse_press(self, button: str = "left") -> dict[str, Any]:
    """Press mouse button down."""
    try:
      button_map = {"left": Button.left, "right": Button.right, "middle": Button.middle}
      btn = button_map.get(button, Button.left)
      self._mouse_controller.press(btn)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def mouse_release(self, button: str = "left") -> dict[str, Any]:
    """Release mouse button."""
    try:
      button_map = {"left": Button.left, "right": Button.right, "middle": Button.middle}
      btn = button_map.get(button, Button.left)
      self._mouse_controller.release(btn)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def mouse_scroll(
    self, dx: float = 0, dy: float = 0, x: float | None = None, y: float | None = None
  ) -> dict[str, Any]:
    """Scroll mouse wheel."""
    try:
      if x is not None and y is not None:
        self._mouse_controller.position = (int(x), int(y))

      self._mouse_controller.scroll(int(dx), int(dy))
      return {"success": True, "position": self._mouse_controller.position}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def mouse_drag(
    self,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    button: str = "left",
    duration: float = 0.5,
  ) -> dict[str, Any]:
    """Drag mouse from one position to another."""
    try:
      button_map = {"left": Button.left, "right": Button.right, "middle": Button.middle}
      btn = button_map.get(button, Button.left)

      # Move to start position
      self._mouse_controller.position = (int(x1), int(y1))
      time.sleep(0.1)

      # Press button
      self._mouse_controller.press(btn)

      # Drag to end position
      steps = int(duration * 60)
      if steps > 0:
        dx = (x2 - x1) / steps
        dy = (y2 - y1) / steps
        step_duration = duration / steps
        current_x, current_y = x1, y1
        for _ in range(steps):
          current_x += dx
          current_y += dy
          self._mouse_controller.position = (int(current_x), int(current_y))
          time.sleep(step_duration)
      self._mouse_controller.position = (int(x2), int(y2))

      # Release button
      time.sleep(0.1)
      self._mouse_controller.release(btn)

      return {"success": True, "position": self._mouse_controller.position}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def mouse_position(self) -> dict[str, Any]:
    """Get current mouse position."""
    try:
      pos = self._mouse_controller.position
      return {"success": True, "x": pos[0], "y": pos[1]}
    except Exception as e:
      return {"success": False, "error": str(e)}

  # ---------------------------------------------------------------------------
  # Keyboard Operations
  # ---------------------------------------------------------------------------

  def _parse_key(self, key_str: str) -> Key | str:
    """Parse key string to pynput Key or character."""
    key_map = {
      "enter": Key.enter,
      "esc": Key.esc,
      "escape": Key.esc,
      "tab": Key.tab,
      "space": Key.space,
      "backspace": Key.backspace,
      "delete": Key.delete,
      "up": Key.up,
      "down": Key.down,
      "left": Key.left,
      "right": Key.right,
      "ctrl": Key.ctrl,
      "control": Key.ctrl,
      "alt": Key.alt,
      "shift": Key.shift,
      "cmd": Key.cmd,
      "command": Key.cmd,
      "f1": Key.f1,
      "f2": Key.f2,
      "f3": Key.f3,
      "f4": Key.f4,
      "f5": Key.f5,
      "f6": Key.f6,
      "f7": Key.f7,
      "f8": Key.f8,
      "f9": Key.f9,
      "f10": Key.f10,
      "f11": Key.f11,
      "f12": Key.f12,
    }

    key_lower = key_str.lower()
    if key_lower in key_map:
      return key_map[key_lower]

    # Return as-is for regular characters
    return key_str

  def keyboard_type(self, text: str, interval: float = 0.05) -> dict[str, Any]:
    """Type text character by character."""
    try:
      for char in text:
        self._keyboard_controller.type(char)
        if interval > 0:
          time.sleep(interval)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def keyboard_press(self, key: str) -> dict[str, Any]:
    """Press keyboard key."""
    try:
      parsed_key = self._parse_key(key)
      self._keyboard_controller.press(parsed_key)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def keyboard_release(self, key: str) -> dict[str, Any]:
    """Release keyboard key."""
    try:
      parsed_key = self._parse_key(key)
      self._keyboard_controller.release(parsed_key)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def keyboard_tap(self, key: str) -> dict[str, Any]:
    """Tap keyboard key (press and release)."""
    try:
      parsed_key = self._parse_key(key)
      self._keyboard_controller.tap(parsed_key)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def keyboard_hotkey(self, keys: list[str]) -> dict[str, Any]:
    """Press combination of keys."""
    try:
      parsed_keys = [self._parse_key(k) for k in keys]
      self._keyboard_controller.press(*parsed_keys)
      time.sleep(0.05)
      self._keyboard_controller.release(*parsed_keys)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def keyboard_write(self, text: str) -> dict[str, Any]:
    """Write text instantly."""
    try:
      self._keyboard_controller.type(text)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  # ---------------------------------------------------------------------------
  # Screen Operations
  # ---------------------------------------------------------------------------

  def screen_capture(
    self,
    x: float | None = None,
    y: float | None = None,
    width: float | None = None,
    height: float | None = None,
    save_path: str | None = None,
  ) -> dict[str, Any]:
    """Capture screenshot."""
    try:
      if x is not None and y is not None and width is not None and height is not None:
        bbox = (int(x), int(y), int(x + width), int(y + height))
        img = ImageGrab.grab(bbox=bbox)
      else:
        img = ImageGrab.grab()

      if save_path:
        img.save(save_path)
        return {"success": True, "path": save_path}
      else:
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        return {"success": True, "image": f"data:image/png;base64,{img_base64}"}
    except Exception as e:
      return {"success": False, "error": str(e)}

  def screen_size(self) -> dict[str, Any]:
    """Get screen size."""
    try:
      img = ImageGrab.grab()
      width, height = img.size
      return {"success": True, "width": width, "height": height}
    except Exception as e:
      return {"success": False, "error": str(e)}

  # ---------------------------------------------------------------------------
  # Utility Operations
  # ---------------------------------------------------------------------------

  def wait(self, seconds: float) -> dict[str, Any]:
    """Wait for specified duration."""
    try:
      time.sleep(seconds)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}
