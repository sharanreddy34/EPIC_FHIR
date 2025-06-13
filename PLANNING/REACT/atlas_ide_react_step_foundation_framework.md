# Atlas IDE: React Frontend - Step 0 Foundation & Overall Architecture Framework

This document outlines the confirmed technology choices and the initial setup steps for Step 0 (Foundation & Overall Architecture) of the Atlas IDE React frontend. It serves as a framework for an LLM to begin coding the project.

**Confirmed Technology Choices for Atlas IDE Frontend:**

*   **Monorepo Manager:** **Nx** - Chosen for its robust feature set, excellent support for various frameworks (including Next.js and React), powerful task running, dependency graphing, and code generation capabilities, which are beneficial for a complex project like an IDE.
*   **Core Application Framework:** **Next.js** - As planned, for its versatile routing, rendering options, and ecosystem.
*   **Primary UI Component Library:** **MUI (Material-UI)** - Recommended for its comprehensive set of well-tested, accessible components, and strong theming capabilities suitable for a professional application. Theming will align with a chosen healthcare design system (e.g., CMS/HealthCare.gov Design System), emphasizing compact component variants suitable for the Epic sidebar.
*   **Styling Solution:** **Tailwind CSS** - As planned, for utility-first CSS, enabling rapid development and maintainable styling. It will be used in conjunction with MUI.
*   **UI State Management:** **Zustand** - For its simplicity, minimal boilerplate, and good performance for managing global UI state.
*   **Server State & Data Fetching:** **TanStack Query (React Query)** - For managing FHIR data (via FastAPI proxy) and REST API interactions, offering powerful caching, background updates, and declarative data fetching.
*   **Language:** **TypeScript** - For type safety and improved developer experience.
*   **Code Editor Integration:** **Monaco Editor** (embedded via `code-server`).
*   **Charting Library:** **Chart.js** (with `react-chartjs-2`).

*   **Foundational Principles:** Development will adhere to WCAG 2.2 AA accessibility standards and client-side HIPAA considerations (e.g., no PHI in persistent browser storage, secure data handling) from the outset.

---

**Framework for LLM: Building Step I - Foundation & Overall Architecture**

This section details the commands, file structures, and initial code snippets an LLM would use to set up the foundational layer of the Atlas IDE frontend.

**A. Monorepo Setup (Nx)**

1.  **Rationale for Nx:**
    *   Provides a structured workspace, facilitates code sharing between the Next.js shell and other potential libraries (e.g., UI components, utility functions).
    *   Offers efficient build and test processes, especially for larger projects.
    *   Generators for applications, libraries, components, etc., speed up development.

2.  **Initialize Nx Workspace:**
    *   Command (to be run in the desired parent directory for the project):
        ```bash
        npx create-nx-workspace@latest atlas-ide --preset=next --appName=atlas-ide-shell --style=tailwind --nxCloud=false
        ```
        *   `atlas-ide`: Name of the Nx workspace (root directory).
        *   `--preset=next`: Uses the Next.js preset.
        *   `--appName=atlas-ide-shell`: Name of the initial Next.js application.
        *   `--style=tailwind`: Sets up Tailwind CSS for the Next.js app.
        *   `--nxCloud=false`: Opt-out of Nx Cloud for now (can be enabled later).

3.  **Navigate into the Workspace:**
    ```bash
    cd atlas-ide
    ```

4.  **Environment Configuration Strategy:**
    *   All external service URLs (e.g., FastAPI backend, `code-server` instance, GraphQL endpoint) and sensitive keys will be managed via environment variables (e.g., using `.env` files and Next.js runtime configuration) to avoid hardcoding sensitive information and enhance security.

**B. Core Directory Structure & Initial Libraries**

Nx will create an `apps/atlas-ide-shell` directory for your Next.js application. We'll now define some initial libraries within the `libs/` directory.

