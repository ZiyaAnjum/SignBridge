# ISL Vocabulary (v1: 42 words)

Domain: hospital and bank scenarios. Labels are snake_case and are used as folder names and model classes.

| # | label | English | Hindi | Kannada | Category |
|---|---|---|---|---|---|
| 1 | yes | yes | हाँ | ಹೌದು | core |
| 2 | no | no | नहीं | ಇಲ್ಲ | core |
| 3 | help | help | मदद | ಸಹಾಯ | core |
| 4 | please | please | कृपया | ದಯವಿಟ್ಟು | core |
| 5 | thank_you | thank you | धन्यवाद | ಧನ್ಯವಾದ | core |
| 6 | sorry | sorry | माफ़ कीजिए | ಕ್ಷಮಿಸಿ | core |
| 7 | repeat | repeat | दोबारा | ಮತ್ತೊಮ್ಮೆ | core |
| 8 | understand | understand | समझ | ಅರ್ಥ | core |
| 9 | wait | wait | रुकिए | ಕಾಯಿರಿ | core |
| 10 | i | I | मैं | ನಾನು | core |
| 11 | you | you | आप | ನೀವು | core |
| 12 | water | water | पानी | ನೀರು | core |
| 13 | today | today | आज | ಇಂದು | time |
| 14 | tomorrow | tomorrow | कल | ನಾಳೆ | time |
| 15 | emergency | emergency | आपातकाल | ತುರ್ತು | emergency |
| 16 | ambulance | ambulance | एम्बुलेंस | ಆಂಬ್ಯುಲೆನ್ಸ್ | emergency |
| 17 | pain | pain | दर्द | ನೋವು | emergency |
| 18 | blood | blood | खून | ರಕ್ತ | emergency |
| 19 | doctor | doctor | डॉक्टर | ವೈದ್ಯರು | hospital |
| 20 | nurse | nurse | नर्स | ನರ್ಸ್ | hospital |
| 21 | hospital | hospital | अस्पताल | ಆಸ್ಪತ್ರೆ | hospital |
| 22 | medicine | medicine | दवा | ಔಷಧಿ | hospital |
| 23 | fever | fever | बुखार | ಜ್ವರ | hospital |
| 24 | cough | cough | खांसी | ಕೆಮ್ಮು | hospital |
| 25 | head | head | सिर | ತಲೆ | body |
| 26 | stomach | stomach | पेट | ಹೊಟ್ಟೆ | body |
| 27 | chest | chest | छाती | ಎದೆ | body |
| 28 | injection | injection | इंजेक्शन | ಚುಚ್ಚುಮದ್ದು | hospital |
| 29 | appointment | appointment | अपॉइंटमेंट | ಅಪಾಯಿಂಟ್ಮೆಂಟ್ | hospital |
| 30 | test | test | जाँच | ಪರೀಕ್ಷೆ | hospital |
| 31 | allergy | allergy | एलर्जी | ಅಲರ್ಜಿ | hospital |
| 32 | bank | bank | बैंक | ಬ್ಯಾಂಕ್ | bank |
| 33 | money | money | पैसा | ಹಣ | bank |
| 34 | account | account | खाता | ಖಾತೆ | bank |
| 35 | card | card | कार्ड | ಕಾರ್ಡ್ | bank |
| 36 | cash | cash | नकद | ನಗದು | bank |
| 37 | loan | loan | ऋण | ಸಾಲ | bank |
| 38 | form | form | फ़ॉर्म | ಅರ್ಜಿ | bank |
| 39 | signature | signature | हस्ताक्षर | ಸಹಿ | bank |
| 40 | deposit | deposit | जमा | ಜಮಾ | bank |
| 41 | withdraw | withdraw | निकासी | ಹಿಂಪಡೆಯುವುದು | bank |
| 42 | balance | balance | शेष राशि | ಬಾಕಿ | bank |

## Data collection targets (per word)
- Minimum 40 samples per word, ideally 60+
- At least 5 different signers
- Vary lighting, distance from camera, background, and clothing
- Each sample: about 2 seconds, 30 frames, saved as landmark arrays only (no video)
- Split by signer, not by random sample, so test accuracy reflects unseen people

## Verification checklist
- [ ] Confirm each word has a standard sign in the ISLRTC Indian Sign Language dictionary
- [ ] Cross-check against the INCLUDE dataset vocabulary and note overlaps
- [ ] Replace any word without a clear single sign (candidates: loan, deposit, withdraw, balance)
- [ ] Have a native Hindi and Kannada speaker check the translations
- [ ] Have at least one deaf or hard-of-hearing signer review the final list
