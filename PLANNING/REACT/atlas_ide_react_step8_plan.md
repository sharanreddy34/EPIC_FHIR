# Atlas IDE: React Frontend - Step 8 Plan: Intelligent FHIR-Aware Code Generation & Advanced AI Collaboration Tools

This document outlines the tasks for Step 8, focusing on introducing intelligent code generation capabilities sensitive to FHIR context, enhancing AI-driven suggestions for FHIR-related code, and adding initial collaborative AI tooling. This step builds upon the V1 stabilized features from Step 6/7.

## Introduction

Step 8 aims to significantly enhance the AI's role as a proactive coding partner, particularly when working with FHIR data structures and clinical workflows. Key themes include:

*   **FHIR-Contextual Code Generation:** Moving beyond simple completions to generating meaningful code blocks (e.g., functions, components) based on FHIR resource types and user intent.
*   **Smart FHIR Snippets & Templates:** Providing developers with readily usable, best-practice code snippets for common FHIR operations.
*   **AI-Powered Debugging for FHIR Interactions:** Assisting developers in identifying and correcting issues in code that consumes or produces FHIR data.
*   **Collaborative AI:** Initial features for sharing, discussing, or versioning AI suggestions or generated code within a team context (placeholder for future full-fledged features).
*   **Enhanced Task Understanding:** Improving the AI's awareness of the developer's current high-level task or goal.

This plan follows the nano-scale instruction format for direct LLM implementation.

---

## A. FHIR-Contextual Code Generation & Smart Snippets

This section focuses on enabling the AI to generate meaningful code blocks based on FHIR context and providing developers with intelligent FHIR-related code snippets.

### 1. Enhance AI Chat for Code Generation Requests

*   **File:** `libs/core/core-hooks/src/lib/useAIChatAPI.ts` (from Step 4)
    *   **Task:** Modify the `sendMessage` function or add a new function `requestAiCodeGeneration`.
    *   **New Parameters:** Accept `generationGoal: string` (e.g., "generate a React component to display a Patient resource", "create a function to extract all conditions from a bundle"), `fhirContext: { resourceType?: string, profileUrl?: string, exampleResource?: object }`, `codeContext: { languageId: string, surroundingCode?: string, projectFramework?: 'Next.js' | 'React' }`.
    *   **API Endpoint:** This will likely target a new backend endpoint (e.g., `/api/v1/ai/generate_code`) optimized for code generation tasks.
    *   **Response Interface:** Expect a response like `{ generatedCode: string, languageId: string, explanation?: string, requiredImports?: string[], potentialIssues?: string[] }`.
    *   **State Management:** Handle loading, success (with generated code), and error states specific to code generation.

*   **File:** `apps/atlas-ide-shell/src/components/AIChat/AIChatView.tsx` (from Step 3)
    *   **Task:** Add a new UI element (e.g., a dedicated button or a prefix like `/generate`) to trigger code generation mode within the chat.
    *   **Input Gathering:** When in generation mode, guide the user to provide necessary context (e.g., target FHIR resource, desired functionality).
    *   **Displaying Generated Code:** Render the `generatedCode` in a formatted block (e.g., using a syntax highlighter component). Provide options to "Copy Code", "Insert into Editor", or "Request Revisions".
    *   **Displaying Metadata:** Show `explanation`, `requiredImports`, and `potentialIssues` alongside the code.

### 2. New `code-server` Messages for Code Insertion & Management

*   **File:** `libs/core/core-hooks/src/lib/codeServerMessageTypes.ts` (from Step 3)
    *   **Task:** Define new message types:
        ```typescript
        // Request from React Shell to Code Server Extension
        export interface InsertCodeSnippetCommand extends BaseMessageToCodeServer {
          type: 'INSERT_CODE_SNIPPET_COMMAND';
          payload: { 
            code: string; 
            languageId: string; 
            imports?: string[]; // Optional: extension might try to add these
            position?: 'cursor' | 'selection' | 'newFile'; 
            newFileName?: string; // if position is newFile
          };
        }
        export interface PreviewCodeChangesCommand extends BaseMessageToCodeServer { 
          type: 'PREVIEW_CODE_CHANGES_COMMAND';
          payload: { originalContent: string; modifiedContent: string; languageId: string; title?: string };
        } // This might reuse SHOW_DIFF_VIEW_COMMAND if semantics match

        // Response from Code Server Extension to React Shell
        export interface InsertCodeSnippetResponse extends BaseMessageFromCodeServer {
          type: 'INSERT_CODE_SNIPPET_RESPONSE';
          payload: { success: boolean; filePath?: string; error?: string };
        }
        ```

