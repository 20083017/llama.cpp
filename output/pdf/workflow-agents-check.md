Use the installed `i-have-adhd` skill. If unavailable, disclose that once and follow the concise presentation rules below without installing anything.

Perform a periodic, read-only health check of our shared workflow configuration: workflow, agents, skills, rules, and Husky/session setup.

Scope:
- Resolve the registered configuration repository through the existing `git claude` setup and inspect its current `main`.
- Check the current consumer checkout and the registered primary checkout if different. Inspect additional consumers only when named.
- Preserve repository files, branches, indexes, hooks, registration, and generated-rule receipts. Do not fix, refresh, delete, install, or rerun the upgrade plan.
- Use current evidence. Old commits, test counts, approvals, and HOLDs are historical references, not current results.

Complete these five checks continuously:

1. Repository identity
Confirm configuration ownership, main HEAD, checked-out branch, and working-tree state. Distinguish configuration Git from application Git. Bind findings and tests to the inspected main revision. If local files differ, use a temporary snapshot outside the repositories or mark the affected verification unavailable; do not switch branches.

2. Workflow and agents
Check the declared coordinator, referenced child roles, frontmatter, permissions, inheritance, and delegation limits. Verify that instructions support automatic progression within authorized scope, applicable review, internal result transfer, and resuming unfinished work with valid evidence. Identify contradictory instructions or unnecessary repeated approvals.

3. Rules and skills
Check relevant instruction consistency and applicability. C++ checks must use actual target paths, flags, and language standards. Testing and documentation commands must match the real project. Check obsolete references and removed mower rules, distinguishing documentation mentions from active rule files and proven runtime loading.

4. Focused validation
Run the existing relevant instruction, workflow-policy, and regression checks using the established runner. Keep generated test output outside the repositories. Report actual commands, counts, failures, and skips. Run each relevant check once; repeat only when a failure or changed input justifies it. Do not install missing tools.

5. Consumer and session readiness
Use supported check-only initializer commands. Inspect generated-rule receipts, stale outputs, Husky wiring, hook syntax, and CLI version/provenance.
Report these separately:
- Initializer readiness.
- Hook inspection versus actual execution.
- Fresh-session native loading.

Use safe native diagnostics when available. Otherwise mark the relevant dimension NOT VERIFIED. Resolve historical HOLDs against current evidence. Keep cleanup outside this audit.

Presentation:
Give brief progress as “Check N/5: result; next action.” Continue without asking between checks. Do not repeatedly print the plan.

Final response:
- Overall verdict: PASS, WARNING, or HOLD, with the inspected revision and consumer scope.
- One compact table covering the five checks, with evidence and explicit unverified dimensions.
- Up to three priority findings: impact, file/line or command evidence, and minimum suggested correction. State the count of any additional findings and retain their details.
- Exactly one concrete next action I can begin within two minutes. If nothing remains, say CHECK COMPLETE.

A clean branch or passing static tests does not prove fresh-session loading. Report only the readiness actually verified.

Also check legacy-worktree integration protection.

Shared workflow configuration is authoritative. Application integrations from older worktrees must exclude incoming changes to configuration paths already migrated to shared ownership.

1. Resolve the exact protected paths and ownership:
   `.claude/`, the actual Claude/agent instruction filenames, and `.worktree-policy.yml`. Verify spelling, case, and any registered equivalents. Do not automatically exclude unrelated nested project instructions.

2. Verify that the integration workflow preserves the pre-integration target state for those paths, including content, file type, references/symlinks, and absence. Previously removed files must not be resurrected. Preserve the actual shared configuration directory and local consumer state.

3. Verify protection covers clean merges as well as conflicts, including rebase, cherry-pick, and squash where supported. Neither `.gitignore` nor a global “ours” option is sufficient. Legitimate shared-configuration changes require a separate configuration task.

4. Require final candidate verification: protected application paths match the frozen target baseline, while intended application changes remain intact. Any squash tree-equality check must use the reviewed, filtered candidate. If the target has not completed migration, report that gap separately.

During this periodic audit, inspect this protection and its existing evidence only. Report missing protection as a finding; do not perform a merge, migration, cleanup, or configuration change.