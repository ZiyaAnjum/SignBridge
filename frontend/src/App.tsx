import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from './components/layout/Header';
import { StateSwitcher } from './components/layout/StateSwitcher';
import { BottomBar } from './components/layout/BottomBar';
import { WebcamPreview } from './components/sign-to-speech/WebcamPreview';
import { LiveCaptions } from './components/sign-to-speech/LiveCaptions';
import { Timeline } from './components/conversation/Timeline';
import { SentenceConfirmation } from './components/conversation/SentenceConfirmation';
import { EmergencyBanner } from './components/alerts/EmergencyBanner';
import { ErrorBanner } from './components/alerts/ErrorBanner';
import { RecordPage } from './components/record/RecordPage';
import { useCameraLandmarks } from './hooks/useCameraLandmarks';
import { useSignBridgeWebSocket } from './hooks/useSignBridgeWebSocket';
import { speakText } from './lib/speech';
import {
  ConversationMessage,
  Language,
  Scenario,
  UIState,
  ConfidenceTier,
} from './types';

interface DraftWord {
  english: string;
  hindi?: string;
  kannada?: string;
}

export const App: React.FC = () => {
  const [activeView, setActiveView] = useState<'workplace' | 'record'>(
    typeof window !== 'undefined' && window.location.pathname === '/record'
      ? 'record'
      : 'workplace'
  );
  const [scenario, setScenario] = useState<Scenario>('hospital');
  const [selectedLanguage, setSelectedLanguage] = useState<Language>('english');
  const [showLandmarks, setShowLandmarks] = useState(true);
  const [showEmergency, setShowEmergency] = useState(false);
  const [voiceNotice, setVoiceNotice] = useState<string | null>(null);

  // Dev mode: inspect all 8 states; toggled via URL (?dev=true) or Shift+D keyboard shortcut
  const [isDevMode, setIsDevMode] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return (
      window.location.search.includes('dev=true') ||
      window.location.hash.includes('dev') ||
      localStorage.getItem('signbridge_dev') === 'true'
    );
  });
  const [devStateOverride, setDevStateOverride] = useState<UIState | null>(null);

  // Accumulated words in current sign sentence draft
  const [draftWords, setDraftWords] = useState<DraftWord[]>([]);

  // Seed conversation messages
  const [messages, setMessages] = useState<ConversationMessage[]>([
    {
      id: 'm1',
      speaker: 'signer',
      text: 'Need doctor appointment today',
      translatedText: {
        hindi: 'आज डॉक्टर से अपॉइंटमेंट चाहिए',
        kannada: 'ಇಂದು ವೈದ್ಯರ ಅಪಾಯಿಂಟ್ಮೆಂಟ್ ಬೇಕು',
      },
      confidence: 0.94,
      confidenceTier: 'High',
      timestamp: '09:42 AM',
    },
    {
      id: 'm2',
      speaker: 'hearing',
      text: 'Good morning. General OPD is open. Do you have a registration token?',
      timestamp: '09:43 AM',
    },
    {
      id: 'm3',
      speaker: 'signer',
      text: 'Yes, have token',
      translatedText: {
        hindi: 'हाँ, टोकन है',
        kannada: 'ಹೌದು, ಟೋಕನ್ ಇದೆ',
      },
      confidence: 0.88,
      confidenceTier: 'High',
      timestamp: '09:44 AM',
    },
  ]);

  // Keyboard shortcut: Shift + D toggles dev state switcher
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.shiftKey && (e.key === 'D' || e.key === 'd')) {
        setIsDevMode((prev) => {
          const next = !prev;
          if (typeof localStorage !== 'undefined') {
            localStorage.setItem('signbridge_dev', String(next));
          }
          if (!next) setDevStateOverride(null);
          return next;
        });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // 1. Live WebSocket client to /ws/landmarks
  const {
    status: wsStatus,
    lastPrediction,
    serverLatencyMs,
    isEmergency: wsEmergency,
    modelLoaded,
    sendLandmarks,
    resetSession,
  } = useSignBridgeWebSocket({
    enabled: activeView === 'workplace',
    onPrediction: (result) => {
      // Emergency alert handling
      if (result.is_emergency) {
        setShowEmergency(true);
      }

      // Words accumulate into draft sentence only when a valid word is reported
      // Note: If model is not loaded (demo mode), words are NOT added to sentence draft
      if (result.model_loaded && result.label && result.label !== 'idle') {
        const engText = result.english || result.label;
        setDraftWords((prev) => {
          // Avoid appending the same word in immediate succession
          if (prev.length > 0 && prev[prev.length - 1].english.toLowerCase() === engText.toLowerCase()) {
            return prev;
          }
          return [
            ...prev,
            {
              english: engText,
              hindi: result.hindi || undefined,
              kannada: result.kannada || undefined,
            },
          ];
        });
      }
    },
  });

  // 2. Shared 15 FPS camera capture pipeline
  const handleFrame = useCallback(
    (landmarks: Float32Array) => {
      if (activeView === 'workplace') {
        sendLandmarks(landmarks);
      }
    },
    [activeView, sendLandmarks]
  );

  const {
    videoRef,
    canvasRef,
    cameraError,
    startCamera,
  } = useCameraLandmarks({
    enabled: activeView === 'workplace',
    showOverlay: showLandmarks,
    onFrame: handleFrame,
  });

  // 3. Resolve active UI state
  const computedState: UIState = useMemo(() => {
    if (devStateOverride) return devStateOverride;
    if (cameraError) return 'camera_denied';
    if (wsStatus === 'connecting') return 'connecting';
    if (wsStatus === 'connection_lost' || wsStatus === 'error') return 'error';
    if (wsEmergency || showEmergency) return 'emergency';
    if (lastPrediction?.state === 'no_signer') return 'no_signer';
    if (lastPrediction?.state === 'buffering') return 'loading_model';
    if (lastPrediction?.state === 'low_confidence') return 'low_confidence';
    if (draftWords.length > 0) return 'confirmed_sentence';
    if (lastPrediction?.label && lastPrediction.label !== 'idle') return 'recognising';
    return 'empty';
  }, [
    devStateOverride,
    cameraError,
    wsStatus,
    wsEmergency,
    showEmergency,
    lastPrediction,
    draftWords.length,
  ]);

  // Caption text resolution
  const displayedCaption = useMemo(() => {
    if (devStateOverride) {
      if (devStateOverride === 'recognising') return scenario === 'hospital' ? 'medicine' : 'account';
      if (devStateOverride === 'low_confidence') return 'doctor';
      if (devStateOverride === 'confirmed_sentence') return 'Need doctor appointment today';
      if (devStateOverride === 'emergency') return 'emergency';
      return '';
    }

    if (lastPrediction?.label && lastPrediction.label !== 'idle') {
      return lastPrediction.english || lastPrediction.label;
    }

    if (draftWords.length > 0) {
      return draftWords[draftWords.length - 1].english;
    }

    return '';
  }, [devStateOverride, scenario, lastPrediction, draftWords]);

  const translatedCaption = useMemo(() => {
    if (selectedLanguage === 'english') return undefined;
    if (selectedLanguage === 'hindi') {
      return lastPrediction?.hindi || (draftWords.length > 0 ? draftWords[draftWords.length - 1].hindi : undefined);
    }
    if (selectedLanguage === 'kannada') {
      return lastPrediction?.kannada || (draftWords.length > 0 ? draftWords[draftWords.length - 1].kannada : undefined);
    }
    return undefined;
  }, [selectedLanguage, lastPrediction, draftWords]);

  const confidenceScore = lastPrediction?.confidence ?? 0.0;
  const confidenceTier: ConfidenceTier =
    confidenceScore >= 0.8 ? 'High' : confidenceScore >= 0.6 ? 'Medium' : 'Low';

  // Draft sentence representation
  const draftEnglishSentence = useMemo(
    () => draftWords.map((w) => w.english).join(' '),
    [draftWords]
  );
  const draftTranslatedSentence = useMemo(() => {
    if (selectedLanguage === 'hindi') {
      return draftWords.map((w) => w.hindi || w.english).join(' ');
    }
    if (selectedLanguage === 'kannada') {
      return draftWords.map((w) => w.kannada || w.english).join(' ');
    }
    return undefined;
  }, [draftWords, selectedLanguage]);

  // Sentence confirmation & speech synthesis
  const handleConfirmSentence = () => {
    // Enforce rule: If model is not loaded, do not speak or add anything to conversation
    if (!modelLoaded) {
      return;
    }

    const sentenceToConfirm = draftEnglishSentence || displayedCaption || 'Yes';
    if (!sentenceToConfirm.trim()) return;

    const newMessage: ConversationMessage = {
      id: `msg-${Date.now()}`,
      speaker: 'signer',
      text: sentenceToConfirm,
      translatedText: {
        hindi: draftTranslatedSentence || (lastPrediction?.hindi ?? undefined),
        kannada: draftTranslatedSentence || (lastPrediction?.kannada ?? undefined),
      },
      confidence: confidenceScore > 0 ? confidenceScore : 0.95,
      confidenceTier: confidenceTier,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, newMessage]);

    // Speak sentence with browser speech synthesis in selected language
    const textToSpeak =
      selectedLanguage === 'hindi' && draftTranslatedSentence
        ? draftTranslatedSentence
        : selectedLanguage === 'kannada' && draftTranslatedSentence
        ? draftTranslatedSentence
        : sentenceToConfirm;

    const speechRes = speakText(textToSpeak, selectedLanguage);
    if (!speechRes.spoken && speechRes.notice) {
      setVoiceNotice(speechRes.notice);
    } else {
      setVoiceNotice(null);
    }

    // Reset draft and clear server repetition locks
    setDraftWords([]);
    resetSession();
    if (devStateOverride) setDevStateOverride(null);
  };

  const handleFixSentence = () => {
    // Remove last word from draft
    setDraftWords((prev) => prev.slice(0, -1));
  };

  const handleClearDraft = () => {
    setDraftWords([]);
    resetSession();
    if (devStateOverride) setDevStateOverride(null);
  };

  const handleHearingSpeak = (transcript: string) => {
    const newMessage: ConversationMessage = {
      id: `msg-${Date.now()}`,
      speaker: 'hearing',
      text: transcript,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, newMessage]);
  };

  if (activeView === 'record') {
    return (
      <RecordPage
        onBackToApp={() => {
          setActiveView('workplace');
          if (typeof window !== 'undefined' && window.location.pathname === '/record') {
            window.history.pushState({}, '', '/');
          }
        }}
      />
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-bg text-ink">
      {/* 1. Global Header */}
      <Header
        scenario={scenario}
        onScenarioChange={setScenario}
        isConnected={wsStatus === 'connected'}
        activeView={activeView}
        onNavigate={(view) => {
          setActiveView(view);
          if (typeof window !== 'undefined') {
            window.history.pushState({}, '', view === 'record' ? '/record' : '/');
          }
        }}
      />

      {/* 2. Dev State Switcher (Hidden unless ?dev=true or Shift+D pressed) */}
      <StateSwitcher
        currentState={computedState}
        onStateSelect={(st) => {
          setDevStateOverride(st);
          if (st === 'emergency') setShowEmergency(true);
        }}
        isDevMode={isDevMode}
        onToggleDevMode={() => {
          setIsDevMode(false);
          setDevStateOverride(null);
          if (typeof localStorage !== 'undefined') {
            localStorage.setItem('signbridge_dev', 'false');
          }
        }}
      />

      {/* 3. Emergency Alert Banner */}
      {(showEmergency || computedState === 'emergency') && (
        <EmergencyBanner
          onDismiss={() => {
            setShowEmergency(false);
            if (devStateOverride === 'emergency') setDevStateOverride(null);
          }}
          scenarioText={
            scenario === 'hospital'
              ? 'Distress sign recognized: Patient indicated severe pain / emergency triage needed.'
              : 'Emergency sign recognized: Customer triggered immediate assistance.'
          }
        />
      )}

      {/* 4. Connection Error Banner */}
      {computedState === 'error' && (
        <ErrorBanner
          onRetry={() => {
            resetSession();
            setDevStateOverride(null);
          }}
          message="Connection to recognition service lost (WebSocket: ws://127.0.0.1:8000/ws/landmarks). Reconnecting with backoff..."
        />
      )}

      {/* 5. Main Two-Pane Workplace Layout */}
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 p-6 lg:flex-row">
        {/* Left Pane: Camera Stream & Live Captions */}
        <div className="flex flex-1 flex-col">
          <WebcamPreview
            videoRef={videoRef}
            canvasRef={canvasRef}
            uiState={computedState}
            showLandmarks={showLandmarks}
            onToggleLandmarks={() => setShowLandmarks((prev) => !prev)}
            onRetryCamera={startCamera}
            signerNotice={lastPrediction?.reason}
          />

          <LiveCaptions
            captionText={displayedCaption}
            translatedText={translatedCaption}
            confidence={confidenceScore}
            confidenceTier={confidenceTier}
            topGuesses={lastPrediction?.top_guesses}
            uiState={computedState}
            modelLoaded={modelLoaded}
            statusNotice={lastPrediction?.reason}
          />
        </div>

        {/* Right Pane: Conversation Timeline & Sentence Draft Confirmation */}
        <div className="flex flex-1 flex-col">
          {/* Sentence Draft Confirmation Card */}
          {(draftWords.length > 0 || computedState === 'confirmed_sentence') && (
            <SentenceConfirmation
              sentence={draftEnglishSentence || displayedCaption || 'Need doctor appointment'}
              translatedSentence={draftTranslatedSentence}
              words={draftWords.map((w) => w.english)}
              modelLoaded={modelLoaded}
              voiceNotice={voiceNotice}
              onConfirm={handleConfirmSentence}
              onFix={handleFixSentence}
              onClear={handleClearDraft}
            />
          )}

          <Timeline
            messages={messages}
            isEmpty={computedState === 'empty' && messages.length === 0}
          />
        </div>
      </main>

      {/* 6. Persistent Bottom Action Bar with Status Bar */}
      <BottomBar
        selectedLanguage={selectedLanguage}
        onLanguageChange={setSelectedLanguage}
        onSpeak={handleHearingSpeak}
        onTriggerEmergency={() => {
          setShowEmergency(true);
        }}
        latencyMs={serverLatencyMs}
        connectionStatus={wsStatus}
        modelLoaded={modelLoaded}
      />
    </div>
  );
};

export default App;
