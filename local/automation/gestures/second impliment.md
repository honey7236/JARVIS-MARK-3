# 🖐️🤚 Two-Hand Gesture Mouse Controller

A futuristic **AI-powered, camera-based hand gesture mouse controller** that allows users to control their computer without a physical mouse.

The system uses a webcam to track **both hands in real time**, recognize gestures, and translate hand movements into mouse and zoom actions.

---

## ✨ Features

- 🖱️ Move the mouse using your hand
- 🖱️ Left click
- 🖱️ Right click
- 🖱️ Double click
- ✋ Drag and drop
- 🔄 Scroll up and down
- 🔍 Two-hand zoom in/out
- 🎯 Cursor smoothing
- 🛡️ Gesture confirmation to prevent accidental actions
- ⏱️ Gesture cooldown to prevent repeated clicks
- 👐 Independent two-hand controls
- ⚡ Real-time webcam processing

---

# 🖐️ Hand Gesture Controls

The system divides responsibilities between the **left hand**, **right hand**, and **both hands**.

---

## 🖐️ Left Hand — Navigation

| Gesture | Action |
|---|---|
| ☝️ Index Finger | Move Mouse Cursor |
| ✊ Closed Fist | Stop Cursor |
| 👍 Thumb Up | Scroll Up |
| 👎 Thumb Down | Scroll Down |

The left hand is primarily responsible for **navigation and cursor movement**.

---

## 🤚 Right Hand — Mouse Actions

| Gesture | Action |
|---|---|
| 🤏 Thumb + Index Pinch | Left Click |
| 🤏 Hold Pinch | Drag |
| ✌️ Index + Middle Finger | Right Click |
| 🤏 Double Pinch | Double Click |
| ✋ Open Palm | Release / Stop |

The right hand handles the main **mouse actions**.

---

# 👐 Two-Hand Zoom Control

Both hands can be used together for a natural **zoom in / zoom out** experience.

The system calculates the distance between the **left-hand and right-hand palm centers**.

### 🔍 Zoom In

Move both hands **away from each other**.

```text
👐  ←────────────→  👐
       HANDS AWAY
           ↓
       🔍 ZOOM IN
```

### 🔎 Zoom Out

Move both hands **towards each other**.

```text
👐  ────────────→  👐
       HANDS CLOSE
           ↓
       🔎 ZOOM OUT
```

### Zoom Logic

```text
          BOTH HANDS
              ↓
       Detect hand centers
              ↓
     Calculate hand distance
              ↓
       Compare with baseline
              ↓
      ┌───────┴───────┐
      ↓               ↓
 Distance ↑       Distance ↓
      ↓               ↓
  ZOOM IN         ZOOM OUT
```

A **dead zone / threshold** is used to ignore small movements and prevent accidental zooming.

---

# 🧠 Gesture Processing

To make the system reliable, gestures are not triggered from a single frame.

The controller uses:

### 🎯 Cursor Smoothing

Smooths hand movement before sending coordinates to the operating system.

```text
Raw Hand Position
       ↓
Smoothing Filter
       ↓
Stable Coordinates
       ↓
Mouse Cursor
```

### 🛡️ Gesture Confirmation

Important actions such as clicking require the gesture to remain detected for a short period before execution.

```text
Gesture Detected
       ↓
Confirmation Delay
       ↓
Gesture Still Valid?
       ↓
      YES
       ↓
Execute Action
```

### ⏱️ Gesture Cooldown

After an action is performed, a short cooldown prevents the same gesture from triggering multiple times.

---

# 🖱️ Click Protection

Clicking does **not** immediately move the cursor.

For example, when a pinch is detected:

```text
🤏 Pinch
   ↓
Freeze Cursor
   ↓
Confirm Pinch
   ↓
Left Click
   ↓
Unlock Cursor
```

This prevents the cursor from jumping when the user performs a click.

---

# ✊ Drag & Drop

Dragging is controlled using a **held pinch**.

