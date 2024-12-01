# Atlas IDE React Frontend - Detailed To-Do List for LLM Implementation

## 1. Introduction

**Purpose:** This document outlines a highly detailed, granular, and machine-executable to-do list. It is specifically designed to guide a **coding LLM** through the systematic implementation of the React-based frontend for the Atlas IDE.

**Guiding Principles:**
*   **Document-Driven:** All tasks are derived from and must strictly adhere to the 9 core planning documents provided:
    1.  `atlas_ide_react_step_foundation_framework.md`
    2.  `atlas_ide_react_step1_plan.md`
    3.  `atlas_ide_react_step2_plan.md`
    4.  `atlas_ide_react_step3_plan.md`
    5.  `atlas_ide_react_step4_plan.md`
    6.  `atlas_ide_react_step5_plan.md`
    7.  `atlas_ide_react_step6_plan.md`
    8.  `atlas_ide_react_step7_plan.md`
    9.  `atlas_ide_react_step8_plan.md`
*   **Extreme Granularity:** Each task is broken down to the smallest feasible unit, specifying target files, component/function/hook definitions (names, basic signatures, props), core logic summaries, UI elements (MUI), styling notes (Tailwind CSS, sidebar constraints), state management interactions (Zustand, Apollo Client), API/`code-server` calls, key imports, and precise acceptance criteria.
*   **LLM Executability:** The plan prioritizes clarity and explicitness to enable direct execution by a coding LLM. No actual code will be written *in this plan*; it provides instructions *about* the code.
*   **Phased Approach:** Development will proceed through defined phases, from foundational setup to advanced feature implementation, each concluding with critical review checkpoints.

**Project Context:**
*   **Atlas IDE:** An AI-enabled, VS Code-like development environment embedded as a SMART-on-FHIR application within an Epic EMR sidebar.
*   **Goal:** Provide clinicians with Cursor-like AI coding assistance (context-aware chat, ghost-text, AI-driven modifications, FHIR-specific commands) while interacting with real-time FHIR data.
*   **Architecture:** Runs within a `code-server` instance, wrapped by a Next.js React shell. Backend is a FastAPI proxy.

**Core Technologies:**
*   **Monorepo:** Nx
*   **Core Application Framework:** Next.js
*   **UI Component Library:** MUI (Material-UI)
*   **Styling:** Tailwind CSS
*   **UI State Management:** Zustand
*   **Server State & Data Fetching:** TanStack Query (React Query)
*   **Language:** TypeScript

## 2. Nx Monorepo Structure

The project will be organized within an Nx monorepo to manage complexity, promote code sharing, and enforce architectural boundaries.

**Benefits of Nx:**
*   Improved maintainability and scalability.
*   Efficient code sharing between applications and libraries.
*   Integrated tooling for building, testing, and linting.
*   Clear separation of concerns.

**Proposed Directory Structure:**

