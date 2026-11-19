# Documentation index

Use these documents as the current entry points. Earlier reports retain their original results and approval history; they are not instructions to repeat imports or apply historical pending actions.

| Task | Current document |
| --- | --- |
| Install, configure, seed, run and test the local Flask/dashboard/storefront system | [DEVELOPER-SETUP.md](../DEVELOPER-SETUP.md) and [setup verification](LOCAL-SETUP-REPORT.md) |
| Prepare isolated staging, API origins, Atlas, SMTP, health checks and deployment order | [STAGING-DEPLOYMENT-PLAN.md](STAGING-DEPLOYMENT-PLAN.md) and [environment templates](staging/) |
| Review source and run verification before GitHub | [GITHUB-REVIEW-CHECKLIST.md](GITHUB-REVIEW-CHECKLIST.md) |
| Reviewed local release snapshot, exclusions, security scope and latest full-suite results | [LOCAL-COMMIT-REVIEW.md](LOCAL-COMMIT-REVIEW.md) |
| Cleanup outcome, exact changes, retained dependencies and current test results | [REPOSITORY-CLEANUP-REPORT.md](REPOSITORY-CLEANUP-REPORT.md) |
| End-to-end local UAT procedure and service limitations | [LOCAL-UAT-REPORT.md](LOCAL-UAT-REPORT.md) |
| Current PDF image results, exact mappings and unresolved placeholders | [product-images/REPORT.md](product-images/REPORT.md) |
| Existing-product import procedure and identity restrictions | [pdf-products/EXISTING-PRODUCTS-PROCEDURE.md](pdf-products/EXISTING-PRODUCTS-PROCEDURE.md) and [integration report](pdf-products/INTEGRATION-REPORT.md) |
| Original PDF, manifest, review decisions and media | [brochure/](brochure/) |
| Legacy dependency evidence before this cleanup | [LEGACY-CLEANUP-AUDIT.md](LEGACY-CLEANUP-AUDIT.md) |
| Earlier backend design and safety history | [history/DEVELOPMENT-PHASE1-3-README.md](history/DEVELOPMENT-PHASE1-3-README.md) |
| Storefront API contracts, content provenance and inquiry workflow | [../storefront-next/docs/README.md](../storefront-next/docs/README.md) |

Brochure source media, CSV/JSON review and import metadata, approved WebPs and image plans remain at their existing paths because tools and tests read them. Historical UAT screenshots/logs and operation reports are retained as evidence rather than merged into current instructions. No source record or image should be removed as an apparently duplicate report artifact without checking its consumers.

The reviewed Git snapshot includes essential JSON audit summaries and source media. Regenerable browser screenshots are retained locally and ignored; historical report links to those screenshots describe optional local evidence, not files promised in a fresh clone. Rerun the isolated browser UAT to regenerate them. See [the exact staging/exclusion manifest](final-commit-verification/STAGING-MANIFEST.json).