1.  **Generate UI Core Library:** For shared, low-level UI components or MUI customizations.
    ```bash
    nx generate @nx/react:library ui-core --directory=libs/shared --style=tailwind --publishable --importPath=@atlas-ide/shared/ui-core
    ```
2.  **Generate FHIR Utilities Library:** For types, helper functions related to FHIR data.
    ```bash
    nx generate @nx/js:library fhir-utils --directory=libs/fhir --publishable --importPath=@atlas-ide/fhir/fhir-utils
    ```
3.  **Generate Core Hooks Library:** For reusable React hooks.
    ```bash
    nx generate @nx/react:library core-hooks --directory=libs/core --style=none --publishable --importPath=@atlas-ide/core/core-hooks
    ```
4.  **Generate Core State Library:** For Zustand stores.
    ```bash
    nx generate @nx/js:library core-state --directory=libs/core --publishable --importPath=@atlas-ide/core/core-state
    ```
5.  **Generate Server State (TanStack Query) Library:** For TanStack Query setup and data fetching operations (e.g., in `libs/core/core-tanstack-query` or `libs/core/data-access`).
    ```bash
    nx generate @nx/js:library core-graphql --directory=libs/core --publishable --importPath=@atlas-ide/core/core-graphql
    ```

**Expected Structure (simplified):**

```
atlas-ide/
├── apps/
│   └── atlas-ide-shell/      # Next.js application
│       ├── pages/
│       ├── components/
│       ├── public/
│       ├── styles/
│       ├── tailwind.config.js
│       └── ...
├── libs/
│   ├── core/
│   │   ├── core-graphql/
│   │   ├── core-hooks/
│   │   └── core-state/
│   ├── fhir/
│   │   └── fhir-utils/
│   └── shared/
│       └── ui-core/
├── nx.json
├── package.json
└── tsconfig.base.json
```

**C. Next.js Shell (`apps/atlas-ide-shell`) Configuration**

0.  **Optimized Font Loading:**
    *   Utilize `next/font` for loading primary project fonts (e.g., Roboto) to enhance performance, prevent layout shifts, and ensure a consistent high-quality visual experience.

1.  **Install MUI:**
    ```bash
    npm install @mui/material @emotion/react @emotion/styled @mui/icons-material
    ```
    (Run this command in the root of the Nx workspace `atlas-ide/`)

2.  **Create a Basic MUI Theme:**
    *   File: `apps/atlas-ide-shell/src/theme/theme.ts`
    ```typescript
    import { createTheme } from '@mui/material/styles';
    import { red } from '@mui/material/colors';

    // Create a theme instance.
    const theme = createTheme({
      palette: {
        primary: {
          main: '#556cd6', // Example primary color
        },
        secondary: {
          main: '#19857b', // Example secondary color
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
      // Add overrides for Epic sidebar constraints if known
      // e.g., smaller default font sizes, compact component variants
    });

    export default theme;
    ```

3.  **Configure `_app.tsx` for MUI and Layout:**
    *   File: `apps/atlas-ide-shell/pages/_app.tsx`
    ```tsx
    import '../styles/globals.css'; // Tailwind globals
    import type { AppProps } from 'next/app';
    import { ThemeProvider } from '@mui/material/styles';
    import CssBaseline from '@mui/material/CssBaseline';
    import theme from '../src/theme/theme'; // Adjust path if needed
    import Layout from '../src/components/Layout/Layout'; // Create this next

    function CustomApp({ Component, pageProps }: AppProps) {
      return (
        <ThemeProvider theme={theme}>
          {/* CssBaseline kickstart an elegant, consistent, and simple baseline to build upon. */}
          <CssBaseline />
          <Layout>
            <Component {...pageProps} />
          </Layout>
        </ThemeProvider>
      );
    }

    export default CustomApp;
    ```

