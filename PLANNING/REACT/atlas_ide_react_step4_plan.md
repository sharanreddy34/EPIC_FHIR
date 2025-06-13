# Atlas IDE: React Frontend - Step 4 Plan: Core AI Feature Implementation (Phase 1)

This document outlines the tasks for Step 4, focusing on implementing the initial versions of core AI features. This phase builds upon the interactive UI, communication channels, and feature placeholders established in Step 3. The goal is to bring foundational AI-driven "Cursor-like" and "Windsurf" functionalities to life within the Atlas IDE shell.

## A. Advanced AI Chat Functionality (`AIChatView` & Backend Integration)

### 1. Backend Communication Hook for AI Chat
*   **File:** `libs/core/core-hooks/src/lib/useAIChatAPI.ts` (New file)
*   **Task:**
    *   Create a hook to manage API calls to the FastAPI backend for chat.
    *   Define TypeScript interfaces for chat request and response payloads (e.g., `ChatMessagePayload`, `AIResponseChunk`).
    *   Implement `sendMessage(prompt: string, history: ChatMessage[], options?: { onChunk?: (chunk: AIResponseChunk) => void; onComplete?: () => void; onError?: (error: Error) => void })`.
    *   This function should handle POST requests to a designated chat endpoint (e.g., `/api/v1/chat/streaming`).
    *   Support streaming responses (e.g., using `fetch` with a readable stream, or Server-Sent Events if the backend supports it). The `onChunk` callback will be used to pass data back to the UI for real-time display.
    *   Manage loading and error states within the hook.

### 2. Integrate `useAIChatAPI` into `AIChatView.tsx`
*   **File:** `apps/atlas-ide-shell/src/components/AIChat/AIChatView.tsx` (from Step 3)
*   **Task:**
    *   Import and use `useAIChatAPI`.
    *   Replace the mock AI response logic with actual calls to `sendMessage` from the hook.
    *   Update the message list in `AIChatView`'s state based on user input and AI responses received via `onChunk` and `onComplete`.
    *   Display loading indicators (e.g., `LoadingSpinner` from `ui-core`) while waiting for the first chunk and handle API errors gracefully.

### 3. Implement Streaming UI in Chat
*   **File:** `apps/atlas-ide-shell/src/components/AIChat/AIChatView.tsx`
*   **Task:**
    *   Modify the rendering of AI messages to support streaming. The last AI message object in the state should be updated incrementally as chunks arrive from `onChunk`.
    *   Ensure the UI smoothly appends text to the current AI message block.
    *   The `status` field in the message object (e.g., `{ id: string, text: string, sender: 'ai', status: 'streaming' | 'complete' | 'error' }`) should be updated accordingly.

### 4. Implement Chat Action Buttons
*   **File:** `apps/atlas-ide-shell/src/components/AIChat/AIChatView.tsx`
*   **Task:**
    *   **Stop Generation:** If the `useAIChatAPI` hook or backend supports aborting a stream (e.g., via `AbortController`), implement this functionality for the "Stop Generation" button.
    *   **Copy Message:** Implement clipboard copy functionality for AI messages.
    *   **Regenerate Response:** Allow resending the last user prompt (or the prompt that led to the selected AI message) to the API. This might involve storing the prompt associated with each AI response.

### 5. Basic Chat History Management
*   **File:** `libs/core/core-state/src/lib/chatStore.ts` (New file, or extend `uiStore.ts`)
*   **Task:**
    *   Create a Zustand store to manage chat history (array of `ChatMessage` objects).
    *   `AIChatView.tsx` should use this store to persist messages across sessions (e.g., using `zustand/middleware/persist` with `localStorage` or `IndexedDB` - careful with PHI if real data ever enters chat context directly).
    *   Load history when the component mounts and save updates as new messages are added.

## B. Enhanced `code-server` Interaction with the `code-server` Extension for AI Features

**This section details how the React shell will communicate with the `code-server` extension to access editor information and command editor actions necessary for AI features. The `code-server` extension is responsible for all direct interactions with the Monaco editor API.**