*   **File:** `libs/core/core-hooks/src/lib/useCodeServerComm.ts` (from Step 3)
    *   **Task:** Implement helper functions to send these new messages (e.g., `insertCodeSnippet(payload: InsertCodeSnippetCommand['payload'])`).
    *   Handle responses, including success/failure and potential error messages.

### 3. `CodeGenerationPreview.tsx` Component (Optional Modal or AIChatView Enhancement)

*   **Directory:** `apps/atlas-ide-shell/src/components/AICodeGeneration/` (New directory)
*   **File:** `CodeGenerationPreview.tsx` (New file)
*   **Task:** Create a component to specifically handle the preview and interaction with AI-generated code.
    *   **Input:** Takes `generatedCode`, `languageId`, `explanation`, `requiredImports`, `potentialIssues` as props.
    *   **Features:**
        *   Syntax-highlighted code display (e.g., using `react-syntax-highlighter`).
        *   Display of explanation and potential issues.
        *   Buttons: "Copy to Clipboard", "Insert into Editor at Cursor", "Insert into New File", "Request Revisions".
        *   "Insert into Editor" would use `useCodeServerComm.insertCodeSnippet()`.
        *   "Request Revisions" would re-prompt the AI with the original request plus user feedback.
    *   Could be rendered as a modal dialog or integrated directly into an expanded `AIChatView` message.

### 4. Smart FHIR Snippet Library & Access

*   **Concept:** A curated or AI-augmented library of common FHIR-related code patterns and snippets.
*   **Data Structure (Placeholder):** Define a `FhirSnippet` interface:
    ```typescript
    // Potentially in libs/fhir/fhir-utils/src/lib/fhirSnippets.types.ts
    interface FhirSnippet {
      id: string;
      title: string;
      description: string;
      fhirResourceType?: string; // e.g., 'Patient', 'Observation'
      category: 'Data Access' | 'Data Transformation' | 'UI Component Example' | 'Validation';
      languageId: 'typescript' | 'javascript';
      code: string;
      requiredImports?: string[];
      tags: string[];
    }
    ```
*   **Storage/Access (Initial - Mocked/Static):**
    *   **File:** `libs/fhir/fhir-utils/src/lib/mockFhirSnippets.ts` (New file)
    *   **Task:** Create an array of mock `FhirSnippet` objects.
*   **`FhirSnippetExplorer.tsx` Component (New Component)
    *   **Directory:** `apps/atlas-ide-shell/src/components/FhirTools/` (New directory)
    *   **File:** `FhirSnippetExplorer.tsx`
    *   **Task:**
        *   Display snippets from `mockFhirSnippets.ts` (later, this could be fetched from a backend or an AI service).
        *   Allow filtering by `fhirResourceType`, `category`, `tags`.
        *   Display snippet details (description, code) on selection.
        *   Provide "Copy Code" and "Insert into Editor" (via `useCodeServerComm`) actions for selected snippets.
*   **Integration:** Could be a tab in the `Sidebar` or accessible via the Command Palette.

*   **AI Integration with Snippets:**
    *   The `useAIChatAPI` for code generation could be enhanced to allow the AI to reference/utilize these snippets if relevant to the user's request.
    *   The AI could also suggest snippets from the library based on editor context.

### 5. Command Palette Integration for Code Generation & Snippets

*   **File:** `libs/core/core-hooks/src/lib/useCommandRegistry.ts` (from Step 4)
    *   **Task:** Register new commands:
        *   `{ id: 'ai.generateCode', title: 'AI: Generate Code...', action: () => { /* Open AIChatView in generation mode or trigger CodeGenerationModal */ } }`
        *   `{ id: 'fhir.browseSnippets', title: 'FHIR: Browse Code Snippets', action: () => { /* Open FhirSnippetExplorer.tsx view */ } }`
        *   `{ id: 'ai.generateFhirComponent', title: 'AI: Generate FHIR React Component for [ResourceType]', action: (context) => { /* Prompt for ResourceType, then trigger generation */ } }` (This command might be dynamic or require a sub-prompt).