```text
🤏 Pinch
   ↓
Hold Pinch
   ↓
Mouse Button DOWN
   ↓
Move Hand
   ↓
Object Follows Cursor
   ↓
Release Pinch
   ↓
Mouse Button UP
```

---

# 🏗️ System Architecture

```text
                    WEBCAM
                       │
                       ▼
              ┌─────────────────┐
              │     OpenCV      │
              │ Camera Capture  │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    MediaPipe    │
              │  Hand Tracking  │
              └────────┬────────┘
                       │
                ┌──────┴──────┐
                │             │
                ▼             ▼
          🖐️ LEFT HAND   🤚 RIGHT HAND
          Navigation        Actions
                │             │
                ▼             ▼
          Cursor Engine   Gesture Engine
                │             │
                └──────┬──────┘
                       │
                       ▼
                👐 TWO-HAND MODE
                       │
                       ▼
                 Zoom Engine
                       │
                       ▼
                ┌──────────────┐
                │ Mouse / Zoom │
                │   Controller │
                └──────┬───────┘
                       │
                       ▼
                   WINDOWS
```

---

# 🛠️ Technologies

| Technology | Purpose |
|---|---|
| **Python** | Core programming language |
| **OpenCV** | Webcam and image processing |
| **MediaPipe** | Hand landmark detection |
| **PyAutoGUI** | Mouse and keyboard automation |
| **NumPy** | Mathematical calculations |

---

# 📦 Installation

Clone the repository:

```bash
git clone <your-repository-url>
cd <project-folder>
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# ▶️ Run

Start the application:

```bash
python main.py
```

Make sure your webcam is connected and accessible.

---

# 🎮 Control Summary

```text
┌─────────────────────────────────────────┐
│             GESTURE CONTROLS            │
├─────────────────────────────────────────┤
│                                         │
│ 🖐️ LEFT HAND                           │
│ ☝️  Index        → Move Cursor          │
│ ✊  Fist         → Stop Cursor          │
│ 👍  Thumb Up     → Scroll Up            │
│ 👎  Thumb Down   → Scroll Down          │
│                                         │
│ 🤚 RIGHT HAND                           │
│ 🤏  Pinch        → Left Click           │
│ 🤏  Hold         → Drag                 │
│ ✌️  Two Fingers  → Right Click          │
│ 🤏  Double Pinch → Double Click         │
│ ✋  Open Palm     → Release / Stop      │
│                                         │
│ 👐 BOTH HANDS                           │
│ ↔️  Hands Away   → Zoom In              │
│ ↔️  Hands Close  → Zoom Out             │
│                                         │
└─────────────────────────────────────────┘
```

---

# 🚀 Future Improvements

- 🎤 Voice + gesture hybrid control
- 🤖 AI-based custom gesture recognition
- 🖥️ Multi-monitor support
- 🎚️ Adjustable gesture sensitivity
- ⚡ Adaptive cursor acceleration
- 🔊 Gesture-based volume control
- 🪟 Gesture-based window switching
- 📸 Screenshot gesture
- 🎵 Gesture-based media controls
- 🧠 Personalized gesture profiles
- 🟦 JARVIS holographic HUD integration
- 🔐 User-specific gesture authentication

---

# 🤖 JARVIS Mark 3 Integration

This gesture controller is designed as a module for **JARVIS Mark 3**, allowing the AI assistant to interact with the computer through a combination of:

```text
           JARVIS MARK 3
                 │
        ┌────────┼────────┐
        ↓        ↓        ↓
      VOICE    GESTURE    AI
        │        │        │
        └────────┼────────┘
                 ↓
          COMPUTER CONTROL
```

The ultimate goal is to create a **natural, hands-free and futuristic computer interface** inspired by the JARVIS interface from Iron Man.

---

## 📌 Project Status

**Status:** 🚧 In Development

**Platform:** Windows

**Input:** Webcam + Two Hands

**Control Type:** Contactless / Gesture-Based

---

## ⭐ Vision

> **"Control your computer naturally — without touching it."**

Built as part of **JARVIS Mark 3**.