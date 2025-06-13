# Atlas IDE React Frontend - Step 9: FHIR ServiceRequest Integration & Low-Code AI Action Builder

## 1. Overview

This step focuses on integrating FHIR ServiceRequest resources into the Atlas IDE, allowing clinicians to leverage existing service orders to initiate and contextualize AI-driven development tasks. Given Epic's FHIR API limitations, this integration will primarily support **Read** and **Search** operations for ServiceRequests. No creation or updates will be performed via the API.

The core deliverables include:
1.  UI components to search and display FHIR ServiceRequests.
2.  A system for defining "AI Actions" that can be triggered from a ServiceRequest (e.g., "Outline an application based on this request," "Generate boilerplate code for this service type").
3.  Mechanisms to pass ServiceRequest context to the AI backend to inform these actions.
4.  Integration of AI-generated outputs back into the IDE workflow (e.g., chat, new files, code snippets).

This plan aims for extreme granularity to guide a coding LLM in implementation.

## 2. Assumptions & Prerequisites

*   Successful completion and integration of Atlas IDE React Frontend Steps 1 through 8.
*   Existing architecture (Nx, Next.js, MUI, Tailwind, Zustand, react query Client) is stable.
*   `code-server` communication (`useCodeServerComm.ts`, `codeServerMessageTypes.ts`) is functional.
*   AI Chat functionalities (`useAIChatAPI.ts`, `AIChatView.tsx`) are operational.
*   The FastAPI backend is capable of proxying FHIR ServiceRequest queries to Palantir Foundry and handling new AI task requests.
*   Relevant patient context is available within the IDE.

## 3. Nx Monorepo Structure Considerations

*   **New Library (Optional):** Consider if a dedicated `libs/service-request-feature` library is warranted or if functionality can be distributed among existing libs (`ui-core`, `core-state`, `core-hooks`, `core-graphql`). For this plan, we'll assume distribution.
*   **New Components:** Will reside primarily in `libs/ui-core/src/lib/components/`.
*   **New Stores/State:** `libs/core-state/src/lib/stores/`.
*   **New Hooks:** `libs/core-hooks/src/lib/`.
*   **GraphQL Queries:** `libs/core-graphql/src/lib/queries/`.

## 4. Detailed User Workflow and AI Design Considerations

### 4.1. Detailed User Workflow

The envisioned workflow for a clinician using this feature is as follows:

1.  **Need Identification & Navigation:** The clinician identifies a clinical need or problem that could be addressed with a software solution (e.g., a tool to track patient adherence based on a care plan detailed in an existing ServiceRequest, an application to visualize specific data points mentioned in an order).
    *   The clinician navigates to a dedicated "Service Requests" tab or section within the Atlas IDE sidebar.

2.  **ServiceRequest Search & Selection:**
    *   The `ServiceRequestSearchPanel` is presented. If patient context is already loaded in the IDE (e.g., via `patientContextStore`), the patient ID field might be pre-populated or suggested.
    *   The clinician can further refine the search using parameters like status (e.g., "active," "completed"), category, or keywords related to `orderDetail` or `reasonCode`.
    *   Search results (a list of ServiceRequests) are displayed in the panel.
    *   The clinician reviews the list and selects the most relevant ServiceRequest. This action updates the `selectedServiceRequest` in the `serviceRequestStore`.

3.  **ServiceRequest Detail Review:**
    *   The `ServiceRequestDisplay` component updates to show the details of the `selectedServiceRequest`.
    *   The clinician verifies that this is the correct request they intend to use.

4.  **Initiating AI Action:**
    *   The clinician clicks a prominent button like "Use this ServiceRequest with AI" within the `ServiceRequestDisplay`.
    *   This action triggers the display of the `ServiceRequestAIActionPanel` (e.g., as a modal, an expanded section, or by navigating to a dedicated view), which is populated with the `selectedServiceRequest` context.

5.  **Selecting and Configuring AI Action:**
    *   The `ServiceRequestAIActionPanel` lists available predefined AI actions (e.g., "Outline Application from ServiceRequest," "Generate FHIR Query Ideas," "Draft User Stories based on Order Detail").
    *   The clinician selects the desired AI action from the list.
    *   If the selected action `requiresParameters` (as defined in its `ServiceRequestAIAction` configuration), corresponding input fields (e.g., `TextField` for additional notes) appear in the panel.
    *   The clinician fills in any required parameters.

6.  **AI Processing:**
    *   The clinician clicks a "Generate" or "Execute" button in the `ServiceRequestAIActionPanel`.
    *   The `triggerServiceRequestAIAction` function (from `useAIChatAPI` or a dedicated hook) is invoked.
    *   This function constructs a detailed prompt by:
        *   Populating the `promptTemplate` of the selected `ServiceRequestAIAction` with data extracted from the `selectedServiceRequest`.
        *   Appending any user-provided parameters.
        *   Optionally, fetching and appending relevant context from the active code editor (e.g., selected code, current file path, language via `useCodeServerComm`).
    *   The composed prompt, along with the `aiTaskType`, is sent to the FastAPI backend, which then communicates with the LLM.

7.  **Receiving and Utilizing AI Output:**
    *   The AI's response is received by the frontend.
    *   **Text-based outputs** (e.g., application outlines, user stories, textual explanations) are typically displayed in the `AIChatView`, becoming part of the ongoing conversation.
    *   **Code-based outputs** (e.g., boilerplate code, function stubs) can be:
        *   Displayed as ghost text in the active editor.
        *   Inserted directly at the cursor.
        *   Used to create a new file with the generated content.
        *   Presented in a diff view for review before application.
    *   The clinician reviews the AI-generated output and can then copy, modify, or further iterate on it within the IDE.

### 4.2. AI Design Considerations (General)

*   **Modularity:** The AI interaction logic should be modular. The `aiServiceRequestActions.ts` registry allows for easy addition or modification of actions without deep changes to UI components.
*   **Context is Key:** The quality of AI output heavily depends on the quality and relevance of the context provided. The design prioritizes combining ServiceRequest data, optional editor context, and explicit user parameters.
*   **User Feedback Loop:** While not explicitly detailed for MVP, future iterations should consider mechanisms for users to provide feedback on the quality of AI-generated outputs, which can be used to refine prompts or AI models.
*   **Transparency:** Clearly indicate to the user what information is being sent to the AI (e.g., via tooltips or a summary before sending the request).

## 5. Phased Implementation Plan

### Phase 9.A: FHIR ServiceRequest Integration (Read & Search)

**Objective:** Allow users to search for and view details of existing FHIR ServiceRequests for the current patient.

**9.A.1: GraphQL Queries for ServiceRequest**