---

## B. AI-Powered Debugging & Analysis for FHIR Interactions

This section focuses on leveraging AI to help developers understand, debug, and optimize code that interacts with FHIR resources.

### 1. New `code-server` Messages for Debugging Context

*   **File:** `libs/core/core-hooks/src/lib/codeServerMessageTypes.ts` (from Step 3, extended in Step 8.A)
    *   **Task:** Define new message types:
        ```typescript
        // Request from React Shell to Code Server Extension
        export interface GetCodeContextForAnalysisCommand extends BaseMessageToCodeServer {
          type: 'GET_CODE_CONTEXT_FOR_ANALYSIS_COMMAND';
          payload: { 
            filePath: string; 
            selectionRange?: { startLine: number; startColumn: number; endLine: number; endColumn: number }; // Optional, for selected text
            includeFullFileContent?: boolean; // Option to send whole file
            includeDiagnostics?: boolean; // Option to include compiler/linter diagnostics for the selection/file
          };
        }

        // Response from Code Server Extension to React Shell
        export interface GetCodeContextForAnalysisResponse extends BaseMessageFromCodeServer {
          type: 'GET_CODE_CONTEXT_FOR_ANALYSIS_RESPONSE';
          payload: {
            filePath: string;
            selectedCode?: string;
            fullFileContent?: string;
            languageId: string;
            diagnostics?: Array<{ 
              message: string; 
              severity: 'error' | 'warning' | 'info' | 'hint'; 
              range: { startLine: number; startColumn: number; endLine: number; endColumn: number }; 
            }>;
            error?: string; // If context retrieval failed
          };
        }
        ```

*   **File:** `libs/core/core-hooks/src/lib/useCodeServerComm.ts` (from Step 3, extended in Step 8.A)
    *   **Task:** Implement a helper function `getCodeContextForAnalysis(payload: GetCodeContextForAnalysisCommand['payload'])`.
    *   This function will be used to fetch the necessary code and diagnostic information from the `code-server` extension before sending it to the AI for analysis.

### 2. Enhance AI Chat for Debugging/Analysis Requests

*   **File:** `libs/core/core-hooks/src/lib/useAIChatAPI.ts` (from Step 4, extended in Step 8.A)
    *   **Task:** Add a new function `requestAiCodeAnalysis`.
    *   **Parameters:** Accept `analysisGoal: 'explainError' | 'suggestFix' | 'optimizeCode' | 'explainCode'`, `codeContext: GetCodeContextForAnalysisResponse['payload']`, `userQuery?: string` (e.g., "Why am I getting a type error here?", "How can I make this FHIR search more efficient?").
    *   **API Endpoint:** This will likely target a new backend endpoint (e.g., `/api/v1/ai/analyze_code`) designed for code understanding and debugging tasks.
    *   **Response Interface:** Expect a response like `{ analysis: string, suggestedFixes?: Array<{ description: string; codePatch?: string; explanation?: string }>, relatedFhirDocs?: Array<{ title: string, url: string }> }`.
        *   `codePatch` could be in a standard diff format or simply the replacement code block.

*   **File:** `apps/atlas-ide-shell/src/components/AIChat/AIChatView.tsx` (from Step 3, extended in Step 8.A)
    *   **Task:** Integrate UI elements for AI-powered debugging.
        *   Allow users to trigger analysis, e.g., by right-clicking selected code in `CodeServerView` (requires `code-server` extension support for context menus that message the shell) or via a command palette action.
        *   When triggered, use `useCodeServerComm.getCodeContextForAnalysis()` then `useAIChatAPI.requestAiCodeAnalysis()`.
        *   Display `analysis`, `suggestedFixes` (with options to apply patches using `INSERT_CODE_SNIPPET_COMMAND` or `PREVIEW_CODE_CHANGES_COMMAND`), and links to `relatedFhirDocs`.

### 3. `AIDebuggingAssistant.tsx` Component (Alternative to AIChatView integration)

*   **Directory:** `apps/atlas-ide-shell/src/components/AIDebugging/` (New directory)
*   **File:** `AIDebuggingAssistant.tsx` (New file)
*   **Task:** A dedicated component (perhaps in a separate panel or modal) for AI debugging interactions.
    *   Could be invoked from context menus in `CodeServerView` or the `ProblemsView`.
    *   Manages the flow of fetching code context, sending to AI, and displaying results (analysis, suggestions).
    *   Provides UI to apply suggested code patches (e.g., showing a diff preview before applying).

