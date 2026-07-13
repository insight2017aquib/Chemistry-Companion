# Research Tools: Feature Cross-Reference Matrix

This matrix provides a high-level overview of the health, completeness, and integration status of the Research Tools subsystem components.

**Legend:**
- `✓` Implemented
- `△` Partial / Stubbed
- `✗` Missing
- `⚠` Broken
- `○` Not Required

| Component | Frontend | Backend | API | Database | AI | Export | Visualization | External Tools | Tests | Documentation | Integration Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Virtual Screening** | ✓ | ✓ | ✓ | ✓ | ✓ | ○ | ✓ | ✓ | △ | ✓ | ✓ |
| **MedChem Workbench** | △ | △ | ✓ | ✓ | △ | △ | △ | ✓ | △ | ✓ | △ |
| **ADMET & Developability**| △ | △ | ✓ | ✓ | △ | ○ | △ | ✓ | ✗ | ✓ | △ |
| **Lead Optimization** | △ | △ | ✓ | ✓ | △ | ○ | △ | ○ | ✗ | ✓ | △ |
| **Research OS** | ✓ | ✓ | ✓ | ✓ | △ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| **Publication Assistant** | △ | ✓ | ✓ | ✓ | △ | ✓ | ○ | ✓ | ✓ | ✓ | △ |
| **Knowledge Engine** | △ | ⚠ | ✓ | ✓ | △ | ○ | ○ | ○ | ✓ | ✓ | ⚠ |

### Notes on Status:
- **Frontend & Visualization (△):** MedChem, ADMET, Lead Optimization, and Publication Assistant currently rely on mocked data or hardcoded scripts in their UI templates for visualizations (e.g., Chart.js data points) or traceability viewers.
- **Backend (△):** MedChem relies on rudimentary Matched Molecular Pair (MMP) detection. ADMET heuristics are basic.
- **AI (△):** Most AI integration layers route to Expert services, but several of these appear to be prompt stubs missing robust provider integration or fallback logic (unlike Virtual Screening which is fully wired).
- **External Tools (✓):** Effectively integrates RDKit, AutoDock Vina, python-docx, and the Crossref API.
- **Knowledge Engine (⚠):** The Knowledge Miner backend is a rudimentary proof-of-concept; it hardcodes string matching for "solubility" rather than performing true semantic extraction, rendering its integration status broken.
