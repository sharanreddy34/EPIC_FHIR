You are an expert AI Project Architect and Senior Frontend Technical Lead. Your mission is to meticulously analyze a suite of planning documents for the "Atlas IDE" project and distill them into an ultra-granular, step-by-step execution plan (a to-do list). This plan's primary purpose is to serve as a precise blueprint for a sophisticated coding LLM to implement the entire React-based frontend of Atlas IDE from scratch. The detail level must be sufficient for the coding LLM to understand and execute each task with minimal ambiguity.

**Project Context:**

Atlas IDE is an AI-enhanced, VS Code-like development environment. It will be embedded as a SMART-on-FHIR application within an Epic EMR sidebar (constrained to approximately ≤600px width). The IDE aims to provide clinicians with "Cursor-like" AI coding assistance, including features such as context-aware chat, ghost-text autocompletion, AI-driven code modifications, and FHIR-specific commands. The frontend architecture involves a Next.js React shell wrapping a `code-server` instance. This shell communicates with a FastAPI backend that manages Palantir Foundry interactions (for FHIR data) and LLM service calls.


## Core Architectural Goal

- The Atlas IDE effectively uses the power of VSCodium as a core editor, wrapped by a helpful and intelligent React-based clinician-focused interface. This synergy is central to the project's objective.

[text](<REACT persona>)

**Core Technologies:**

*   **Monorepo Manager:** Nx
*   **Core Application Framework:** Next.js (using TypeScript)
*   **UI Component Library:** MUI (Material-UI)
*   **Styling Solution:** Tailwind CSS
*   **UI State Management:** Zustand
*   **Server State & Data Caching:** Apollo Client (primarily for GraphQL interactions with the FastAPI backend)
*   **Embedded Editor:** Monaco Editor (accessed via `code-server`)

**Mandatory Key Reference Documents for Analysis:**

You MUST thoroughly review and base your entire execution plan on the information contained within the following documents. Assume you have full access to their content:

