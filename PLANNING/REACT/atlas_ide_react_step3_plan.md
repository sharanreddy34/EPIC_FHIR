# Atlas IDE: React Frontend - Step 3 Plan: Interactive UI, Communication & Feature Placeholders

This document outlines the tasks for Step 3, focusing on adding interactivity to the shell, setting up initial `code-server` communication, and creating placeholders for core FHIR data display and AI chat functionalities. Granularity is increased to provide clearer sub-tasks.

## A. Interactive Sidebar (`apps/atlas-ide-shell` & `libs/core/core-state`)

1.  **Integrate Zustand for Sidebar State:**
    *   **File (Store):** `libs/core/core-state/src/lib/uiStore.ts` (from Step 1)
    *   **Task:** Ensure `isSidebarOpen` state and `toggleSidebar` action are correctly defined.
    *   **File (Component):** `apps/atlas-ide-shell/src/components/Layout/Sidebar.tsx` (from Step 2)
    *   **Task:** 
        *   Use the `useUIStore` hook to consume `isSidebarOpen` and `toggleSidebar`.
        *   Control the MUI `Drawer`'s `open` prop with `isSidebarOpen`.
        *   The `onClose` prop of the Drawer should call `toggleSidebar` if it's intended to be dismissible by clicking outside or an explicit close button within the sidebar.

2.  **Add Sidebar Toggle Control:**
    *   **File:** `apps/atlas-ide-shell/src/components/Layout/Header.tsx` (from Step 2)
    *   **Task:**
        *   Add an MUI `IconButton` (e.g., with a Menu icon from `@mui/icons-material`) to the `Header`.
        *   On click, this button should call the `toggleSidebar` action from `useUIStore`.

3.  **Refine Layout Responsiveness to Sidebar State:**
    *   **File:** `apps/atlas-ide-shell/src/components/Layout/Layout.tsx` (from Step 2)
    *   **Task:**
        *   Ensure the main content area correctly resizes or shifts when the sidebar opens/closes. This might involve adjusting MUI `Box` properties or using `Grid` components for layout management.
        *   Verify smooth transitions.

4.  **Structure Sidebar Content Sections:**
    *   **File:** `apps/atlas-ide-shell/src/components/Layout/Sidebar.tsx`
    *   **Task:**
        *   Within the `Drawer`, create distinct sections using MUI `Box`, `List`, `ListItem`, `Typography`, or `Divider`.
        *   Label these sections, e.g., "AI Assistant" and "Patient Data".
        *   **UX Improvement:** Implement collapsible functionality for these sections (e.g., using MUI `Accordion` or `Collapse`) to manage space effectively in the narrow sidebar.
        *   These sections will house the `AIChatView` and `PatientContextDisplay` components later. **The use of collapsible sections is highly recommended to maximize usability within the constrained width of the Epic sidebar.**

## B. `code-server` Communication Setup (`libs/core/core-hooks` & `apps/atlas-ide-shell`)

**This section details the setup for communication between the React shell and a dedicated `code-server` extension. This extension will be responsible for interacting with the Monaco editor API, accessing VSCodium features, and performing editor-specific tasks on behalf of the React shell.**

1.  **Define Message Interfaces:**
    *   **File:** `libs/core/core-hooks/src/lib/codeServerMessageTypes.ts` (New file)
    *   **Task:** Create TypeScript interfaces for messages sent to and received from **the `code-server` extension**. This defines the contract for their interaction.
        ```typescript
        // Example message types
        export type MessageToCodeServerType = 'INIT_CONTEXT' | 'EXECUTE_COMMAND' | 'GET_FILE_CONTENT';
        export interface BaseMessageToCodeServer {
          type: MessageToCodeServerType;
          payload?: any;
          messageId: string;
        }

        export type MessageFromCodeServerType = 'CONTEXT_READY' | 'COMMAND_RESULT' | 'FILE_CONTENT_RESULT' | 'ERROR';
        export interface BaseMessageFromCodeServer {
          type: MessageFromCodeServerType;
          payload?: any;
          correlationId?: string; // To correlate with a sent message
        }

        // Specific message examples (extend as needed)
        export interface InitContextMessage extends BaseMessageToCodeServer {
          type: 'INIT_CONTEXT';
          payload: { patientId?: string; encounterId?: string; fhirUser?: string };
        }
        ```

