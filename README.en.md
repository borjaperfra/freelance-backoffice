# Freelance Backoffice

A freelancer's back office that lives in a GitHub repo, with Claude Code as the office assistant.

Clients, projects, proposals, invoices, expenses and quarterly tax returns are JSON and PDF files in your private repo. You tell Claude Code what happened ("invoice Acme for Phase 1", "log this expense", "close Q4") and it does the work through this repo's skills. A minimal web admin shows everything, and your clients see their proposal or project in a private space, each person with their own revocable link.

It runs on the free plans of Cloudflare Pages and GitHub Actions. No database, no SaaS account: if you stop using it, you keep your files.

**Spain only, for now.** The tax rules built in are Spanish (VAT, IRPF withholding, forms 303 and 130), and the interface and skills are in Spanish. The core (clients, projects, client spaces, expenses with receipts) is country-agnostic, and tax packs for other countries are welcome as contributions.

To check your setup at any time, run `python backoffice.py doctor`. To get new versions, `python backoffice.py actualizar`: it updates the code and never touches your `datos/` folder.

See the Spanish [README](README.md) for features, setup and the disclaimer: this is not tax advice, figures are estimates to review with your accountant, and Verifactu compliance is the user's responsibility.

MIT licensed.