*   **Task:** Define GraphQL queries for ServiceRequest.
    *   **File:** `libs/core-graphql/src/lib/queries/fhirQueries.ts` (or a new `serviceRequestQueries.ts`)
    *   **Action:** Add the following queries:
        *   `searchServiceRequests(patientId: ID!, status: String, category: String, code: String, limit: Int): [ServiceRequest]`
        *   `getServiceRequestById(id: ID!): ServiceRequest`
    *   **Details:** Ensure queries request necessary fields: `id`, `status`, `intent`, `category`, `code`, `subject (Patient reference)`, `requester (Practitioner/Organization reference)`, `orderDetail`, `occurrenceDateTime`, `authoredOn`, `reasonCode`, `note`.
    *   **Acceptance Criteria:** Queries are defined, typed, and can be successfully used with react query Client against a mock or real backend.

**9.A.2: Zustand Store for ServiceRequest UI State**

*   **Task:** Create a new Zustand store for managing ServiceRequest UI state.
    *   **File:** `libs/core-state/src/lib/stores/serviceRequestStore.ts`
    *   **Action:** Define the store structure and actions.
        *   **State Shape:**
            ```typescript
            interface ServiceRequestState {
              searchResults: fhir4.ServiceRequest[];
              selectedServiceRequest: fhir4.ServiceRequest | null;
              isLoading: boolean;
              error: string | null;
              searchTerm: string; // If implementing local filtering or for display
            }
            ```
        *   **Actions:**
            *   `setSearchResults(results: fhir4.ServiceRequest[]): void`
            *   `setSelectedServiceRequest(request: fhir4.ServiceRequest | null): void`
            *   `setLoading(loading: boolean): void`
            *   `setError(error: string | null): void`
            *   `setSearchTerm(term: string): void`
            *   `fetchServiceRequests(react queryClient: react queryClient<any>, patientId: string, params: { status?: string; category?: string; code?: string }): Promise<void>` (handles react query query and updates store)
            *   `fetchServiceRequestById(react queryClient: react queryClient<any>, id: string): Promise<void>`
    *   **Acceptance Criteria:** Store is created, typed, and actions correctly update the state. `fetch` actions successfully interact with react query Client.

**9.A.3: UI Component - `ServiceRequestSearchPanel.tsx`**

*   **Task:** Create a component to search for and display a list of ServiceRequests.
    *   **File:** `libs/ui-core/src/lib/components/service-request/ServiceRequestSearchPanel.tsx` (create new `service-request` subfolder)
    *   **Core Logic:**
        *   Uses `serviceRequestStore` for state (search results, loading, error).
        *   Uses react query Client (via store actions or directly) to fetch ServiceRequests.
        *   Input fields (MUI `TextField`, `Select`) for search parameters (e.g., status, category - initially can be simple text search, later more structured).
        *   MUI `Button` to trigger search.
        *   Displays results in an MUI `List` or `Table`. Each item should be selectable.
        *   On selection, calls `setSelectedServiceRequest` from `serviceRequestStore`.
    *   **Props:**
        ```typescript
        interface ServiceRequestSearchPanelProps {
          patientId: string; // Or retrieved from a global patient context store
          onServiceRequestSelect?: (serviceRequest: fhir4.ServiceRequest) => void; // Optional callback
        }
        ```
    *   **UI Elements:** MUI `TextField`, `Button`, `List`, `ListItem`, `ListItemText`, `CircularProgress`, `Alert`.
    *   **Styling:** Tailwind CSS. Ensure responsiveness for sidebar constraints (≤600px).
    *   **Key Imports:** `React`, `useEffect`, `useState`, `useServiceRequestStore`, `@mui/material`, `fhir4` types.
    *   **Acceptance Criteria:** Component renders, allows search input, triggers search, displays results (or loading/error states), and updates `selectedServiceRequest` in store upon selection.

**9.A.4: UI Component - `ServiceRequestDisplay.tsx`**

*   **Task:** Create a component to display the details of a selected ServiceRequest.
    *   **File:** `libs/ui-core/src/lib/components/service-request/ServiceRequestDisplay.tsx`
    *   **Core Logic:**
        *   Subscribes to `selectedServiceRequest` from `serviceRequestStore`.
        *   Displays key fields of the ServiceRequest in a readable format.
        *   Includes a button: "Use this ServiceRequest with AI" (links to Phase 9.B).
    *   **Props:**
        ```typescript
        interface ServiceRequestDisplayProps {
          // serviceRequest?: fhir4.ServiceRequest | null; // Can take as prop or rely on store
        }
        ```
    *   **UI Elements:** MUI `Typography`, `Card`, `CardContent`, `Grid`, `Chip`, `Button`.
    *   **Styling:** Tailwind CSS.
    *   **Key Imports:** `React`, `useServiceRequestStore`, `@mui/material`, `fhir4` types.
    *   **Acceptance Criteria:** Component renders details of `selectedServiceRequest`. "Use with AI" button is present.

**9.A.5: Integration into IDE Layout**

*   **Task:** Integrate the `ServiceRequestSearchPanel` and `ServiceRequestDisplay` into the Atlas IDE layout.
    *   **File:** e.g., `apps/atlas-ide-shell/components/layout/SidebarAddons.tsx` (new conceptual component for sidebar tabs/sections) or modify existing `Sidebar.tsx`.
    *   **Action:** Add a new tab or collapsible section in the sidebar titled "Service Requests".
        *   This section will host `ServiceRequestSearchPanel.tsx`.
        *   `ServiceRequestDisplay.tsx` could be shown below the search panel or in a main panel area when a request is selected.
    *   **Acceptance Criteria:** Service Request feature is accessible from the IDE's UI. Search and display components are correctly placed and functional.

**9.A.6: Mock Data for ServiceRequests**

*   **Task:** Create mock FHIR ServiceRequest data for development and testing.
    *   **File:** `libs/fhir-utils/src/lib/mocks/mockServiceRequests.ts`
    *   **Action:** Define an array of realistic `fhir4.ServiceRequest` objects.
    *   **Acceptance Criteria:** Mock data is available and can be used by components and tests.

### Phase 9.B: Low-Code AI Action Builder for ServiceRequests

**Objective:** Allow users to select a ServiceRequest and trigger predefined AI actions contextualized by its data.

**9.B.1: Define AI Action Registry**