2.  **Refine `useCodeServerComm.ts` Hook:**
    *   **File:** `libs/core/core-hooks/src/lib/useCodeServerComm.ts` (from Step 1)
    *   **Task:**
        *   Import and use the defined message types.
        *   Enhance `postMessageToIframe` to accept typed messages and ensure `messageId` generation.
        *   Improve the `handleMessage` listener:
            *   Strictly check `event.origin` against the expected `code-server` origin (configurable, perhaps via an environment variable). **Security Note:** Ensure `postMessageToIframe` also uses a specific `targetOrigin` (not `'*'`) in production environments for secure communication with the `code-server` iframe hosting the extension.
            *   Use a type guard or switch statement to handle different `BaseMessageFromCodeServer` types.
            *   Implement a basic callback registry or event emitter within the hook so other parts of the **React shell application** can subscribe to specific message types received **from the `code-server` extension**.
            *   **Robustness:** Implement basic error handling for message posting (e.g., logging failures, potential timeouts if applicable) and reception.

3.  **Connect `CodeServerView.tsx` to the Hook:**
    *   **File:** `apps/atlas-ide-shell/src/components/CodeServerView/CodeServerView.tsx` (from Step 1)
    *   **Task:**
        *   Create a `ref` for the `iframe` element.
        *   Instantiate `useCodeServerComm` hook (which manages communication **with the `code-server` extension**), passing the `iframe` ref.
        *   Add a `useEffect` to send an initial `INIT_CONTEXT` message (with mock data) **to the `code-server` extension** once the iframe is loaded (use the `onLoad` event of the iframe). This message can provide initial context like patient ID or user details to the extension.
        *   Log received messages (from the `code-server` extension) to the console for now to demonstrate two-way communication setup.

## C. Initial FHIR Data Display (Mocked - `apps/atlas-ide-shell` or new `libs/features/fhir-display`)

1.  **Define Mock GraphQL Query & Data:**
    *   **File:** `libs/core/core-graphql/src/lib/queries/patientQueries.ts` (New file or extend existing)
    *   **Task:** Define a simple GraphQL query for mock patient data.
        ```graphql
        # Example query (will be against a mock resolver initially)
        query GetMockPatientContext($patientId: ID!) {
          patient(id: $patientId) {
            id
            name {
              text # Full name
            }
            birthDate
            # Add a few more mock fields
          }
        }
        ```
    *   If using Apollo's local state for mocking, configure a mock resolver in `apolloClient.ts` or a separate mocking setup.

2.  **Create `PatientContextDisplay.tsx` Component:**
    *   **Directory:** `apps/atlas-ide-shell/src/components/PatientDisplay/` (New directory)
    *   **File:** `PatientContextDisplay.tsx` (New file)
    *   **Task:**
        *   Use the `@apollo/client` `useQuery` hook to fetch data using the mock query (pass a mock patient ID).
        *   Display loading (consider using `LoadingSpinner` from `ui-core`) and error states gracefully.
        *   **Reusable FHIR Components:** Create very basic, reusable components in `libs/fhir/fhir-utils` or a new `libs/fhir/fhir-ui-components` (e.g., `HumanNameDisplay.tsx`, `DateDisplay.tsx`) for rendering specific FHIR data types. Use these within `PatientContextDisplay.tsx`.
        *   Render the fetched mock patient data using these components and MUI `Typography`, `Chip`, or `Card` components.
        *   Style minimally using Tailwind CSS or MUI `sx` prop.
        *   **Data Sensitivity Cue:** Include a small visual note or placeholder comment (e.g., an icon and tooltip) indicating that this area will display sensitive patient data and adherence to HIPAA is critical.

3.  **Integrate `PatientContextDisplay` into UI:**
    *   **File:** `apps/atlas-ide-shell/src/components/Layout/Header.tsx` OR `Sidebar.tsx`
    *   **Task:** Import and render the `PatientContextDisplay` component in a suitable location (e.g., in the `Header` or within the "Patient Data" section of the `Sidebar`).