### 1. Define New Message Types for Communication with the `code-server` Extension
*   **File:** `libs/core/core-hooks/src/lib/codeServerMessageTypes.ts` (from Step 3)
*   **Task:** Add new message types for more advanced editor interactions:
    ```typescript
    // Requests from React Shell to the `code-server` Extension (via `useCodeServerComm`)
    export interface GetSelectedTextRequest extends BaseMessageToCodeServer { type: 'GET_SELECTED_TEXT_REQUEST'; }
    export interface GetEditorContextRequest extends BaseMessageToCodeServer { type: 'GET_EDITOR_CONTEXT_REQUEST'; } // e.g., file path, language, text around cursor
    export interface InsertTextCommand extends BaseMessageToCodeServer { type: 'INSERT_TEXT_COMMAND'; payload: { text: string; position?: 'cursor' | 'selection' }; }
    export interface ReplaceTextCommand extends BaseMessageToCodeServer { type: 'REPLACE_TEXT_COMMAND'; payload: { text: string; range?: { startLine: number; startCol: number; endLine: number; endCol: number }; }; }
    export interface ShowGhostTextCommand extends BaseMessageToCodeServer { type: 'SHOW_GHOST_TEXT_COMMAND'; payload: { text: string; /* other styling/position options */ }; }
    export interface ClearGhostTextCommand extends BaseMessageToCodeServer { type: 'CLEAR_GHOST_TEXT_COMMAND'; }
    export interface ShowDiffViewCommand extends BaseMessageToCodeServer { type: 'SHOW_DIFF_VIEW_COMMAND'; payload: { originalContent: string; modifiedContent: string; languageId?: string; title?: string }; }

    // Responses from the `code-server` Extension to the React Shell (handled by `useCodeServerComm`)
    export interface GetSelectedTextResponse extends BaseMessageFromCodeServer { type: 'GET_SELECTED_TEXT_RESPONSE'; payload: { selectedText: string }; }
    export interface GetEditorContextResponse extends BaseMessageFromCodeServer { type: 'GET_EDITOR_CONTEXT_RESPONSE'; payload: { filePath: string; languageId: string; textBeforeCursor: string; textAfterCursor: string; selectedText?: string; fullContent?: string; }; }
    // Add other relevant responses (e.g., ACK for commands)
    ```

### 2. Extend `useCodeServerComm.ts` Hook for New `code-server` Extension Messages
*   **File:** `libs/core/core-hooks/src/lib/useCodeServerComm.ts` (from Step 3)
*   **Task:**
    *   Implement helper functions to send these new typed messages (e.g., `getSelectedText()`, `insertTextAtCursor(text: string)`).
    *   These functions should handle the `postMessageToIframe` call, promise resolution for request-response pairs (using `messageId` and `correlationId`), and potential timeouts.
    *   Update the `handleMessage` listener to correctly route and process the new response types **from the `code-server` extension**.

### 3. Develop a `CodeServerInteractionTest` Component (for testing communication with the `code-server` extension)
*   **File:** `apps/atlas-ide-shell/src/components/DevTools/CodeServerInteractionTest.tsx` (New component in a new `DevTools` directory)
*   **Task:**
    *   Create a UI with buttons to trigger each of the new commands/requests **to be sent to the `code-server` extension**.
    *   Display responses or confirmations in the UI or console.
    *   This component is for development and testing of the communication layer **between the React Shell and the `code-server` extension** for AI features.
    *   Integrate this component into a non-production route or a collapsible panel in the main UI for easy access during development.

## C. Ghost Text / Inline Autocompletion (Initial Implementation - Orchestrated by React Shell, Rendered by `code-server` Extension)

### 1. Logic for Ghost Text Suggestions
*   **Hook:** `libs/core/core-hooks/src/lib/useGhostText.ts` (New file)
*   **Task:**
    *   This hook will encapsulate the logic for **orchestrating** ghost text suggestions.
    *   It will use `useCodeServerComm` to request editor context (e.g., text before cursor, current line, file language) **from the `code-server` extension**. This request would be triggered by editor events (debounced content changes, which the extension would notify the shell about) or manual triggers from the shell.
    *   It will then use `useAIChatAPI` (or a new dedicated `useAISuggestionsAPI`) to request an inline completion from the backend, sending the relevant context.
    *   Backend request example: `{ prefix: string, suffix: string, languageId: string, fileName: string }`.
    *   Backend response example: `{ suggestions: [{text: string, type: 'line' | 'snippet'}] }`.

