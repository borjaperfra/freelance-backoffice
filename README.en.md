# Freelance Backoffice

A freelancer's back office that lives in a GitHub repo, with your coding agent as the office assistant.

Clients, projects, proposals, invoices, expenses and quarterly tax returns are JSON and PDF files in your private repo. You tell your coding agent (Claude Code, Pi, Codex, OpenCode…) what happened ("invoice Acme for Phase 1", "log this expense", "close Q4") and it does the work through this repo's skills. A minimal web admin shows everything, and your clients see their proposal or project in a private space, each person with their own revocable link.

Projects that run in phases get their own view: phases, deliverables as folders, Markdown documents rendered as slides or long reads with their PDF, decisions, tests and a chaptered summary. You can share the whole thing with the client, read-only. See [docs/trabajo.md](docs/trabajo.md) (in Spanish).

It runs on the free plans of Cloudflare Pages and GitHub Actions. No database, no SaaS account: if you stop using it, you keep your files.

**Spain only, for now.** The tax rules built in are Spanish (VAT, IRPF withholding, forms 303 and 130), and the interface and skills are in Spanish. The core (clients, projects, client spaces, expenses with receipts) is country-agnostic, and tax packs for other countries are welcome as contributions.

To check your setup at any time, run `python backoffice.py doctor`. To get new versions, `python backoffice.py actualizar`: it updates the code and never touches your `datos/` folder.

**Melso.** If your taxes are handled by [Melso](https://melso.ai), the online accounting firm, the back office sends them your expenses (with the PDFs), the invoices you issue and your payments through Melso's MCP server, and compares its VAT estimate with theirs. Invoices are still issued here, and it never issues invoices, files taxes or deletes anything in Melso. It hasn't been tried with a real Melso account yet. See [docs/melso.md](docs/melso.md) (in Spanish).

See the Spanish [README](README.md) for features, setup and the disclaimer: this is not tax advice, figures are estimates to review with your accountant, and Verifactu compliance is the user's responsibility.

The agent instructions live in `CLAUDE.md` and the skills in `.claude/skills/`. Agents that read `AGENTS.md` (Codex, Pi, OpenCode…) find there where everything is.

MIT licensed. Made by [@borjaperfra](https://github.com/borjaperfra).