```text
/Users/gabe/ATLAS Palantir/ (workspace root, implies Nx workspace named 'atlas-palantir')
├── apps/
│   └── atlas-ide-shell/            # The main Next.js application
│       ├── app/                    # Next.js 13+ app directory (or pages/)
│       ├── components/             # Shell-specific components (e.g., layout)
│       ├── public/
│       ├── styles/
│       ├── next.config.js
│       ├── tsconfig.json
│       └── ...
├── libs/
│   ├── core/
│   │   ├── hooks/                  # e.g., useCodeServerComm.ts, useAIChatAPI.ts, useGhostText.ts
│   │   ├── state/                  # e.g., uiStore.ts, chatStore.ts, taskContextStore.ts
│   │   ├── data-access/            # e.g., queryClient.ts (TanStack Query), data fetching hooks
│   │   ├── types/                  # Core TS types (e.g., code-server.types.ts)
│   │   └── utils/                  # General utility functions
│   ├── fhir/
│   │   ├── utils/                  # FHIR-specific utilities, data mappers
│   │   ├── components/             # Reusable FHIR UI components
│   │   └── types/                  # FHIR-specific TS types
│   ├── ui/
│   │   ├── core-components/        # Generic, reusable UI components (Button, Modal)
│   │   ├── layout-components/      # Layout structure components (SidebarLayout)
│   │   └── feature-components/     # Feature-specific larger components
│   │       ├── chat/               # e.g., AIChatView.tsx
│   │       ├── editor-enhancements/# e.g., GhostTextView.tsx, CodeContextDisplay.tsx
│   │       ├── command-palette/    # e.g., CommandPaletteModal.tsx
│   │       ├── fhir-integration/   # e.g., PatientContextDisplay.tsx
│   │       └── ai-tools/           # e.g., CodeGenerationPreview.tsx
│   ├── services/
│   │   └── code-server-comm/       # Abstractions for code-server communication
│   ├── assets/                     # Global static assets
│   └── integration-tests/          # E2E or integration tests
├── tools/                          # Workspace scripts, generators
├── nx.json
├── package.json
└── tsconfig.base.json

Key Library Breakdown (Initial & Evolving):

apps/atlas-ide-shell: The Next.js application.
libs/core/hooks: Reusable React hooks.
libs/core/state: Zustand stores.
libs/core/data-access: TanStack Query setup, query client, and data fetching logic.
libs/core/types: Shared TypeScript interfaces/types.
libs/core/utils: General utility functions.
libs/fhir/utils: FHIR data processing and helpers.
libs/fhir/components: UI components for FHIR data.
libs/shared/ui-core: Shared, low-level UI components or MUI customizations (e.g. Button, Modal wrappers).
libs/ui/layout-components: Major layout structuring components.
libs/ui/feature-components: Organizes components by feature (chat, editor, command palette, etc.) for modularity.
3. Phase 0: Foundation Setup
This phase establishes the foundational structure and core configurations for the Atlas IDE frontend. It involves setting up the Nx monorepo, initializing the Next.js shell application, integrating key libraries (MUI, Tailwind CSS), and preparing basic state management and code-server communication placeholders.

Source Document: atlas_ide_react_step_foundation_framework.md

3.1. Nx Monorepo Initialization & Next.js App Setup

Task 3.1.1: Initialize Nx Workspace.
Target Files: Workspace root (`/Users/gabe/ATLAS Palantir/`) including `nx.json`, `package.json`, `tsconfig.base.json`, etc.
Definition: Use Nx CLI to create a new integrated monorepo named `atlas-palantir`.
Command: `npx create-nx-workspace@latest atlas-palantir --preset=next --appName=atlas-ide-shell --style=tailwind --nxCloud=false`
Core Logic: Nx workspace scaffolding. The workspace name `atlas-palantir` aligns with the root directory. Generated import paths will use `@atlas-palantir/...`.
Acceptance Criteria: Nx workspace `atlas-palantir` is created successfully with a Next.js application `atlas-ide-shell` configured with Tailwind CSS.
Task 3.1.2: Define Environment Configuration Strategy.
Target Files: Documentation (e.g., `README.md` or a dedicated `docs/environment.md` within the workspace).
Definition: Outline the strategy for managing environment variables (e.g., for FastAPI backend URL, `code-server` URL, API keys).
Core Logic: Specify the use of `.env` files (`.env.local`, `.env.development`, `.env.production`) and Next.js runtime configuration for accessing these variables securely.
Acceptance Criteria: A clear strategy for environment variable management is documented.

Task 3.1.3: Verify Next.js Application (atlas-ide-shell) Setup.
Target Files: apps/atlas-ide-shell/ directory structure, apps/atlas-ide-shell/pages/index.tsx (or app/page.tsx), apps/atlas-ide-shell/next.config.js, apps/atlas-ide-shell/tailwind.config.js.
Definition: Ensure the atlas-ide-shell Next.js application is correctly scaffolded by Nx.
Core Logic: Review generated files for basic Next.js and Tailwind CSS configuration.
UI Elements: Default Next.js welcome page should render.
Styling: Basic Tailwind CSS classes should be applicable.
Acceptance Criteria: The atlas-ide-shell app can be served (nx serve atlas-ide-shell) and displays the default page. Tailwind CSS is functional.
3.2. Core Library Generation

Task 3.2.1: Generate core-hooks library.
Target Files: `libs/core/hooks/` directory, `libs/core/hooks/src/index.ts`.
Definition: Use Nx CLI to generate a new React library for reusable hooks.
Command: `nx g @nx/react:library core-hooks --directory=libs/core --style=none --buildable --publishable --importPath=@atlas-palantir/core-hooks`.
Core Logic: Nx React library scaffolding.
Acceptance Criteria: `core-hooks` library is created. Path mapping in `tsconfig.base.json` is updated for `@atlas-palantir/core-hooks`.
Task 3.2.2: Generate core-state library.
Target Files: `libs/core/state/` directory, `libs/core/state/src/index.ts`.
Definition: Use Nx CLI to generate a new JS library for Zustand stores.
Command: `nx g @nx/js:library core-state --directory=libs/core --buildable --publishable --importPath=@atlas-palantir/core-state`.
Core Logic: Nx library scaffolding.
Acceptance Criteria: `core-state` library is created. Path mapping in `tsconfig.base.json` is updated for `@atlas-palantir/core-state`.
Task 3.2.3: Generate core-data-access library (for TanStack Query).
Target Files: `libs/core/data-access/` directory, `libs/core/data-access/src/index.ts`.
Definition: Use Nx CLI to generate a new JS library for TanStack Query setup and data fetching logic.
Command: `nx g @nx/js:library data-access --directory=libs/core --buildable --publishable --importPath=@atlas-palantir/core-data-access`.
Core Logic: Nx library scaffolding.
Acceptance Criteria: `core-data-access` library is created. Path mapping in `tsconfig.base.json` is updated for `@atlas-palantir/core-data-access`.
Task 3.2.4: Generate core-types library.
Target Files: libs/core/types/ directory, libs/core/types/src/index.ts.
Definition: Use Nx CLI to generate a new buildable library.
Command: nx g @nx/js:lib types --directory=libs/core --buildable --publishable --importPath=@atlas-palantir/core-types.
Core Logic: Nx library scaffolding.
Acceptance Criteria: core-types library is created. Path mapping in tsconfig.base.json is updated.
Task 3.2.5: Generate core-utils library.
Target Files: libs/core/utils/ directory, libs/core/utils/src/index.ts.
Definition: Use Nx CLI to generate a new buildable library.
Command: nx g @nx/js:lib utils --directory=libs/core --buildable --publishable --importPath=@atlas-palantir/core-utils.
Core Logic: Nx library scaffolding.
Acceptance Criteria: core-utils library is created. Path mapping in tsconfig.base.json is updated.
Task 3.2.6: Generate fhir-utils library.
Target Files: `libs/fhir/utils/` directory, `libs/fhir/utils/src/index.ts`.
Definition: Use Nx CLI to generate a new JS library for FHIR-specific utilities and types.
Command: `nx g @nx/js:library fhir-utils --directory=libs/fhir --buildable --publishable --importPath=@atlas-palantir/fhir-utils`.
Core Logic: Nx library scaffolding.
Acceptance Criteria: `fhir-utils` library is created. Path mapping in `tsconfig.base.json` is updated for `@atlas-palantir/fhir-utils`.
Task 3.2.7: Generate shared-ui-core library.
Target Files: `libs/shared/ui-core/` directory, `libs/shared/ui-core/src/index.ts`.
Definition: Use Nx CLI to generate a new React library for shared, low-level UI components or MUI customizations.
Command: `nx g @nx/react:library ui-core --directory=libs/shared --style=tailwind --buildable --publishable --importPath=@atlas-palantir/shared-ui-core`.
Core Logic: Nx React library scaffolding. Tailwind is configured for this lib.
Acceptance Criteria: `shared/ui-core` library is created. Path mapping in `tsconfig.base.json` is updated for `@atlas-palantir/shared-ui-core`.
3.3. Next.js Shell Configuration (atlas-ide-shell)

Task 3.3.1: Install MUI Core & Icons.
Target File: package.json (root).
Definition: Add MUI dependencies.
Command: npm install @mui/material @emotion/react @emotion/styled @mui/icons-material (or yarn/pnpm equivalent).
Core Logic: Package installation.
Acceptance Criteria: Dependencies are added to package.json and installed in node_modules.
Task 3.3.2: Configure MUI ThemeProvider and Basic Theme.
Target File: apps/atlas-ide-shell/src/theme/theme.ts (new file) and apps/atlas-ide-shell/pages/_app.tsx (or app/layout.tsx / app/providers.tsx for App Router).
Definition: Create a basic MUI theme incorporating Roboto font and wrap the application with ThemeProvider.
apps/atlas-ide-shell/src/theme/theme.ts Content:
```typescript
import { createTheme } from '@mui/material/styles';
import { red } from '@mui/material/colors';

// Create a theme instance.
const theme = createTheme({
  palette: {
    primary: {
      main: '#556cd6', // Example primary color from foundation doc
    },
    secondary: {
      main: '#19857b', // Example secondary color from foundation doc
    },
    error: {
      main: red.A400,
    },
    background: {
      default: '#fff',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
  // Consider adding overrides for Epic sidebar constraints later (compact variants)
});

export default theme;
```
Update _app.tsx / providers.tsx:
```tsx
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import theme from '../src/theme/theme'; // Adjusted path
// import Layout from '../src/components/Layout/Layout'; // Will be part of Layout setup

function MyApp({ Component, pageProps }) { // or Providers({ children })
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline /> {/* MUI's CSS reset */}
      {/* <Layout> will wrap Component in a later task */}
      <Component {...pageProps} /> {/* or {children} */}
    </ThemeProvider>
  );
}
export default MyApp;
```
Core Logic: Initialize MUI's ThemeProvider at the application root. Apply CssBaseline for consistent styling. Use Roboto font.
Styling: Uses the defined `theme`.
Acceptance Criteria: `theme.ts` is created. Application is wrapped with MUI ThemeProvider. Basic theme settings (colors, Roboto font) are applied. CssBaseline is active.
Task 3.3.3: Ensure Tailwind CSS Integration with MUI.
Target File: apps/atlas-ide-shell/tailwind.config.js.
Definition: Configure Tailwind to work alongside MUI, potentially using important strategy or prefixing if conflicts arise (though generally, they coexist well). Ensure Tailwind's preflight (if used) doesn't overly clash with MUI's CssBaseline.
Core Logic: Tailwind configuration review/adjustment.
Ensure content array in tailwind.config.js includes paths to all component files: ../../libs/**/*.{ts,tsx}, ./**/*.{ts,tsx}.
Acceptance Criteria: Tailwind utility classes and MUI components can be used together in the same component without major styling conflicts.
Task 3.3.4: Create Basic Layout Component.
Target File: apps/atlas-ide-shell/components/Layout.tsx.
Component Definition: Layout: React.FC<{ children: React.ReactNode }>
UI Elements: Use MUI <Box> for basic structure.
Example: <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>{children}</Box>
Core Logic: A simple wrapper component for consistent page layout.
Styling: Basic flex styling to ensure content fills the viewport.
Acceptance Criteria: Layout component is created and can wrap page content in _app.tsx or individual pages.
Task 3.3.5: Update _app.tsx (or page layouts) to use Layout component.
Target File: apps/atlas-ide-shell/pages/_app.tsx (or individual page files).
Definition: Wrap the <Component {...pageProps} /> (or page content) with the newly created Layout component.
Core Logic: Integrate the Layout component into the application's root or page structure.
Acceptance Criteria: Application pages render within the defined Layout.
3.4. State Management Initialization

Task 3.4.1: Install Zustand and TanStack Query.
Target File: `package.json` (root).
Definition: Add Zustand and TanStack Query dependencies.
Command: `npm install zustand @tanstack/react-query` (or yarn/pnpm equivalent).
Core Logic: Package installation.
Acceptance Criteria: Dependencies are added to `package.json` and installed in `node_modules`.
Target File: package.json (root).
Definition: Add Zustand dependency.
Command: npm install zustand.
Core Logic: Package installation.
Acceptance Criteria: Zustand is added to package.json and installed.
Task 3.4.2: Create Initial uiStore.ts in core-state library.
Target File: `libs/core/state/src/lib/uiStore.ts` (Ensure this file is created if it doesn't exist, within the `core-state` lib).
Definition: Define a basic Zustand store for general UI state.
State Shape (Example): interface UIState { sidebarOpen: boolean; }
Actions (Example): toggleSidebar: () => void;
Store Setup:
typescript
```typescript
import { create } from 'zustand';

interface UIState {
  sidebarOpen: boolean;
  toggleSidebar: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}));
