# PHASE_01_FOUNDATION.md

OBJECTIVE

Build the foundation for future protein preparation intelligence without changing existing docking behavior.

TASKS

## 1. Documentation Framework

Create:

docs/
docs/developer/
docs/architecture/
docs/changelog/

Files:

docs/ARCHITECTURE_DECISIONS.md
docs/DEVELOPER_GUIDE.md
docs/PHASE_STATUS.md
docs/architecture/system_overview.md

Requirements:

* Add Mermaid diagrams.
* Document current architecture.
* Document docking workflow.
* Document AI workflow.
* Document API flow.

---

## 2. AI Provider Manager

Create:

services/ai/

Implement:

AIProviderManager

Providers:

* Groq
* Gemini
* OpenRouter
* DeepSeek

Environment Variables:

GROQ_API_KEY
GEMINI_API_KEY
OPENROUTER_API_KEY
DEEPSEEK_API_KEY

Configuration:

DEFAULT_FAST_PROVIDER
DEFAULT_REASONING_PROVIDER
FALLBACK_CHAIN

Requirements:

* Automatic provider failover.
* Provider health checks.
* Logging.
* Structured responses.

---

## 3. AI Recommendation Framework

Create interfaces only.

No UI yet.

Implement:

recommend_chain()
recommend_pocket()
recommend_waters()
recommend_cofactors()
recommend_metals()

Return:

recommendation
confidence
reasoning

---

## 4. Architecture Safety

Before modifying any file:

* Identify existing implementation.
* Avoid duplicate services.
* Preserve backward compatibility.

DELIVERABLES

* Working AIProviderManager
* Gemini integration
* Documentation system
* ADR framework
* PHASE_STATUS.md
* Tests
