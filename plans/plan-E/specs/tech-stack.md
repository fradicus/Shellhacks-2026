# Shared engineering decisions

## Existing foundation
Next.js/React/TypeScript for one web app; Python batch ingestion and canonical matching; JSON Schemas and golden fixtures across both languages; MongoDB Atlas for sources, versioned projects, matches, reviews, runs and briefs. Gemini extracts approved pages and drafts supported briefs.

## Visual layer
MapLibre + OpenFreeMap provide the geographic base. Direct Three.js runs inside a MapLibre custom layer, sharing camera/context. Client-only loading; pin a tested compatible dependency set during implementation. No extra API key. UI selection, camera, date-height and hypothetical scenarios cannot alter authoritative coordinates or matches.

Render selected/local project date markers; aggregate actual overview records. Add no fabricated transmission network, power-flow simulation, photorealistic substations or unrestricted source-fetch/upload route. Preserve attribution, accessible table, reduced motion and WebGL-failure fallback.

## Scaling
The hackathon corpus keeps canonical all-pairs matching. National rollout requires source-specific adapters, legal-owner aliases, effective dates, source scope/coverage records and cross-source duplicate resolution. Before spatial candidate retrieval replaces all-pairs, QA proves recall against a complete reference at region seams and the strict threshold. Planning regions organize sources; they cannot partition away valid pairs.

Keep actual geographic coordinates separate from projected positions and Alaska/Hawaii insets. Flag antimeridian endpoint cases for center-rule review. Month/year-only dates stay uncertain and receive no fabricated exact vertical position.

## Deployment and access
Existing server-only Gemini, scoped Atlas RO/RW and operator-route token arrangements remain. Three.js adds no account or secret. Hosting/Atlas egress is still an early gate. No provider version or performance outcome is claimed tested by this plan.