4.  **Create Basic Layout Component:**
    *   File: `apps/atlas-ide-shell/src/components/Layout/Layout.tsx`
    ```tsx
    import React, { ReactNode } from 'react';
    import Head from 'next/head';
    import Box from '@mui/material/Box';
    // import Header from './Header'; // Future component
    // import Sidebar from './Sidebar'; // Future component

    type Props = {
      children?: ReactNode;
      title?: string;
    };

    const Layout = ({ children, title = 'Atlas IDE' }: Props) => (
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Head>
          <title>{title}</title>
          <meta charSet="utf-8" />
          <meta name="viewport" content="initial-scale=1.0, width=device-width" />
        </Head>
        {/* <Header /> */}
        <Box component="main" sx={{ flexGrow: 1, display: 'flex', flexDirection: 'row' /* or column depending on sidebar */ }}>
          {/* <Sidebar /> */} {/* Placeholder for AI chat, FHIR data panels */}
          <Box sx={{ flexGrow: 1, p: 1 /* Adjust padding as needed */ }}>
            {children}
          </Box>
        </Box>
        {/* Potentially a Footer component */}
      </Box>
    );

    export default Layout;
    ```

5.  **Update `pages/index.tsx` (Main IDE View Placeholder):**
    *   File: `apps/atlas-ide-shell/pages/index.tsx`
    ```tsx
    import Typography from '@mui/material/Typography';
    import Box from '@mui/material/Box';
    import CodeServerView from '../src/components/CodeServerView/CodeServerView'; // Create this next

    export default function IndexPage() {
      return (
        <Box sx={{ width: '100%', height: 'calc(100vh - 64px)' /* Adjust based on header height */ }}>
          <Typography variant="h4" gutterBottom>
            Welcome to Atlas IDE
          </Typography>
          {/* This will eventually hold the code-server iframe and surrounding UI */}
          <CodeServerView />
        </Box>
      );
    }
    ```

**D. State Management Setup**

1.  **Zustand:**
    *   Install: `npm install zustand` (in workspace root)
    *   Create initial UI store in the `core-state` library:
        *   File: `libs/core/core-state/src/lib/uiStore.ts`
        ```typescript
        import { create } from 'zustand';

        interface UiState {
          isAiChatPanelOpen: boolean;
          toggleAiChatPanel: () => void;
          themeMode: 'light' | 'dark';
          setThemeMode: (mode: 'light' | 'dark') => void;
        }

        export const useUiStore = create<UiState>((set) => ({
          isAiChatPanelOpen: false,
          toggleAiChatPanel: () => set((state) => ({ isAiChatPanelOpen: !state.isAiChatPanelOpen })),
          themeMode: 'light',
          setThemeMode: (mode) => set({ themeMode: mode }),
        }));
        ```

2.  **TanStack Query (React Query):**
    *   Install: `npm install @apollo/client graphql` (in workspace root)
    *   Create TanStack Query client (`QueryClient`) configuration (e.g., in `libs/core/core-tanstack-query/src/lib/queryClient.ts` or a similar `data-access` library):
        *   File: `libs/core/core-graphql/src/lib/apolloClient.ts`
        ```typescript
        import { ApolloClient, InMemoryCache, HttpLink } from '@apollo/client';

        // Replace with your actual FastAPI proxy URL for GraphQL
        const FASTAPI_PROXY_URL = process.env.NEXT_PUBLIC_FASTAPI_PROXY_URL || 'http://localhost:8000/graphql';

        const httpLink = new HttpLink({
          uri: FASTAPI_PROXY_URL,
          // You might need to configure headers for authentication here
          // headers: {
          //   authorization: `Bearer ${YOUR_AUTH_TOKEN}`,
          // },
        });

        const apolloClient = new ApolloClient({
          link: httpLink,
          cache: new InMemoryCache(),
          connectToDevTools: process.env.NODE_ENV === 'development',
        });

        export default apolloClient;
        ```
    *   Remember to wrap your app in `ApolloProvider` in `apps/atlas-ide-shell/pages/_app.tsx` when you start using it:
        ```tsx
        // In _app.tsx
        // import { ApolloProvider } from '@apollo/client';
        // import apolloClient from '@atlas-ide/core/core-graphql'; // Adjust path
        // ...
        // return (
        //   <ApolloProvider client={apolloClient}>
        //     <ThemeProvider theme={theme}>
        //       ...
        //     </ThemeProvider>
        //   </ApolloProvider>
        // );
        ```

