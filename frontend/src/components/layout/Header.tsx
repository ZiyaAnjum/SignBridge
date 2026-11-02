import React from 'react';
import { ShieldCheck, Activity, Building2, Stethoscope } from 'lucide-react';
import { Scenario } from '../../types';

interface HeaderProps {
  scenario: Scenario;
  onScenarioChange: (scenario: Scenario) => void;
  isConnected: boolean;
  activeView: 'workplace' | 'record';
  onNavigate: (view: 'workplace' | 'record') => void;
}

export const Header: React.FC<HeaderProps> = ({
  scenario,
  onScenarioChange,
  isConnected,
  activeView,
  onNavigate,
}) => {
  return (
    <header className="border-b border-border bg-surface px-6 py-4">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
        {/* Brand & Context */}
        <div className="flex items-center gap-4">
          <div>
            <h1 className="font-serif text-2xl font-bold tracking-tight text-ink">
              SignBridge
            </h1>
            <p className="font-sans text-xs text-ink-muted">
              Assistive Indian Sign Language (ISL) communication
            </p>
          </div>

          {/* Privacy Badge */}
          <div className="hidden sm:flex items-center gap-2 rounded-input border border-border bg-bg px-3 py-1 text-xs text-ink-muted">
            <ShieldCheck className="h-4 w-4 text-accent" aria-hidden="true" />
            <span>Privacy guaranteed: Landmark coordinates only, no video stored</span>
          </div>
        </div>

        {/* Controls: View Nav, Scenario Switcher & Connection Status */}
        <div className="flex items-center gap-4">
          {/* View Nav */}
          <div className="flex items-center rounded-input border border-border bg-bg p-1">
            <button
              type="button"
              onClick={() => onNavigate('workplace')}
              className={`rounded-input px-3 py-1.5 text-xs font-semibold transition-colors min-h-[36px] ${
                activeView === 'workplace'
                  ? 'bg-ink text-surface'
                  : 'text-ink hover:bg-surface'
              }`}
            >
              Workplace
            </button>
            <button
              type="button"
              onClick={() => onNavigate('record')}
              className={`rounded-input px-3 py-1.5 text-xs font-semibold transition-colors min-h-[36px] ${
                activeView === 'record'
                  ? 'bg-ink text-surface'
                  : 'text-ink hover:bg-surface'
              }`}
            >
              Record Samples
            </button>
          </div>

          {/* Scenario Selector */}
          <div
            className="flex items-center rounded-input border border-border bg-bg p-1"
            role="group"
            aria-label="Scenario selector"
          >
            <button
              type="button"
              onClick={() => onScenarioChange('hospital')}
              className={`flex items-center gap-2 rounded-input px-3 py-1.5 text-xs font-semibold transition-colors min-h-[36px] ${
                scenario === 'hospital'
                  ? 'bg-accent text-accent-ink'
                  : 'text-ink hover:bg-surface'
              }`}
            >
              <Stethoscope className="h-4 w-4" aria-hidden="true" />
              <span>Hospital & Clinic</span>
            </button>
            <button
              type="button"
              onClick={() => onScenarioChange('bank')}
              className={`flex items-center gap-2 rounded-input px-3 py-1.5 text-xs font-semibold transition-colors min-h-[36px] ${
                scenario === 'bank'
                  ? 'bg-accent text-accent-ink'
                  : 'text-ink hover:bg-surface'
              }`}
            >
              <Building2 className="h-4 w-4" aria-hidden="true" />
              <span>Bank Counter</span>
            </button>
          </div>

          {/* Connection Status Badge */}
          <div
            className="flex items-center gap-2 rounded-input border border-border px-3 py-1.5 text-xs font-medium"
            role="status"
          >
            <Activity
              className={`h-4 w-4 ${isConnected ? 'text-ok' : 'text-emergency'}`}
              aria-hidden="true"
            />
            <span className="text-ink">
              {isConnected ? 'Model Connected' : 'Offline'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};