### 4. Integration with `ProblemsView.tsx`

*   **File:** `apps/atlas-ide-shell/src/components/ProblemsView/ProblemsView.tsx` (from Step 5)
    *   **Task:** For each listed problem/diagnostic, add an action button/icon (e.g., "Ask AI" or a lightbulb icon).
    *   **Action:** Clicking this button would:
        1.  Call `useCodeServerComm.getCodeContextForAnalysis()` with the `filePath` and `range` of the specific diagnostic.
        2.  Call `useAIChatAPI.requestAiCodeAnalysis()` with `analysisGoal: 'explainError'` or `'suggestFix'`, the retrieved context, and the diagnostic message as the `userQuery`.
        3.  Display the AI's response, potentially in the `AIChatView` or a dedicated `AIDebuggingAssistant` panel.

### 5. Command Palette Integration for Debugging

*   **File:** `libs/core/core-hooks/src/lib/useCommandRegistry.ts` (from Step 4, extended in Step 8.A)
    *   **Task:** Register new commands:
        *   `{ id: 'ai.explainSelection', title: 'AI: Explain Selected Code', action: () => { /* Trigger getCodeContextForAnalysis for selection, then requestAiCodeAnalysis with 'explainCode' */ } }`
        *   `{ id: 'ai.suggestFixForSelection', title: 'AI: Suggest Fix for Selected Code', action: () => { /* Trigger for selection, then 'suggestFix' */ } }`
        *   `{ id: 'ai.optimizeSelection', title: 'AI: Optimize Selected Code', action: () => { /* Trigger for selection, then 'optimizeCode' */ } }`
        *   `{ id: 'ai.analyzeCurrentFileProblems', title: 'AI: Analyze Problems in Current File', action: () => { /* Get diagnostics for active file, send to AI */ } }`

---

## C. Rudimentary AI Collaboration & Suggestion Management

This section introduces initial features for managing AI-generated suggestions and outputs, laying groundwork for future collaborative capabilities. The focus is on allowing users to save, revisit, and potentially share key AI interactions.

### 1. Enhancing AI Interaction History & Pinning

*   **File:** `libs/core/core-state/src/lib/chatStore.ts` (from Step 4)
    *   **Task:** Extend the chat message interface (`ChatMessage`) and store to support more metadata and user actions on messages.
        ```typescript
        interface ChatMessage {
          // ... existing fields (id, role, content, timestamp)
          type: 'userQuery' | 'aiResponse' | 'aiGeneratedCode' | 'aiAnalysis' | 'systemNotification';
          metadata?: { 
            codeLanguage?: string;
            sourceFilePath?: string;
            sourceSelection?: string;
            relatedFhirResource?: string;
            // ... other relevant context from the AI request
          };
          isPinned?: boolean;
          userFeedback?: 'helpful' | 'unhelpful' | null;
          tags?: string[];
        }
        // Add actions to pin/unpin messages, add tags, submit feedback
        // Add a selector for pinned messages
        ```

*   **File:** `apps/atlas-ide-shell/src/components/AIChat/AIChatView.tsx` (extended in Step 8.A & 8.B)
    *   **Task:** Update UI to reflect new `ChatMessage` capabilities.
        *   Display metadata associated with AI responses/generations in a structured way (e.g., under a collapsible section).
        *   Add a "Pin" button to individual AI messages (especially those containing code or significant analysis).
        *   Allow users to provide quick feedback (thumbs up/down) on AI responses.
        *   (Optional) Allow users to add simple text tags to messages for easier filtering/search later.

### 2. `PinnedSuggestionsView.tsx` Component

*   **Directory:** `apps/atlas-ide-shell/src/components/AISuggestions/` (New directory)
*   **File:** `PinnedSuggestionsView.tsx` (New file)
*   **Task:** Create a new view, possibly as a tab in the Sidebar or a dedicated panel, to display all pinned AI messages/suggestions.
    *   **Data Source:** Subscribes to the `chatStore` and filters for messages where `isPinned === true`.
    *   **Display:** Shows a summary of each pinned item (e.g., a snippet of the content, timestamp, associated metadata like `sourceFilePath` or `relatedFhirResource`).
    *   **Actions:**
        *   Clicking an item could jump back to its context in the main `AIChatView` (if feasible) or simply show its full content within the `PinnedSuggestionsView`.
        *   Allow unpinning items.
        *   (Optional) Basic search/filter by tags or keywords within pinned items.