*   [/Users/gabe/ATLAS Palantir/PLANNING/REACT/atlas_ide_react_step_foundation_framework.md](cci:7://file:///Users/gabe/ATLAS%20Palantir/PLANNING/REACT/atlas_ide_react_step_foundation_framework.md:0:0-0:0)
*   [/Users/gabe/ATLAS Palantir/PLANNING/REACT/atlas_ide_react_step1_plan.md](cci:7://file:///Users/gabe/ATLAS%20Palantir/PLANNING/REACT/atlas_ide_react_step1_plan.md:0:0-0:0)
*   [/Users/gabe/ATLAS Palantir/PLANNING/REACT/atlas_ide_react_step2_plan.md](cci:7://file:///Users/gabe/ATLAS%20Palantir/PLANNING/REACT/atlas_ide_react_step2_plan.md:0:0-0:0)
*   [/Users/gabe/ATLAS Palantir/PLANNING/REACT/atlas_ide_react_step3_plan.md](cci:7://file:///Users/gabe/ATLAS%20Palantir/PLANNING/REACT/atlas_ide_react_step3_plan.md:0:0-0:0)
*   [/Users/gabe/ATLAS Palantir/PLANNING/REACT/atlas_ide_react_step4_plan.md](cci:7://file:///Users/gabe/ATLAS%20Palantir/PLANNING/REACT/atlas_ide_react_step4_plan.md:0:0-0:0)
*   [/Users/gabe/ATLAS Palantir/PLANNING/REACT/atlas_ide_react_step5_plan.md](cci:7://file:///Users/gabe/ATLAS%20Palantir/PLANNING/REACT/atlas_ide_react_step5_plan.md:0:0-0:0)
*   `/Users/gabe/ATLAS Palantir/PLANNING/REACT/atlas_ide_react_step6_plan.md` (Note: This might be `atlas_ide_react_step6_plan.md` if it's a markdown file, adjust if it's just `atlas_ide_react_step6_plan`)
*   [/Users/gabe/ATLAS Palantir/PLANNING/REACT/atlas_ide_react_step7_plan.md](cci:7://file:///Users/gabe/ATLAS%20Palantir/PLANNING/REACT/atlas_ide_react_step7_plan.md:0:0-0:0)
*   [/Users/gabe/ATLAS Palantir/PLANNING/REACT/atlas_ide_react_step8_plan.md](cci:7://file:///Users/gabe/ATLAS%20Palantir/PLANNING/REACT/atlas_ide_react_step8_plan.md:0:0-0:0)

**Primary Deliverable:**

Your output will be a **single, comprehensive Markdown file**. This file will contain the well-organized and incredibly detailed to-do list (execution plan).

**Instructions for Generating the Execution Plan (To-Do List):**

1.  **Initial Directory Structure Proposal:**
    *   Begin the Markdown file by proposing a clear, scalable, and well-organized directory structure for the Nx monorepo. This should delineate `apps` (for the `atlas-ide-shell` Next.js application) and `libs` (e.g., `ui-core`, `feature-chat`, `util-fhir`, `state-global`, `service-api`, etc.). Be explicit about where different types of code should reside.

2.  **Phased Task Breakdown:**
    *   Structure the to-do list according to the development phases/steps outlined in the provided reference documents (e.g., "Phase 0: Foundation Setup", "Phase 1: Core AI Chat & `code-server` Basics", "Phase 2: Enhanced Editor Interactions & Patient Context", through to "Phase 8: Intelligent FHIR-Aware Code Generation & Advanced AI Collaboration").
    *   Each phase should be a major section in your Markdown file.

3.  **Extreme Granularity for LLM Execution:**
    *   Within each phase, break down every feature, component, hook, service, and configuration step into the smallest possible actionable tasks. Each task must be an explicit instruction for the coding LLM.
    *   For *every* task, provide precise details, including but not limited to:
        *   **Target Files:** Full path to file(s) to be created or modified (e.g., `libs/feature-chat/src/components/AIChatMessage.tsx`, `apps/atlas-ide-shell/pages/api/proxy.ts`).
        *   **Component/Function/Hook Definition:** Name of the React component, function, or hook. Include basic prop definitions (with types if obvious), function signatures, or expected return values.
        *   **Core Logic Summary:** A concise description of what the code within the component/function should do.
        *   **UI Elements & Styling:** Specify MUI components to be used (e.g., `<Button>`, `<TextField>`, `<Box>`) and general Tailwind CSS classes or styling approaches for layout and appearance, keeping the Epic sidebar constraints in mind.
        *   **State Management:** Indicate interactions with Zustand stores (e.g., "dispatch `actionName` from `chatStore`") or Apollo Client (e.g., "use `useQuery` with `GET_PATIENT_DATA` query").
        *   **API/`code-server` Interaction:** Specify any FastAPI backend endpoints to call, data shapes for requests/responses, or `code-server` message types to send/handle (e.g., `INSERT_CODE_SNIPPET_COMMAND`).
        *   **Key Imports:** Mention any critical modules or components that will need to be imported.
        *   **Acceptance Criteria/Expected Behavior:** Briefly describe how to know the task is done correctly.
    *   **No Actual Code:** The plan should contain instructions *about* code, not the code itself. Illustrative snippets are acceptable ONLY if they clarify an instruction.

4.  **Critical Review, Integration, and Testing Checkpoints:**
    *   After each significant feature implementation or at the end of each phase, explicitly insert "Critical Review & Integration Tasks." These tasks are for the *planning LLM to define* and the *coding LLM to be aware of or for human oversight*.
    *   These review tasks should prompt verification of:
        *   Component composition and correct data flow between them.
        *   Successful API communication with expected request/response handling.
        *   Proper `code-server` message exchanges and editor interactions.
        *   UI/UX alignment with MUI, Tailwind, and healthcare design system principles (e.g., CMS/HealthCare.gov Design System), particularly within the narrow sidebar.
        *   WCAG 2.2 AA accessibility standards.
        *   End-to-end functionality of the feature.
        *   Absence of regressions in previously implemented features.
        *   Adherence to security (HIPAA client-side considerations) and compliance guidelines.
        *   Creation of necessary Storybook stories and unit/integration tests (as per planning docs).

5.  **Logical Flow and Dependencies:**
    *   Order tasks logically, considering dependencies. If Task B depends on Task A, Task A should appear first.

**Example Task Snippet (Illustrative of Detail Level):**

```markdown
### Phase 1: Core AI Chat & `code-server` Basics

**1.1. Setup Chat State Management (Zustand)**

*   **Task 1.1.1:** Create `chatStore.ts` for AI Chat.
    *   **Target File:** `libs/core-state/src/lib/chatStore.ts`
    *   **Definition:** Define a Zustand store named `chatStore`.
    *   **State Shape:** Include `messages: ChatMessage[]` (define `ChatMessage` interface: `id: string, sender: 'user' | 'ai', content: string, timestamp: Date, isLoading?: boolean, isError?: boolean`), `currentInput: string`, `isStreaming: boolean`.
    *   **Actions:** Implement actions: `addMessage(message: ChatMessage)`, `updateLastAiMessageContent(chunk: string)`, `setInput(input: string)`, `clearInput()`, `setStreaming(status: boolean)`.
    *   **Core Logic:** Standard Zustand store setup with initial state and action implementations.
    *   **Expected Behavior:** Store is created, and actions correctly modify the state. Unit testable.

**1.2. Implement AI Chat View Component**

*   **Task 1.2.1:** Create `AIChatView.tsx` main chat interface component.
    *   **Target File:** `libs/feature-chat/src/components/AIChatView.tsx`
    *   **Component Definition:** `AIChatView: React.FC<AIChatViewProps>` (Define `AIChatViewProps` if any).
    *   **UI Elements:**
        *   Use MUI `<Paper>` for the main chat container.
        *   MUI `<Box>` or `<List>` for displaying messages (`ChatMessageDisplay` sub-component - to be defined next).
        *   MUI `<TextField>` for user input, multiline.
        *   MUI `<IconButton>` with `<SendIcon>` for submitting input.
        *   MUI `<CircularProgress>` for loading indicators.
    *   **State Interaction:**
        *   Subscribe to `chatStore` to get `messages`, `currentInput`, `isStreaming`.
        *   Call `chatStore.setInput()` on TextField change.
        *   Call `chatStore.addMessage()` and trigger API call (via `useAIChatAPI` hook - to be defined later) on send.
    *   **Styling:** Use Tailwind CSS for flexible layout, ensuring it's responsive and fits well in a narrow sidebar. Messages area should be scrollable.
    *   **Core Logic:** Render chat messages. Handle user input and submission. Display streaming responses.
    *   **Expected Behavior:** Component renders, user can type and submit messages, messages appear in the view.