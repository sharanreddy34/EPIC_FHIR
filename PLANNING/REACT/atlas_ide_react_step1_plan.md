# Atlas IDE: React Frontend - Step I Foundation Plan

This document outlines the tasks for Step I (Foundation & Overall Architecture) of the Atlas IDE React frontend.

## A. Monorepo Setup (Nx)

1.  **Initialize Nx Workspace:**
    *   Command:
        ```bash
        npx create-nx-workspace@latest atlas-ide --preset=next --appName=atlas-ide-shell --style=tailwind --nxCloud=false --packageManager=npm --interactive=false
        ```
    *   **Workspace Name:** `atlas-ide`
    *   **Initial App:** `atlas-ide-shell` (Next.js with Tailwind CSS)

2.  **Navigate into the Workspace:**
    ```bash
    cd atlas-ide
    ```

## B. Core Directory Structure & Initial Libraries

Generate the following libraries within the `libs/` directory of the `atlas-ide` workspace.

1.  **UI Core Library:**
    ```bash
    nx generate @nx/react:library ui-core --directory=libs/shared --style=tailwind --publishable --importPath=@atlas-ide/shared/ui-core
    ```
2.  **FHIR Utilities Library:**
    ```bash
    nx generate @nx/js:library fhir-utils --directory=libs/fhir --publishable --importPath=@atlas-ide/fhir/fhir-utils
    ```
3.  **Core Hooks Library:**
    ```bash
    nx generate @nx/react:library core-hooks --directory=libs/core --style=none --publishable --importPath=@atlas-ide/core/core-hooks
    ```
4.  **Core State Library:**
    ```bash
    nx generate @nx/js:library core-state --directory=libs/core --publishable --importPath=@atlas-ide/core/core-state
    ```
5.  **Server State (TanStack Query) Library:**
    ```bash
    nx generate @nx/js:library core-graphql --directory=libs/core --publishable --importPath=@atlas-ide/core/core-graphql
    ```

## C. Next.js Shell (`apps/atlas-ide-shell`) Configuration

1.  **Install MUI & Dependencies:**
    (Run in the workspace root: `atlas-ide/`)
    ```bash
    npm install @mui/material @emotion/react @emotion/styled @mui/icons-material
    ```

2.  **Create Basic MUI Theme:**
    *   **File:** `apps/atlas-ide-shell/src/theme/theme.ts`
    *   **Tasks:**
        *   Research and apply initial theming principles from the chosen healthcare design system (e.g., CMS/HealthCare.gov). Adapt `theme.ts` with its color palette, typography, and spacing. **Critically, consider the Epic EMR sidebar's typical width constraints (e.g., <=600px) from the outset. This should inform choices for compact component variants, responsive typography, and efficient use of space in the theme design.**
        *   **Initial Content:**
        ```typescript
        import { createTheme } from '@mui/material/styles';
        import { red } from '@mui/material/colors';

        const theme = createTheme({
          palette: {
            primary: { main: '#556cd6' },
            secondary: { main: '#19857b' },
            error: { main: red.A400 },
            background: { default: '#fff' },
          },
          typography: {
            fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
          },
        });

        export default theme;
        ```

3.  **Configure `_app.tsx` for MUI and Layout:**
    *   **File:** `apps/atlas-ide-shell/pages/_app.tsx`
    *   **Content:**
        ```tsx
        import '../styles/globals.css';
        import type { AppProps } from 'next/app';
        import { ThemeProvider } from '@mui/material/styles';
        import CssBaseline from '@mui/material/CssBaseline';
        import theme from '../src/theme/theme';
        import Layout from '../src/components/Layout/Layout';
        import { ApolloProvider } from '@apollo/client';
        import { apolloClient } from '@atlas-ide/core/core-graphql'; // Using importPath for library

        function CustomApp({ Component, pageProps }: AppProps) {
          return (
            <ApolloProvider client={apolloClient}> {/* Added Wrapper */}
              <ThemeProvider theme={theme}>
                <CssBaseline />
                <Layout>
                  <Component {...pageProps} />
                </Layout>
              </ThemeProvider>
            </ApolloProvider> {/* Added Wrapper */}
          );
        }
        export default CustomApp;
        ```

