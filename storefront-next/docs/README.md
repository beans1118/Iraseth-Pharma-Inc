# Storefront documentation

The active storefront is integrated with the existing Flask catalog, inquiry workflow and reference tracking. Use [the current application README](../README.md), [repository verification checklist](../../docs/GITHUB-REVIEW-CHECKLIST.md), [local commit review](../../docs/LOCAL-COMMIT-REVIEW.md) and [staging deployment plan](../../docs/STAGING-DEPLOYMENT-PLAN.md) for setup and release instructions.

- [Public catalog contract](PHASE2_API_CONTRACT.md): public field boundaries, availability and pricing contract.
- [Order inquiries](ORDER_INQUIRIES.md): My Order submission and employee workflow.
- [Content provenance](CONTENT_PROVENANCE.md): source company content/images and publication approvals still required.
- [UI refinement history](UX_REFINEMENT_AND_NEXT_STEPS.md): earlier design notes; assess proposals against the current implementation before acting.

The early Phase 1 scaffold limitations have been superseded: the catalog, submissions, tracking, gallery, lockfile and backend integration now exist. Do not follow old scaffold instructions to create another branch, copy this app into another repository, remove the directory to roll back, use mock products or build the old `storefront/` pipeline. Real secrets and MongoDB business records do not belong in this Git snapshot. The contact form's external-delivery behavior, company claims and external hero-image rights still require the explicit checks recorded in the deployment/provenance documents.
