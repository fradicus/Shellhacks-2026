# F07: independent QA on the Mac Codex session

The user explicitly assigned this session F07 after reviewing the existing Windows
Codex data work and Claude app work. This Mac session adopts lane C, qa-verifier,
and owns only F07. The Windows F01 claim and Claude app claims remain unchanged.
No F07 PR existed at claim time. This feature-specific assignment records the
user's override of the earlier two-worker roadmap without editing shared files.

The golden verifier reads the sponsor workbook independently and obtains live core
output through a separate subprocess; its reference calculation imports no matcher
code. Browser checks use the production fixture build and the existing CI e2e job.
The UI's Evidence link is the pair navigation action; clicking its surrounding row
selects a map pair. Test both behaviors rather than changing F05's interaction.

Undo: close the F07 claim and explicitly reassign F07 before another worker starts.