### 3. Simple Export/Sharing of AI Outputs

*   **File:** `apps/atlas-ide-shell/src/components/AIChat/AIChatView.tsx` or `PinnedSuggestionsView.tsx`
    *   **Task:** Add a "Share" or "Export" action to individual AI messages (especially code generations or analyses).
    *   **Functionality (Initial - Simple):**
        *   **"Copy as Markdown"**: Copies the AI's output (code, explanation) formatted as Markdown to the clipboard. This allows easy pasting into documents, issues, or other communication channels.
        *   **"Save as File"**: For generated code, allow saving the content directly to a local file (e.g., `.ts`, `.tsx`, `.md`). This would use browser download capabilities.
    *   **Note:** This is not a full collaborative editing feature but provides basic utility for sharing.

### 4. Command Palette Integration for Suggestion Management

*   **File:** `libs/core/core-hooks/src/lib/useCommandRegistry.ts` (extended in Step 8.A & 8.B)
    *   **Task:** Register new commands:
        *   `{ id: 'ai.viewPinnedSuggestions', title: 'AI: View Pinned Suggestions', action: () => { /* Open PinnedSuggestionsView.tsx */ } }`
        *   `{ id: 'ai.clearChatHistory', title: 'AI: Clear Chat History (excluding pinned)', action: () => { /* Implement in chatStore, prompt for confirmation */ } }`

---

## D. Enhanced AI Task & Workflow Understanding

This section focuses on improving the AI's awareness of the developer's broader goals and current workflow, enabling more contextually relevant and proactive assistance, especially for multi-step FHIR-related tasks.

### 1. Task Context State Management

*   **Directory:** `libs/core/core-state/src/lib/` (Existing directory)
*   **File:** `taskContextStore.ts` (New file)
*   **Task:** Create a new Zustand store to manage the developer's current task context.
    ```typescript
    interface TaskContext {
      currentTaskId: string | null;
      currentTaskDescription: string | null; // e.g., "Implement patient search by MRN"
      relatedFiles: Array<{ filePath: string; relevance?: string }>;
      relatedFhirResources: string[]; // e.g., ['Patient', 'Encounter']
      taskSteps?: Array<{ description: string; status: 'pending' | 'in-progress' | 'completed' | 'blocked'; notes?: string }>;
      taskStartDate: Date | null;
      taskDueDate?: Date | null; // Optional
    }

    interface TaskContextState extends TaskContext {
      setCurrentTask: (description: string, details?: Partial<Omit<TaskContext, 'currentTaskDescription'>>) => void;
      updateTaskStepStatus: (stepIndex: number, status: TaskContext['taskSteps'][0]['status'], notes?: string) => void;
      addRelatedFile: (filePath: string, relevance?: string) => void;
      clearCurrentTask: () => void;
    }

    // const useTaskContextStore = create<TaskContextState>((set, get) => ({ ...initial state and actions... }));
    ```
    *   **Actions:** Include methods to set/clear the current task, add related files/FHIR resources, and update steps (if using a simple step tracker).

### 2. UI for Managing Task Context

*   **`TaskContextInput.tsx` Component (New Component)
    *   **Directory:** `apps/atlas-ide-shell/src/components/TaskManagement/` (New directory)
    *   **File:** `TaskContextInput.tsx`
    *   **Task:** Create a simple UI element (e.g., a text input in the sidebar or a modal) where the user can describe their current high-level task.
        *   On submit, it calls `useTaskContextStore.setCurrentTask()`.
        *   Could also have fields to quickly add related FHIR resource types involved.

*   **`CurrentTaskDisplay.tsx` Component (New Component)
    *   **Directory:** `apps/atlas-ide-shell/src/components/TaskManagement/`
    *   **File:** `CurrentTaskDisplay.tsx`
    *   **Task:** Display the `currentTaskDescription` and other relevant task context (e.g., related files, FHIR resources) in a visible area of the IDE (e.g., header, status bar, or a dedicated panel).
        *   Allows the user to quickly see and potentially clear/edit the current task.

