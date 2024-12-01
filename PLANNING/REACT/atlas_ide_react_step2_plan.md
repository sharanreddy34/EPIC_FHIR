# Atlas IDE: React Frontend - Step 2 Plan: Basic Shell UI & Core Component Styling

This document outlines the tasks for Step 2, focusing on building out the basic UI structure of the `atlas-ide-shell` application and starting the `ui-core` shared library with Storybook.

## A. Refine Layout Component (`apps/atlas-ide-shell`)

1.  **Enhance `Layout.tsx`:**
    *   **File:** `apps/atlas-ide-shell/src/components/Layout/Layout.tsx`
    *   **Tasks:**
        *   Add placeholders and basic structure for `Header`, `Sidebar`, and `Footer` components within the layout.
        *   Integrate these new components into `Layout.tsx`.
        *   Ensure the main content area dynamically adjusts based on the presence/state of `Sidebar`.
        *   Apply MUI components (e.g., `AppBar` for Header, `Drawer` for Sidebar, `Box` for Footer and content areas) for structure.
        *   Style using Tailwind CSS utility classes for dimensions, spacing, and basic appearance.
        *   **UI Polish:** Implement basic loading skeletons (e.g., using MUI `Skeleton`) for these placeholder areas to improve perceived performance.
        *   Consider responsiveness, rigorously testing for the Epic sidebar constraint (max 600px width) and ensuring a polished look. **Ensure the main content area, which will host `CodeServerView`, is designed to clearly demarcate the boundary between the React shell and the embedded `code-server` editor and provides adequate, non-cluttered space for it.**

2.  **Create Placeholder Components for Layout:**
    *   **Header:**
        *   **File:** `apps/atlas-ide-shell/src/components/Layout/Header.tsx`
        *   **Content:** Basic MUI `AppBar` with a title (`Typography`) and placeholder for future action buttons or branding.
    *   **Sidebar:**
        *   **File:** `apps/atlas-ide-shell/src/components/Layout/Sidebar.tsx`
        *   **Content:** Basic MUI `Drawer` (persistent or temporary variant, to be decided) with placeholder text or sections for "AI Chat" and "FHIR Data". Manage open/close state via the `uiStore` (Zustand) from `libs/core/core-state` – **this store is dedicated to managing the state of the React shell's UI elements.**
    *   **Footer:**
        *   **File:** `apps/atlas-ide-shell/src/components/Layout/Footer.tsx`
        *   **Content:** Basic MUI `Box` with copyright text or status information.

## B. Style the Shell Application (`apps/atlas-ide-shell`)

1.  **Apply Global Styles & Theme:**
    *   Ensure `theme.ts` from Step 1 is effectively theming MUI components.
    *   Add any necessary global styles in `styles/globals.css` (Tailwind base, components, utilities are already set up).
    *   Review overall look and feel, ensuring MUI and Tailwind CSS are working harmoniously.

2.  **Style Layout Components:**
    *   Apply specific Tailwind CSS classes and MUI `sx` props to `Header.tsx`, `Sidebar.tsx`, `Footer.tsx`, and the main content area within `Layout.tsx` for a cohesive look.
    *   Ensure the `CodeServerView` component (the iframe hosting `code-server`) fits well within the main content area. **Its styling should respect its role as the window to the core coding environment, which will be interacted with primarily via its own internal VSCodium features and the `code-server` extension(s) that the React shell will communicate with.**

## C. Develop Initial Shared UI Components (`libs/shared/ui-core`)

1.  **Setup Storybook for `ui-core`:**
    *   Command (run in workspace root `atlas-ide/`):
        ```bash
        nx generate @nx/react:storybook-configuration ui-core --generateStories --interactionTests=false
        ```
    *   Verify Storybook runs for the `ui-core` library:
        ```bash
        nx run shared-ui-core:storybook
        ```
    *   **Accessibility Addon:** Install and configure the `@storybook/addon-a11y` to enable accessibility checks directly within Storybook.

2.  **Create Basic Reusable Components:**
    *   Define and implement a few simple components in `libs/shared/ui-core/src/lib/`.
    *   For each component:
        *   Use MUI as the base where appropriate, styled with Tailwind CSS.
        *   Ensure they are exportable from the library.
        *   Create corresponding `.stories.tsx` files.
    *   **Example Components:**
        *   `StyledButton/Button.tsx`: A general-purpose button with variants (primary, secondary, text) using MUI `Button` styled further with Tailwind.
            *   `Button.stories.tsx`
        *   `Panel/Panel.tsx`: A container component (e.g., using MUI `Paper` or `Card`) for grouping content, with optional title.
            *   `Panel.stories.tsx`
        *   `LoadingSpinner/LoadingSpinner.tsx`: A simple loading indicator using MUI `CircularProgress`.
            *   `LoadingSpinner.stories.tsx`
    *   **Note on Component Design:** When designing these components, consider common clinical UI patterns, information density needs, and iconography relevant to healthcare applications. Ensure components are highly responsive and adhere to the established theme.

3.  **Export Components:**
    *   Ensure all new components are exported from `libs/shared/ui-core/src/index.ts`.

## D. Optimize Font Loading (if not completed in Step 1)

1.  **Implement Font Strategy:**
    *   Ensure the chosen font loading strategy (e.g., using `next/font` for Roboto) is implemented in `_app.tsx` or `Layout.tsx` to optimize performance and visual stability.

## E. Integrate and Test

1.  **Use Shared Components in Shell (Optional):**
    *   Optionally, replace some basic HTML elements or ad-hoc styled MUI components in `atlas-ide-shell` (e.g., in the placeholder `Header` or `Sidebar`) with the new components from `ui-core` to test integration.

2.  **Review Visuals and Responsiveness:**
    *   Run the `atlas-ide-shell` application (`nx serve atlas-ide-shell`).
    *   Check the overall layout and styling in a browser.
    *   Test responsiveness, **critically focusing on how all layout components (Header, Sidebar, Footer, main content area with `CodeServerView`) behave and appear at narrower widths (e.g., <= 600px) to simulate the Epic sidebar environment.**

---
This step aims to establish a clear visual structure for the application shell and kickstart the development of a reusable component library, which is essential for building out more complex features in subsequent steps.