4.  **Create Basic Layout Component:**
    *   **File:** `apps/atlas-ide-shell/src/components/Layout/Layout.tsx`
    *   **Content:**
        ```tsx
        import React, { ReactNode } from 'react';
        import Head from 'next/head';
        import Box from '@mui/material/Box';

        type Props = { children?: ReactNode; title?: string; };

        const Layout = ({ children, title = 'Atlas IDE' }: Props) => (
          <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <Head>
              <title>{title}</title>
              <meta charSet="utf-8" />
              <meta name="viewport" content="initial-scale=1.0, width=device-width" />
            </Head>
            <Box component="main" sx={{ flexGrow: 1, display: 'flex', flexDirection: 'row' }}>
              <Box sx={{ flexGrow: 1, p: 1 }}>
                {children}
              </Box>
            </Box>
          </Box>
        );
        export default Layout;
        ```

5.  **Update `pages/index.tsx` (Main IDE View Placeholder):**
    *   **File:** `apps/atlas-ide-shell/pages/index.tsx`
    *   **Content:**
        ```tsx
        import Typography from '@mui/material/Typography';
        import Box from '@mui/material/Box';
        import { CodeServerView } from '../src/components/CodeServerView/CodeServerView'; // Corrected path

        export default function IndexPage() {
          return (
            <Box sx={{ height: 'calc(100vh - 16px)', display: 'flex', flexDirection: 'column' }}> {/* Assuming 16px padding from Layout (p:1 means 8px on all sides, potentially top+bottom = 16px). Adjust as needed. Header/Sidebar would also affect this calc. */}
              <Typography variant="h4" component="h1" gutterBottom>
                Welcome to Atlas IDE
              </Typography>
              <CodeServerView src="http://localhost:8080" /> {/* Replace with actual code-server URL from env var or config */}
            </Box>
          );
        }
        ```

## D. State Management Setup (Initial)

1.  **Zustand Setup:**
    *   Install: `npm install zustand` (in workspace root)
    *   Create initial UI store in `libs/core/core-state/src/lib/uiStore.ts`. **This store will manage the UI state of the React shell application itself (e.g., sidebar visibility, modal states). It should not attempt to duplicate or manage the internal state of the `code-server` editor.**
        ```typescript
        import { create } from 'zustand';

        interface UIState {
          isSidebarOpen: boolean;
          toggleSidebar: () => void;
          // Add other UI related states here
        }

        export const useUIStore = create<UIState>((set) => ({
          isSidebarOpen: true,
          toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
        }));
        ```

2.  **TanStack Query Setup:**
    *   Install: `npm install @tanstack/react-query` (in workspace root)
    *   Create `QueryClient` instance in `libs/core/core-graphql/src/lib/queryClient.ts` (or your chosen data-access library, adjust path as needed):
        ```typescript
        import { QueryClient } from '@tanstack/react-query';

        // Optional: Configure default options for all queries/mutations
        const queryClientConfig = {
          defaultOptions: {
            queries: {
              staleTime: 1000 * 60 * 5, // 5 minutes
              retry: (failureCount: number, error: any) => {
                // Don't retry on 404s or auth errors
                if (error.response?.status === 404 || error.response?.status === 401 || error.response?.status === 403) {
                  return false;
                }
                return failureCount < 3; // Retry up to 3 times otherwise
              },
              // You might want to set a global refetchOnWindowFocus: false if it's too aggressive
              // refetchOnWindowFocus: false,
            },
          },
        };

        export const queryClient = new QueryClient(queryClientConfig);

        // Example of how you might check for an API endpoint if needed globally,
        // though often this is handled per-query/service.
        if (!process.env.NEXT_PUBLIC_API_BASE_URL) {
            console.warn('NEXT_PUBLIC_API_BASE_URL is not set. TanStack Query may not function as expected for server interactions if relying on this base URL.');
        }
        ```

## E. Code Server Integration Placeholder

This section lays the groundwork for embedding and interacting with the `code-server` instance. The `CodeServerView.tsx` component will render the `code-server` iframe. Crucially, this integration is not just about displaying `code-server`, but establishing a robust communication channel (e.g., using `postMessage` API) that will be managed by a dedicated hook (e.g., `useCodeServerComm.ts` in a later step).