## D. Basic AI Chat UI Placeholder (`apps/atlas-ide-shell` or new `libs/features/ai-chat`)

1.  **Create `AIChatView.tsx` Component:**
    *   **Directory:** `apps/atlas-ide-shell/src/components/AIChat/` (New directory)
    *   **File:** `AIChatView.tsx` (New file)
    *   **Task:**
        *   **Message List Area:** Use an MUI `List` or a scrollable `Box` with appropriate `aria-live` attributes for screen reader announcements. Style user and AI messages distinctly (e.g., alignment, background color, typography). Implement a visual placeholder for *streaming* AI responses (e.g., a subtle typing indicator animation or a blinking cursor in the AI message area).
        *   **Input Area:** Use an MUI `TextField` (multiline optional) for user input and an MUI `Button` or `IconButton` (Send icon) to submit.
        *   **Action Placeholders:** Add placeholder UI elements (e.g., small `IconButtons` next to AI messages) for 'stop generation', 'copy message', and 'regenerate response' (these will be non-functional initially).
        *   **Local State Management:** Use `React.useState` to manage the list of messages (array of objects like `{ id: string, text: string, sender: 'user' | 'ai', status?: 'streaming' | 'complete' | 'error' }`) and the current input field value.
        *   **Functionality:** On send, add the user's message to the list and clear the input. For now, optionally add a canned AI response after a short delay, potentially simulating a streaming effect, to simulate interaction. **In later steps, this will involve sending the user's message and relevant context (e.g., from the `code-server` extension via `useCodeServerComm`) to a backend AI service and rendering its response.**
        *   Style using MUI components and Tailwind CSS for a basic chat interface look and feel, aiming for a professional and clean aesthetic.

2.  **Integrate `AIChatView` into Sidebar:**
    *   **File:** `apps/atlas-ide-shell/src/components/Layout/Sidebar.tsx`
    *   **Task:** Import and render the `AIChatView` component within the "AI Assistant" section of the `Sidebar`.

## E. Storybook & Component Accessibility

1.  **Create Stories for New Components:**
    *   If `PatientContextDisplay` or `AIChatView` (or parts of them) are structured to be reusable or warrant isolated testing, create corresponding `.stories.tsx` files for them within their respective library/application structure (if Nx supports stories for app components easily, or abstract to `ui-core` if truly generic).
    *   Update stories for any `ui-core` components modified or enhanced.
    *   **Healthcare Context in Stories:** When creating stories, include scenarios relevant to clinicians, such as displaying dense information tables, forms with clinical terminology, or interactions within a confined modal/panel, especially for components that might be used in FHIR data display or complex AI interactions.

2.  **Accessibility Review:**
    *   For all new interactive elements (sidebar toggle, chat input, buttons):
        *   Ensure proper `aria-labels`, `role` attributes.
        *   Verify keyboard navigability and operability.
        *   Check color contrast (though full design pass is later).
    *   Refer to `REACT.md` Section 3 (Accessibility & Inclusivity) for guidelines.

## F. Testing and Verification

1.  **Manual Testing:**
    *   Run `nx serve atlas-ide-shell`.
    *   Verify sidebar interactivity (open/close, content sections).
    *   Check `code-server` communication placeholders (console logs for messages **sent to and received from the `code-server` extension**).
    *   Confirm mock patient data display.
    *   Test basic AI chat UI placeholder functionality.
    *   Review overall layout and responsiveness.

2.  **Storybook Verification:**
    *   Run `nx run shared-ui-core:storybook` (and any other storybook instances).
    *   Verify all stories render correctly.

---
This step significantly increases the interactivity of the shell and puts in place the foundational UI and communication mechanisms for the core features of Atlas IDE. **It is crucial during this step to also begin defining a clear API contract (message types, expected payloads, and responses) for the `code-server` extension, as its development will be a parallel and critical effort.** Subsequent steps will build upon these placeholders to connect to real backends and implement full feature logic.