**E. `code-server` Integration Placeholder**

1.  **Component for Embedding `code-server` Iframe:**
    *   File: `apps/atlas-ide-shell/src/components/CodeServerView/CodeServerView.tsx`
    ```tsx
    import React from 'react';
    import Box from '@mui/material/Box';
    import Typography from '@mui/material/Typography';

    // TODO: Get this URL from environment variables or configuration
    const CODE_SERVER_URL = process.env.NEXT_PUBLIC_CODE_SERVER_URL || 'http://localhost:8080'; // Example URL

    const CodeServerView = () => {
      // TODO: Add error handling, loading states, and security for iframe
      return (
        <Box sx={{ width: '100%', height: '100%', border: '1px solid #ccc' }}>
          {CODE_SERVER_URL ? (
            <iframe
              src={CODE_SERVER_URL}
              title="Atlas IDE Code Server"
              style={{ width: '100%', height: '100%', border: 'none' }}
              // sandbox="allow-scripts allow-same-origin allow-forms allow-popups" // Configure sandbox appropriately
              // allow="clipboard-read; clipboard-write;" // Permissions
            />
          ) : (
            <Typography color="error">
              Code Server URL is not configured.
            </Typography>
          )}
        </Box>
      );
    };

    export default CodeServerView;
    ```

2.  **Utility/Hook for Iframe Communication (Placeholder):**
    *   Create in `core-hooks` library:
        *   File: `libs/core/core-hooks/src/lib/useCodeServerComm.ts`
        ```typescript
        import { useEffect, useCallback } from 'react';

        // TODO: Define message types/interfaces
        // interface CodeServerMessage {
        //   type: string;
        //   payload: any;
        // }

        export const useCodeServerComm = (iframeRef: React.RefObject<HTMLIFrameElement>) => {
          const postMessageToIframe = useCallback((message: any) => {
            if (iframeRef.current && iframeRef.current.contentWindow) {
              // Ensure targetOrigin is specific and correct for security
              iframeRef.current.contentWindow.postMessage(message, process.env.NEXT_PUBLIC_CODE_SERVER_URL || '*');
            }
          }, [iframeRef]);

          useEffect(() => {
            const handleMessageFromIframe = (event: MessageEvent) => {
              // IMPORTANT: Validate event.origin for security
              // if (event.origin !== process.env.NEXT_PUBLIC_CODE_SERVER_URL) {
              //   console.warn('Message received from untrusted origin:', event.origin);
              //   return;
              // }
              // const data = event.data as CodeServerMessage;
              // console.log('Message from code-server:', data);
              // TODO: Handle different message types
            };

            window.addEventListener('message', handleMessageFromIframe);
            return () => {
              window.removeEventListener('message', handleMessageFromIframe);
            };
          }, []);

          return { postMessageToIframe };
        };
        ```

**F. Initial `tsconfig.json` and Linting/Formatting**

*   **`tsconfig.base.json`:** Nx creates a base `tsconfig.base.json` in the workspace root. This typically includes path aliases for your libraries (e.g., `@atlas-ide/*`). Ensure this is configured correctly and suits your needs.
*   **ESLint & Prettier:** Nx sets up ESLint and Prettier during project generation. Configure rules as needed in `.eslintrc.json` and `.prettierrc` files at the workspace root and potentially override them in specific app/lib configurations.

---

This detailed framework for Step I provides the initial structure, configurations, and placeholder components/utilities. An LLM can use these instructions to generate the boilerplate code and set up the project foundation. The next steps would involve building out the specific UI components, integrating the AI features, and handling FHIR data as outlined in the subsequent phases of the overall plan.
