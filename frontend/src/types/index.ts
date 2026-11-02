/**
 * SignBridge Strict Type Definitions
 */

export type Scenario = 'hospital' | 'bank';

export type Language = 'english' | 'hindi' | 'kannada';

export type SpeakerRole = 'signer' | 'hearing';

export type ConfidenceTier = 'High' | 'Medium' | 'Low';

export interface TopGuess {
  label: string;
  confidence: number;
}

export interface PredictionPayload {
  label: string;
  english: string;
  hindi: string;
  kannada: string;
  confidence: number;
  is_emergency: boolean;
  top_guesses: TopGuess[];
  timestamp: number;
}

export interface ConversationMessage {
  id: string;
  speaker: SpeakerRole;
  text: string;
  translatedText?: {
    hindi?: string;
    kannada?: string;
  };
  confidence?: number;
  confidenceTier?: ConfidenceTier;
  timestamp: string;
}

export type UIState =
  | 'empty'
  | 'camera_denied'
  | 'loading_model'
  | 'recognising'
  | 'low_confidence'
  | 'confirmed_sentence'
  | 'error'
  | 'emergency';

