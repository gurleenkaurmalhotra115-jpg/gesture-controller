import cv2
import mediapipe as mp
import math
import numpy as np
import screen_brightness_control as sbc
import pyautogui
import time
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Disable PyAutoGUI fail-safe to prevent crash when mouse is in corners
pyautogui.FAILSAFE = False

# --- Volume Setup ---
try:
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    vol_min, vol_max = volume.GetVolumeRange()[:2]
except Exception as e:
    print(f"Warning: Audio device setup failed ({e}). Volume controls will be simulated.")
    volume = None
    vol_min, vol_max = -65.25, 0.0

# --- MediaPipe Setup ---
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    static_image_mode=False
)

# --- State Variables ---
is_locked = True
last_gesture = "None"
cooldown_time = 0.0
last_brightness = sbc.get_brightness(display=0)[0] if sbc.get_brightness() else 50
current_volume_pct = 50

# --- HUD Notifications ---
hud_notification = ""
notification_timer = 0

def get_fingers(hand_landmarks, hand_label):
    landmarks = hand_landmarks.landmark
    fingers = []

    # Thumb: Uses relative X coordinate
    if hand_label == "Right":
        if landmarks[4].x < landmarks[3].x:
            fingers.append(1)
        else:
            fingers.append(0)
    else:
        if landmarks[4].x > landmarks[3].x:
            fingers.append(1)
        else:
            fingers.append(0)

    # Other 4 fingers: Uses relative Y coordinates
    for tip_id in [8, 12, 16, 20]:
        if landmarks[tip_id].y < landmarks[tip_id - 2].y:
            fingers.append(1)
        else:
            fingers.append(0)

    return fingers

def get_gesture_name(fingers):
    if fingers == [0, 0, 0, 0, 0]:
        return "Fist"
    elif fingers == [1, 1, 1, 1, 1]:
        return "Open Hand"
    elif fingers == [0, 1, 0, 0, 0]:
        return "Pointing"
    elif fingers == [0, 1, 1, 0, 0]:
        return "Peace"
    elif fingers == [1, 0, 0, 0, 0]:
        return "Thumbs Up"
    elif fingers == [0, 0, 0, 0, 1]:
        return "Pinky"
    elif fingers == [1, 1, 0, 0, 1]:
        return "Rock On"
    elif fingers == [0, 1, 1, 1, 1]:
        return "Four"
    else:
        return "Unknown"

