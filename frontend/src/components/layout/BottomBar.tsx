import React, { useState } from 'react';
import { Mic, Languages, AlertOctagon, Send } from 'lucide-react';
import { Language } from '../../types';

interface BottomBarProps {
  selectedLanguage: Language;
  onLanguageChange: (lang: Language) => void;
  onSpeak: (transcript: string) => void;
  onTriggerEmergency: () => void;
}

export const BottomBar: React.FC<BottomBarProps> = ({
  selectedLanguage,
  onLanguageChange,
  onSpeak,
  onTriggerEmergency,
}) => {
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    onSpeak(inputText.trim());
    setInputText('');
  };

  const handleSimulateVoice = () => {
    setIsRecording(true);
    setTimeout(() => {
      setIsRecording(false);
      onSpeak('Please take this token to counter 4 for your prescription.');
    }, 800);
  };

  return (
    <footer className="border-t border-border bg-surface px-6 py-4">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
        {/* Hearing Person Input Form */}
        <form onSubmit={handleSubmit} className="flex flex-1 items-center gap-3 min-w-[280px]">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Type hearing staff response or click Speak..."
            className="flex-1 rounded-input border border-border bg-bg px-4 py-3 text-sm text-ink placeholder:text-ink-muted focus-visible:outline-none min-h-[48px]"
          />

          <button
            type="submit"
            disabled={!inputText.trim()}
            className="flex items-center justify-center gap-2 rounded-input border border-border bg-surface px-4 py-3 text-sm font-semibold text-ink hover:bg-bg disabled:opacity-40 min-h-[48px]"
          >
            <Send className="h-4 w-4 text-ink-muted" aria-hidden="true" />
            <span className="hidden sm:inline">Send</span>
          </button>

          <button
            type="button"
            onClick={handleSimulateVoice}
            className={`flex items-center justify-center gap-2 rounded-input bg-accent px-5 py-3 text-sm font-bold text-accent-ink hover:opacity-95 min-h-[48px] ${
              isRecording ? 'opacity-80' : ''
            }`}
          >
            <Mic className="h-4 w-4" aria-hidden="true" />
            <span>{isRecording ? 'Listening...' : 'Speak'}</span>
          </button>
        </form>

        {/* Language Selector & Emergency Trigger */}
        <div className="flex items-center gap-3">
          {/* Language Selector */}
          <div className="flex items-center gap-2 rounded-input border border-border bg-bg px-3 py-1.5 min-h-[48px]">
            <Languages className="h-4 w-4 text-ink-muted" aria-hidden="true" />
            <label htmlFor="language-select" className="sr-only">
              Translation Language
            </label>
            <select
              id="language-select"
              value={selectedLanguage}
              onChange={(e) => onLanguageChange(e.target.value as Language)}
              className="bg-transparent text-xs font-bold text-ink cursor-pointer focus-visible:outline-none"
            >
              <option value="english">English (US)</option>
              <option value="hindi">Hindi (हिंदी)</option>
              <option value="kannada">Kannada (ಕನ್ನಡ)</option>
            </select>
          </div>

          {/* Persistent Emergency Button */}
          <button
            type="button"
            onClick={onTriggerEmergency}
            className="flex items-center gap-2 rounded-input bg-emergency px-5 py-3 text-sm font-bold text-surface hover:opacity-95 min-h-[48px]"
          >
            <AlertOctagon className="h-4 w-4" aria-hidden="true" />
            <span>Emergency Alert</span>
          </button>
        </div>
      </div>
    </footer>
  );
};

