# C8: hand off the remaining loader corrections

On 2026-09-26 the user explicitly confirmed that the remote Claude worker had stopped. No active F06 PR remained. Windows Codex takes F06 corrective ownership to finish issue 66 (current audit decisions) and issue 43 (F12 current-fact hash integration). The feature remains lane B / technical-lead, with isolated worktree claims and normal CI/ownership checks. Its original delivery and completion marker remain intact.

This changes only the local worker assignment, not product schemas, algorithms, service credentials or the running mode. F12 remains the active Windows implementation; F06 source edits begin after F12 is merged. The correction uses GPT-5.6 Sol high with independent Astra review. Other completed feature assignments are unchanged. The shared claim is recorded on issue 66.

The user also requested expedited completion. Optional F17 is not being started. Existing source, audit, live-service deferral and merge gates remain in force; this handoff does not waive checks. A future reassignment must again establish that the old worker has stopped and record the new owner.

The user requested completion now rather than further optional work. The roadmap and F18 spec therefore allow an earlier final handoff only after every non-stretch implementation feature/core correction is verified complete (or an allowed cut is explicitly recorded) and final integration passes. F18 remains the final report/STOP/marker step. User-deferred live services stay visibly deferred; F17 need not start. This resolves the prior rule that would require an otherwise completed run to wait for the clock. The scheduled report gate remains the latest reporting target and the hard stop is unchanged.