### 2. Commanding the `code-server` Extension to Display Ghost Text
*   **Hook Integration:** `useGhostText.ts`
*   **Task:**
    *   Upon receiving a suggestion from the AI backend, the `useGhostText` hook will use `useCodeServerComm` to send the `SHOW_GHOST_TEXT_COMMAND` **to the `code-server` extension**, providing the suggestion text. **The `code-server` extension is then responsible for actually rendering this text inline within the Monaco editor.**
    *   Implement a mechanism to clear ghost text (e.g., on user typing (an event the extension could signal), on editor blur (extension signal), or by the shell sending a `CLEAR_GHOST_TEXT_COMMAND` **to the `code-server` extension**).

### 3. Triggering Ghost Text (Manual for Step 4)
*   **File:** `apps/atlas-ide-shell/src/components/DevTools/CodeServerInteractionTest.tsx`
*   **Task:**
    *   Add a button: "Suggest Inline Completion".
    *   When clicked, this button will invoke a function from `useGhostText` to fetch and display a suggestion.
    *   The actual rendering of ghost text inline within Monaco is the responsibility of the `code-server` extension. The React shell's role is to provide the suggestion content and command its display.

## D. Code Context Display Component

### 1. `CodeContextDisplay.tsx` Component
*   **File:** `apps/atlas-ide-shell/src/components/ContextDisplay/CodeContextDisplay.tsx` (New file in a new `ContextDisplay` directory)
*   **Task:**
    *   This component will display information about the current editor context (e.g., file path, language, current function/class name) **as provided by the `code-server` extension**.

### 2. Fetching and Displaying Code Context
*   **Task:**
    *   Use `useCodeServerComm` hook to send `GET_EDITOR_CONTEXT_REQUEST` **to the `code-server` extension** on a relevant trigger (e.g., editor focus change event from the extension, tab change, periodically, or manual refresh button).
    *   Store the received `GetEditorContextResponse` payload in component state or a Zustand store.
    *   Render the context information using MUI components (`Typography`, `Chip`, `Paper`, `List`).
    *   Example display: "File: `/path/to/file.ts` (TypeScript) | Current Context: `function processData()`".

### 3. Integration into Layout
*   **File:** `apps/atlas-ide-shell/src/components/Layout/Sidebar.tsx` (from Step 2)
*   **Task:**
    *   Add a new collapsible section or tab within the `Sidebar` titled "Code Context".
    *   Render the `CodeContextDisplay` component within this section.

## E. Command Palette Foundation

### 1. `CommandPaletteModal.tsx` Component
*   **File:** `apps/atlas-ide-shell/src/components/CommandPalette/CommandPaletteModal.tsx` (New file in a new `CommandPalette` directory)
*   **Task:**
    *   Build the UI using MUI `Dialog` or `Modal`, an `Autocomplete` or `TextField` for input, and a `List` for displaying filtered commands.
    *   Style for clarity and ease of use.

### 2. Command Definition and Registry
*   **Interface:** Define `Command { id: string; title: string; description?: string; icon?: React.ReactElement; action: (context?: any) => void | Promise<void>; category?: string; keywords?: string[]; }` in a shared types file (e.g., `libs/core/core-types/src/lib/command.types.ts`).
*   **Hook/Service:** Create `libs/core/core-hooks/src/lib/useCommandRegistry.ts`.
    *   Provides functions `registerCommand(command: Command)` and `getCommands(): Command[]`.
    *   Store commands in a simple array or Map within the hook's scope (or a Zustand store if global registration is needed from different parts of the app).
*   **Initial Commands:** Register a few commands in `_app.tsx` or a central initialization spot:
    *   `{ id: 'theme.toggle', title: 'Toggle Dark/Light Theme', category: 'Appearance', action: () => { /* dispatch to uiStore */ } }`
    *   `{ id: 'editor.getSelectedText', title: 'Get Selected Editor Text', category: 'Editor', action: async () => { /* const selection = await hookFromUseCodeServerComm.getSelectedText(); console.log(selection); */ } }` // Placeholder for actual call via useCodeServerComm to the extension
    *   `{ id: 'ai.explainSelection', title: 'AI: Explain Selected Code', category: 'AI', action: async () => { /* get selection, send to AIChatView/useAIChatAPI */ } }`

### 3. State Management and Trigger for Palette
*   **File:** `libs/core/core-state/src/lib/uiStore.ts` (from Step 1)
*   **Task:** Add `isCommandPaletteOpen: boolean` and `toggleCommandPalette: () => void` to the store.
*   **File:** `apps/atlas-ide-shell/src/components/Layout/Header.tsx` (from Step 2)
*   **Task:** Add an `IconButton` (e.g., with a keyboard shortcut hint like `Ctrl+Shift+P` or a specific icon) to trigger `toggleCommandPalette`.
*   `CommandPaletteModal.tsx` will use `isCommandPaletteOpen` to control its visibility.