*   **Task:** Define a structure and registry for "AI Actions" that can be performed using a ServiceRequest.
    *   **File:** `libs/core-state/src/lib/aiServiceRequestActions.ts` (new)
    *   **Action:** Define types and an initial list of actions.
        ```typescript
        export interface ServiceRequestAIAction {
          id: string;
          name: string;
          description: string;
          // Template for the prompt to be sent to the AI, using placeholders for SR fields
          // e.g., "Based on the following service request details (Category: {{category}}, Code: {{code}}, Order Detail: {{orderDetail}}), please {{task}}."
          promptTemplate: string; 
          // Specific task for the AI, e.g., "outline a web application", "generate boilerplate Python code", "draft user stories"
          aiTaskType: 'OUTLINE_APP' | 'GENERATE_BOILERPLATE' | 'DRAFT_USER_STORIES' | 'CUSTOM_PROMPT'; 
        }

        export const serviceRequestUIActions: ServiceRequestAIAction[] = [
          {
            id: 'sr_outline_app',
            name: 'Outline Application from Service Request',
            description: 'Generates a high-level application structure based on the service request details.',
            promptTemplate: 'Based on the service request (ID: {{id}}, Category: {{category}}, Code: {{code}}, Order Detail: {{orderDetail}}), please outline the key components and features of a software application designed to fulfill this request.',
            aiTaskType: 'OUTLINE_APP',
          },
          {
            id: 'sr_generate_fhir_queries',
            name: 'Suggest FHIR Queries for Service',
            description: 'Generates potential FHIR API query examples relevant to fulfilling or analyzing the service request.',
            promptTemplate: 'Given the ServiceRequest (ID: {{id}}, Details: {{orderDetail}}, Reason: {{reasonCode}}), suggest 3 to 5 specific FHIR resource queries (e.g., for Patient, Observation, DiagnosticReport) that would be useful for a developer trying to build an application related to this request. Provide example query parameters.',
            aiTaskType: 'CUSTOM_PROMPT', // Or a more specific 'GENERATE_FHIR_QUERIES' if backend supports specialized logic
          },
          {
            id: 'sr_draft_user_stories',
            name: 'Draft User Stories from Service Request',
            description: 'Generates user stories based on the service request to help define application features.',
            promptTemplate: 'From the perspective of a clinician or patient, draft 3-5 user stories based on this ServiceRequest (ID: {{id}}, Intent: {{intent}}, Order Detail: {{orderDetail}}). Each story should follow the format: "As a [user type], I want to [action] so that [benefit]." Focus on the primary goals implied by the request.',
            aiTaskType: 'DRAFT_USER_STORIES',
          }
        ];
        ```
    *   **Prompt Template Best Practices:**
        *   Be explicit about the desired output format if possible (e.g., "Provide the outline in markdown format").
        *   Clearly label the different pieces of context being provided (e.g., "ServiceRequest Details:", "Selected Code:").
        *   Handle missing data gracefully in the template population logic (e.g., substitute 'N/A' or omit sections if critical data is missing, and inform the AI).
    *   **Acceptance Criteria:** AI action types and registry are defined and accessible. Prompt templates are designed for clarity and robustness.

**9.B.2: UI Component - `ServiceRequestAIActionPanel.tsx`**

*   **Task:** Create a component to display available AI Actions for a selected ServiceRequest and trigger them.
    *   **File:** `libs/ui-core/src/lib/components/service-request/ServiceRequestAIActionPanel.tsx`
    *   **Core Logic:**
        *   Takes `selectedServiceRequest` (from store or prop).
        *   Displays a list of `ServiceRequestAIAction` from the registry (e.g., using MUI `Select` or `List`).
        *   Allows the user to select an action.
        *   On selection and confirmation (e.g., "Generate" button), it will use `useAIChatAPI` (or a new dedicated hook) to trigger the AI task.
    *   **Props:**
        ```typescript
        interface ServiceRequestAIActionPanelProps {
          serviceRequest: fhir4.ServiceRequest;
        }
        ```
    *   **UI Elements:** MUI `Select`, `MenuItem`, `Button`, `Typography`, `Card`.
    *   **Styling:** Tailwind CSS.
    *   **Key Imports:** `React`, `useState`, `serviceRequestUIActions`, `useAIChatAPI` (or new hook), `@mui/material`, `fhir4` types.
    *   **Acceptance Criteria:** Panel displays available actions for the given ServiceRequest. User can select an action and trigger it.

**9.B.3: Enhance/Create AI Interaction Hook**

*   **Task:** Update `useAIChatAPI.ts` or create `useAIServiceRequestActions.ts` to handle AI tasks initiated from ServiceRequests.
    *   **File:** `libs/core-hooks/src/lib/useAIChatAPI.ts` (or new `useAIServiceRequestActions.ts`)
    *   **Action:** Add a new function, e.g., `triggerServiceRequestAIAction`.
        ```typescript
        // In useAIChatAPI.ts or new hook
        async function triggerServiceRequestAIAction(
          serviceRequest: fhir4.ServiceRequest,
          aiAction: ServiceRequestAIAction
        ): Promise<void> {
          // 1. Construct the prompt using aiAction.promptTemplate and serviceRequest data.
          //    Replace placeholders like {{id}}, {{category}}, {{code}}, {{orderDetail}}.
          //    Example placeholder replacement:
          //    let prompt = aiAction.promptTemplate.replace('{{id}}', serviceRequest.id || '');
          //    prompt = prompt.replace('{{category}}', serviceRequest.category?.map(c => c.coding?.map(co => co.code).join(', ')).join('; ') || 'N/A'); ... etc.
          //    This should use a robust utility function, e.g.:
          //    function populatePromptTemplate(template: string, srData: Record<string, any>, userParams: Record<string, any>): string { /* ... */ }
          //    The srData should be a carefully selected/flattened representation of the ServiceRequest.

          // 2. Combine with Editor Context (if applicable and desired for the action):
          //    let combinedPrompt = constructedServiceRequestPrompt;
          //    const editorContext = await codeServerComm.getActiveEditorContext(); // Fetches { filePath, language, selectedText, surroundingCode }
          //    if (aiAction.utilizeEditorContext && editorContext?.selectedText) { // Add a flag to ServiceRequestAIAction interface
          //      combinedPrompt += `\n\nRelevant Code Context from ${editorContext.filePath} (${editorContext.language}):\n${editorContext.selectedText}`;
          //      if (editorContext.surroundingCode) combinedPrompt += `\nSurrounding Code:\n${editorContext.surroundingCode}`;
          //    }

          // 3. Send to AI backend:
          //    The payload to the FastAPI backend should be structured, including the final prompt, the aiTaskType,
          //    and potentially a summary of the contexts used (e.g., serviceRequestId, editorContext.filePath).
          //    Example: 
          //    const response = await sendChatMessage(combinedPrompt, {
          //      originalServiceRequest: serviceRequest, // For logging or deeper backend processing
          //      aiTaskType: aiAction.aiTaskType,
          //      editorContextSummary: editorContext ? { path: editorContext.filePath, lang: editorContext.language } : undefined
          //    });

          // 4. Handle the AI response:
          //    - Check for errors from the AI service or network issues. Update chatStore with user-friendly error messages.
          //    - If successful, parse the response. The AI might return structured data (e.g., JSON for code snippets + explanation).
          //    - Based on aiAction.aiTaskType and response structure:
          //      - For text-heavy tasks ('OUTLINE_APP', 'DRAFT_USER_STORIES'): Add to chatStore.
          //      - For 'GENERATE_BOILERPLATE': Use code-server commands (Phase 9.D) like INSERT_SNIPPET_AT_CURSOR_COMMAND or CREATE_FILE_WITH_CONTENT_COMMAND.
          //      - The AI response itself might suggest the preferred handling (e.g., { type: 'insert_snippet', language: 'python', code: '...', explanation: '...' }).
          //    - Update loading states in the relevant store (e.g., taskContextStore or a dedicated action store).
        }
        ```
    *   **AI Error Handling Details:**
        *   **Network/Server Errors:** The `useAIChatAPI` (or equivalent) should catch errors from `fetch` or react query Client and translate them into user-facing error messages in the chat (e.g., "Failed to connect to AI service. Please try again.").
        *   **AI Service Errors (e.g., 4xx/5xx from LLM backend):** If the FastAPI proxy forwards an error from the LLM, display a clear message (e.g., "AI service returned an error: [error details from response]").
        *   **Malformed/Unexpected AI Responses:** If the AI response isn't in the expected format (e.g., not valid JSON when expected, or code snippet missing), log the raw response for debugging and show a generic error: "AI returned an unexpected response. Please try rephrasing your request or contact support if the issue persists."
    *   **Acceptance Criteria:** Hook function robustly constructs prompts using ServiceRequest data, user parameters, and optional editor context. It sends structured requests to the AI backend. It handles various AI response types and errors gracefully, updating UI/state accordingly.

