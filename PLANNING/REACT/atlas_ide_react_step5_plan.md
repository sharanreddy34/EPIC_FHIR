# Atlas IDE: React Frontend - Step 5 Plan: Advanced AI, FHIR Tooling & DX Refinements

This document outlines the tasks for Step 5, focusing on advancing the AI capabilities, deepening FHIR-specific tooling, refining the developer experience (DX), and polishing the UI. This step builds significantly on the features implemented in Step 4.

## A. Advanced AI Chat & Contextual Understanding

### 1. Multi-File Context for AI Chat
*   **Concept:** Allow the AI Chat to be aware of multiple open files or a selection of files/folders relevant to the user's current query.
*   **`useAIChatAPI.ts` & Backend:** 
    *   Modify `sendMessage` to accept an optional `contextFiles: { filePath: string; content?: string; }[]` parameter.
    *   The backend needs to be updated to process this multi-file context.
*   **`AIChatView.tsx` & UI:**
    *   Introduce a UI mechanism for the user to select files/folders to include in the chat context (e.g., a small tree view, or a button "Add current file to AI context").
    *   The `CodeContextDisplay.tsx` could also list "Chat Context Files" and allow removal.
    *   Visually indicate in the chat prompt or system message when multi-file context is being used.
*   **`code-server` Extension Communication:**
    *   New message `GET_FILE_CONTENT_BATCH_REQUEST` from React **to the `code-server` extension** to fetch content for multiple files efficiently.
    *   Corresponding `GET_FILE_CONTENT_BATCH_RESPONSE` (from the extension).

### 2. AI Chat: Threaded Conversations & History Enhancement
*   **`chatStore.ts` & `AIChatView.tsx`:**
    *   Modify chat history to support threads or distinct conversations. Each thread could have its own context (including multi-file context).
    *   Enhance UI to display and navigate between chat threads (e.g., a separate panel or a dropdown).
    *   Consider more robust history persistence, potentially allowing users to name or tag conversations.

### 3. AI-Assisted Code Refactoring Preview (using Diff View)
*   **Concept:** AI suggests a refactoring for selected code, and the user sees a diff preview before applying.
*   **`useAIChatAPI.ts` (or new `useAIRefactorAPI.ts`):**
    *   New API endpoint `/api/v1/ai/suggest_refactor` taking `{ code: string, languageId: string, instruction: string, contextFiles?: ... }`.
    *   Response should be `{ suggestedCode: string }`.
*   **Integration with `AIChatView` or Command Palette:**
    *   New AI command: "AI: Suggest Refactor for Selection".
    *   On receiving `suggestedCode` from the AI backend, the React shell will use `useCodeServerComm` to send the `SHOW_DIFF_VIEW_COMMAND` (from Step 4) **to the `code-server` extension**, providing the original and suggested content. The extension is responsible for rendering the diff.
    *   Add "Apply Refactor" and "Discard" buttons to the diff view (which is rendered by the extension but could have controls managed or influenced by the shell) or an associated UI panel in the shell. Applying the refactor would involve the shell sending the `REPLACE_TEXT_COMMAND` **to the `code-server` extension** with the `suggestedCode`.

## B. Deeper FHIR Integration & Tooling

### 1. Live FHIR Server Connectivity & Data Fetching
*   **`PatientContextDisplay.tsx` & `apolloClient.ts`:**
    *   Move beyond mock data. Configure TanStack Query to fetch data from a real (or dev instance) FHIR server (e.g., Palantir Foundry-proxied FHIR endpoint via REST APIs).
    *   Implement authentication/authorization token handling for FHIR API calls (this is critical and may require coordination with backend and `code-server` for token propagation if the **`code-server` extension** also makes FHIR calls).
    *   Update GraphQL queries in `libs/core/core-graphql` to reflect actual FHIR server capabilities.
    *   Allow user to input/select a Patient ID to fetch live data.
*   **Error Handling:** Robust error handling for FHIR API calls (network errors, auth errors, resource not found).

### 2. FHIR Resource Validation in Editor
*   **Concept:** Provide real-time validation for FHIR JSON resources being edited.
*   **`code-server` Extension Prerequisite:** This heavily relies on a **`code-server` extension** capable of FHIR validation (e.g., using `fhir.js` or official FHIR validator tooling).
*   **`useCodeServerComm.ts` & Message Types (from Step 4 suggestions):
    *   The React shell will listen for `FHIR_VALIDATION_RESULT` messages **from the `code-server` extension**.
*   **React UI: `ProblemsView.tsx` (New Component)
    *   Create a new panel/tab (e.g., in the bottom panel or sidebar) to display diagnostics (errors, warnings) from various sources, including FHIR validation.
    *   Clicking a problem should ideally navigate to the relevant line in the editor (this requires the React shell to send a `GO_TO_LOCATION_REQUEST` message **to the `code-server` extension**).

