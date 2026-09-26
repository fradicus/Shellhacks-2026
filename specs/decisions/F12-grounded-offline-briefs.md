# F12: grounded briefs with deferred live execution

The user explicitly deferred live Gemini execution. Implement the optional live pipeline and strict validators,
while the committed run makes zero calls, records a null model and unavailable status, and preserves existing briefs.
Offline response fixtures are explicitly synthetic; there are no recorded production Gemini responses.
F12 owns the pure current-fact hash helper; the F06 owner wires it into staging through issue #43.
Runtime: Codex, GPT-6 Astra high; logical role: Gemini engineer. No shared contracts are changed.
