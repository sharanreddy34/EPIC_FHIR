# Atlas IDE Frontend Development Executive Summary

## Vision & Project Overview
Atlas IDE reimagines healthcare software development by bringing AI-powered coding directly into the clinician's workflow. We're building a React frontend that wraps VSCodium (open-source VS Code) via code-server, embedding it directly in Epic's EMR sidebar. This gives clinicians a familiar, powerful development environment where they can code while maintaining full context of their patient's data. By combining VSCodium with Cursor.sh-like AI capabilities and Epic's SMART-on-FHIR platform, we create an intelligent development environment that understands both code and healthcare data.

### Key Differentiators
- **Contextual Intelligence**: The IDE understands both the code being written and the patient context from Epic
- **Healthcare-First Design**: Built specifically for clinician-developers working with FHIR data
- **Seamless Integration**: Lives directly in Epic's sidebar, no context switching needed
- **AI Pair Programming**: Provides intelligent code suggestions based on both code context and patient data

### User Experience
When a clinician opens Atlas IDE in Epic's sidebar, they'll see:
1. A modern, VS Code-like editor interface optimized for the narrow sidebar width
2. Patient context always visible and informing the AI
3. Intelligent code completion that understands FHIR schemas
4. An AI chat interface that can explain code in healthcare terms
5. Real-time access to patient data for testing and development

## Tech Stack
- **Core Framework**: Next.js
- **Monorepo Management**: Nx
- **UI Components**: Material-UI (MUI)
- **Styling**: Tailwind CSS
- **State Management**: 
  - UI State: Zustand
  - Server State: TanStack Query (React Query)
- **Language**: TypeScript

## Technical Architecture & Development Phases

