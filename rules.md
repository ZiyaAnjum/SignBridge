# SignBridge Coding Rules & Conventions

These conventions are strictly enforced across all components of the SignBridge monorepo.

---

## 1. File Organization & Code Quality
- **Small, focused files**: Keep files under 200 lines where practical. Single responsibility principle.
- **TypeScript strict mode**: `strict: true`, no `any`, explicit interfaces/types for all component props, states, and API payloads.
- **Type hints in Python**: All Python functions, methods, and schemas must include PEP 484 type annotations and docstrings.
- **Small, testable utilities**: Logic (landmark extraction, normalization, token mappings) should be decoupled from UI rendering and endpoint handlers.

---

## 2. Security & Configuration
- **No hard-coded secrets**: Pass all API keys, URLs, ports, and configuration via environment variables.
- **Environment files**: Always supply an updated `.env.example` mirroring required `.env` variables with safe defaults.
- **Input validation**: Validate all incoming WebSocket payloads and REST requests using Pydantic models before processing.

---

## 3. Privacy-First Data & ML Policy
- **Zero Video / Image Storage**: Under no circumstances should raw webcam video frames, photographs, or streaming buffers be saved to disk, logged, cached, or transmitted off-device.
- **Landmark Coordinates Only**: Only processed numeric skeletal coordinates (`(30, 225)` floats representing Pose and Hand keypoints) may be stored in `data/landmarks/` or streamed over WebSockets.
- **Compliance**: Adhere to healthcare and banking patient/customer confidentiality standards.

---

## 4. Architectural Boundaries
- **Keep ML code separate from API code**:
  - `ml-service/app/`: FastAPI routing, WebSocket connection handling, and serialization schemas.
  - `ml-service/scripts/` & `ml-service/models/`: Model architecture definitions, dataset loaders, training pipelines, and offline evaluation.
  - The API routes must interact with ML models via clean inference service interfaces, not embedded training scripts.

---

## 5. Verification & Testing
- **Actionable verification**: After every code change, provide exact, reproducible terminal commands to run and test the change locally.
- **Fail-fast error handling**: Provide clear, accessible user-facing error messages for denied permissions, lost connections, and low-confidence recognitions.