**9.B.4: Integrate AI Action Panel Trigger**

*   **Task:** Connect the "Use this ServiceRequest with AI" button from `ServiceRequestDisplay.tsx` to show `ServiceRequestAIActionPanel.tsx`.
    *   **File:** `libs/ui-core/src/lib/components/service-request/ServiceRequestDisplay.tsx`
    *   **Action:** Modify the button's `onClick` handler.
        *   This could involve setting a state in `serviceRequestStore` (e.g., `showAIActionPanelFor: serviceRequest.id`) and having another component listen to this state to render the panel as a modal or inline.
        *   Alternatively, navigate to a view or expand a section containing the `ServiceRequestAIActionPanel`.
    *   **Acceptance Criteria:** Clicking the button on `ServiceRequestDisplay` makes the `ServiceRequestAIActionPanel` visible and operational for the selected ServiceRequest.

### Phase 9.C: Handling AI-Generated Outputs

**Objective:** Provide flexible and user-friendly ways to manage and use outputs generated by AI actions based on ServiceRequests.

**Objective:** Provide initial ways to manage and use outputs generated by AI actions based on ServiceRequests.

**9.C.1: Displaying Outputs in AI Chat**

*   **Task:** Ensure that standard text-based outputs from ServiceRequest AI Actions are displayed in the existing `AIChatView.tsx`.
    *   **File:** `libs/core-hooks/src/lib/useAIChatAPI.ts` (and related chat store/components).
    *   **Action:** The `triggerServiceRequestAIAction` function should, by default, route text responses to be added to the chat history via `chatStore`.
    *   **Action:** The `triggerServiceRequestAIAction` function should, by default, route text responses (or textual parts of structured responses) to be added to the chat history via `chatStore`. Ensure that messages originating from a ServiceRequest action are clearly attributed or visually distinct in the chat if possible (e.g., prefixing with "AI (from ServiceRequest Action):" or a specific icon).
    *   **Acceptance Criteria:** AI responses from ServiceRequest actions appear clearly and appropriately attributed in the chat view.

**9.C.2: Conceptual: "Project Pad" or Output Collection Area**

*   **Task (Low Priority for initial Step 9, focus on chat/editor integration):** Design a basic mechanism to collect or pin important AI-generated artifacts derived from ServiceRequests.
    *   **Concept:** Similar to `PinnedSuggestionsView.tsx` (Step 8 Memory) or a new `ProjectPadStore.ts`.
    *   **Details:** This is a stretch goal. For now, ensure outputs can be copied from chat or directly inserted into the editor.
    *   **Details:** This is a stretch goal for Step 9 MVP. For the initial implementation, ensure outputs can be easily copied from the chat. If AI generates larger documents (e.g., full application outlines), consider if the chat view can adequately handle them or if a temporary modal/viewer is needed for better readability before copying.
    *   **Acceptance Criteria (MVP):** Textual AI outputs are readable in chat and can be easily copied. Consideration given to how larger text outputs are presented.

### Phase 9.D: Rich Integration with VSCodium/`code-server` for AI Outputs

**Objective:** Enable AI actions to interact with the code editor (e.g., insert generated code).

**9.D.1: New `code-server` Message Types (if needed)**

*   **Task:** Define new `code-server` message types if AI actions need to directly manipulate the editor beyond existing capabilities (ghost text, insert/replace).
    *   **File:** `libs/core-state/src/lib/types/codeServerMessageTypes.ts`
    *   **Potential New Commands (Illustrative, only add if essential for Step 9 MVP):**
        *   `CREATE_FILE_WITH_CONTENT_COMMAND`: { `filePath`: string, `content`: string }
        *   `INSERT_SNIPPET_AT_CURSOR_COMMAND`: { `snippet`: string }
    *   **Action:** Define types and ensure the `code-server` extension can handle them.
    *   **Acceptance Criteria:** Necessary message types are defined and documented.

**9.D.2: Update `useCodeServerComm.ts`**

*   **Task:** If new message types are added, update `useCodeServerComm.ts` to include functions for sending these commands.
    *   **File:** `libs/core-hooks/src/lib/useCodeServerComm.ts`
    *   **Action:** Add corresponding `sendCommand` wrappers.
    *   **Acceptance Criteria:** Hook is updated to support new editor interactions.

**9.D.3: Using Editor Commands in AI Action Handling**

*   **Task:** Modify `triggerServiceRequestAIAction` (in `useAIChatAPI.ts` or new hook) to use these `code-server` commands for relevant `aiTaskType` responses.
    *   **File:** `libs/core-hooks/src/lib/useAIChatAPI.ts` (or new hook)
    *   **Action:** For an `aiTaskType` like `GENERATE_BOILERPLATE`, the response handler might call `codeServerComm.sendCommand('INSERT_SNIPPET_AT_CURSOR_COMMAND', { snippet: aiResponse.code })`.
    *   **Action:** Modify `triggerServiceRequestAIAction` (in `useAIChatAPI.ts` or new hook) to use these `code-server` commands for relevant `aiTaskType` responses. The AI response itself might guide which command to use. For example, an AI response could be structured JSON:
        ```json
        {
          "action_type": "insert_snippet", // or "create_file", "show_ghost_text"
          "language": "python",
          "content": "def hello_world():\n  print('Hello, world!')",
          "explanation": "A simple Python function.",
          "filePath_suggestion": "utils/helpers.py" // for create_file
        }
        ```
        The frontend logic would parse this and call the appropriate `codeServerComm.sendCommand(...)`.
    *   **Acceptance Criteria:** AI actions can result in content being inserted, files being created, or ghost text being shown in the editor, based on structured AI responses.

### Phase 9.E: Testing, Documentation, and Accessibility