```
Core Logic: Basic Zustand store setup.
Key Imports: create from zustand.
Acceptance Criteria: `uiStore.ts` created with basic state and actions. Exported correctly from `@atlas-palantir/core-state` library index.

Task 3.4.3: Initialize TanStack Query Client.
Target File: `libs/core/data-access/src/lib/queryClient.ts` (new file within the `core-data-access` lib).
Definition: Create and configure an instance of `QueryClient`.
```typescript
// libs/core/data-access/src/lib/queryClient.ts
import { QueryClient } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Default query options, e.g., staleTime, cacheTime
      // refetchOnWindowFocus: false, // Example customization
    },
  },
});

export default queryClient;
```
Core Logic: Standard TanStack Query client setup.
Acceptance Criteria: `queryClient.ts` is created and exports a `QueryClient` instance. Exported from `@atlas-palantir/core-data-access` library index.

Task 3.4.4: Setup TanStack Query Provider.
Target File: `apps/atlas-ide-shell/pages/_app.tsx` (or `app/layout.tsx` / `app/providers.tsx`).
Definition: Wrap the application with `QueryClientProvider`.
```tsx
// In _app.tsx / providers.tsx
// ... other imports
import { QueryClientProvider } from '@tanstack/react-query';
import queryClient from '@atlas-palantir/core-data-access'; // Adjust if export is not default or path differs
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools'; // Optional: for development

function MyApp({ Component, pageProps }) { // or Providers({ children })
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <Layout>
          <Component {...pageProps} />
        </Layout>
        {/* <ReactQueryDevtools initialIsOpen={false} /> */}
      </QueryClientProvider>
    </ThemeProvider>
  );
}
// export default MyApp;
```
Core Logic: Provide the TanStack Query client to the React component tree.
Acceptance Criteria: Application is wrapped with `QueryClientProvider`. TanStack Query is available for use in components.
Task 3.4.5: Install Apollo Client & GraphQL.
Target File: package.json (root).
Definition: Add Apollo Client and GraphQL dependencies.
Command: npm install @apollo/client graphql.
Core Logic: Package installation.
Acceptance Criteria: Dependencies are added and installed.
Task 3.4.6: Create Initial apolloClient.ts in core-graphql library.
Target File: libs/core/graphql/src/lib/apolloClient.ts.
Definition: Configure a basic Apollo Client instance.
Client Setup (Basic):
```typescript
import { ApolloClient, InMemoryCache, HttpLink } from '@apollo/client';

const httpLink = new HttpLink({
  uri: '/api/graphql', // Placeholder, will point to FastAPI proxy
});

export const apolloClient = new ApolloClient({
  link: httpLink,
  cache: new InMemoryCache(),
});
```
Core Logic: Initialize Apollo Client with an HttpLink (pointing to a yet-to-be-created API route) and InMemoryCache.
Key Imports: ApolloClient, InMemoryCache, HttpLink from @apollo/client.
Acceptance Criteria: apolloClient.ts is created. It can be imported. Don't forget to export from libs/core/graphql/src/index.ts.
Task 3.4.7: Setup ApolloProvider in _app.tsx.
Target File: apps/atlas-ide-shell/pages/_app.tsx (or app/providers.tsx).
Definition: Wrap the application with ApolloProvider.
_app.tsx / providers.tsx Update:
```tsx
// ... other imports
import { ApolloProvider } from '@apollo/client';
import { apolloClient } from '@atlas-palantir/core-graphql'; // Adjust import path

function MyApp({ Component, pageProps }) { // or Providers({ children })
  return (
    <ApolloProvider client={apolloClient}>
      <ThemeProvider theme={defaultTheme}> {/* Existing ThemeProvider */}
        <CssBaseline />
        <Component {...pageProps} /> {/* or {children} */}
      </ThemeProvider>
    </ApolloProvider>
  );
}
// ...
```
Core Logic: Provide Apollo Client instance to the React component tree.
Acceptance Criteria: Application has Apollo Client context. useQuery, useMutation can be used later.
3.5. code-server Integration Placeholders

Task 3.5.1: Create CodeServerView.tsx Placeholder Component.
Target File: libs/ui/feature-components/src/lib/editor/CodeServerView.tsx (To be created in a feature library, e.g., `ui-feature-editor` or similar, if not already defined. For now, assuming `ui/feature-components` has an `editor` sub-directory or we create a more specific lib later. For Phase 0, this path is fine as a placeholder). (create subdirectories if they don't exist, adjust path based on final structure in step 2). Ensure it's exported from libs/ui/feature-components/src/index.ts.
Component Definition: CodeServerView: React.FC
UI Elements: A simple MUI <Box> or <Paper> with a placeholder text like "code-server iframe will be here."
Core Logic: Render a styled container for the future iframe.
tsx
```tsx
import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

export const CodeServerView: React.FC = () => {
  return (
    <Box
      sx={{
        flexGrow: 1,
        border: '1px dashed grey',
        p: 2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '400px', // Example height
      }}
    >
      <Typography variant="h6">code-server iframe will be embedded here</Typography>
    </Box>
  );
};
```
Styling: Basic styling to make the placeholder visible and occupy space.
Acceptance Criteria: Component created and renders the placeholder.
Task 3.5.2: Create useCodeServerComm.ts Hook Placeholder in core-hooks.
Target File: libs/core/hooks/src/lib/useCodeServerComm.ts.
Definition: Create a basic hook structure for future code-server communication logic.
Hook Structure (Basic):
```typescript
// import { useState, useEffect, useCallback } from 'react';

// interface CodeServerMessage { type: string; payload?: any; }

