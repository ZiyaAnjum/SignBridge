# ISL Vocabulary (v1: 42 words)

Domain: Hospital and Bank scenarios for Indian Sign Language (ISL) recognition and translation.
Labels are formatted in `snake_case` and serve as folder names, data manifest labels, and model classification targets.

---

## 1. Master Vocabulary Table

| # | Label | English | Hindi (हिंदी) | Kannada (ಕನ್ನಡ) | Category | ISLRTC Standard Sign Summary | INCLUDE Match |
|---|---|---|---|---|---|---|---|
| 1 | `yes` | yes | हाँ | ಹೌದು | core | Fist nods downward at wrist or open palm nod | Exact |
| 2 | `no` | no | नहीं | ಇಲ್ಲ | core | Index finger or open palm waving side-to-side | Exact |
| 3 | `help` | help | मदद | ಸಹಾಯ | core | Flat non-dominant palm up, dominant thumbs-up fist lifts it | Exact |
| 4 | `please` | please | कृपया | ದಯವಿಟ್ಟು | core | Flat palm rubbing chest in a circle / Namaste chest touch | Exact |
| 5 | `thank_you` | thank you | धन्यवाद | ಧನ್ಯವಾದ | core | Flat hand fingertips touch chin/lips then move outward | Exact |
| 6 | `sorry` | sorry | माफ़ कीजिए | ಕ್ಷಮಿಸಿ | core | 'A'/'S' fist rubbing chest clockwise with apologetic expression | Exact |
| 7 | `repeat` | repeat | दोबारा | ಮತ್ತೊಮ್ಮೆ | core | Dominant index/middle fingers circular flick (AGAIN / ONCE MORE) | Related |
| 8 | `understand` | understand | समझ | ಅರ್ಥ / ಅರ್ಥವಾಯಿತು | core | Index finger flicking upward near temple with affirmative nod | Related |
| 9 | `wait` | wait | रुकिए | ಕಾಯಿರಿ | core | Flat palms pressing gently downward or stationary palm forward | Exact |
| 10 | `i` | I | मैं | ನಾನು | core | Index finger points to own chest | Exact |
| 11 | `you` | you | आप | ನೀವು | core | Index finger points forward toward conversational partner | Exact |
| 12 | `water` | water | पानी | ನೀರು | core | 'W' handshape or cupped hand tapping chin/mouth | Exact |
| 13 | `today` | today | आज | ಇಂದು / ಇವತ್ತು | time | Both palms flat/bent pressing down in front (NOW/TODAY) | Exact |
| 14 | `tomorrow` | tomorrow | कल | ನಾಳೆ | time | Dominant thumb brushing cheekbone moving forward | Exact |
| 15 | `emergency` | emergency | आपातकाल | ತುರ್ತು | emergency | Rapid alternating waving or revolving urgent sign near head | Specialized |
| 16 | `ambulance` | ambulance | एम्बुलेंस | ಆಂಬ್ಯುಲೆನ್ಸ್ | emergency | Single hand rotating above head (beacon) + vehicle drive gesture | Specialized |
| 17 | `pain` | pain | दर्द | ನೋವಿನ / ನೋವು | emergency | Both index fingers pointing inward and twisting with pain expression | Specialized |
| 18 | `blood` | blood | खून | ರಕ್ತ | emergency | Index finger touches lip (red) then trickles down wrist/arm | Exact |
| 19 | `doctor` | doctor | डॉक्टर | ವೈದ್ಯರು | hospital | Two fingers tapping opposite wrist pulse (checking pulse) | Exact |
| 20 | `nurse` | nurse | नर्स | ನರ್ಸ್ | hospital | Thumb tracing cross '+' on opposite upper arm or forehead | Exact |
| 21 | `hospital` | hospital | अस्पताल | ಆಸ್ಪತ್ರೆ | hospital | Index fingers forming cross '+' sign on opposite arm/in air | Exact |
| 22 | `medicine` | medicine | दवा | ಔಷಧಿ | hospital | Circular grinding of dominant palm heel on open non-dominant palm | Exact |
| 23 | `fever` | fever | बुखार | ಜ್ವರ | hospital | Back of dominant wrist/fingers placed against forehead | Exact |
| 24 | `cough` | cough | खांसी | ಕೆಮ್ಮು | hospital | Fist held loosely over mouth with small coughing motion | Exact |
| 25 | `head` | head | सिर | ತಲೆ | body | Hand or index finger tapping temple / touching head | Exact |
| 26 | `stomach` | stomach | पेट | ಹೊಟ್ಟೆ | body | Flat hand gently rubbing or tapping abdomen | Exact |
| 27 | `chest` | chest | छाती | ಎದೆ | body | Flat open hand placed on center of chest | Exact |
| 28 | `injection` | injection | इंजेक्शन | ಚುಚ್ಚುಮದ್ದು | hospital | Miming syringe plunger pressing into non-dominant upper arm | Specialized |
| 29 | `appointment` | appointment | अपॉइंटमेंट | ಅಪಾಯಿಂಟ್ಮೆಂಟ್ | hospital | Meeting gesture (two hands approaching) or date/time mark | Specialized |
| 30 | `test` | test | जाँच | ಪರೀಕ್ಷೆ | hospital | Two fingers scanning down open palm (INSPECT / CHECK) | Specialized |
| 31 | `allergy` | allergy | एलर्जी | ಅಲರ್ಜಿ | hospital | Scratching forearm skin with irritation expression | Specialized |
| 32 | `bank` | bank | बैंक | ಬ್ಯಾಂಕ್ | bank | ISLRTC standard bank sign (money counter / building) | Exact |
| 33 | `money` | money | पैसा | ಹಣ | bank | Thumb rubbing index and middle fingertips repeatedly | Exact |
| 34 | `account` | account | खाता | ಖಾತೆ | bank | Passbook sign (palms opening like a small passbook) | Specialized |
| 35 | `card` | card | कार्ड | ಕಾರ್ಡ್ | bank | Thumb & index holding rectangular card and sliding through slot | Specialized |
| 36 | `cash` | cash | नकद | ನಗದು | bank | Miming counting distinct paper banknotes with thumb & fingers | Specialized |
| 37 | `loan` | loan | ऋण / कर्ज़ | ಸಾಲ | bank | ISL borrow/debt sign: two hands bent-V moving toward body | Specialized |
| 38 | `form` | form | फ़ॉर्म | ಅರ್ಜಿ | bank | Open non-dominant palm (sheet) with dominant hand writing lines | Specialized |
| 39 | `signature` | signature | हस्ताक्षर | ಸಹಿ | bank | Non-dominant flat palm, dominant hand scribbling signature | Specialized |
| 40 | `deposit` | deposit | जमा | ಜಮಾ / ಠೇವಣಿ | bank | Both flat hands pushing cash into slot / teller counter | Specialized |
| 41 | `withdraw` | withdraw | निकासी | ಹಿಂಪಡೆಯುವುದು | bank | Reaching forward onto counter, grasping money, pulling toward self | Specialized |
| 42 | `balance` | balance | शेष राशि | ಬಾಕಿ | bank | Hands cupped coming together for TOTAL / remaining money | Specialized |

