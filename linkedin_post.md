🖐️ Project Release: Hand Gesture Controller — OpenCV, MediaPipe & System API Integrations!

How do you control your laptop's volume, screen brightness, and music player without ever touching your keyboard or mouse? By turning your hand into a virtual remote control.

I’m excited to share my latest project: a real-time **Hand Gesture Controller** built in **Python using OpenCV, Google MediaPipe, Pycaw, and PyAutoGUI**.

### 🛠️ The Tech Stack:
* **Computer Vision**: OpenCV (webcam acquisition & HUD overlay rendering)
* **Hand Tracking**: Google MediaPipe Hands (landmark coordinates extraction)
* **OS Integrations**: Pycaw (Windows volume API), screen-brightness-control (screen settings), and PyAutoGUI (virtual media key shortcuts)

---

### 💡 High-Impact Features & Engineering Challenges:

1. **Anti-Trigger Activation Lock (Rock On 🤘)**:
   A common issue with computer vision gesture controllers is "accidental triggers"—adjusting settings while just talking with your hands. I built a state-machine that toggles the system lock state. Volume and brightness changes are completely ignored until you perform the "Rock On" gesture.

2. **Multi-Action Analogs (Volume & Brightness)**:
   * **Volume Mode**: Uses spatial math to interpolate the pixel distance between the thumb tip (landmark 4) and index tip (landmark 8) and connects to Windows master audio endpoints.
   * **Brightness Mode**: By raising just the index finger (pointing), the vertical coordinate of the fingertip maps to screen brightness levels, with a 3% change buffer for screen lag optimization.

3. **Discrete Media Triggers (Thumbs Up 👍, Pinky 🤙, Fist ✊)**:
   * "Thumbs Up" triggers Media Play/Pause.
   * "Pinky Up" skips to the next track.
   * "Fist" toggles mute.
   * *Challenge*: Because these are detected across multiple frames, I implemented transition debouncing to ensure play/pause triggers exactly once when the hand changes state.

4. **Futuristic HUD Display**:
   To present a premium aesthetic, I built a glassmorphic dashboard on the camera feed showing the Lock State, Active Mode, and active gesture using OpenCV pixel blending (`cv2.addWeighted`).

---

💻 **Explore the GitHub Repository**: [Link to your GitHub repository here]
🎥 **Watch the demo**: [Link to demo or attachment here]

Working on this project deepened my understanding of coordinate translation grids, event debouncing in continuous frames, and designing interactive human-computer interfaces.

I'd love to hear your thoughts on hand-tracking and gesture interfaces!

#ComputerVision #OpenCV #MediaPipe #Python #HCI #SoftwareEngineering #CreativeCoding #PortfolioProject
