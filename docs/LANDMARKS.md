# SignBridge Landmark Protocol & Normalization Specification

This document defines the canonical landmark coordinate specification, memory layout, normalization math, mirroring conventions, and sampling rules. This specification is strictly identical across the Python backend (`ml-service`) and the browser TypeScript frontend (`frontend`).

---

## 1. Feature Vector Layout: Shape `(30, 225)`

Every gesture sample is an array of shape `(30, 225)` representing **30 sequential frames** recorded at **15 frames per second** (duration: 2.0 seconds).

Each frame contains 75 keypoints in 3D $(x, y, z)$, yielding $75 \times 3 = 225$ floating-point values:

| Landmark Group | Point Count | Coordinate Index in 225-vector | Keypoint Descriptions |
|---|---|---|---|
| **Pose** | 33 landmarks | `[0 : 99]` | Holistic/Pose landmarks 0 to 32 $(x, y, z)$ |
| **Left Hand** | 21 landmarks | `[99 : 162]` | Anatomical Left Hand (wrist + finger joints 0 to 20) |
| **Right Hand** | 21 landmarks | `[162 : 225]` | Anatomical Right Hand (wrist + finger joints 0 to 20) |

### Key Landmark Indices (Pose)
* `11`: Left Shoulder $(x_{11}, y_{11}, z_{11})$
* `12`: Right Shoulder $(x_{12}, y_{12}, z_{12})$
* `23`: Left Hip
* `24`: Right Hip

### Missing Hand Rule
If a hand is not detected in the frame:
* All 63 values for that hand (`[99:162]` for left, `[162:225]` for right) remain **strictly 0.0**.
* **Never** normalize or translate coordinates for an undetected hand.

---

## 2. Aspect Ratio Correction & Coordinate Space

MediaPipe outputs coordinates $(x, y)$ normalized to $[0, 1]$ relative to image width and height.
Because video frames are non-square (typically 16:9, aspect ratio $A = \frac{\text{width}}{\text{height}} \approx 1.777$), Euclidean distances between points without aspect correction distort the human anatomy.

Before computing shoulder width or Euclidean distances:
1. Aspect-correct $x$:
   $$x_{\text{aspect}} = x \times A \quad \left(A = \frac{W}{H}\right)$$
2. $y$ and $z$ remain in height-normalized units.

---

## 3. Shoulder Midpoint Normalization & Scale

All detected coordinates are translated relative to the signer's shoulder midpoint and scaled by their shoulder width. This makes sign recognition invariant to signer distance and position in the frame.

### 3.1 Midpoint Anchor
$$M_x = \frac{x_{11,\text{aspect}} + x_{12,\text{aspect}}}{2}$$
$$M_y = \frac{y_{11} + y_{12}}{2}$$
$$M_z = \frac{z_{11} + z_{12}}{2}$$

### 3.2 Scale Factor (Shoulder Width)
$$S = \sqrt{(x_{11,\text{aspect}} - x_{12,\text{aspect}})^2 + (y_{11} - y_{12})^2 + (z_{11} - z_{12})^2}$$

### 3.3 Missing Shoulder / Degenerate Scale Rule
* **Threshold**: Minimum valid shoulder distance is $S_{\min} = 0.05$.
* If either shoulder has visibility $\le 0.5$, or if either shoulder coordinates are $(0, 0, 0)$, or if $S < S_{\min}$:
  1. **Reuse Anchor**: Use the most recent valid anchor $(M_x, M_y, M_z, S)$ from the current sequence.
  2. **Fallback**: If no valid anchor has been established yet in the sequence, use the neutral fallback:
     $$M_x = 0.5 \times A, \quad M_y = 0.5, \quad M_z = 0.0, \quad S = 1.0$$

### 3.4 Normalization Formula
For every landmark $i$ that was **actually detected**:
$$x'_i = \frac{x_{i,\text{aspect}} - M_x}{S}$$
$$y'_i = \frac{y_i - M_y}{S}$$
$$z'_i = \frac{z_i - M_z}{S}$$

* **Missing Hands**: If hand landmarks are undetected (all zero), they are **NOT** translated and remain exactly $0.0$.

---

## 4. Mirroring & Handedness Specification

* **Unmirrored Coordinates**:
  The recognition model (Python backend) and training dataset always receive the **UNMIRRORED** raw coordinate stream.
* **Display Mirroring**:
  Webcam preview in the browser is mirrored visually using CSS:
  ```css
  video, canvas { transform: scaleX(-1); }
  ```
* **MediaPipe Handedness Mapping**:
  MediaPipe returns handedness labels relative to the signer's anatomical body:
  * `categoryName: "Left"` $\to$ Anatomical Left Hand $\to$ indices `[99 : 162]`
  * `categoryName: "Right"` $\to$ Anatomical Right Hand $\to$ indices `[162 : 225]`
  This is identical in both Python (MediaPipe Holistic) and JavaScript (MediaPipe Tasks Vision).

---

## 5. Sampling Rate: Fixed 15 FPS

* Both the `/record` collection page and live WebSocket inference capture frames at **exactly 15 FPS** by timestamp intervals:
  $$\Delta t = \frac{1000\text{ ms}}{15} \approx 66.67\text{ ms}$$
* A frame is only extracted and pushed into the buffer when:
  $$t_{\text{current}} - t_{\text{last\_frame}} \ge 66.67\text{ ms}$$
* Fixed 30 frames per sample ensures deterministic sequence length $(30, 225)$ across different devices, refresh rates (60Hz, 120Hz, 144Hz), and camera hardware.

