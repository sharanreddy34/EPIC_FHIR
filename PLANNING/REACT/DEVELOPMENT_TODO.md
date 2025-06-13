# Atlas IDE Development Todo List

## Phase 0: Foundation Setup
- [ ] Initialize Nx monorepo structure
  - Create 'atlas-ide-shell' Next.js app
  - Set up workspace libraries (ui-core, fhir-utils, etc.)
  - Configure TypeScript and linting

- [ ] VSCodium Integration Setup
  - [ ] Set up code-server with VSCodium
  - [ ] Configure code-server communication layer
  - [ ] Create VSCodium wrapper component in React
  - [ ] Implement basic message passing between React and VSCodium

- [ ] Core UI Framework
  - [ ] Set up MUI with custom theme
  - [ ] Configure Tailwind CSS
  - [ ] Create base layout components for Epic sidebar constraints

## Phase 1: Core Infrastructure
- [ ] Basic UI Shell
  - [ ] Create VSCodium iframe container
  - [ ] Implement sidebar layout (≤600px width)
  - [ ] Add basic navigation components

- [ ] VSCodium Communication Layer
  - [ ] Implement useCodeServerComm hook
  - [ ] Set up message types for VSCodium interaction
  - [ ] Create basic editor control functions

- [ ] FHIR Integration
  - [ ] Set up Apollo Client for FHIR queries
  - [ ] Create patient context components
  - [ ] Implement basic FHIR data display

## Phase 2: AI Integration
- [ ] Core AI Features
  - [ ] Implement AI chat interface
  - [ ] Add ghost text support in VSCodium
  - [ ] Create code context display
  - [ ] Build command palette

- [ ] VSCodium-AI Bridge
  - [ ] Set up code analysis pipeline
  - [ ] Implement multi-file diff viewing
  - [ ] Create AI suggestion system

- [ ] FHIR-AI Integration
  - [ ] Add FHIR schema awareness to AI
  - [ ] Implement AI-powered FHIR queries
  - [ ] Create FHIR-aware code suggestions

## Phase 3: Advanced Features
- [ ] Enhanced UI/UX
  - [ ] Optimize VSCodium performance in sidebar
  - [ ] Improve navigation and context switching
  - [ ] Add advanced UI animations and transitions

- [ ] FHIR-Aware Development Tools
  - [ ] Implement FHIR code generation
  - [ ] Add FHIR debugging tools
  - [ ] Create FHIR snippet library

- [ ] ServiceRequest Integration
  - [ ] Build ServiceRequest components
  - [ ] Implement AI actions for ServiceRequests
  - [ ] Add task-based code generation

## Final Steps
- [ ] Testing & Validation
  - [ ] Unit tests for React components
  - [ ] Integration tests for VSCodium communication
  - [ ] End-to-end testing of AI features
  - [ ] FHIR integration testing

- [ ] Documentation
  - [ ] API documentation
  - [ ] VSCodium integration guide
  - [ ] FHIR feature documentation
  - [ ] Deployment guide

- [ ] Performance & Security
  - [ ] Optimize VSCodium load time
  - [ ] Security audit of communication layers
  - [ ] HIPAA compliance verification
  - [ ] Performance testing in Epic environment

## Notes
- All UI components must work within Epic's 600px sidebar constraint
- VSCodium integration via code-server is the core foundation
- React frontend provides the shell and enhanced features
- AI features should seamlessly integrate with VSCodium
- FHIR awareness should be maintained throughout all features