**Key Principle for `code-server` Interaction (to be applied throughout all steps):** The Atlas IDE React shell will primarily act as an orchestrator and UI provider. For functionalities that require deep interaction with the code editor (e.g., reading selections, inserting text, displaying ghost text, providing language-specific intelligence), the React shell will communicate with a dedicated **`code-server` extension**. This extension will leverage VSCodium's APIs. The React shell should *avoid* attempting to replicate these VSCodium core functionalities. The communication will typically occur via `postMessage` to/from the `code-server` iframe.

1.  **Basic `CodeServerView.tsx` Component:**
    *   Create in `apps/atlas-ide-shell/src/components/CodeServerView/CodeServerView.tsx`. **This component will initially just render the iframe. In subsequent steps, it will be enhanced to work with `useCodeServerComm.ts` to send and receive messages to/from the `code-server` instance and its extension(s).**
        ```tsx
        import React from 'react';
        import Box from '@mui/material/Box';

        interface CodeServerViewProps {
          src: string; // URL of the code-server instance
        }

        export const CodeServerView: React.FC<CodeServerViewProps> = ({ src }) => {
          return (
            <Box
              component="iframe"
              src={src}
              sx={{
                width: '100%',
                height: '100%', // Parent container needs to define height for this to work effectively
                border: 'none',
                flexGrow: 1, // Make iframe take available space in a flex container
              }}
              title="Code Server"
            />
          );
        };
        ```

2.  **Placeholder Hook for Iframe Communication:**
    *   Create in `libs/core/core-hooks/src/lib/useCodeServerComm.ts`:
        ```typescript
        import { useEffect, useCallback, RefObject } from 'react';

        // This is a very basic placeholder. Actual implementation will be more complex.
        export const useCodeServerComm = (iframeRef: RefObject<HTMLIFrameElement>) => {
          const postMessageToIframe = useCallback((message: any) => {
            if (iframeRef.current && iframeRef.current.contentWindow) {
              // Consider using a more specific targetOrigin than '*' in production
              iframeRef.current.contentWindow.postMessage(message, '*'); 
            }
          }, [iframeRef]);

          useEffect(() => {
            const handleMessage = (event: MessageEvent) => {
              // IMPORTANT: Always verify event.origin for security before processing the message
              // if (event.origin !== 'expected-code-server-origin') return;
              
              // Process message from iframe
              console.log('Message from code-server:', event.data);
              // Example: dispatch(handleCodeServerAction(event.data));
            };

            window.addEventListener('message', handleMessage);
            return () => window.removeEventListener('message', handleMessage);
          }, []);

          return { postMessageToIframe };
        };
        ```

## F. Branding & Metadata

1.  **Add Favicon & Meta Tags:**
    *   Add a project favicon (e.g., `favicon.ico` and other sizes like `apple-touch-icon.png`, `favicon-32x32.png`) to `apps/atlas-ide-shell/public/`.
    *   Include essential meta tags (e.g., `<meta name="description" content="Atlas IDE - AI-powered clinical development environment">`, `<meta name="theme-color" content="#yourPrimaryColor">`) in `apps/atlas-ide-shell/pages/_document.tsx` or within the main `Layout` component's `<Head>` section.

## G. Linting & TypeScript Configuration

*   Nx provides good defaults for ESLint and TypeScript.
*   Review and customize `eslintrc.json` and `tsconfig.base.json` (and app/lib specific ones like `apps/atlas-ide-shell/tsconfig.json`, `libs/core/core-state/tsconfig.json`, etc.) as needed, adhering to project standards.
*   Ensure strict TypeScript rules are enabled (e.g., `"strict": true` in `tsconfig.base.json` and inherited).
*   **Install & Configure Linters:** Install and configure `eslint-plugin-jsx-a11y` for accessibility linting and `eslint-plugin-tailwindcss` for Tailwind CSS best practices.
*   Consider other ESLint plugins for React, Hooks, and MUI for better code quality and consistency.

---
This plan provides the foundational steps. Subsequent steps will build upon this base, including creating actual components, implementing features, and refining configurations.