### System Architecture
```
                                Palantir Foundry (FHIR Data)
                                     ^
                                     |
                                     v
┌─ FastAPI Backend Proxy ──────────┐  ┌─ LLM Service(s) ──────────┐
│ - FHIR Data Orchestration      │<===>│ - Code Gen/Analysis      │
│ - LLM Request Handling         │  │ - Chat Completion        │
│ - Code-Server Auth/Proxy (opt) │  │ - FHIR-Aware Logic       │
│ - Business Logic               │  └──────────────────────────┘
└───────────────┬────────────────┘
                ^
                |
                v
┌─ Epic EMR ───────────────────────────────────────────────────────────┐
│  ┌─ Sidebar (≤600px) ──────────────────────────────────────────────┐  │
│  │ ┌─ Atlas IDE Shell (Next.js React App) ───────────────────────┐ │  │
│  │ │  - UI Components (MUI/Tailwind)                             │ │  │
│  │ │  - State Management (Zustand/TanStack Query)                │ │  │
│  │ │  - Communication with FastAPI Backend                      │ │  │
│  │ │                                                             │ │  │
│  │ │ ┌─ Embedded code-server ─────────────────────────────────┐ │ │  │
│  │ │ │  - VSCodium Instance                                  │ │ │  │
│  │ │ │  - Monaco Editor Core                                 │ │ │  │
│  │ │ │  - Communication with Next.js Shell & FastAPI Backend │ │ │  │
│  │ │ └───────────────────────────────────────────────────────┘ │ │  │
│  │ │                                                             │ │  │
│  │ │ ┌─ Integrated AI Tools (React Components) ───────────────┐ │ │  │
│  │ │ │  - AI Chat View                                       │ │ │  │
│  │ │ │  - Ghost Text Display                                 │ │ │  │
│  │ │ │  - Diff Viewer, Command Palette, etc.                 │ │ │  │
│  │ │ └───────────────────────────────────────────────────────┘ │ │  │
│  │ └───────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Backend: FastAPI Proxy

The backend is a crucial component, built with FastAPI (Python). It serves several key purposes:

1.  **FHIR Data Orchestration**: It acts as a secure proxy to Palantir Foundry, fetching and (potentially) transforming FHIR data needed by the IDE. This keeps direct Foundry interactions server-side.
2.  **LLM Interaction Gateway**: All requests to Large Language Models (for chat, code generation, analysis, etc.) are routed through the FastAPI backend. This allows for centralized prompt engineering, context management, and potentially caching or logging of LLM interactions.
3.  **Business Logic Layer**: Any complex logic that shouldn't reside in the frontend (e.g., advanced data processing, specific AI workflow management) can be handled here.
4.  **`code-server` Orchestration (Potential)**: It may handle aspects of `code-server` lifecycle management or act as an authentication/authorization proxy for `code-server` communications, enhancing security.
5.  **API for Frontend**: Provides well-defined RESTful or GraphQL endpoints for the Next.js React frontend to consume, abstracting away the complexities of interacting directly with Foundry or LLMs.

## Development Phases

### Foundation (Step 0) - Building the Core
This critical phase establishes the foundation that enables all future features:
- Initialize Nx monorepo with Next.js app ('atlas-ide-shell')
- Setup core libraries: ui-core, fhir-utils, core-hooks, core-state, core-graphql
- Configure MUI, Tailwind, and basic layout components
- Establish code-server integration foundation with VSCodium

### Phase 1: Core Infrastructure (Steps 1-3) - Making it Real
Establishing the fundamental user experience:
1. Basic UI Shell & Navigation
2. code-server Integration & Communication
3. FHIR Data Layer & Patient Context

### Phase 2: AI Features (Steps 4-6) - Adding Intelligence
Transforming the IDE into an AI-powered coding companion:
4. Core AI Features:
   - Advanced AI Chat
   - Ghost Text (Initial)
   - Code Context Display
   - Command Palette
5. Enhanced AI Features:
   - Multi-file Diff View
   - Improved Ghost Text
6. FHIR-AI Integration:
   - FHIR Schema Integration
   - AI-powered FHIR Queries

### Phase 3: Advanced Features (Steps 7-9) - Elevating the Experience
Delivering sophisticated healthcare-specific capabilities:
7. Advanced UI & UX:
   - Enhanced Sidebar
   - Improved Navigation
   - Performance Optimizations
8. Intelligent FHIR-Aware Features:
   - FHIR-Contextual Code Generation
   - AI-Powered FHIR Debugging
   - Smart Snippets
9. ServiceRequest Integration:
   - ServiceRequest UI Components
   - AI Action Registry
   - Task-based Code Generation

## Key Technical Considerations & Challenges

### Epic Integration Challenges
- Working within 600px sidebar width constraint
- Maintaining performance within Epic's environment
- Managing state between Epic context and IDE
- Handling Epic session management

### AI Integration Complexity
- Ensuring AI responses are healthcare-context aware
- Managing real-time code suggestions in narrow UI
- Balancing AI feature performance with sidebar constraints
- Handling sensitive PHI data with AI features

### Security & Compliance
- HIPAA compliance throughout
- CSP implementation
- Secure code-server communication
- PHI handling guidelines

### Performance
- Optimized for Epic sidebar constraints (≤600px)
- Code splitting and lazy loading
- Efficient state management
- Strategic caching with react query Client

### Accessibility
- WCAG 2.2 AA compliance
- Healthcare-focused UI/UX
- Keyboard navigation support
- Screen reader optimization

## Development Workflow
1. Component Development (Storybook)
2. TypeScript & Linting
3. Testing (Unit, Integration, A11y)
4. Security Review
5. Performance Testing
6. Deployment & Integration Testing

## Timeline & Dependencies
Each phase builds upon previous phases, with continuous integration and testing throughout. The foundation phase is critical for establishing the core architecture that enables all subsequent features.

## Next Steps
1. Initialize Nx monorepo and core configuration
2. Establish development environment and workflows
3. Begin foundation phase implementation
4. Regular review points for technical alignment and course correction