**9.E.1: Storybook Stories**

*   **Task:** Create Storybook stories for all new UI components.
    *   **Files:** In `libs/ui-core/src/lib/components/service-request/`, create `*.stories.tsx` files for:
        *   `ServiceRequestSearchPanel.stories.tsx`
        *   `ServiceRequestDisplay.stories.tsx`
        *   `ServiceRequestAIActionPanel.stories.tsx`
    *   **Details:** Include stories for different states (loading, error, with data, no data).
    *   **Acceptance Criteria:** Components are viewable and testable in Storybook.

**9.E.2: Unit Tests**

*   **Task:** Write unit tests for new Zustand stores, hooks, and critical utility functions.
    *   **Files:** `*.spec.ts` alongside the respective files.
    *   **Focus:** `serviceRequestStore.ts`, `useAIServiceRequestActions.ts` (if created), logic within `aiServiceRequestActions.ts`.
    *   **Acceptance Criteria:** Core logic is covered by unit tests.

**9.E.3: Manual End-to-End Testing Plan**

*   **Task:** Define and execute a manual test plan for the entire ServiceRequest AI action flow.
    *   **Scenarios:**
        1.  Search for ServiceRequests (with and without results).
        2.  Select a ServiceRequest, view its details.
        3.  Trigger an "Outline Application" AI action; verify prompt construction and AI response in chat.
        4.  Trigger a "Generate Boilerplate" AI action; verify code snippet insertion (if implemented).
        5.  Test error handling (e.g., API errors from FHIR or AI backend).
    *   **Acceptance Criteria:** All key user flows are tested and functional.

**9.E.4: Accessibility Review**

*   **Task:** Conduct an accessibility review (WCAG 2.2 AA) for all new UI components.
    *   **Tools:** Storybook A11y addon, browser developer tools, screen reader (VoiceOver/NVDA).
    *   **Focus:** Keyboard navigation, ARIA attributes, color contrast, focus management.
    *   **Acceptance Criteria:** New UI meets accessibility standards.

**9.E.5: Documentation Update**

*   **Task:** Update project documentation (`TO-do-list-react.md`, `REACT.md`, etc.) with details of Step 9 features.
    *   **Acceptance Criteria:** Documentation reflects the new functionalities.

## 5. Security and Compliance

*   **HIPAA:** Reiterate that all ServiceRequest data is PHI. Ensure it's handled securely:
    *   No PHI stored in browser local storage, cookies, or unencrypted IndexedDB unless explicitly required and secured.
    *   Scrub PHI from any telemetry or logs sent from the client.
    *   Secure communication (HTTPS) with FastAPI backend and `code-server`.
*   **CSP:** Ensure Content Security Policy is appropriate for any new interactions or embedded content.

## 6. Definition of Done for Step 9 (MVP)

*   Clinicians can search for FHIR ServiceRequests by patient context and view their details within the Atlas IDE.
*   A predefined list of AI Actions (e.g., "Outline App," "Generate Boilerplate") can be triggered from a selected ServiceRequest.
*   The AI prompt is correctly contextualized using data from the selected ServiceRequest.
*   AI-generated text responses are displayed in the `AIChatView`.
*   (If implemented) AI-generated code snippets can be inserted into the active editor via `code-server` commands.
*   New UI components (`ServiceRequestSearchPanel`, `ServiceRequestDisplay`, `ServiceRequestAIActionPanel`) are created, styled with Tailwind, use MUI, are documented in Storybook, and have basic accessibility checks.
*   Core logic in new stores/hooks has unit tests.
*   The feature is integrated into the IDE sidebar/layout.
*   End-to-end manual testing of the primary flow is successful.

## 7. Future Considerations (Beyond Step 9 MVP)

*   More sophisticated search filters for ServiceRequests.
*   User-defined AI Action templates.
*   Advanced "drag and drop" UI for linking ServiceRequests to AI tasks or application blueprints.
*   Visual application builder UI (the "build service requests into applications" concept).
*   Directly creating/editing FHIR resources if Epic API capabilities expand.

## 12. Phase 9: FHIR ServiceRequest Integration & Low-Code AI Action Builder

This phase focuses on integrating FHIR ServiceRequest resources into the Atlas IDE, allowing clinicians to leverage existing service orders to initiate and contextualize AI-driven development tasks. It includes UI components for searching/displaying ServiceRequests, a system for defining and triggering AI Actions based on ServiceRequests, and mechanisms for handling AI-generated outputs within the IDE.

