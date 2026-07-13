# Frontend Structure

Chemistry Companion employs a unique, lightweight frontend architecture that avoids the complexity of Node.js, Webpack, or large Single Page Application (SPA) frameworks like React or Angular.

## Core Technologies
1. **Jinja2**: Server-side HTML templating handled by FastAPI. Base layouts and structural components are rendered on the server before reaching the browser.
2. **HTMX**: Enables SPA-like behavior (dynamic partial page updates) using simple HTML attributes (`hx-get`, `hx-post`, `hx-swap`). It connects the UI directly to FastAPI endpoints without writing custom JavaScript fetch logic.
3. **Alpine.js**: Handles complex, localized client-side state. Used extensively in interactive modules (like the Docking Wizard) where state needs to persist across multiple steps without hitting the server.
4. **TailwindCSS**: Utility-first CSS framework for rapid UI styling.
5. **Mol***: High-performance 3D WebGL viewer for rendering protein and ligand structures (`molstar.js`).

## Key Workspaces

### Docking Workspace (`templates/docking_workspace.html`)
This is the most complex UI component in the application. It acts as a 7-step wizard for protein docking.
- **State Machine**: Powered by an Alpine.js component (`x-data="dockingWorkspace()"`). It tracks:
  - `step`: The current wizard step (1 to 7).
  - `proteinAnalysis`, `proteinPdbqt`, `ligandPdbqt`: Data payloads returned from the backend.
  - `grid`: The bounding box parameters.
  - `showPockets`, `showGridBox`: UI toggles for the 3D viewer.
- **Mol* Integration**: The workspace initializes a Mol* instance and binds it to a container (`#protein-preview-viewer`). Alpine.js watches state variables and triggers Mol* plugin commands to highlight residues, pockets, and grid boxes dynamically.

### Dashboard (`templates/dashboard.html`)
A unified launchpad utilizing HTMX. It dynamically swaps the main content area with different workspace templates (Docking, Spectra, etc.) when the user clicks navigation links, providing seamless transitions without full page reloads.

## Best Practices
- **Do not introduce heavy JS frameworks**. Keep the architecture aligned with HTMX and Alpine.
- **Handle errors gracefully**. Alpine components include specific `try/catch` logic to catch FastAPI 422/500 errors and display them in localized alert banners.
