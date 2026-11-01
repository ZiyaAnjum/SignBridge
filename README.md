# SignBridge: Indian Sign Language (ISL) Recognition & Translation

SignBridge is an assistive communication system bridging Indian Sign Language (ISL) users with healthcare providers and banking professionals. It recognizes dynamic ISL gestures captured as 30-frame skeletal landmark sequences and translates them into multilingual text and audio (English, Hindi, and Kannada).

---

## 1. Vocabulary (v1: 42 Words)

The v1 vocabulary focuses on high-frequency **hospital** and **bank** scenarios:
- **Core (12)**: `yes`, `no`, `help`, `please`, `thank_you`, `sorry`, `repeat`, `understand`, `wait`, `i`, `you`, `water`
- **Time (2)**: `today`, `tomorrow`
- **Emergency (4)**: `emergency`, `ambulance`, `pain`, `blood`
- **Hospital / Health (10)**: `doctor`, `nurse`, `hospital`, `medicine`, `fever`, `cough`, `injection`, `appointment`, `test`, `allergy`
- **Body Parts (3)**: `head`, `stomach`, `chest`
- **Bank / Finance (11)**: `bank`, `money`, `account`, `card`, `cash`, `loan`, `form`, `signature`, `deposit`, `withdraw`, `balance`

Full definitions, ISLRTC standard sign descriptions, and language translations are documented in [VOCABULARY.md](VOCABULARY.md) and [config/vocabulary.json](config/vocabulary.json).

---

## 2. Data Collection Protocol

- **Target Samples**: Minimum 40 samples/word (Target: 60+).
- **Signer Diversity**: $\ge 5$ distinct signers.
- **Privacy & Storage**: Landmark arrays **only** (`.npy` format, shape `(30, 225)` covering 33 Pose + 21 Left Hand + 21 Right Hand coordinates). No raw video is stored.
- **Signer-Independent Split**: Split train/val/test strictly by signer ID to evaluate generalization on unseen users.

### Starting Data Collection
```bash
python scripts/collect_landmarks.py --signer signer_01 --samples 40
```

### Auditing Dataset Progress
```bash
python scripts/inspect_dataset.py
```