**Source Document:** [atlas_ide_react_step9_plan.md](cci:7://file:///Users/gabe/ATLAS%20Palantir/PLANNING/REACT/atlas_ide_react_step9_plan.md:0:0-0:0)

### 12.1. Phase 9.A: FHIR ServiceRequest Integration (Read & Search)

**Objective:** Allow users to search for and view details of existing FHIR ServiceRequests for the current patient.

**Task 12.1.1: GraphQL Queries for ServiceRequest**
*   **Target Files:** `libs/core-graphql/src/lib/queries/fhirQueries.ts` (or a new `serviceRequestQueries.ts`)
*   **Definition:** Define GraphQL queries necessary for searching ServiceRequests and retrieving a specific ServiceRequest by ID.
*   **Core Logic:**
    *   Add `searchServiceRequests(patientId: ID!, status: String, category: String, code: String, limit: Int): [ServiceRequest]` query.
    *   Add `getServiceRequestById(id: ID!): ServiceRequest` query.
    *   Ensure queries request necessary fields: `id`, `status`, `intent`, `category`, `code`, `subject (Patient reference)`, `requester (Practitioner/Organization reference)`, `orderDetail`, `occurrenceDateTime`, `authoredOn`, `reasonCode`, `note`.
*   **Key Imports:** `gql` from `@react query/client`.
*   **Acceptance Criteria:** GraphQL queries are defined, correctly typed, and can be successfully used with react query Client against a mock or actual backend. The queries fetch all specified fields for the ServiceRequest resource.

**Task 12.1.2: Zustand Store for ServiceRequest UI State**
*   **Target Files:** `libs/core-state/src/lib/stores/serviceRequestStore.ts`
*   **Definition:** Create a new Zustand store to manage the UI state related to ServiceRequests, including search results, selected request, loading states, and errors.
*   **Core Logic:**
    *   Define `ServiceRequestState` interface:
        ```typescript
        interface ServiceRequestState {
          searchResults: fhir4.ServiceRequest[];
          selectedServiceRequest: fhir4.ServiceRequest | null;
          isLoading: boolean;
          error: string | null;
          searchTerm: string;
        }
        ```
    *   Implement actions: `setSearchResults`, `setSelectedServiceRequest`, `setLoading`, `setError`, `setSearchTerm`.
    *   Implement async actions:
        *   `fetchServiceRequests(react queryClient: react queryClient<any>, patientId: string, params: { status?: string; category?: string; code?: string }): Promise<void>`: Executes the `searchServiceRequests` GraphQL query using the provided react query Client and updates the store with results, loading state, and errors.
        *   `fetchServiceRequestById(react queryClient: react queryClient<any>, id: string): Promise<void>`: Executes `getServiceRequestById` query.
*   **Key Imports:** `create` from `zustand`, `fhir4` types, `react queryClient`.
*   **Acceptance Criteria:** The `serviceRequestStore` is created and typed correctly. Actions update the state as expected. Asynchronous fetch actions successfully interact with react query Client and manage loading/error states appropriately.

**Task 12.1.3: UI Component - `ServiceRequestSearchPanel.tsx`**
*   **Target Files:** `libs/ui/feature-components/src/lib/service-request/ServiceRequestSearchPanel.tsx` (create new `service-request` subfolder if it doesn't exist under `feature-components`)
*   **Definition:** Develop a React component that allows users to input search criteria, trigger a search for FHIR ServiceRequests, and display the results in a list.
*   **Core Logic:**
    *   Uses `useServiceRequestStore` to access and update search results, loading state, error state, and search term.
    *   Uses react query Client (likely via actions in `serviceRequestStore`) to fetch ServiceRequests based on user input.
    *   Provides input fields (MUI `TextField`, `Select`) for search parameters (e.g., status, category, free-text search for `orderDetail` or `reasonCode`).
    *   Includes an MUI `Button` to initiate the search.
    *   Displays search results in an MUI `List` or `Table`. Each item in the list should be selectable.
    *   Upon selection of a ServiceRequest from the list, calls `setSelectedServiceRequest` action from `serviceRequestStore`.
*   **Props:**
    ```typescript
    interface ServiceRequestSearchPanelProps {
      patientId: string; // Or retrieved from a global patient context store
      onServiceRequestSelect?: (serviceRequest: fhir4.ServiceRequest) => void; // Optional callback
    }
    ```
*   **UI Elements:** MUI `TextField`, `Button`, `List`, `ListItem`, `ListItemText`, `CircularProgress` (for loading state), `Alert` (for error messages).
*   **Styling:** Tailwind CSS. Ensure the component is responsive and usable within potential sidebar width constraints (e.g., ≤600px).
*   **Key Imports:** `React`, `useEffect`, `useState`, `useServiceRequestStore`, `@mui/material` components, `fhir4` types.
*   **Acceptance Criteria:** Component renders correctly. Users can input search criteria. Search is triggered, and results (or loading/error states) are displayed. Selecting a result updates `selectedServiceRequest` in the `serviceRequestStore`.

**Task 12.1.4: UI Component - `ServiceRequestDisplay.tsx`**
*   **Target Files:** `libs/ui/feature-components/src/lib/service-request/ServiceRequestDisplay.tsx`
*   **Definition:** Create a React component to display the detailed information of a selected FHIR ServiceRequest.
*   **Core Logic:**
    *   Subscribes to `selectedServiceRequest` from `useServiceRequestStore`.
    *   If `selectedServiceRequest` is not null, displays its key fields in a clear, readable format (e.g., ID, status, intent, category, code, order details, reason, notes).
    *   Includes a prominent MUI `Button` labeled "Use this ServiceRequest with AI" (this button will trigger the display of the `ServiceRequestAIActionPanel` as defined in Phase 9.B).
*   **Props:** (Likely none, as it will primarily rely on the store)
    ```typescript
    // interface ServiceRequestDisplayProps {}
    ```
*   **UI Elements:** MUI `Typography` for various fields, `Card`, `CardContent`, `Grid` for layout, `Chip` for status/category, `Button`.
*   **Styling:** Tailwind CSS.
*   **Key Imports:** `React`, `useServiceRequestStore`, `@mui/material` components, `fhir4` types.
*   **Acceptance Criteria:** Component correctly renders the details of the `selectedServiceRequest` from the store. The "Use this ServiceRequest with AI" button is present and visible when a request is selected. Displays a placeholder or empty state if no request is selected.

**Task 12.1.5: Integration into IDE Layout**
*   **Target Files:** `apps/atlas-ide-shell/components/layout/SidebarAddons.tsx` (or equivalent layout component managing sidebar tabs/sections, e.g., `apps/atlas-ide-shell/components/layout/Sidebar.tsx`).
*   **Definition:** Integrate the ServiceRequest search and display functionality into a dedicated section or tab within the Atlas IDE's sidebar.
*   **Core Logic:**
    *   Add a new collapsible section or tab in the sidebar, labeled "Service Requests".
    *   This new section should host the `ServiceRequestSearchPanel` component.
    *   The `ServiceRequestDisplay` component should be placed logically, perhaps below the search panel or in a way that it becomes visible/populated when a request is selected from the search panel.
*   **Acceptance Criteria:** The "Service Requests" feature is accessible from the IDE's main UI (sidebar). The `ServiceRequestSearchPanel` and `ServiceRequestDisplay` components are correctly placed and function as expected within the layout.

**Task 12.1.6: Mock Data for ServiceRequests**
*   **Target Files:** `libs/fhir/utils/src/lib/mocks/mockServiceRequests.ts` (or `libs/fhir-utils/src/mocks/mockServiceRequests.ts` depending on exact Nx setup)
*   **Definition:** Create an array of realistic mock FHIR ServiceRequest objects for development, testing, and Storybook stories.
*   **Core Logic:**
    *   Define at least 3-5 diverse `fhir4.ServiceRequest` objects, covering different statuses, categories, and details.
    *   Ensure mock data includes all fields that the UI components and GraphQL queries expect.
*   **Key Imports:** `fhir4` types.
*   **Acceptance Criteria:** An array of mock `fhir4.ServiceRequest` objects is created and exported. This data can be imported and used by components for development and in unit/integration tests.

### 12.2. Phase 9.B: Low-Code AI Action Builder for ServiceRequests

**Objective:** Allow users to select a ServiceRequest and trigger predefined AI actions contextualized by its data.

**Task 12.2.1: Define AI Action Registry (`aiServiceRequestActions.ts`)**
*   **Target Files:** `libs/core/state/src/lib/aiServiceRequestActions.ts` (or `libs/core-state/src/lib/resources/aiServiceRequestActions.ts`)
*   **Definition:** Define the structure for "AI Actions" and create a registry (an array) of predefined actions that can be performed using a ServiceRequest.
*   **Core Logic:**
    *   Define `ServiceRequestAIAction` interface:
        ```typescript
        export interface ServiceRequestAIAction {
          id: string;
          name: string;
          description: string;
          promptTemplate: string; // e.g., "Outline an app for: {{orderDetail}}"
          aiTaskType: string; // e.g., 'OUTLINE_APP', 'GENERATE_BOILERPLATE', 'CUSTOM_PROMPT'
          requiresParameters?: Array<{ id: string; label: string; type: 'string' | 'number' /* ... */ }>;
          utilizeEditorContext?: boolean; // New flag
        }
        ```
    *   Create `serviceRequestUIActions` array with initial actions:
        *   `sr_outline_app`: Outlines an application.
        *   `sr_generate_fhir_queries`: Suggests FHIR queries.
        *   `sr_draft_user_stories`: Drafts user stories.
    *   **Prompt Template Best Practices:** Ensure templates are clear, explicitly request formats if needed, label context, and consider how missing data will be handled during population.
*   **Key Imports:** (Potentially none beyond local types)
*   **Acceptance Criteria:** The `ServiceRequestAIAction` interface is defined. The `serviceRequestUIActions` array is populated with at least three diverse actions. Prompt templates are designed for clarity and robustness.

**Task 12.2.2: UI Component - `ServiceRequestAIActionPanel.tsx`**
*   **Target Files:** `libs/ui/feature-components/src/lib/service-request/ServiceRequestAIActionPanel.tsx`
*   **Definition:** Create a component that displays available AI actions for a selected ServiceRequest and allows the user to trigger them.
*   **Core Logic:**
    *   Receives `selectedServiceRequest` (e.g., via props or `useServiceRequestStore`).
    *   Displays a list of `ServiceRequestAIAction` (from `serviceRequestUIActions`).
    *   Allows selection of an action.
    *   If `action.requiresParameters` is defined, dynamically render input fields (MUI `TextField`) for these parameters.
    *   Includes a "Generate" or "Execute" button to trigger the selected AI action.
    *   On trigger, calls the `triggerServiceRequestAIAction` hook/function (from Task 12.2.3).
*   **Props:**
    ```typescript
    interface ServiceRequestAIActionPanelProps {
      serviceRequest: fhir4.ServiceRequest; // The currently selected ServiceRequest
      // onActionTriggered?: () => void; // Callback after action is sent
    }
    ```
*   **UI Elements:** MUI `Select` or `List` for actions, `TextField` for parameters, `Button`, `Typography`.
*   **Styling:** Tailwind CSS.
*   **Key Imports:** `React`, `useState`, `ServiceRequestAIAction`, `serviceRequestUIActions`, `useServiceRequestStore` (if needed), `@mui/material`, `fhir4`.
*   **Acceptance Criteria:** Panel displays actions for the given ServiceRequest. Parameter inputs appear if required. "Generate" button triggers the AI action logic.

**Task 12.2.3: Hook for AI Interaction (`useAIServiceRequestActions.ts` or enhance `useAIChatAPI.ts`)**
*   **Target Files:** `libs/core/hooks/src/lib/useAIChatAPI.ts` (enhance) or new `libs/core/hooks/src/lib/useAIServiceRequestActions.ts`.
*   **Definition:** Create or enhance a hook to manage the logic of triggering an AI action based on a ServiceRequest, selected AI action, and user parameters.
*   **Core Logic:**
    *   Define `triggerServiceRequestAIAction(serviceRequest: fhir4.ServiceRequest, aiAction: ServiceRequestAIAction, params: Record<string, any>)`.
    *   **Prompt Population:** Implement robust logic to populate `aiAction.promptTemplate` using data from `serviceRequest` and `params`. Use a utility function like `populatePromptTemplate(template, srData, userParams)`. Handle missing data gracefully.
    *   **Editor Context:** If `aiAction.utilizeEditorContext` is true, fetch active editor context (filePath, language, selectedText, surroundingCode) using `useCodeServerComm`. Append this to the prompt.
    *   **Backend Communication:** Send the final composed prompt, `aiAction.aiTaskType`, and relevant metadata (e.g., `serviceRequestId`, editor context summary) to the FastAPI backend (likely via `sendChatMessage` from `useAIChatAPI` or a similar mechanism).
    *   **Response Handling:**
        *   Manage loading states.
        *   Handle network/server errors and AI service errors by updating `chatStore` with user-friendly messages.
        *   Parse successful AI responses (could be text or structured JSON).
        *   Route responses based on `aiAction.aiTaskType` (e.g., text to chat, code to editor commands - see Phase 9.D).
*   **Key Imports:** `useCallback`, `useState`, `useChatStore`, `useCodeServerComm`, `ServiceRequestAIAction`, `fhir4`, `react queryClient` (if direct calls needed).
*   **Acceptance Criteria:** Hook function robustly constructs prompts using ServiceRequest data, user parameters, and optional editor context. It sends structured requests to the AI backend. It handles various AI response types and errors gracefully, updating UI/state accordingly.

**Task 12.2.4: Integrate AI Action Panel Trigger**
*   **Target Files:** `libs/ui/feature-components/src/lib/service-request/ServiceRequestDisplay.tsx` and potentially a store like `uiStore.ts` or `serviceRequestStore.ts` to manage panel visibility.
*   **Definition:** Connect the "Use this ServiceRequest with AI" button in `ServiceRequestDisplay.tsx` to show/hide the `ServiceRequestAIActionPanel.tsx`.
*   **Core Logic:**
    *   Modify the button's `onClick` handler in `ServiceRequestDisplay.tsx`.
    *   When clicked, set a state (e.g., in `uiStore` or `serviceRequestStore` like `showAIActionPanelForRequest: serviceRequest`) that controls the visibility of `ServiceRequestAIActionPanel.tsx`.
    *   The panel should be rendered (e.g., as a modal, or an inline expansion) when this state indicates it should be visible for the currently selected `ServiceRequest`.
*   **Acceptance Criteria:** Clicking the "Use this ServiceRequest with AI" button on `ServiceRequestDisplay.tsx` makes the `ServiceRequestAIActionPanel.tsx` visible and operational, populated with the context of the selected ServiceRequest.

### 12.3. Phase 9.C: Handling AI-Generated Outputs

**Objective:** Provide flexible and user-friendly ways to manage and use outputs generated by AI actions based on ServiceRequests.

**Task 12.3.1: Display Text Outputs in Chat View**
*   **Target Files:** `libs/core/hooks/src/lib/useAIChatAPI.ts` (or `useAIServiceRequestActions.ts`), `libs/core/state/src/lib/stores/chatStore.ts`.
*   **Definition:** Ensure that standard text-based outputs (or textual parts of structured responses) from ServiceRequest AI Actions are displayed in the existing `AIChatView.tsx`.
*   **Core Logic:**
    *   The `triggerServiceRequestAIAction` function (from Task 12.2.3) should, by default, route text responses to be added to the chat history via `chatStore.addMessage()`.
    *   Ensure messages originating from a ServiceRequest action are clearly attributed or visually distinct in the chat (e.g., prefixing with "AI (from ServiceRequest Action):" or using a specific icon/metadata in the chat message object).
*   **Acceptance Criteria:** AI responses from ServiceRequest actions appear clearly and appropriately attributed in the `AIChatView`.

**Task 12.3.2: Conceptual: "Project Pad" or Output Collection Area (MVP: Copy from Chat)**
*   **Target Files:** (Conceptual for now, impacts chat view design for copyability)
*   **Definition:** For MVP, ensure AI-generated text can be easily copied from the chat. For larger text outputs, consider if the chat view handles them well or if a temporary modal/viewer is needed.
*   **Core Logic (MVP):**
    *   Ensure chat messages in `AIChatView.tsx` have a "Copy" button or are easily selectable for manual copying.
    *   If AI generates large documents (e.g., full application outlines), review if the chat view's presentation is adequate for readability and copying.
*   **Acceptance Criteria (MVP):** Textual AI outputs are readable in the chat view and can be easily copied by the user. Consideration has been given to the presentation of larger text outputs.

### 12.4. Phase 9.D: Rich Integration with VSCodium/`code-server` for AI Outputs

**Objective:** Enable AI actions to interact directly with the code editor, such as inserting generated code snippets or creating new files.

**Task 12.4.1: Define New `code-server` Message Types (if needed)**
*   **Target Files:** `libs/core/types/src/lib/code-server.types.ts`
*   **Definition:** Review existing `code-server` message types. If Step 8 (`atlas_ide_react_step8_plan.md`) already defined sufficient commands (e.g., `INSERT_CODE_SNIPPET_COMMAND`, `CREATE_FILE_WITH_CONTENT_COMMAND`, `SHOW_GHOST_TEXT_COMMAND`), new ones might not be strictly necessary for this phase. If not, define them.
*   **Example Commands (if not existing):**
    *   `INSERT_SNIPPET_AT_CURSOR_COMMAND` / `INSERT_SNIPPET_AT_CURSOR_RESPONSE`
    *   `CREATE_FILE_WITH_CONTENT_COMMAND` / `CREATE_FILE_WITH_CONTENT_RESPONSE`
    *   `SHOW_GHOST_TEXT_COMMAND` / `SHOW_GHOST_TEXT_RESPONSE`
*   **Acceptance Criteria:** Necessary `code-server` message types for inserting snippets, creating files, and showing ghost text are defined and available for use by `useCodeServerComm.ts`.

**Task 12.4.2: Utilize `code-server` Commands for Code Outputs**
*   **Target Files:** `libs/core/hooks/src/lib/useAIChatAPI.ts` (or `useAIServiceRequestActions.ts`), `libs/core/hooks/src/lib/useCodeServerComm.ts`.
*   **Definition:** Modify the AI response handling logic in `triggerServiceRequestAIAction` to use `code-server` commands when the AI output is code and the `aiTaskType` suggests editor interaction.
*   **Core Logic:**
    *   The AI response might be structured JSON indicating the desired editor action (e.g., `{"action_type": "insert_snippet", "language": "python", "content": "...", "explanation": "..."}`).
    *   Based on this structured response or the `aiTaskType` (e.g., `GENERATE_BOILERPLATE`):
        *   Call `codeServerComm.sendCommand('INSERT_SNIPPET_AT_CURSOR_COMMAND', { snippet: aiResponse.code })`.
        *   Or `codeServerComm.sendCommand('CREATE_FILE_WITH_CONTENT_COMMAND', { filePath: suggestedPath, content: aiResponse.code })`.
        *   Or `codeServerComm.sendCommand('SHOW_GHOST_TEXT_COMMAND', { text: aiResponse.code, context: ... })`.
    *   Handle responses from these `code-server` commands (e.g., success/failure notifications).
*   **Acceptance Criteria:** AI actions can result in content being inserted as snippets, new files being created with generated content, or ghost text being shown in the editor, based on structured AI responses and appropriate `code-server` commands.

### 12.5. Phase 9.E: Testing, Documentation, and Accessibility

**Objective:** Ensure the new ServiceRequest integration and AI action features are robust, well-documented, and accessible.

**Task 12.5.1: Unit & Integration Tests**
*   **Target Files:** Relevant `*.spec.ts` files alongside components, hooks, and stores.
*   **Definition:** Write unit tests for new Zustand stores, hooks (`populatePromptTemplate`, `triggerServiceRequestAIAction` logic), and UI components. Write integration tests for the flow from search to AI action triggering.
*   **Core Logic:**
    *   Use Jest and React Testing Library.
    *   Mock react query Client responses for store tests.
    *   Mock `code-server` communication for hook tests.
    *   Test various states of UI components (loading, error, data).
*   **Acceptance Criteria:** Key logic in new stores, hooks, and components is covered by unit tests. Core user flows (search, select, trigger AI action) have integration tests. Test coverage meets project standards.

**Task 12.5.2: Storybook Stories**
*   **Target Files:** Relevant `*.stories.tsx` files alongside new UI components (`ServiceRequestSearchPanel`, `ServiceRequestDisplay`, `ServiceRequestAIActionPanel`).
*   **Definition:** Create Storybook stories for all new UI components to document their states and props.
*   **Core Logic:**
    *   Showcase components with mock data (from Task 12.1.6).
    *   Demonstrate different states (e.g., loading, error, with data, empty).
    *   Include controls for interactive props.
*   **Acceptance Criteria:** Storybook stories are created for all new UI components, covering their primary use cases and states.

**Task 12.5.3: Update Project Documentation**
*   **Target Files:** `README.md`, `docs/features.md`, `docs/ai_actions.md` (new).
*   **Definition:** Document the new ServiceRequest integration feature, including how to use it, how to define new AI actions, and any relevant architectural decisions.
*   **Core Logic:**
    *   Explain the user workflow.
    *   Detail the `ServiceRequestAIAction` interface and how to add new actions to `aiServiceRequestActions.ts`.
*   **Acceptance Criteria:** Project documentation is updated to reflect the new features and their usage.

**Task 12.5.4: Accessibility Review (WCAG 2.2 AA)**
*   **Target Files:** All new UI components.
*   **Definition:** Perform an accessibility review of the new UI components, ensuring they meet WCAG 2.2 Level AA standards.
*   **Core Logic:**
    *   Check keyboard navigability.
    *   Ensure proper ARIA attributes are used where necessary.
    *   Verify color contrast.
    *   Test with screen reader (basic check).
*   **Acceptance Criteria:** New UI components are keyboard accessible, have appropriate ARIA roles/attributes, meet color contrast requirements, and are generally usable with assistive technologies.

**Task 12.5.5: End-to-End Manual Testing**
*   **Target Files:** The `atlas-ide-shell` application.
*   **Definition:** Conduct comprehensive manual testing of the entire Step 9 feature set in a simulated environment.
*   **Core Logic:**
    *   Test searching for ServiceRequests with various criteria.
    *   Test selecting and displaying ServiceRequest details.
    *   Test triggering different AI actions with and without parameters.
    *   Verify AI outputs are handled correctly (chat, code insertion).
    *   Test edge cases and error handling (e.g., no search results, AI errors).
*   **Acceptance Criteria:** The primary user flow from searching a ServiceRequest to receiving and utilizing an AI-generated output is successful and robust. Error states are handled gracefully. The feature is stable.