*   **Implicit Context Collection (Future Consideration - Out of Scope for Initial Implementation):**
    *   The `code-server` extension could potentially infer task context by observing file open patterns, edited symbols, or frequently used commands, and suggest a task context to the user.

### 3. Integrating Task Context with AI Requests

*   **File:** `libs/core/core-hooks/src/lib/useAIChatAPI.ts` (extended in Step 8.A & 8.B)
    *   **Task:** Modify AI request functions (`sendMessage`, `requestAiCodeGeneration`, `requestAiCodeAnalysis`) to optionally include the current task context.
    *   **Logic:** Before sending a request to the AI backend, retrieve `currentTaskDescription`, `relatedFiles`, `relatedFhirResources` from `useTaskContextStore`.
    *   **API Payload:** Add these fields to the payload sent to the backend AI service. The backend can then use this broader context to tailor its responses.
        ```typescript
        // Example modification to an AI request payload
        interface AIRequestPayload {
          // ... existing fields ...
          currentTask?: {
            description: string;
            relatedFiles?: string[]; // Paths or just names
            relatedFhirResources?: string[];
          };
        }
        ```

### 4. AI-Assisted Workflow Guidance (Conceptual - Initial Steps)

*   **Concept:** The AI, aware of the `currentTaskDescription` and potentially pre-defined `taskSteps`, could offer proactive guidance or suggestions related to the overall task, not just isolated code issues.
*   **Example Interaction (within `AIChatView`):
    *   User sets task: "Implement FHIR Patient Demographics Display Component"
    *   AI (if task context is sent): "Okay, for a Patient Demographics component, you'll typically need to:
        1.  Fetch Patient resource data.
        2.  Design the UI layout (e.g., using MUI Cards or Lists).
        3.  Handle loading and error states.
        4.  Ensure accessibility.
        Would you like help starting with fetching the Patient data, or perhaps a basic component structure?"
*   **Initial Implementation Focus:**
    *   The backend AI service would be responsible for breaking down tasks or providing workflow suggestions based on the `currentTaskDescription`.
    *   The frontend would primarily focus on sending the task context and displaying the AI's workflow-related responses.
    *   The `taskSteps` in `taskContextStore` could be manually populated by the user or potentially by the AI if it suggests a plan.

### 5. Command Palette for Task Management

*   **File:** `libs/core/core-hooks/src/lib/useCommandRegistry.ts` (extended in Step 8.A, B, C)
    *   **Task:** Register new commands:
        *   `{ id: 'task.setCurrent', title: 'Task: Set/Update Current Task...', action: () => { /* Open TaskContextInput.tsx or a modal */ } }`
        *   `{ id: 'task.viewCurrent', title: 'Task: View Current Task Details', action: () => { /* Show CurrentTaskDisplay.tsx or relevant info in a modal/panel */ } }`
        *   `{ id: 'task.clearCurrent', title: 'Task: Clear Current Task', action: () => { useTaskContextStore.getState().clearCurrentTask(); } }`

---

## E. Testing, Documentation, and Accessibility for Step 8 Features

This section outlines the testing, documentation, and accessibility considerations for the features introduced in Step 8, ensuring they meet the project's quality standards.

### 1. Testing Strategies

*   **Unit Tests (Jest & React Testing Library):**
    *   `useAIChatAPI.ts`: Mock backend responses and test new functions (`requestAiCodeGeneration`, `requestAiCodeAnalysis`) for handling different states (loading, success, error) and parsing various AI response structures.
    *   `useCodeServerComm.ts`: Test new helper functions for sending messages (`insertCodeSnippet`, `getCodeContextForAnalysis`) and handling their responses.
    *   `chatStore.ts`: Test new actions and selectors related to pinning, feedback, and metadata.
    *   `taskContextStore.ts`: Test all actions for setting, updating, and clearing task context.
    *   New UI Components (`CodeGenerationPreview.tsx`, `FhirSnippetExplorer.tsx`, `AIDebuggingAssistant.tsx`, `PinnedSuggestionsView.tsx`, `TaskContextInput.tsx`, `CurrentTaskDisplay.tsx`): Test rendering based on props, user interactions (button clicks, form submissions), and state changes.

