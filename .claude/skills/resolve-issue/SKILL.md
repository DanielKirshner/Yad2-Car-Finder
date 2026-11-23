---
name: resolve-issue
description: Take a GitHub issue of Yad2 Car Finder from reading it to an open pull request, with this repo's branch, commit and PR format. Use when asked to work on, fix or implement an issue, or to open a PR for one.
---

# Resolve an issue

1. **Read it**: `gh issue view <number> --comments`. Check which parts master already covers, since
   several issues overlap (#10 and #17, #11 and #12).
2. **Branch** from an up-to-date master: `git fetch origin && git checkout -b <type>/<number>-<slug> origin/master`
3. **Bug**: reproduce it first the way a user would hit it, and keep the evidence for the PR.
   **Feature**: if the issue leaves a decision open that is hard to undo (storage, a new service, a
   public interface), ask before building.
4. **Implement** per `.claude/CLAUDE.md`. Update `README.md` and `.claude/CLAUDE.md` if they became wrong.
5. **Check** it with the `verify` skill.
6. **Commit**: `<type>(<scope>): <imperative summary> (#<number>)`. No co-author line.
7. **Open the PR**:

   ```bash
   git push -u origin HEAD
   gh pr create --base master --title "<same as the commit>" --body-file <file>
   ```

   Body: `Closes #<number>`, then **Summary**, **Testing** (what ran, with results) and
   **Not covered** (parts of the issue left out, and why). If the PR only does part of the issue,
   write `Part of #<number>` instead, so merging does not close it.

Do not merge: the maintainer reviews and merges.
