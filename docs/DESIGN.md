# SignBridge Design System

## Direction
Calm, clinical, warm. Reads like a well-designed clinic or bank counter, not a tech startup. Trust and legibility over decoration.

## Colour tokens (verify every pair with a contrast checker; target WCAG AA, 4.5:1 minimum for text)
:root {
  --bg: #F7F4EE;          /* warm off-white page */
  --surface: #FFFFFF;     /* cards, panels */
  --ink: #1B1F1E;         /* primary text */
  --ink-muted: #5A6360;   /* secondary text */
  --border: #D9D4C9;
  --accent: #0E6B63;      /* deep teal: primary actions, focus */
  --accent-ink: #FFFFFF;  /* text on accent */
  --emergency: #B3261E;   /* emergency only, never decorative */
  --emergency-bg: #FCEDEB;
  --ok: #2E7D32;
  --warn: #8A5A00;
  --warn-bg: #FFF4DC;
}
Rules: one accent colour only. No gradients. No purple. Emergency red is reserved for emergency states. Never use colour alone to convey meaning (always add an icon and text label).

## Typography
- UI, captions, body: Atkinson Hyperlegible (designed for readability)
- Headings only: Source Serif 4
- Live caption: minimum 28px, weight 600, line-height 1.3
- Body: 16px minimum, line-height 1.5
- Scale: 14 / 16 / 20 / 28 / 36

## Spacing and shape
- Spacing scale (4px base): 4, 8, 12, 16, 24, 32, 48, 64. Use only these.
- Radius: 6px for inputs and buttons, 10px for cards. Nothing fully round except avatars.
- Depth: use 1px borders instead of shadows. At most one subtle shadow level for overlays.

## Layout (desktop, two panes; stack on mobile)
- Left pane: webcam preview (16:9), a landmark overlay toggle, and the live caption directly beneath it.
- Right pane: conversation timeline, newest at the bottom. Each message shows who said it (Signer / Hearing person), the text, and a small confidence indicator for signed messages.
- Bottom bar: "Speak" (hearing person) button, language selector (English / Hindi / Kannada), and a persistent Emergency button.
- A signer-confirmation step: after a sentence is built, show it with "Confirm" and "Fix" before it is spoken.

## States to design (all required)
1. Empty: no conversation yet, with one-line instructions
2. Camera permission denied: explain why camera is needed and how to enable it
3. Loading model
4. Recognising: signer detected, sign in progress
5. Low confidence: "Not sure. Please sign again." with the top 2 guesses shown
6. Confirmed sentence awaiting speech
7. Error / connection lost, with retry
8. Emergency: full-width banner, red border + icon + text "Emergency signed", persistent until dismissed, with an audible and visible alert

## Components
- Buttons: primary (accent fill), secondary (border only), destructive/emergency (emergency colour). Min height 48px, min touch target 44x44px.
- Focus: 3px accent outline with 2px offset on every interactive element. Never remove it.
- Confidence indicator: text label ("High", "Medium", "Low") + bar. Not colour only.
- Messages: left-aligned cards with a text label for the speaker, no chat-bubble tails.

## Motion
- Maximum 3 animated moments: sign recognised (brief highlight on the caption), message added (short fade), emergency banner appearing.
- Duration 150-200ms, ease-out. Respect prefers-reduced-motion by removing all motion.

## Copy tone
Plain, short, human. Examples:
- "Ready. Ask them to sign in front of the camera."
- "Not sure what you signed. Please try again."
- "Camera is blocked. Allow camera access in your browser settings."
Avoid: "Revolutionize", "seamless", "powered by AI", exclamation marks, emojis.

## Do not
- Add gradients, glassmorphism, blur backdrops, or glow effects
- Use emojis as icons (use one consistent icon set, e.g. Lucide)
- Add a marketing hero or a three-card feature grid
- Introduce new colours, fonts, or radii outside this file

