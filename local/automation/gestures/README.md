# 🖐️🤚 JARVIS Gesture Controller (Normal & Zoom Modes)

An AI-powered desktop hand gesture controller that tracks **both hands in real-time** via webcam and features a dedicated, isolated **Zoom Mode State Machine**.

---

## 🏗️ System Architecture & Modes

```text
                 JARVIS GESTURE CONTROLLER
                          │
             ┌────────────┴────────────┐
             ↓                         ↓
        NORMAL MODE                ZOOM MODE
             │                         │
       ┌─────┴─────┐              Distance only
       ↓           ↓                    │
    LEFT HAND   RIGHT HAND              ↓
    Navigation   Actions            Zoom In/Out
```

### 1. 🔍 ZOOM MODE Lifecycle
```text
👐 Both palms open
       ↓
Hold for 0.5 sec
       ↓
🔍 ZOOM MODE ACTIVATED
       ↓
Hands apart  → Zoom In  (Ctrl + Wheel Up)
Hands closer → Zoom Out (Ctrl + Wheel Down)
       ↓
✊ Close either hand (Fist)
       ↓
ZOOM MODE OFF (Returns to NORMAL MODE)
```

---

## 🎮 Control Map

### 🖐️ Left Hand — Navigation (Normal Mode)
| Gesture | Action | Description |
|---|---|---|
| ☝️ **Index Finger** | **Move Cursor** | Point and move your left index finger to navigate the mouse cursor smoothly. |
| ✊ **Closed Fist** | **Stop Cursor** | Make a fist to immediately freeze the cursor in place. |
| 👍 **Thumb Up** | **Scroll Up** | Point thumb up (other fingers curled) to scroll up smoothly. |
| 👎 **Thumb Down** | **Scroll Down** | Point thumb down (other fingers curled) to scroll down smoothly. |

### 🤚 Right Hand — Mouse Actions (Normal Mode)
| Gesture | Action | Description |
|---|---|---|
| 🤏 **Thumb + Index Pinch** | **Left Click** | Quick pinch tap ($\le$ 350ms) performs a left click with click protection. |
| 🤏 **Hold Pinch** | **Drag & Drop** | Hold pinch ($\ge$ 350ms) to grab/hold the mouse button; release pinch or open palm to drop. |
| 🤏🤏 **Double Pinch** | **Double Click** | Pinch twice in quick succession to double click. |
| ✌️ **Index + Middle Up** | **Right Click** | Show two fingers (peace sign) to perform a right click. |
| ✋ **Open Palm** | **Release / Stop** | Release any active drag or click operation. |

### 🔍 Zoom Mode
- **Activation**: Open both palms facing the camera and hold for **0.5 seconds**. The HUD shows a live progress bar.
- **In Zoom Mode**:
  - All mouse movements and clicks are suspended.
  - ↔️ **Move hands apart**: Zoom In.
  - ↔️ **Move hands closer**: Zoom Out.
- **Deactivation**: Close either hand into a fist (✊) to immediately return to Normal Mode.

---

## 🚀 Quick Start

1. **Activate Virtual Environment:**
   ```powershell
   .\venv\Scripts\activate
   ```

2. **Run Controller:**
   ```powershell
   python main.py
   ```

3. **Run Unit Tests:**
   ```powershell
   python test_gestures.py
   ```

---

## ⌨️ Hotkeys

While the camera feed window is active:
- `Q` or `ESC`: Quit application cleanly.
- `P`: Toggle manual pause/unpause.
- `D`: Toggle debug overlay.
