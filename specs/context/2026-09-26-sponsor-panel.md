# Sponsor panel — notes

September 26, 2026 · Sperrytech / Dakota Matting

## Main takeaways

- Clean, well-understood data is a prerequisite for useful automation. Their team still spends substantial time
  checking sources and organizing inputs.
- Build with the people who will use the product. Small, frequent improvements help establish trust and adoption.
- Field conditions should shape the interface: simple interactions, clear information, and little time spent
  operating software.

## Data and automation

- The team described roughly 9–10 years of internal data, including PDFs, emails, and structured records. About
  five years are in Microsoft Dataverse.
- Business expertise helps the engineers interpret historical patterns and decide whether they apply to new projects.
- Much of their tooling is developed internally for their particular workflows.
- They emphasized preserving data quality and checking database results before relying on downstream outputs.
- This internal dataset belongs to the sponsor; our project does not currently have access to it.

## Maps, imagery, and site access

- Their construction work involves assessing vegetation, water, soil conditions, and access routes.
- Utilities may provide Google Earth files or PDFs. The team uses mapping tools and is exploring multimodal models
  to interpret the material.
- Old imagery and outdated plans can miss current obstacles, including buildings in a proposed route.
- Fresh imagery can be expensive or poorly suited to a long, narrow construction corridor.
- Getting trucks and equipment into and out of a site is an important part of the planning problem.

## Estimating workflow

- They are testing document tools to help estimators assess whether a job is worth pursuing before a site walk-down.
- Internal SOPs and construction knowledge provide context for interpreting job specifications.
- This was described as work in progress, rather than a fully deployed automated decision process.

## Adoption and product development

- A previous estimating system struggled with adoption after being designed without enough involvement from its users.
- Their current approach includes visiting job sites, getting regular feedback, and shipping small improvements frequently.
- Users who help shape a tool can help introduce it to colleagues.
- Field crews work in difficult conditions. Software needs to solve an immediate problem with minimal friction.
- The panel recommended focusing on one customer's problem and learning from actual use before broadening the product.

## Engineering and team practices

- Their operational stack includes Power Apps, Power Automate, and Dataverse.
- Safe development environments let engineers learn and test without disrupting production data.
- Production changes affect an operating construction business and need careful verification.
- The team emphasized ownership, admitting mistakes, staying calm when problems occur, and learning unfamiliar tools.
- Leadership encouraged field exposure and adaptability across technical and business roles.

## Implications for GridBridge

- Validate the workflow with a real project manager and a concrete project.
- Keep source evidence and uncertainty close to the result.
- Prioritize a small useful task over a large collection of loosely connected features.
- Treat imagery-based analysis and historical prediction as areas to investigate, with their own evidence requirements.

These are discussion notes. Examples and estimates reflect what the panel described; they are not independently
verified measurements. Product choices are recorded separately in [C16](../decisions/C16-sponsor-context.md).