def draw_glass_rect(img, pt1, pt2, color, alpha=0.35):
    """Draws a semi-transparent filled rectangle for glassmorphism HUD look."""
    overlay = img.copy()
    cv2.rectangle(overlay, pt1, pt2, color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

# --- Webcam ---
cap = cv2.VideoCapture(0)
print("Camera started. Press Q to quit.")

while True:
    success, frame = cap.read()
    if not success:
        continue

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)

    gesture = "None"
    finger_count = 0
    current_time = time.time()

    # Decrement HUD notification timer
    if notification_timer > 0:
        notification_timer -= 1
    else:
        hud_notification = ""

    if result.multi_hand_landmarks and result.multi_handedness:
        for hand_landmarks, handedness in zip(result.multi_hand_landmarks, result.multi_handedness):
            # Draw standard skeleton landmarks
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            hand_label = handedness.classification[0].label
            landmarks = hand_landmarks.landmark

            # Calculate fingertips status
            fingers = get_fingers(hand_landmarks, hand_label)
            finger_count = sum(fingers)
            gesture = get_gesture_name(fingers)

            # --- Lock State Toggle (Rock On 🤘) ---
            if gesture == "Rock On" and (current_time - cooldown_time) > 1.5:
                is_locked = not is_locked
                cooldown_time = current_time
                hud_notification = "🔓 ACTIVATED" if not is_locked else "🔒 LOCKED"
                notification_timer = 30

            # --- Actions Only Run If Unlocked ---
            if not is_locked:
                
                # 1. Volume Control Mode (Peace ✌️ or Open Hand 🖐️)
                if gesture in ["Peace", "Open Hand"]:
                    thumb_x = int(landmarks[4].x * w)
                    thumb_y = int(landmarks[4].y * h)
                    index_x = int(landmarks[8].x * w)
                    index_y = int(landmarks[8].y * h)

                    # Dynamic color coding for distance line
                    distance = math.hypot(index_x - thumb_x, index_y - thumb_y)
                    line_color = (0, 255, 0) if distance < 60 else (0, 255, 255) if distance < 140 else (0, 0, 255)

                    cv2.circle(frame, (thumb_x, thumb_y), 10, (255, 0, 255), -1)
                    cv2.circle(frame, (index_x, index_y), 10, (255, 0, 255), -1)
                    cv2.line(frame, (thumb_x, thumb_y), (index_x, index_y), line_color, 2)

                    # Map pinch distance to volume ranges
                    vol_percent = int(np.interp(distance, [30, 180], [0, 100]))
                    vol_percent = max(0, min(100, vol_percent))
                    current_volume_pct = vol_percent

                    if volume:
                        vol = float(np.interp(distance, [30, 180], [vol_min, vol_max]))
                        volume.SetMasterVolumeLevel(vol, None)

                # 2. Brightness Control Mode (Pointing ☝️)
                elif gesture == "Pointing":
                    index_x = int(landmarks[8].x * w)
                    index_y = int(landmarks[8].y * h)

                    cv2.circle(frame, (index_x, index_y), 12, (0, 215, 255), -1)

                    # Map vertical pointer height to brightness [0.2, 0.75] Y range
                    bright = int(np.interp(landmarks[8].y, [0.2, 0.75], [100, 0]))
                    bright = max(0, min(100, bright))

                    if abs(bright - last_brightness) >= 3:
                        try:
                            sbc.set_brightness(bright)
                            last_brightness = bright
                        except Exception:
                            pass

                # 3. Media Controls (One-shot triggers on transition)
                elif gesture == "Thumbs Up" and last_gesture != "Thumbs Up":
                    pyautogui.press('playpause')
                    hud_notification = "⏯ PLAY/PAUSE"
                    notification_timer = 25
                elif gesture == "Pinky" and last_gesture != "Pinky":
                    pyautogui.press('nexttrack')
                    hud_notification = "⏭ NEXT TRACK"
                    notification_timer = 25
                elif gesture == "Fist" and last_gesture != "Fist":
                    pyautogui.press('volumemute')
                    hud_notification = "🔇 MUTE TOGGLE"
                    notification_timer = 25

            last_gesture = gesture

    # --- Draw Premium HUD overlay ---
    # Top status bar
    draw_glass_rect(frame, (15, 15), (340, 155), (20, 20, 20), 0.5)
    
    # 1. Lock Status Indicator
    if is_locked:
        cv2.putText(frame, "🔒 SYSTEM LOCKED", (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(frame, "Show Rock On (🤘) to Unlock", (25, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    else:
        cv2.putText(frame, "🔓 SYSTEM ACTIVE", (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "Show Rock On (🤘) to Lock", (25, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    # 2. Mode and Gesture status
    mode_str = "IDLE"
    mode_color = (150, 150, 150)
    if not is_locked:
        if gesture in ["Peace", "Open Hand"]:
            mode_str, mode_color = "VOLUME CONTROL", (0, 255, 0)
        elif gesture == "Pointing":
            mode_str, mode_color = "BRIGHTNESS", (0, 215, 255)
        elif gesture in ["Thumbs Up", "Pinky", "Fist"]:
            mode_str, mode_color = "MEDIA CONTROL", (255, 191, 0)

    cv2.putText(frame, f"MODE: {mode_str}", (25, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.55, mode_color, 2)
    cv2.putText(frame, f"GESTURE: {gesture.upper()}", (25, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    # 3. Dynamic Side Gauge (Volume / Brightness)
    if not is_locked:
        if mode_str == "VOLUME CONTROL":
            # Draw green volume slider
            cv2.rectangle(frame, (600, 150), (615, 380), (40, 40, 40), -1)
            bar_y = int(np.interp(current_volume_pct, [0, 100], [380, 150]))
            cv2.rectangle(frame, (600, bar_y), (615, 380), (0, 255, 0), -1)
            cv2.putText(frame, f"VOL: {current_volume_pct}%", (540, 410), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        elif mode_str == "BRIGHTNESS":
            # Draw golden brightness slider
            cv2.rectangle(frame, (600, 150), (615, 380), (40, 40, 40), -1)
            bar_y = int(np.interp(last_brightness, [0, 100], [380, 150]))
            cv2.rectangle(frame, (600, bar_y), (615, 380), (0, 215, 255), -1)
            cv2.putText(frame, f"BRT: {last_brightness}%", (540, 410), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 215, 255), 2)

    # 4. Action Notifications Popup (Center Screen HUD display)
    if hud_notification:
        draw_glass_rect(frame, (180, 200), (460, 260), (30, 30, 30), 0.6)
        cv2.putText(frame, hud_notification, (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # Display window
    cv2.imshow("Gesture Controller HUD", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()