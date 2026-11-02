import React, { useState } from 'react';
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
import {
  ConversationMessage,
  Language,
  Scenario,
  UIState,
} from './types';

export const App: React.FC = () => {
  const [activeView, setActiveView] = useState<'workplace' | 'record'>(
    typeof window !== 'undefined' && window.location.pathname === '/record'
      ? 'record'
      : 'workplace'
  );
  const [scenario, setScenario] = useState<Scenario>('hospital');
  const [selectedLanguage, setSelectedLanguage] = useState<Language>('english');
  const [uiState, setUiState] = useState<UIState>('recognising');
  const [showEmergency, setShowEmergency] = useState(false);

  // Sample seed messages demonstrating the hospital & bank conversations
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

  // Current live caption state simulation
  const captionMap: Record<UIState, { text: string; hindi: string; kannada: string }> = {
    empty: { text: '', hindi: '', kannada: '' },
    camera_denied: { text: '', hindi: '', kannada: '' },
    loading_model: { text: '', hindi: '', kannada: '' },
    recognising: {
      text: scenario === 'hospital' ? 'medicine' : 'account',
      hindi: scenario === 'hospital' ? 'दवा' : 'खाता',
      kannada: scenario === 'hospital' ? 'ಔಷಧಿ' : 'ಖಾತೆ',
    },
    low_confidence: { text: 'doctor', hindi: 'डॉक्टर', kannada: 'ವೈದ್ಯರು' },
    confirmed_sentence: {
      text: scenario === 'hospital' ? 'I need medicine for fever' : 'I want to deposit cash',
      hindi: scenario === 'hospital' ? 'मुझे बुखार की दवा चाहिए' : 'मुझे नकद जमा करना है',
      kannada: scenario === 'hospital' ? 'ನನಗೆ ಜ್ವರದ ಔಷಧಿ ಬೇಕು' : 'ನಾನು ನಗದು ಜಮಾ ಮಾಡಬೇಕು',
    },
    error: { text: '', hindi: '', kannada: '' },
    emergency: { text: 'emergency', hindi: 'आपातकाल', kannada: 'ತುರ್ತು' },
  };

  const currentCaption = captionMap[uiState];

  const handleStateSelect = (state: UIState) => {
    setUiState(state);
    if (state === 'emergency') {
      setShowEmergency(true);
    }
  };

  const handleConfirmSentence = () => {
    const newMessage: ConversationMessage = {
      id: `msg-${Date.now()}`,
      speaker: 'signer',
      text: currentCaption.text,
      translatedText: {
        hindi: currentCaption.hindi,
        kannada: currentCaption.kannada,
      },
      confidence: 0.95,
      confidenceTier: 'High',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, newMessage]);
    setUiState('recognising');
  };

  const handleFixSentence = () => {
    setUiState('recognising');
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
        isConnected={uiState !== 'error'}
        activeView={activeView}
        onNavigate={(view) => {
          setActiveView(view);
          if (typeof window !== 'undefined') {
            window.history.pushState({}, '', view === 'record' ? '/record' : '/');
          }
        }}
      />

      {/* 2. Interactive Design States Switcher (Inspect all 8 states) */}
      <StateSwitcher
        currentState={uiState}
        onStateSelect={handleStateSelect}
      />

      {/* 3. State 8: Full-Width Emergency Alert Banner */}
      {(showEmergency || uiState === 'emergency') && (
        <EmergencyBanner
          onDismiss={() => {
            setShowEmergency(false);
            if (uiState === 'emergency') setUiState('recognising');
          }}
          scenarioText={
            scenario === 'hospital'
              ? 'Distress sign recognized: Patient indicated severe chest pain / emergency triage needed.'
              : 'Emergency sign recognized: Customer triggered immediate security assistance.'
          }
        />
      )}

      {/* 4. State 7: Connection Error Banner */}
      {uiState === 'error' && (
        <ErrorBanner
          onRetry={() => setUiState('recognising')}
          message="Connection to recognition service lost (WebSocket: ws://localhost:8000/ws/landmarks). Reconnecting..."
        />
      )}

      {/* 5. Main Two-Pane Workplace Layout */}
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 p-6 lg:flex-row">
        {/* Left Pane: Camera Stream & Live Captions */}
        <div className="flex flex-1 flex-col">
          <WebcamPreview
            uiState={uiState}
            onRetryCamera={() => setUiState('recognising')}
          />

          <LiveCaptions
            captionText={currentCaption.text}
            translatedText={
              selectedLanguage === 'hindi'
                ? currentCaption.hindi
                : selectedLanguage === 'kannada'
                ? currentCaption.kannada
                : undefined
            }
            confidence={uiState === 'low_confidence' ? 0.42 : 0.94}
            confidenceTier={uiState === 'low_confidence' ? 'Low' : 'High'}
            uiState={uiState}
          />
        </div>

        {/* Right Pane: Conversation Timeline & Confirmation */}
        <div className="flex flex-1 flex-col">
          {/* State 6: Confirmed Sentence Awaiting Speech */}
          {uiState === 'confirmed_sentence' && (
            <SentenceConfirmation
              sentence={currentCaption.text}
              onConfirm={handleConfirmSentence}
              onFix={handleFixSentence}
            />
          )}

          <Timeline
            messages={messages}
            isEmpty={uiState === 'empty'}
          />
        </div>
      </main>

      {/* 6. Persistent Bottom Action Bar */}
      <BottomBar
        selectedLanguage={selectedLanguage}
        onLanguageChange={setSelectedLanguage}
        onSpeak={handleHearingSpeak}
        onTriggerEmergency={() => {
          setShowEmergency(true);
          setUiState('emergency');
        }}
      />
    </div>
  );
};

export default App;