export const useCodeServerComm = (iframeRef?: React.RefObject<HTMLIFrameElement>) => {
  // const [lastMessage, setLastMessage] = useState<CodeServerMessage | null>(null);

  // const postMessageToCodeServer = useCallback((message: CodeServerMessage) => {
  //   if (iframeRef?.current?.contentWindow) {
  //     iframeRef.current.contentWindow.postMessage(message, '*'); // Consider targetOrigin
  //   }
  // }, [iframeRef]);

  // useEffect(() => {
  //   const handleMessage = (event: MessageEvent) => {
  //     // Add origin check for security: if (event.origin !== 'expected-code-server-origin') return;
  //     // if (event.data && typeof event.data.type === 'string') {
  //     //   setLastMessage(event.data);
  //     // }
  //   };
  //   window.addEventListener('message', handleMessage);
  //   return () => window.removeEventListener('message', handleMessage);
  // }, []);

  // return { lastMessage, postMessageToCodeServer };
  return { postMessageToCodeServer: (message: any) => console.log('Mock postMessage', message) }; // Placeholder
};
```
Core Logic: Placeholder functions and state. Actual implementation will follow in later phases.
Key Imports: (Commented out for now) useState, useEffect, useCallback.
Acceptance Criteria: Hook file is created with a basic structure. It can be imported and "used" without error. Don't forget to export from libs/core/hooks/src/index.ts.
3.6. Linting & TypeScript Configuration

Task 3.6.1: Review and Customize Nx Default ESLint & Prettier Configs.
Target Files: .eslintrc.json (root and app/libs), .prettierrc (root).
Definition: Examine default linting and formatting rules. Make minor adjustments if specific project preferences dictate (e.g., stricter rules, specific formatting options).
Core Logic: Configuration file review.
Acceptance Criteria: Linting (nx lint <project>) and formatting commands work. Team is aware of the active linting rules.
Task 3.6.2: Review and Customize tsconfig.base.json and Project-Specific tsconfig.json files.
Target Files: tsconfig.base.json, apps/atlas-ide-shell/tsconfig.json, libs/**/tsconfig.lib.json.
Definition: Check compiler options, path mappings, and include/exclude patterns. Ensure strict mode is enabled.
Core Logic: TypeScript configuration review.
Acceptance Criteria: TypeScript compiles without errors (nx build <project>). Path aliases work correctly.
3.7. Critical Review & Integration Tasks (End of Phase 0)

Task 3.7.1: Verify Monorepo Structure and Library Imports.
Action: Confirm all generated libraries (core-hooks, core-state, etc.) can be correctly imported into the atlas-ide-shell application and among themselves using Nx path aliases (e.g., @atlas-palantir/core-hooks).
Acceptance Criteria: A simple test component in atlas-ide-shell successfully imports and uses a placeholder export from each core library.
Task 3.7.2: Test Basic Application Rendering with MUI and Tailwind.
Action: Run nx serve atlas-ide-shell. Ensure the application loads, displays the basic layout, and that a simple MUI component (e.g., <Button>) and a Tailwind utility class (e.g., p-4) render correctly on the main page.
Acceptance Criteria: Application starts, MUI components render with theme styling, Tailwind styles are applied. No console errors related to setup.
Task 3.7.3: Confirm State Management Placeholders.
Action: Briefly test that useUIStore can be called in a component and its initial state accessed. Confirm ApolloProvider is wrapping the app without runtime errors.
Acceptance Criteria: No runtime errors when initializing or accessing placeholder stores/providers.
Task 3.7.4: Review Linting and Build Processes.
Action: Run nx lint atlas-ide-shell and nx build atlas-ide-shell.
Acceptance Criteria: Linting passes without critical errors. Build completes successfully.
Task 3.7.5: Initial Commit to Version Control.
Action: Initialize a Git repository (if not already done) and commit the foundational setup.
Acceptance Criteria: Project baseline is committed to Git.

## 4. Phase 1: Core AI Chat & `code-server` Basics

This phase focuses on implementing the fundamental AI chat functionality and establishing basic communication with the `code-server` instance.

**Source Document:** `atlas_ide_react_step1_plan.md`

### 4.1. Chat State Management (Zustand)

**Task 4.1.1:** Define `ChatMessage` and related types.
*   **Target File:** `libs/core/types/src/lib/chat.types.ts` (Create this new file)
*   **Definition:** Create and export TypeScript interfaces for chat messages.
    ```typescript
    // libs/core/types/src/lib/chat.types.ts
    export type MessageSender = 'user' | 'ai' | 'system';

    export interface ChatMessage {
      id: string; // Unique message ID (e.g., uuid)
      sender: MessageSender;
      content: string;
      timestamp: string; // ISO string format
      isLoading?: boolean;
      isError?: boolean;
      errorMessage?: string;
      metadata?: Record<string, any>; // For future use (e.g., sources, suggestions)
    }

    export interface ChatMessageRequest {
      content: string;
      // Potentially add conversation history or other context here later
    }
    ```
*   **Core Logic:** Type definitions for chat interactions.
*   **Key Imports:** None.
*   **Acceptance Criteria:** `chat.types.ts` file is created with the specified interfaces. Export these types from `libs/core/types/src/index.ts`.

**Task 4.1.2:** Create `chatStore.ts` for AI Chat.
*   **Target File:** `libs/core/state/src/lib/chatStore.ts`
*   **Definition:** Define a Zustand store named `chatStore` using the `ChatMessage` type.
*   **State Shape (Initial):**
    *   `messages: ChatMessage[]`
    *   `currentInput: string`
    *   `isSending: boolean` (replaces `isStreaming` for a more general "waiting for AI response" state)
    *   `error: string | null` (for general chat errors)
*   **Actions (Initial):**
    *   `addMessage(message: Omit<ChatMessage, 'id' | 'timestamp'>)`: Adds a new message, generating ID and timestamp.
    *   `updateMessage(id: string, updates: Partial<ChatMessage>)`: Updates an existing message (e.g., to set `isLoading` or `content` for streaming).
    *   `setInput(input: string)`
    *   `clearInput()`
    *   `setSending(status: boolean)`
    *   `setError(error: string | null)`
    *   `clearMessages()`
*   **Core Logic:** Standard Zustand store setup. Use a UUID library (e.g., `uuid`) for generating message IDs.
*   **Key Imports:** `create` from `zustand`, `ChatMessage` from `@atlas-palantir/core-types`. `v4 as uuidv4` from `uuid`.
*   **Acceptance Criteria:** `chatStore.ts` is created. Actions correctly modify the state. Install `uuid` and `@types/uuid` (`npm install uuid @types/uuid`). Export the store and its hook (`useChatStore`) from `libs/core/state/src/index.ts`.

### 4.2. AI Chat UI Components

**Task 4.2.1:** Create `ChatMessageDisplay.tsx` component.
*   **Target File:** `libs/ui/feature-components/src/lib/chat/ChatMessageDisplay.tsx` (Create directory and file)
*   **Component Definition:** `ChatMessageDisplay: React.FC<{ message: ChatMessage }>`
*   **UI Elements:**
    *   MUI `<Paper>` or `<Box>` to wrap the message, styled differently based on `message.sender`.
    *   MUI `<Typography variant="body1">` for `message.content`.
    *   MUI `<Typography variant="caption">` for `message.timestamp` (formatted) and sender.
    *   MUI `<CircularProgress size={16}>` if `message.isLoading`.
    *   MUI `<ErrorOutlineIcon>` and `<Typography color="error">` if `message.isError` and `message.errorMessage`.
*   **Styling:** Use Tailwind CSS for layout (e.g., flex for alignment, different background colors for user/AI messages). Ensure text is selectable. Markdown rendering for AI messages can be added later.
*   **Core Logic:** Render a single chat message with appropriate styling and indicators. Format timestamp (e.g., using `date-fns`).
*   **Key Imports:** `React`, `ChatMessage` from `@atlas-palantir/core-types`, MUI components (`Paper`, `Box`, `Typography`, `CircularProgress`), `ErrorOutlineIcon` from `@mui/icons-material`.
*   **Acceptance Criteria:** Component renders a message correctly based on its properties. Export from `libs/ui/feature-components/src/index.ts` and `libs/ui/feature-components/src/lib/chat/index.ts` (create if needed).

**Task 4.2.2:** Create `ChatInput.tsx` component.
*   **Target File:** `libs/ui/feature-components/src/lib/chat/ChatInput.tsx`
*   **Component Definition:** `ChatInput: React.FC<{ onSendMessage: (input: string) => void; disabled?: boolean }>`
*   **UI Elements:**
    *   MUI `<TextField multiline maxRows={4}>` for text input.
    *   MUI `<IconButton type="submit">` with `<SendIcon>` to send the message.
    *   Wrap in a `<form>` element to handle submission.
*   **State Interaction:**
    *   Internal state for the text field's value.
    *   Calls `onSendMessage` prop when the form is submitted. Clears input after sending.
*   **Styling:** Use Tailwind CSS for layout. TextField should expand with input.
*   **Core Logic:** Manage input field state, handle message submission, disable input/button when `disabled` prop is true.
*   **Key Imports:** `React`, `useState`, MUI components (`TextField`, `IconButton`), `SendIcon` from `@mui/icons-material`.
*   **Acceptance Criteria:** Component renders input field and send button. User can type and submit. `onSendMessage` is called with input. Input clears on send. Export from feature-components index.

**Task 4.2.3:** Create `AIChatView.tsx` main chat interface.
*   **Target File:** `libs/ui/feature-components/src/lib/chat/AIChatView.tsx`
*   **Component Definition:** `AIChatView: React.FC`
*   **UI Elements:**
    *   MUI `<Box>` as the main container, styled with Tailwind (`flex flex-col h-full`).
    *   MUI `<Box className="flex-grow overflow-y-auto p-4 space-y-2">` for displaying messages. Use `ChatMessageDisplay` for each message.
    *   `ChatInput` component at the bottom.
    *   Scroll to bottom when new messages are added.
*   **State Interaction:**
    *   Subscribes to `useChatStore` to get `messages`, `currentInput`, `isSending`, `error`.
    *   Uses `chatStore.setInput` (though `ChatInput` might handle its own input state and just call a submission action).
    *   Defines `handleSendMessage` function that calls `chatStore.addMessage({ sender: 'user', content: input })` and then triggers API call (via `useAIChatAPI` hook - to be defined).
*   **Styling:** Ensure it fills available vertical space within the sidebar. Message area should be scrollable.
*   **Core Logic:** Renders chat messages from the store. Handles sending new messages. Manages scroll behavior.
*   **Key Imports:** `React`, `useEffect`, `useRef`, `useChatStore` from `@atlas-palantir/core-state`, `ChatMessageDisplay`, `ChatInput`, MUI components.
*   **Acceptance Criteria:** Component renders. Messages from store are displayed. User can send messages. New messages appear and scroll into view. Export from feature-components index.

### 4.3. API Communication for Chat

**Task 4.3.1:** Create `useAIChatAPI.ts` hook (placeholder).
*   **Target File:** `libs/core/hooks/src/lib/useAIChatAPI.ts`
*   **Definition:** `export const useAIChatAPI = () => { ... }`
*   **Functions (Placeholder):**
    *   `sendMessageToBackend(message: ChatMessageRequest): Promise<ChatMessage>`: Placeholder async function. Simulates API call.
        *   Internally, this function will eventually use Apollo Client to send a mutation to the FastAPI backend.
*   **Core Logic:** Contains a placeholder function that simulates sending a message to an AI backend and receiving a response. For now, it can return a canned AI response after a short delay.
*   **Key Imports:** `useCallback`, `ChatMessage`, `ChatMessageRequest` from `@atlas-palantir/core-types`, `useChatStore`.
*   **Acceptance Criteria:** Hook is created with placeholder logic. It can be called from `AIChatView`. Update `AIChatView` to call `sendMessageToBackend`, then `chatStore.addMessage` for the AI response, and handle `isSending` state. Export from `libs/core/hooks/src/index.ts`.

### 4.4. Basic `code-server` Message Handling

**Task 4.4.1:** Define initial `CodeServerMessage` types.
*   **Target File:** `libs/core/types/src/lib/code-server.types.ts` (Create this file)
*   **Definition:** Define basic TypeScript types/interfaces for messages exchanged with `code-server`.
    ```typescript
    // libs/core/types/src/lib/code-server.types.ts
    export enum CodeServerMessageType {
      // Shell to CodeServer
      INIT_PLUGIN_COMM = 'INIT_PLUGIN_COMM',
      GET_EDITOR_CONTEXT = 'GET_EDITOR_CONTEXT', // Request current file, language, selection
      // CodeServer to Shell
      PLUGIN_READY = 'PLUGIN_READY',
      EDITOR_CONTEXT_RESPONSE = 'EDITOR_CONTEXT_RESPONSE',
      // Add more as features develop
    }

    export interface CodeServerMessageBase {
      type: CodeServerMessageType;
      payload?: any;
      messageId?: string; // Optional: for request-response matching
    }

    // Example specific message types
    export interface EditorContextResponseMessage extends CodeServerMessageBase {
      type: CodeServerMessageType.EDITOR_CONTEXT_RESPONSE;
      payload: {
        filePath?: string;
        languageId?: string;
        selectedText?: string;
        fileContent?: string; // Potentially large, use with caution
      };
    }
    ```
*   **Core Logic:** Type definitions for `code-server` communication.
*   **Acceptance Criteria:** File created with initial message types. Export types from `libs/core/types/src/index.ts`.

**Task 4.4.2:** Extend `useCodeServerComm.ts` with basic communication logic (Conceptual).
*   **Target File:** `libs/core/hooks/src/lib/useCodeServerComm.ts`
*   **Definition:** Flesh out the `postMessageToCodeServer` and message listening logic conceptually. Actual implementation may depend on `code-server` plugin capabilities not yet built.
*   **`postMessageToCodeServer(message: CodeServerMessageBase)`:**
    *   Should send the message to the `code-server` iframe's `contentWindow`.
*   **Message Listener (`useEffect`):**
    *   Should listen for `message` events from the `code-server` iframe.
    *   Filter messages by origin and validate structure.
    *   Store or handle received messages (e.g., update a Zustand store, or allow components to subscribe to specific message types). For now, just `console.log` received messages.
*   **Core Logic:** Basic iframe postMessage communication. This task is primarily about defining the hook's intended structure; full functionality is deferred.
*   **Key Imports:** `CodeServerMessageBase` from `@atlas-palantir/core-types`.
*   **Acceptance Criteria:** The hook's structure is updated to reflect these conceptual communication patterns. The placeholder `postMessageToCodeServer` can be called.

### 4.5. Integration into Shell

**Task 4.5.1:** Integrate `AIChatView` into `AtlasIdeShellLayout.tsx`.
*   **Target File:** `apps/atlas-ide-shell/components/layout/AtlasIdeShellLayout.tsx`
*   **Definition:** Add the `AIChatView` component to a designated area of the layout (e.g., a collapsible sidebar panel or a dedicated section).
*   **UI Elements:**
    *   May need an MUI `<Drawer>` or a resizable panel to host `AIChatView`. For simplicity, initially, it can be a fixed-width panel.
*   **Styling:** Ensure `AIChatView` is sized appropriately within the layout and doesn't break the overall page structure.
*   **Core Logic:** Import and render `AIChatView`.
*   **Acceptance Criteria:** `AIChatView` is visible and functional within the main application layout.

### 4.6. Critical Review & Integration Tasks (End of Phase 1)

**Task 4.6.1:** Verify Chat Functionality.
*   **Action:** Manually test sending messages from user to (mocked) AI and receiving responses. Check message display, input handling, and loading/error states (if simulated).
*   **Acceptance Criteria:** Basic chat flow works as expected. Messages are stored in Zustand store.

**Task 4.6.2:** Review `code-server` Communication Placeholders.
*   **Action:** Confirm `useCodeServerComm.ts` structure. Ensure `postMessageToCodeServer` can be called and (mocked) received messages are logged.
*   **Acceptance Criteria:** Placeholder communication hooks are in place and do not cause runtime errors.

**Task 4.6.3:** UI/UX Review for Chat.
*   **Action:** Assess the chat interface's usability within the sidebar constraints. Check readability, input ergonomics, and overall layout.
*   **Acceptance Criteria:** Chat UI is reasonably usable and visually coherent.

**Task 4.6.4:** Linting and Build.
*   **Action:** Run `nx lint <affected-project>` and `nx build atlas-ide-shell`.
*   **Acceptance Criteria:** Linting passes. Build completes successfully.

**Task 4.6.5:** Commit Phase 1.
*   **Action:** Commit all Phase 1 changes to Git.
*   **Acceptance Criteria:** Phase 1 work is committed.

## Phase 2: Basic Shell UI & Core Component Styling

This phase focuses on building out the basic UI structure of the `atlas-ide-shell` application, styling it, and starting the `ui-core` shared library with Storybook, based on `atlas_ide_react_step2_plan.md`.

### 2.A. Refine Layout Component (`apps/atlas-ide-shell`)

**Task 2.A.1:** Enhance `Layout.tsx` with Header, Sidebar, Footer structure.
*   **Target File:** `apps/atlas-ide-shell/src/components/Layout/Layout.tsx`
*   **Definition:** Modify `Layout.tsx` to import and structurally include `Header`, `Sidebar`, and `Footer` components.
*   **Core Logic:** Integrate `Header`, `Sidebar`, `Footer` (to be created in subsequent tasks). The main content area, designated for `CodeServerView`, must dynamically adjust its dimensions (e.g., width, margin) based on the `Sidebar`'s presence and open/closed state. Implement basic loading skeletons (e.g., MUI `Skeleton`) for Header, Sidebar, and main content areas to improve perceived performance during initial load or content fetching.
*   **UI Elements:** Use MUI `AppBar` as a container for `Header`, MUI `Drawer` for `Sidebar`, MUI `Box` for `Footer`, and MUI `Box` for the main content area.
*   **Styling:** Apply Tailwind CSS for overall dimensions, spacing, flexbox/grid layouts. Ensure the main content area for `CodeServerView` is clearly demarcated, provides adequate space, and is not cluttered. Rigorously test responsiveness, especially for the Epic sidebar constraint (max 600px width), ensuring a polished and functional look.
*   **Acceptance Criteria:** `Layout.tsx` renders with distinct structural areas for Header, Sidebar, and Footer. The main content area correctly adapts to Sidebar visibility changes. Basic skeletons are visible during a simulated loading state. The layout is responsive and maintains a polished appearance at narrow widths (<= 600px).

**Task 2.A.2:** Create `Header.tsx` placeholder component.
*   **Target File:** `apps/atlas-ide-shell/src/components/Layout/Header.tsx` (Create this file and its directory if needed)
*   **Definition:** `Header: React.FC`
*   **UI Elements:** An MUI `AppBar` containing an MUI `Toolbar`. Inside the `Toolbar`, use MUI `Typography` for the title (e.g., "Atlas IDE"). Include a placeholder for future action buttons or branding elements (e.g., an empty MUI `Box` with `marginLeft: 'auto'`).
*   **Styling:** Basic Tailwind CSS for height, background color (from theme), and text styling. Ensure it aligns with the overall application theme.
*   **Key Imports:** `React`, `AppBar`, `Toolbar`, `Typography` from `@mui/material`.
*   **Acceptance Criteria:** `Header.tsx` component renders a simple application bar with a title. It should be exportable from `apps/atlas-ide-shell/src/components/Layout/index.ts` (create this index file if it doesn't exist).

**Task 2.A.3:** Create `Sidebar.tsx` placeholder component.
*   **Target File:** `apps/atlas-ide-shell/src/components/Layout/Sidebar.tsx` (Create this file)
*   **Definition:** `Sidebar: React.FC`
*   **UI Elements:** An MUI `Drawer`. Initially, use `variant="persistent"` or `variant="permanent"` (if always visible in the design for narrow screens) for simplicity. Include placeholder MUI `Typography` or `List`/`ListItem` elements for future sections like "AI Chat" and "FHIR Data".
*   **State Management:** 
    *   Connect to `uiStore` (from `libs/core/core-state`).
    *   Use `sidebarOpen` state from `uiStore` to control the `open` prop of the MUI `Drawer`.
    *   Provide a mechanism to toggle the sidebar (e.g., a button in `Header` or `Layout` that calls `toggleSidebar` from `uiStore` - this button can be added in a later task if not immediately part of `Header`'s design).
*   **Styling:** Tailwind CSS for width, background color, and internal padding. Ensure it integrates smoothly with `Layout.tsx` and doesn't overlap content incorrectly.
*   **Key Imports:** `React`, `Drawer`, `Typography`, `List`, `ListItem` from `@mui/material`, `useUiStore` (assuming a hook is created for `uiStore`).
*   **Acceptance Criteria:** `Sidebar.tsx` component renders a drawer. Its open/close state is driven by `uiStore`. Placeholder content is visible. Exportable from `apps/atlas-ide-shell/src/components/Layout/index.ts`.

**Task 2.A.4:** Create `Footer.tsx` placeholder component.
*   **Target File:** `apps/atlas-ide-shell/src/components/Layout/Footer.tsx` (Create this file)
*   **Definition:** `Footer: React.FC`
*   **UI Elements:** An MUI `Box` component acting as the footer container. Inside, use MUI `Typography` for text like copyright information (e.g., "© 2025 Atlas Health") or basic status indicators.
*   **Styling:** Tailwind CSS for height, background color, text alignment, and padding. Ensure it's visually distinct and appropriately positioned at the bottom of the layout.
*   **Key Imports:** `React`, `Box`, `Typography` from `@mui/material`.
*   **Acceptance Criteria:** `Footer.tsx` component renders a simple footer bar with text. Exportable from `apps/atlas-ide-shell/src/components/Layout/index.ts`.

**Task 2.A.5:** Create or Update `uiStore.ts` for Sidebar state management.
*   **Target File:** `libs/core/core-state/src/lib/uiStore.ts` (This file should exist from Foundation/Step 0 or 1; update it. If it doesn't, it's a critical omission from prior steps that needs to be addressed first, but for this task, assume it exists or create it with basic structure if absolutely necessary.)
*   **Definition:** Ensure the Zustand store `uiStore` is defined or updated.
*   **State Shape (Add/Ensure):** `sidebarOpen: boolean` (initialize to `true` or `false` based on default design), `isMobileNavOpen: boolean` (for potential future use with smaller screens).
*   **Actions (Add/Ensure):** `toggleSidebar: () => void`, `setSidebarOpen: (isOpen: boolean) => void`, `toggleMobileNav: () => void`.
*   **Core Logic:** Implement the state and actions. `toggleSidebar` should invert `sidebarOpen`. `setSidebarOpen` should set it directly.
*   **Acceptance Criteria:** `uiStore` correctly manages `sidebarOpen` state. Actions `toggleSidebar` and `setSidebarOpen` function as expected. The store is exportable and usable via a custom hook (e.g., `useUiStore`) from `libs/core/core-state/src/index.ts`.

### 2.B. Style the Shell Application (`apps/atlas-ide-shell`)

**Task 2.B.1:** Review and Apply Global Styles & Theme.
*   **Target Files:** `apps/atlas-ide-shell/src/styles/theme.ts` (should exist from Step Foundation), `apps/atlas-ide-shell/pages/_app.tsx` (for theme provider), `apps/atlas-ide-shell/tailwind.config.js`, `apps/atlas-ide-shell/src/styles/globals.css`.
*   **Core Logic:** Verify that the MUI `ThemeProvider` in `_app.tsx` is correctly applying `theme.ts`. Ensure `tailwind.config.js` is configured to scan all necessary component files for class usage. Confirm `globals.css` includes Tailwind's base, components, and utilities directives (`@tailwind base; @tailwind components; @tailwind utilities;`). Add any overriding global styles if absolutely necessary, but prefer theming and utility classes.
*   **Acceptance Criteria:** MUI components across the application consistently reflect the custom theme defined in `theme.ts`. Tailwind CSS utility classes can be applied effectively and work harmoniously with MUI components. The overall look and feel is consistent with design intentions.

**Task 2.B.2:** Style Layout Components (`Header`, `Sidebar`, `Footer`, `Layout`).
*   **Target Files:** `apps/atlas-ide-shell/src/components/Layout/Header.tsx`, `Sidebar.tsx`, `Footer.tsx`, `Layout.tsx`.
*   **Core Logic:** Apply specific Tailwind CSS classes and MUI `sx` props to these components for a cohesive and polished visual appearance. Focus on dimensions, spacing, borders, background colors, typography, and iconography (if any placeholders exist).
*   **Styling Details:** 
    *   `Header`: Ensure appropriate elevation, padding, and alignment of title/actions.
    *   `Sidebar`: Consistent width, background, and clear separation from content.
    *   `Footer`: Subtle styling, clear text, and fixed or static positioning as per design.
    *   `Layout` (main content area): Proper padding, background, and ensure the `CodeServerView` iframe (when added) will fit well within this area, respecting its role as the primary coding interface. The boundary between the React shell and the embedded editor should be clear.
*   **Acceptance Criteria:** All layout components are visually polished and harmonized. The main content area designated for `CodeServerView` is well-defined and appropriately styled. The application has a professional and consistent look and feel.

### 2.C. Develop Initial Shared UI Components (`libs/ui-core`)

**Task 2.C.1:** Setup Storybook for `ui-core` library.
*   **Target Library:** `ui-core` (located at `libs/ui-core/` as per foundation setup).
*   **Action:** If not already done in foundation, run `nx generate @nx/react:storybook-configuration ui-core --generateStories --interactionTests=false` in the workspace root (`atlas-palantir/`). If already configured, verify its correctness.
*   **Verification:** Run `nx run ui-core:storybook`. Ensure Storybook loads and can find/display stories.
*   **Accessibility Addon:** Install `@storybook/addon-a11y` package (`npm install -D @storybook/addon-a11y` or equivalent yarn command). Configure it in `libs/ui-core/.storybook/main.ts` by adding `'@storybook/addon-a11y'` to the `addons` array.
*   **Acceptance Criteria:** Storybook is correctly configured for the `ui-core` library. The `@storybook/addon-a11y` is installed and integrated. Storybook runs successfully, and accessibility checks are available for stories.

**Task 2.C.2.1:** Create `StyledButton/Button.tsx` component in `ui-core`.
*   **Target File:** `libs/ui-core/src/lib/StyledButton/Button.tsx` (Create directory and file).
*   **Definition:** `StyledButton: React.FC<StyledButtonProps>` where `StyledButtonProps extends MuiButtonProps` (from `@mui/material/Button`). Add a `variant` prop that can be `'primary'`, `'secondary'`, `'text'`, `'danger'` etc., if custom variants beyond MUI's default are needed.
*   **UI Elements:** Utilize MUI `Button` as the base.
*   **Styling:** Apply Tailwind CSS classes conditionally based on the `variant` prop and other MUI props (e.g., `size`, `disabled`) to achieve the desired look for each variant. Focus on consistent padding, border-radius, font-weights, and color schemes aligned with `theme.ts`.
*   **Core Logic:** A general-purpose button component that wraps MUI's `Button` and applies consistent project-specific styling via Tailwind. Pass through all other props to the underlying MUI `Button`.
*   **Key Imports:** `React`, `Button as MuiButton`, `ButtonProps as MuiButtonProps` from `@mui/material`.
*   **Acceptance Criteria:** `StyledButton` component is created and exportable from `libs/ui-core/src/index.ts`. It renders correctly with different variants and props. Styling is consistent and adheres to the design system.

**Task 2.C.2.2:** Create `StyledButton/Button.stories.tsx`.
*   **Target File:** `libs/ui-core/src/lib/StyledButton/Button.stories.tsx` (Create file).
*   **Core Logic:** Create multiple stories showcasing all variants (`primary`, `secondary`, `text`, custom ones if any), sizes (`small`, `medium`, `large`), states (`disabled`, with icons), and different children (text, icons with text). Use `args` to control props.
*   **Acceptance Criteria:** Stories render correctly in Storybook, demonstrating all features of the `StyledButton`. Accessibility checks in Storybook pass for all stories.

**Task 2.C.2.3:** Create `Panel/Panel.tsx` component in `ui-core`.
*   **Target File:** `libs/ui-core/src/lib/Panel/Panel.tsx` (Create directory and file).
*   **Definition:** `Panel: React.FC<PanelProps>` where `PanelProps` includes `title?: string`, `children: React.ReactNode`, and potentially props for elevation, padding control, etc. It can also extend MUI `PaperProps`.
*   **UI Elements:** Use MUI `Paper` or `Card` as the main container. If `title` is provided, render it using MUI `Typography` (e.g., `h6` variant) within a header section of the panel.
*   **Styling:** Tailwind CSS for padding, margins, border, shadow (can leverage MUI `Paper` elevation), and title styling. Ensure consistency with the application's theme.
*   **Core Logic:** A reusable container component for grouping related content or features, with an optional title.
*   **Key Imports:** `React`, `Paper`, `Typography`, `Card`, `CardHeader`, `CardContent` from `@mui/material` (choose Card or Paper based on design needs).
*   **Acceptance Criteria:** `Panel` component is created and exportable. It displays children and an optional title correctly. Styling is consistent.

**Task 2.C.2.4:** Create `Panel/Panel.stories.tsx`.
*   **Target File:** `libs/ui-core/src/lib/Panel/Panel.stories.tsx` (Create file).
*   **Core Logic:** Create stories for the `Panel` component: with a title, without a title, with various types of child content (simple text, other components), and different elevation levels if applicable.
*   **Acceptance Criteria:** Stories render correctly in Storybook, showcasing the `Panel` component's features. Accessibility checks pass.

**Task 2.C.2.5:** Create `LoadingSpinner/LoadingSpinner.tsx` component in `ui-core`.
*   **Target File:** `libs/ui-core/src/lib/LoadingSpinner/LoadingSpinner.tsx` (Create directory and file).
*   **Definition:** `LoadingSpinner: React.FC<LoadingSpinnerProps>` where `LoadingSpinnerProps extends MuiCircularProgressProps`. Add optional props for `size` (numeric or 'small', 'medium', 'large' mapping to pixel values), `fullscreen?: boolean` (for centering spinner on screen), or `inline?: boolean`.
*   **UI Elements:** MUI `CircularProgress`.
*   **Styling:** Tailwind CSS for positioning (e.g., centering if `fullscreen` is true, or ensuring it behaves as an inline block element if `inline`).
*   **Core Logic:** A simple, reusable loading indicator. If `fullscreen`, it might render within a `Box` that takes full screen width/height and centers the spinner.
*   **Key Imports:** `React`, `CircularProgress`, `CircularProgressProps as MuiCircularProgressProps`, `Box` from `@mui/material`.
*   **Acceptance Criteria:** `LoadingSpinner` component created and exportable. It renders correctly in different configurations (default, specific size, fullscreen). Styling applies as expected.

**Task 2.C.2.6:** Create `LoadingSpinner/LoadingSpinner.stories.tsx`.
*   **Target File:** `libs/ui-core/src/lib/LoadingSpinner/LoadingSpinner.stories.tsx` (Create file).
*   **Core Logic:** Create stories for `LoadingSpinner`: default, different sizes, fullscreen variant (if implemented), and potentially different colors if theming supports it.
*   **Acceptance Criteria:** Stories render correctly in Storybook. Accessibility checks pass (though spinners can be tricky, ensure it's not obstructive when not needed).

**Task 2.C.3:** Export components from `ui-core`.
*   **Target File:** `libs/ui-core/src/index.ts` (This file should exist from library generation).
*   **Core Logic:** Add export statements for `StyledButton` (and its props type), `Panel` (and its props type), and `LoadingSpinner` (and its props type).
*   **Acceptance Criteria:** All newly created `ui-core` components and their associated prop types are properly exported from the library's main `index.ts` file and can be successfully imported into other libraries or applications within the Nx workspace.

### 2.D. Optimize Font Loading

**Task 2.D.1:** Implement or Verify Font Loading Strategy (e.g., `next/font`).
*   **Target Files:** `apps/atlas-ide-shell/pages/_app.tsx` and/or `apps/atlas-ide-shell/src/components/Layout/Layout.tsx`.
*   **Core Logic:** Ensure that the primary application font (e.g., Roboto, or as specified in design documents) is loaded efficiently using `next/font` (e.g., `next/font/google` or `next/font/local`). This might involve defining the font in a shared file, then applying its class name to a top-level element like `body` or the main layout container.
*   **Verification:** This task may have been completed during the Foundation step. Verify its implementation. If not fully implemented or optimized (e.g., font variables for Tailwind, correct application), complete it now.
*   **Acceptance Criteria:** The chosen application font is loaded efficiently using `next/font`, minimizing FOUT/CLS. The font is correctly applied globally throughout the `atlas-ide-shell` application. Font variables are available for use in Tailwind CSS if that strategy is chosen.

### 2.E. Integrate and Test

**Task 2.E.1:** Optionally use Shared Components in Shell for Integration Testing.
*   **Target Files:** Potentially `apps/atlas-ide-shell/src/components/Layout/Header.tsx`, `Sidebar.tsx`, or other simple components within the shell application.
*   **Core Logic:** As a quick integration test, replace some basic HTML elements or ad-hoc styled MUI components in the `atlas-ide-shell` with the newly created components from `ui-core`. For example, use `StyledButton` for a placeholder button in the `Header` or `Panel` to wrap a section in the `Sidebar`.
*   **Purpose:** This is not about full refactoring yet, but about verifying that `ui-core` components can be successfully imported, rendered, and styled within the main application.
*   **Acceptance Criteria:** At least one or two `ui-core` components are successfully imported and used within the `atlas-ide-shell` application without build or runtime errors. They render as expected according to their Storybook appearance.

**Task 2.E.2:** Review Visuals and Responsiveness of `atlas-ide-shell`.
*   **Action:** Run the `atlas-ide-shell` application using `nx serve atlas-ide-shell`. Thoroughly inspect the application in a web browser.
*   **Core Logic & Checks:**
    *   Verify the overall layout structure (`Header`, `Sidebar`, `Footer`, main content area).
    *   Check the styling of all layout components and any integrated `ui-core` components.
    *   Critically test responsiveness across various screen widths, with a special focus on the target Epic sidebar constraint (e.g., 320px to 600px). Ensure all elements behave correctly, text is readable, and there are no overlaps or broken layouts.
    *   Confirm that the main content area (placeholder for `CodeServerView`) adapts correctly to sidebar changes and screen resizes.
*   **Acceptance Criteria:** The `atlas-ide-shell` application is visually coherent and consistent. The layout is fully responsive and functions well on narrow screens. There are no major styling defects or layout issues. Integrated `ui-core` components look as expected.

### 2.F. Critical Review & Integration Tasks (End of Phase 2)

**Task 2.F.1:** Verify Layout Structure and Component Integration.
*   **Action:** Manually inspect the running `atlas-ide-shell` application. Confirm that `Layout.tsx` correctly incorporates and displays `Header`, `Sidebar`, and `Footer`. Verify that the `Sidebar`'s open/close state is correctly managed by `uiStore` and that interactions (if any toggle mechanism is implemented yet) work.
*   **Acceptance Criteria:** All primary layout components (`Header`, `Sidebar`, `Footer`, main content area) are present and structurally sound. Sidebar state management via `uiStore` is functional. Basic integration of shared components (if done in 2.E.1) is successful.

**Task 2.F.2:** UI/UX Review for Shell.
*   **Action:** Conduct a thorough UI/UX review of the `atlas-ide-shell`. Assess the overall usability and visual appeal of the shell's layout, especially within the narrow sidebar constraints (<=600px). Check for visual consistency with the theme, proper font rendering, appropriate spacing, and intuitive navigation (if any exists).
*   **Acceptance Criteria:** The shell UI is deemed visually appealing, usable within constraints, and consistent with the intended design. No major UX hurdles are identified for the current scope.

**Task 2.F.3:** Storybook Review for `ui-core`.
*   **Action:** Launch Storybook for `ui-core` (`nx run ui-core:storybook`). Verify that all created components (`StyledButton`, `Panel`, `LoadingSpinner`) have comprehensive stories covering their variants and states. Confirm that the `@storybook/addon-a11y` is active and check its output for any reported accessibility issues in the stories.
*   **Acceptance Criteria:** Storybook is fully functional for `ui-core`. All components have adequate stories. The accessibility addon is working, and any critical issues it flags are noted for remediation.

**Task 2.F.4:** Linting and Build Checks.
*   **Action:** Run linting for all affected projects: `nx lint atlas-ide-shell` and `nx lint ui-core`. Run a production build of the shell application: `nx build atlas-ide-shell`.
*   **Acceptance Criteria:** Linting passes without errors for both `atlas-ide-shell` and `ui-core`. The `atlas-ide-shell` application builds successfully without errors.

**Task 2.F.5:** Commit Phase 2 Work.
*   **Action:** Commit all changes made during Phase 2 to the Git repository with a descriptive commit message (e.g., "feat: Implement Phase 2 - Basic Shell UI & Core Components").
*   **Acceptance Criteria:** All Phase 2 work is successfully committed to version control.