*   **Integration Tests (React Testing Library, MSW for backend mocks):**
    *   Test the flow of AI code generation: User input in `AIChatView` -> `useAIChatAPI` -> Mock AI response -> Display in `CodeGenerationPreview` -> Code insertion via `useCodeServerComm`.
    *   Test the flow of AI debugging: Triggering analysis from `ProblemsView` or `AIChatView` -> `useCodeServerComm.getCodeContextForAnalysis` -> `useAIChatAPI.requestAiCodeAnalysis` -> Display of analysis and suggestions.
    *   Test pinning/unpinning suggestions in `AIChatView` and their appearance/disappearance in `PinnedSuggestionsView`.
    *   Test setting/clearing task context via `TaskContextInput` and its reflection in `CurrentTaskDisplay` and inclusion in AI API calls.
    *   Test Command Palette integration for all new commands, ensuring they trigger the correct actions/UI components.

*   **End-to-End Tests (Playwright/Cypress - building on Step 6 suite):**
    *   Create E2E scenarios for core Step 8 user stories:
        *   User successfully generates a FHIR-related React component using AI chat and inserts it into the editor.
        *   User selects a code block with a FHIR-related error, requests AI analysis, receives a suggestion, and applies the fix.
        *   User pins an important AI suggestion and later retrieves it from the pinned suggestions view.
        *   User sets a high-level task, and AI chat responses are more contextually relevant to that task.
        *   User browses and inserts a code snippet from the `FhirSnippetExplorer`.
    *   Validate interactions with the (mocked or live) `code-server` extension for code insertion and context retrieval.

*   **Manual Test Plan:**
    *   Develop a comprehensive manual test plan covering edge cases, usability, and exploratory testing for all new features.
    *   Pay special attention to the quality and relevance of AI-generated code and analysis for various FHIR-related scenarios.

### 2. Documentation

*   **Developer Documentation (`/docs` or Wiki):
    *   Update documentation for `useAIChatAPI.ts`, `useCodeServerComm.ts`, `chatStore.ts`, and `taskContextStore.ts` with details on new functions, state structures, and interaction patterns.
    *   Document new `code-server` message types (`codeServerMessageTypes.ts`) and their expected payloads/behaviors.
    *   Provide guidance on creating and using new UI components (`CodeGenerationPreview.tsx`, etc.).
    *   Explain how to extend the `FhirSnippetExplorer` with new snippets (if applicable).
    *   Document the backend API expectations for new AI endpoints (code generation, code analysis), including how task context is utilized.

*   **End-User Documentation (In-app Help / User Guide):
    *   Create user-friendly guides on how to use the new AI features:
        *   How to request code generation and interact with the results.
        *   How to use AI for debugging and code explanation.
        *   How to manage pinned suggestions.
        *   How to set and use the "Current Task" context feature.
        *   How to browse and use the FHIR Snippet Library.
    *   Update Command Palette documentation with new commands.
    *   Consider short video tutorials or animated GIFs for key workflows.

### 3. Accessibility (WCAG 2.2 AA Compliance)

*   **Review all new UI components introduced in Step 8:**
    *   `CodeGenerationPreview.tsx`
    *   `FhirSnippetExplorer.tsx`
    *   `AIDebuggingAssistant.tsx` (if created as a separate component)
    *   `PinnedSuggestionsView.tsx`
    *   `TaskContextInput.tsx`
    *   `CurrentTaskDisplay.tsx`
    *   Enhancements to `AIChatView.tsx` for pinning, feedback, metadata display.
*   **Specific Checks:**
    *   **Keyboard Navigation:** Ensure all interactive elements are fully keyboard accessible (buttons, inputs, tabs, list items).
    *   **Screen Reader Compatibility:** Verify proper ARIA attributes, roles, and labels for all elements, especially for dynamic content updates (e.g., AI responses, generated code displays, pinned suggestions list).
    *   **Focus Management:** Ensure logical focus order and that focus is appropriately managed when modals (`CodeGenerationPreview`) or new views appear.
    *   **Color Contrast:** Check contrast ratios for text, UI elements, and syntax highlighting in code displays.
    *   **Accessible Names & Descriptions:** Ensure all controls have clear and descriptive labels.
    *   **Forms:** Ensure any new input fields (`TaskContextInput`) have associated labels and clear instructions.
*   **Tools:** Utilize automated accessibility checkers (e.g., Axe DevTools) and perform manual testing with screen readers (e.g., NVDA, VoiceOver).

---

This completes the detailed plan for Step 8.
