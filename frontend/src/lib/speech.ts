/**
 * Speech synthesis utility for SignBridge.
 * Supports English, Hindi, and Kannada.
 * 
 * Rules:
 * - Checks which voices exist for en/hi/kn.
 * - If none exists for the chosen language, returns a short notice instead of failing silently.
 */
import { Language } from '../types';

export interface SpeechResult {
  spoken: boolean;
  notice?: string;
  matchedVoiceName?: string;
}

const LANGUAGE_TAGS: Record<Language, string[]> = {
  english: ['en-IN', 'en-US', 'en-GB', 'en'],
  hindi: ['hi-IN', 'hi'],
  kannada: ['kn-IN', 'kn'],
};

export function findVoiceForLanguage(lang: Language): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    return null;
  }

  const voices = window.speechSynthesis.getVoices();
  const targetPrefixes = LANGUAGE_TAGS[lang];

  for (const prefix of targetPrefixes) {
    const match = voices.find((v) =>
      v.lang.toLowerCase().replace('_', '-').startsWith(prefix.toLowerCase())
    );
    if (match) return match;
  }

  return null;
}

export function speakText(text: string, language: Language): SpeechResult {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    return {
      spoken: false,
      notice: 'Speech synthesis is not supported by your browser.',
    };
  }

  const cleanText = text.trim();
  if (!cleanText) {
    return { spoken: false };
  }

  // Cancel any ongoing speech
  window.speechSynthesis.cancel();

  const voice = findVoiceForLanguage(language);

  if (!voice) {
    const langNames: Record<Language, string> = {
      english: 'English',
      hindi: 'Hindi (हिंदी)',
      kannada: 'Kannada (ಕನ್ನಡ)',
    };
    return {
      spoken: false,
      notice: `No text-to-speech voice found for ${langNames[language]} in your browser. Sentence displayed in timeline.`,
    };
  }

  try {
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.voice = voice;
    utterance.lang = voice.lang;
    utterance.rate = 0.95; // Clear counter communication pace
    utterance.pitch = 1.0;

    window.speechSynthesis.speak(utterance);

    return {
      spoken: true,
      matchedVoiceName: voice.name,
    };
  } catch (err: unknown) {
    const errDetail = err instanceof Error ? err.message : String(err);
    return {
      spoken: false,
      notice: `Speech synthesis error: ${errDetail}`,
    };
  }
}
