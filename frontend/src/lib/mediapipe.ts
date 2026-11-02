/**
 * Browser-based landmark extraction pipeline using MediaPipe Tasks Vision.
 * Produces deterministic (225,) landmark vectors:
 * - 33 Pose landmarks x (x, y, z) = [0 : 99]
 * - 21 Left Hand landmarks x (x, y, z) = [99 : 162]
 * - 21 Right Hand landmarks x (x, y, z) = [162 : 225]
 *
 * Missing hands remain strictly 0.0.
 * Coordinates are unmirrored.
 */

import { FilesetResolver, PoseLandmarker, HandLandmarker } from '@mediapipe/tasks-vision';

let poseLandmarker: PoseLandmarker | null = null;
let handLandmarker: HandLandmarker | null = null;
let isInitializing = false;

export async function initializeMediaPipe(): Promise<boolean> {
  if (poseLandmarker && handLandmarker) return true;
  if (isInitializing) return false;

  isInitializing = true;
  try {
    const vision = await FilesetResolver.forVisionTasks(
      'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
    );

    poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath:
          'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task',
        delegate: 'GPU',
      },
      runningMode: 'VIDEO',
      numPoses: 1,
      minPoseDetectionConfidence: 0.5,
      minPosePresenceConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    handLandmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath:
          'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task',
        delegate: 'GPU',
      },
      runningMode: 'VIDEO',
      numHands: 2,
      minHandDetectionConfidence: 0.5,
      minHandPresenceConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    isInitializing = false;
    return true;
  } catch (error) {
    console.warn('[MediaPipe] Failed to load GPU WASM vision tasks, falling back to simulated landmarks:', error);
    isInitializing = false;
    return false;
  }
}

/**
 * Extract 225-dimensional unmirrored landmark coordinate array from video frame.
 */
export function extractLandmarksFromVideo(
  video: HTMLVideoElement,
  timestampMs: number
): Float32Array {
  const output = new Float32Array(225);

  if (!poseLandmarker || !handLandmarker) {
    // Return empty frame or synthetic placeholder if model not loaded
    return output;
  }

  try {
    // 1. Process Pose (33 points -> indices 0..98)
    const poseResult = poseLandmarker.detectForVideo(video, timestampMs);
    if (poseResult.landmarks && poseResult.landmarks.length > 0) {
      const posePoints = poseResult.landmarks[0];
      for (let i = 0; i < Math.min(33, posePoints.length); i++) {
        const p = posePoints[i];
        output[i * 3] = p.x;
        output[i * 3 + 1] = p.y;
        output[i * 3 + 2] = p.z;
      }
    }

    // 2. Process Hands (21 points per hand)
    const handResult = handLandmarker.detectForVideo(video, timestampMs);
    if (handResult.landmarks && handResult.handedness) {
      for (let hIdx = 0; hIdx < handResult.landmarks.length; hIdx++) {
        const handPoints = handResult.landmarks[hIdx];
        const handednessInfo = handResult.handedness[hIdx]?.[0];
        const categoryName = handednessInfo?.categoryName; // 'Left' or 'Right'

        // Map anatomical left/right to exact slice offsets
        let offset = -1;
        if (categoryName === 'Left') {
          offset = 99; // Left Hand [99 : 162]
        } else if (categoryName === 'Right') {
          offset = 162; // Right Hand [162 : 225]
        }

        if (offset >= 0) {
          for (let pIdx = 0; pIdx < Math.min(21, handPoints.length); pIdx++) {
            const hp = handPoints[pIdx];
            output[offset + pIdx * 3] = hp.x;
            output[offset + pIdx * 3 + 1] = hp.y;
            output[offset + pIdx * 3 + 2] = hp.z;
          }
        }
      }
    }
  } catch (err) {
    console.error('[MediaPipe] Extraction error:', err);
  }

  return output;
}

