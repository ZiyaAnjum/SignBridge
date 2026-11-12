/**
 * Shared camera access and 15 FPS MediaPipe landmark extraction pipeline.
 * Used identically by both /record and live inference view.
 * 
 * Rules:
 * - 15 FPS timestamp sampling (interval >= 66.67ms).
 * - Extracts 225-float unmirrored coordinates (33 pose + 21 left hand + 21 right hand).
 * - Never stores or sends video frames.
 * - Cleans up all tracks on unmount.
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { initializeMediaPipe, extractLandmarksFromVideo } from '../lib/mediapipe';

const TARGET_FPS = 15;
const FRAME_INTERVAL_MS = 1000 / TARGET_FPS; // 66.67ms

// MediaPipe standard skeletal topology
const POSE_CONNECTIONS: [number, number][] = [
  [11, 12], // shoulders
  [11, 13], [13, 15], // left arm
  [12, 14], [14, 16], // right arm
  [11, 23], [12, 24], [23, 24], // torso & hips
];

const HAND_CONNECTIONS: [number, number][] = [
  // Thumb
  [0, 1], [1, 2], [2, 3], [3, 4],
  // Index
  [0, 5], [5, 6], [6, 7], [7, 8],
  // Middle
  [0, 9], [9, 10], [10, 11], [11, 12],
  // Ring
  [0, 13], [13, 14], [14, 15], [15, 16],
  // Pinky
  [0, 17], [17, 18], [18, 19], [19, 20],
];

export interface UseCameraLandmarksOptions {
  enabled?: boolean;
  showOverlay?: boolean;
  onFrame?: (landmarks: Float32Array, timestampMs: number) => void;
}

export interface UseCameraLandmarksReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  isCameraActive: boolean;
  cameraError: string | null;
  isMediaPipeReady: boolean;
  startCamera: () => Promise<void>;
  stopCamera: () => void;
}

export function useCameraLandmarks(
  options: UseCameraLandmarksOptions = {}
): UseCameraLandmarksReturn {
  const { enabled = true, showOverlay = true, onFrame } = options;

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animFrameIdRef = useRef<number | null>(null);
  const onFrameRef = useRef(onFrame);
  onFrameRef.current = onFrame;

  const [isCameraActive, setIsCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [isMediaPipeReady, setIsMediaPipeReady] = useState(false);

  // Draw detected skeleton on overlay canvas
  const drawOverlay = useCallback((landmarks: Float32Array) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const w = canvas.width;
    const h = canvas.height;

    // 1. Draw Pose (indices 0..98 -> 33 landmarks)
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#0E6B63'; // DESIGN.md accent
    ctx.fillStyle = '#0E6B63';

    for (const [i1, i2] of POSE_CONNECTIONS) {
      const x1 = landmarks[i1 * 3] * w;
      const y1 = landmarks[i1 * 3 + 1] * h;
      const x2 = landmarks[i2 * 3] * w;
      const y2 = landmarks[i2 * 3 + 1] * h;

      if ((x1 !== 0 || y1 !== 0) && (x2 !== 0 || y2 !== 0)) {
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    }

    // Pose keypoint nodes
    for (const i of [11, 12, 13, 14, 15, 16, 23, 24]) {
      const x = landmarks[i * 3] * w;
      const y = landmarks[i * 3 + 1] * h;
      if (x !== 0 || y !== 0) {
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
      }
    }

    // 2. Helper to draw hand (21 landmarks)
    const drawHand = (offset: number) => {
      // Check if hand is detected (any non-zero)
      let detected = false;
      for (let p = 0; p < 21; p++) {
        if (landmarks[offset + p * 3] !== 0 || landmarks[offset + p * 3 + 1] !== 0) {
          detected = true;
          break;
        }
      }
      if (!detected) return;

      ctx.lineWidth = 1.5;
      ctx.strokeStyle = '#2E7D32'; // DESIGN.md ok
      ctx.fillStyle = '#2E7D32';

      // Connect finger bones
      for (const [p1, p2] of HAND_CONNECTIONS) {
        const x1 = landmarks[offset + p1 * 3] * w;
        const y1 = landmarks[offset + p1 * 3 + 1] * h;
        const x2 = landmarks[offset + p2 * 3] * w;
        const y2 = landmarks[offset + p2 * 3 + 1] * h;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // Joint dots
      for (let p = 0; p < 21; p++) {
        const x = landmarks[offset + p * 3] * w;
        const y = landmarks[offset + p * 3 + 1] * h;
        ctx.beginPath();
        ctx.arc(x, y, 2.5, 0, 2 * Math.PI);
        ctx.fill();
      }
    };

    // Left hand [99..161] and Right hand [162..224]
    drawHand(99);
    drawHand(162);
  }, []);

  const stopCamera = useCallback(() => {
    if (animFrameIdRef.current !== null) {
      cancelAnimationFrame(animFrameIdRef.current);
      animFrameIdRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      ctx?.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    }
    setIsCameraActive(false);
  }, []);

  const startCamera = useCallback(async () => {
    stopCamera();
    setCameraError(null);

    try {
      // 1. Initialize MediaPipe models once
      const ok = await initializeMediaPipe();
      setIsMediaPipeReady(ok);

      // 2. Request user media with safe resolution constraints
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
        },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      setIsCameraActive(true);

      // 3. Start 15 FPS continuous sampling loop
      let lastTimestamp = 0;

      const loop = (timestamp: number) => {
        if (!streamRef.current) return;

        const delta = timestamp - lastTimestamp;
        if (delta >= FRAME_INTERVAL_MS) {
          lastTimestamp = timestamp;

          const video = videoRef.current;
          if (video && video.readyState >= 2 && video.videoWidth > 0) {
            // Match canvas coordinates to video dimensions
            if (canvasRef.current) {
              if (
                canvasRef.current.width !== video.videoWidth ||
                canvasRef.current.height !== video.videoHeight
              ) {
                canvasRef.current.width = video.videoWidth;
                canvasRef.current.height = video.videoHeight;
              }
            }

            // Extract 225-dim unmirrored landmark coordinate vector
            const landmarks = extractLandmarksFromVideo(video, timestamp);

            // Draw visual skeleton overlay if enabled
            if (showOverlay) {
              drawOverlay(landmarks);
            }

            // Emit frame to consumer
            if (onFrameRef.current) {
              onFrameRef.current(landmarks, timestamp);
            }
          }
        }

        animFrameIdRef.current = requestAnimationFrame(loop);
      };

      animFrameIdRef.current = requestAnimationFrame(loop);
    } catch (err: unknown) {
      const errorMsg =
        err instanceof Error ? err.message : 'Camera access denied or unavailable';
      setCameraError(errorMsg);
      setIsCameraActive(false);
    }
  }, [drawOverlay, showOverlay, stopCamera]);

  useEffect(() => {
    if (enabled) {
      startCamera();
    } else {
      stopCamera();
    }

    return () => {
      stopCamera();
    };
  }, [enabled, startCamera, stopCamera]);

  return {
    videoRef,
    canvasRef,
    isCameraActive,
    cameraError,
    isMediaPipeReady,
    startCamera,
    stopCamera,
  };
}

