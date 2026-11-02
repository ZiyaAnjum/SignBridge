import React from 'react';
import { MessageSquare, Hand, Volume2 } from 'lucide-react';
import { ConversationMessage } from '../../types';

interface TimelineProps {
  messages: ConversationMessage[];
  isEmpty: boolean;
}

export const Timeline: React.FC<TimelineProps> = ({ messages, isEmpty }) => {
  return (
    <section
      className="flex flex-1 flex-col rounded-card border border-border bg-surface p-4"
      aria-label="Conversation timeline"
    >
      {/* Header */}
      <div className="mb-3 flex items-center justify-between border-b border-border pb-2">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-accent" aria-hidden="true" />
          <h2 className="font-serif text-lg font-bold text-ink">
            Conversation History
          </h2>
        </div>
        <span className="text-xs text-ink-muted">
          {messages.length} {messages.length === 1 ? 'message' : 'messages'}
        </span>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 space-y-3 overflow-y-auto pr-1 min-h-[360px] max-h-[520px]">
        {/* State 1: Empty State */}
        {isEmpty || messages.length === 0 ? (
          <div
            className="flex h-full min-h-[300px] flex-col items-center justify-center p-6 text-center"
            role="status"
          >
            <div className="mb-3 rounded-full border border-border bg-bg p-3 text-ink-muted">
              <Hand className="h-6 w-6" aria-hidden="true" />
            </div>
            <h3 className="font-serif text-base font-bold text-ink">
              No conversation yet
            </h3>
            <p className="mt-1 text-sm text-ink-muted max-w-sm">
              Ready. Ask them to sign in front of the camera.
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isSigner = msg.speaker === 'signer';
            return (
              <article
                key={msg.id}
                className="rounded-card border border-border bg-bg p-4 animate-fade-in text-left"
              >
                {/* Speaker Header */}
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {isSigner ? (
                      <span className="inline-flex items-center gap-1.5 rounded-input border border-border bg-surface px-2.5 py-0.5 text-xs font-bold text-accent">
                        <Hand className="h-3.5 w-3.5" aria-hidden="true" />
                        Signer
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-input border border-border bg-surface px-2.5 py-0.5 text-xs font-bold text-ink">
                        <Volume2 className="h-3.5 w-3.5 text-ink-muted" aria-hidden="true" />
                        Hearing Person
                      </span>
                    )}
                    <time className="text-xs text-ink-muted">{msg.timestamp}</time>
                  </div>

                  {/* Confidence Indicator for Signed Messages */}
                  {isSigner && msg.confidence !== undefined && (
                    <div
                      className="flex items-center gap-1.5"
                      aria-label={`Confidence: ${msg.confidenceTier} (${Math.round(msg.confidence * 100)} percent)`}
                    >
                      <span className="text-xs font-semibold text-ink-muted">
                        {msg.confidenceTier} ({Math.round(msg.confidence * 100)}%)
                      </span>
                      <div className="h-1.5 w-10 overflow-hidden rounded-input bg-border">
                        <div
                          className={`h-full ${
                            msg.confidenceTier === 'High'
                              ? 'bg-ok'
                              : msg.confidenceTier === 'Medium'
                              ? 'bg-warn'
                              : 'bg-emergency'
                          }`}
                          style={{ width: `${Math.round(msg.confidence * 100)}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Message Body */}
                <p className="font-sans text-base text-ink leading-relaxed font-medium">
                  {msg.text}
                </p>

                {/* Multilingual translations */}
                {msg.translatedText && (
                  <div className="mt-2 border-t border-border/60 pt-2 text-xs text-ink-muted space-y-0.5">
                    {msg.translatedText.hindi && (
                      <p>
                        <span className="font-semibold text-ink">Hindi:</span> {msg.translatedText.hindi}
                      </p>
                    )}
                    {msg.translatedText.kannada && (
                      <p>
                        <span className="font-semibold text-ink">Kannada:</span> {msg.translatedText.kannada}
                      </p>
                    )}
                  </div>
                )}
              </article>
            );
          })
        )}
      </div>
    </section>
  );
};