### 4. Filtering and Execution Logic
*   **File:** `apps/atlas-ide-shell/src/components/CommandPalette/CommandPaletteModal.tsx`
*   **Task:**
    *   Implement text-based filtering of commands based on user input (matching `title`, `category`, `keywords`).
    *   Allow navigation of filtered commands using arrow keys and selection with Enter.
    *   On selection, execute the command's `action()` function.

## F. FHIR Resource Interaction for AI Prompts (Enhancement)

### 1. Contextual Action in `PatientContextDisplay.tsx`
*   **File:** `apps/atlas-ide-shell/src/components/PatientDisplay/PatientContextDisplay.tsx` (from Step 3)
*   **Task:**
    *   For displayed FHIR data elements (e.g., a Condition, Medication), add a small action button or context menu item like "Send to AI Chat".
    *   When clicked, this should take the relevant FHIR data snippet (e.g., a JSON string or a formatted summary) and pass it to the AI Chat.

### 2. `AIChatView.tsx` Integration
*   **File:** `apps/atlas-ide-shell/src/components/AIChat/AIChatView.tsx`
*   **Task:**
    *   Provide a function (e.g., via Zustand or props) that allows other components to pre-fill or append text to the chat input.
    *   The "Send to AI Chat" action from `PatientContextDisplay` will call this function with a prompt like: "Tell me more about this FHIR resource: {fhir_data_snippet}".

## G. Accessibility, Storybook, and Testing

### 1. Storybook for New Components
*   **Task:** Create stories in Storybook for:
    *   `CodeContextDisplay.tsx`
    *   `CommandPaletteModal.tsx` (demonstrate open state, sample commands)
    *   Individual interactive elements from `AIChatView` if not already covered (e.g., message rendering with actions).

### 2. Accessibility (A11y) Review
*   **Task:**
    *   Ensure the Command Palette is fully keyboard accessible (open, filter, navigate, execute, close).
    *   AI Chat: Verify ARIA roles and live regions for new messages and streaming updates.
    *   Ghost Text: Plan for how screen readers will handle ghost text. **This is highly dependent on the `code-server` extension's implementation of the ghost text UI within Monaco. The React shell should coordinate with the extension team on ARIA attributes or other mechanisms the extension might expose.**
    *   Code Context Display: Ensure content is announced properly if it updates dynamically.

### 3. Manual Testing Plan
*   **Task:** Create a checklist for manually testing all new features:
    *   AI Chat: Send messages, receive streamed responses, test action buttons (copy, stop, regenerate), verify history persistence.
    *   `code-server` interactions via `CodeServerInteractionTest` component.
    *   Ghost Text: Manual trigger, verify the `SHOW_GHOST_TEXT_COMMAND` is correctly sent **to the `code-server` extension**. If the extension's display logic isn't ready, this might involve checking console logs or having the extension provide a mock confirmation response.
    *   Code Context Display: Verify it updates and shows relevant information.
    *   Command Palette: Open, filter, execute various command types, close.
    *   FHIR data to AI Chat: Select FHIR data, verify it populates chat input correctly.
    *   Overall responsiveness and UI polish for new components.

## Definition of Done for Step 4

*   AI Chat successfully communicates with a (mocked or real) backend, supporting streaming and basic user actions.
*   New message types for communication **with the `code-server` extension** for AI features are defined, and this communication can be tested via a dev component.
*   The basic mechanism for the React shell to request and orchestrate ghost text suggestions (i.e., getting context from the extension, calling AI, and commanding the **`code-server` extension** to display the suggestion) is in place.
*   `CodeContextDisplay` shows information fetched from the editor via `code-server`.
*   The Command Palette UI is functional, allowing users to search and execute a set of initial commands.
*   A basic flow for using selected FHIR data context in AI prompts is implemented.
*   New components are added to Storybook, and accessibility considerations are addressed.
*   The application remains stable and responsive.

--- 
This step makes significant strides in realizing the core AI-assisted coding experience. Subsequent steps will refine these features, connect to live backend services more deeply, and integrate with the `code-server` Monaco editor more tightly via its extension capabilities.