### 3. FHIR Schema-Aware Autocompletion (via Ghost Text or `code-server`)
*   **Concept:** Provide contextually relevant autocompletions for FHIR resource fields and values.
*   **`useGhostText.ts` Enhancement:**
    *   If the current file is identified as FHIR (e.g., `languageId === 'fhir-json'`), the context sent to the AI for suggestions should explicitly note this.
    *   The AI backend providing suggestions needs to be trained or prompted to offer valid FHIR fields or valueSet options.
*   **`code-server` Extension Long-Term:** A more robust solution involves the **`code-server` extension** providing direct Monaco autocompletions based on FHIR schemas. The React shell would benefit from this automatically without direct orchestration of these specific autocompletions.

### 4. Basic FHIR Resource Navigator/Explorer
*   **`FhirResourceExplorer.tsx` (New Component in `libs/features/fhir-display`):
    *   A tree-like view to navigate a loaded FHIR resource's structure (e.g., a Patient and its referenced Organizations, Practitioners, Conditions).
    *   Clicking elements could show details or allow sending specific parts to AI chat.
    *   Integrate into a new Sidebar tab or a dedicated view.

## C. Developer Experience (DX) & UI Polish

### 1. Application Settings Panel
*   **`SettingsPanel.tsx` (New Component):
    *   Allow users to configure basic IDE settings.
    *   Examples: Theme (Dark/Light/System), AI service endpoint (if configurable), default AI model, `code-server` URL (if not fixed).
*   **`settingsStore.ts` (New Zustand Store in `libs/core/core-state`):
    *   Persist settings using `localStorage`.
    *   Components and hooks should consume settings from this store.
*   **Integration:** Accessible via Command Palette and/or a gear icon in the `Header`.

### 2. Enhanced Error Handling & Notifications
*   **`NotificationProvider.tsx` & `useNotifier.ts` (New in `libs/core/core-hooks` or `ui-core`):
    *   A global system for displaying toast notifications (e.g., using MUI `Snackbar`).
    *   `useNotifier` hook: `notify.success(message)`, `notify.error(message)`, `notify.info(message)`.
    *   Integrate this throughout the app for user feedback (API call success/failure, **`code-server` extension** command ACKs, etc.).

### 3. UI Consistency and Refinement
*   **Task:** Conduct a review of all existing UI components and views.
    *   Ensure consistent use of MUI theme (spacing, typography, colors).
    *   Improve responsiveness and visual appeal across different sidebar widths.
    *   Check for consistent icon usage (`@mui/icons-material`).
    *   Refine loading states and transitions to be smoother.

### 4. Advanced Keyboard Shortcuts Management
*   **Concept:** Allow users to view and potentially customize some keyboard shortcuts.
*   **`useKeyboardShortcuts.ts` (New hook in `libs/core/core-hooks`):
    *   Centralize registration and handling of global keyboard shortcuts (e.g., for opening Command Palette, toggling Sidebar).
    *   Potentially display a list of active shortcuts in a help section or the `SettingsPanel`.

## D. Foundational Work for Future Steps

### 1. Telemetry & Analytics (Opt-in)
*   **Concept:** Plan for collecting basic, anonymized usage data to improve the IDE (feature usage, performance metrics). **Crucial: Must be opt-in and HIPAA compliant (no PHI).**
*   **`telemetryService.ts` (New in `libs/core/core-utils`):
    *   Stub out functions for tracking events (e.g., `trackEvent(eventName, properties)`).
    *   Integrate with a chosen analytics provider (if any).
    *   Ensure any PHI is meticulously scrubbed before sending if data is ever sourced from user content.

## E. Testing, Accessibility, and Documentation

### 1. Unit and Integration Tests
*   **Task:** Increase test coverage for critical hooks (`useAIChatAPI`, `useCodeServerComm`, `useGhostText`) and complex components (`AIChatView`, `CommandPaletteModal`).
*   Write integration tests for core user flows (e.g., sending chat message and receiving response, executing a command palette action that interacts with the **`code-server` extension**).

### 2. Accessibility Audit
*   **Task:** Perform a more thorough accessibility audit of all new and existing features, focusing on WCAG 2.2 AA.
    *   Test with screen readers for AI chat, command palette, FHIR data displays, and settings.
    *   Verify complex interactions like diff views are accessible.

### 3. Update Developer Documentation
*   **Task:** Document new architectural decisions, core hooks, **`code-server` extension** message protocols, and FHIR integration strategies.

## Definition of Done for Step 5

*   AI Chat supports basic multi-file context and threaded conversations (UI placeholders acceptable for full thread management).
*   Users can preview AI-suggested refactorings using a diff view.
*   `PatientContextDisplay` fetches and displays live data from a configured FHIR server (auth handled).
*   Basic FHIR resource validation results (from `code-server` extension) can be displayed in a dedicated 'Problems' view.
*   An initial `SettingsPanel` allows users to configure at least theme and one AI-related setting.
*   A global notification system is implemented and used for key actions.
*   Significant progress on test coverage and accessibility for features developed up to Step 5.

--- 
This step aims to elevate Atlas IDE from a promising foundation to a genuinely powerful and healthcare-aware assistant, setting the stage for even more advanced capabilities.