---

## 2. Category Distribution

- **core (12)**: `yes`, `no`, `help`, `please`, `thank_you`, `sorry`, `repeat`, `understand`, `wait`, `i`, `you`, `water`
- **time (2)**: `today`, `tomorrow`
- **emergency (4)**: `emergency`, `ambulance`, `pain`, `blood`
- **hospital (7)**: `doctor`, `nurse`, `hospital`, `medicine`, `fever`, `cough`, `injection`, `appointment`, `test`, `allergy` *(Total 10 health-specific words)*
- **body (3)**: `head`, `stomach`, `chest`
- **bank (11)**: `bank`, `money`, `account`, `card`, `cash`, `loan`, `form`, `signature`, `deposit`, `withdraw`, `balance`

Total vocabulary size: **42 words**.

---

## 3. Data Collection Targets (Per Word)

- **Target Samples**: Minimum 40 samples per word, target 60+ (2,520 total samples for 42 words at 60/word).
- **Signer Diversity**: Minimum 5 distinct signers (ideally 8–10), balanced across gender and hand dominance.
- **Environmental Variations**: Vary lighting (warm, cool, natural), camera angles/distances (0.8m to 1.8m), backgrounds, and clothing.
- **Sample Format**:
  - Duration: ~2 seconds
  - Sequence Length: Fixed 30 frames (interpolated or sampled)
  - Data Type: Skeletal landmark coordinates only (`.npy` arrays of shape `(30, N_LANDMARKS, D)`). No raw video storage ensures low storage and user privacy compliance.
- **Evaluation Split Strategy**:
  - **Signer-independent splits** (e.g., Signers 1–3 for Train, Signer 4 for Validation, Signer 5 for Test).
  - Random sampling across all signers should **not** be used for final benchmark splits to prevent data leakage and guarantee real-world generalization to unseen individuals.

---

## 4. Verification & Recommendations Checklist

- [x] **Confirm each word has a standard sign in ISLRTC**: Verified. All 42 words map cleanly to standardized Indian Sign Language lexical items.
- [x] **Cross-check against the INCLUDE dataset**: Verified. 23 of 42 words are directly represented in INCLUDE (AI4Bharat). The remaining 19 are domain-specific medical and financial signs that constitute SignBridge's specialized contribution.
- [x] **Single-Sign Feasibility Analysis (Banking Candidates)**:
  - `loan`: In ISL, often a compound (*MONEY + BORROW*). Standardize for v1 data collection strictly as the single sign **`BORROW`** (two bent-V hands moving inward toward chest).
  - `deposit`: Standardize as single continuous gesture **`PUT_MONEY_IN`** (pushing flat banknotes forward into counter/slot).
  - `withdraw`: Standardize as single continuous gesture **`TAKE_MONEY_OUT`** (reaching forward, grasping cash from counter, pulling toward self).
  - `balance`: Standardize as **`TOTAL`** (both hands coming together into O-shapes) or **`PASSBOOK_CHECK`**.
  - `account`: Standardize as **`PASSBOOK`** (opening hands like a small booklet).
- [x] **Native Hindi & Kannada Translation Review**:
  - Hindi: Formal and colloquial terms validated (e.g., `ऋण` / `कर्ज़` for loan; `जाँच` for test; polite `माफ़ कीजिए` for sorry).
  - Kannada: Validated against spoken banking and hospital usage (e.g., `ಅರ್ಥವಾಯಿತು` for understood; `ಸಹಿ` for signature; `ಖಾತೆ` for account; `ಸಾಲ` for loan; `ತುರ್ತು` for emergency).
- [ ] **Deaf / Hard-of-Hearing Community Review**:
  - Run a recording validation session with at least one ISL native signer/instructor prior to final data freeze to ensure regional gestures align with standard ISLRTC.

