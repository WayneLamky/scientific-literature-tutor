---
name: scientific-literature-tutor
description: Create a figure-by-figure, evidence-aware interactive reading experience for a scientific paper. Use when the user asks to 精读论文、逐图讲文章、解释每张 Figure、梳理论文验证逻辑、制作中英双语科研论文 HTML 教程，or build a reusable article-reading workflow from a PDF. The workflow inspects the full paper, crops original figures, distinguishes data construction from model validation, explains how every panel was generated and read, flags inconsistencies and limitations, and produces a standalone interactive HTML reader.
---

# Literature Tutor

Turn a scientific paper into a teachable, auditable, figure-by-figure interactive reader. The goal is comprehension, not a decorative summary.

## Required outcome

Produce both:

1. A standalone HTML reader that remains useful after the conversation.
2. A concise conversational handoff that tells the user where to begin and invites questions by figure or panel.

The generated reader may include the optional GPT tutor drawer and local
Obsidian capture. The core reader must still work when either service is
unavailable, and API keys or vault paths must never be embedded in generated
HTML.

Unless the user asks otherwise, explain in Chinese and preserve important English scientific terms beside their Chinese translations.

## Workflow

### 1. Inspect the complete source

- Read the entire PDF text, including title, abstract, introduction, results, discussion, methods, figure legends, supplementary references, data availability, and conflicts of interest.
- Render and visually inspect every page containing a main figure. Do not infer panel meaning from extracted text alone.
- Record the paper's central question, hypothesis, sample hierarchy, experimental units, inputs, outputs, labels, training procedure, validation procedure, and statistical tests.
- Treat claims in the paper as claims, not automatically as established facts.

### 2. Build an evidence map before writing

Create a private working map containing:

- `question`: what problem the paper tries to solve;
- `hypothesis`: what must be true for the approach to work;
- `samples`: biological donors, experimental conditions, repeated measurements, technical replicates, and the actual independent unit;
- `X`: predictors or measurements available at prediction time;
- `Y`: targets or ground truth and how they were measured;
- `model`: transformations, feature selection, algorithms, and baselines;
- `validation`: exact split unit, leakage risks, metrics, and external validation status;
- `claims`: which figure supports each major claim;
- `limits`: what the design cannot establish.

Never call dataset construction “validation.” Separate these two stages explicitly.

### 3. Extract original figures

- Crop the original main figures from rendered PDF pages. Exclude surrounding article text when practical.
- Keep enough resolution for axes, legends, and panel labels to remain readable.
- Use `scripts/extract_figures.py` with a JSON crop manifest when convenient.
- Label original paper figures as source figures. Label any newly drawn schematic as an explanatory reconstruction.
- Do not alter quantitative values in source figures.

### 4. Explain every main figure with the same logic

For every figure, include:

1. **本图回答什么 / Question**
2. **数据怎么来的 / Data provenance**
3. **图怎么读 / Reading guide** — panels, axes, colors, lines, bars, units, and sample mapping
4. **看到了什么 / Observation**
5. **作者因此主张什么 / Claim**
6. **本图不能证明什么 / Limitation**
7. **中英术语 / Glossary**

Explain the causal and validation logic in plain language. When useful, add a small teaching diagram, a numerical example, or a “blue line versus red line” exercise. Do not replace the source figure with a workflow-only diagram.

### 5. Audit the paper while teaching it

Explicitly flag:

- donor count versus donor-condition samples;
- biological versus technical replicates;
- missing data and failed experiments;
- internal cross-validation versus held-out external cohorts;
- split-unit leakage, including repeated samples from the same donor;
- baseline choice and whether metrics outperform it;
- multiplicity, uncertainty, error bars, and statistical assumptions;
- conflicting statements between prose, tables, captions, and figures;
- commercialization, patent, or funding conflicts relevant to interpretation.

Use calibrated wording: “supports,” “is consistent with,” or “suggests” when the experiment does not establish causality or generalizability.

### 6. Build the HTML reader

- Read `references/content-schema.md` before preparing the reader specification.
- Store paper-specific content in a UTF-8 JSON spec instead of hard-coding it into the renderer.
- Use `scripts/build_reader.py SPEC OUTPUT.html` to create a self-contained HTML file with embedded images.
- Include a navigation rail, reading progress, a paper-level logic chain, figure sections, bilingual terminology, knowledge checks, and an evidence-audit section.
- Include the GPT tutor drawer when requested. Use `scripts/serve_reader.py` as
  the loopback-only proxy. It launches `codex app-server` and reuses the user's
  current ChatGPT/Codex subscription login; do not request an OpenAI API key or
  describe this mode as API-billed. Attach only the active section and selected
  text, and instruct the model to separate paper evidence from general knowledge.
- When the user wants Obsidian integration, read
  `references/obsidian-integration.md`, configure the vault outside the HTML,
  and save question, answer, reading position, user note, tags, and a stable
  block ID to the paper note. If the user says Obsidian is already open, resolve
  the active vault from Obsidian's vault registry or app state without reading
  note bodies; ask only when multiple open vaults remain ambiguous. Never inspect
  unrelated note contents.
- Make the page responsive and keyboard-readable. Avoid external fonts, CDNs, and network dependencies.

### 7. Verify before delivery

- Open or render the final HTML and inspect the top, at least one middle figure, the validation section, and the final summary.
- Confirm every main figure is present and legible.
- Confirm all interactive controls work without network access.
- If Obsidian capture is enabled, save one realistic response twice and confirm
  the second request is deduplicated, the Markdown parses, and the returned
  `obsidian://` link targets the saved block.
- Confirm the paper title, authors, year, figure numbering, sample counts, metrics, and claims match the source.
- Run `python3 scripts/validate_spec.py SPEC` and fix all reported errors.

## Teaching style

- Begin with the scientific question, not with software or laboratory steps.
- Use concrete mappings such as `早期形态 X → 数周后的分化能力 Y`.
- Translate jargon at first use, then keep the English term in parentheses.
- State one key takeaway per figure before adding detail.
- Invite follow-up questions by figure and panel, for example “Figure 3C 为什么要除以 pellet size？”
- Do not hide weaknesses to make the paper feel cleaner. Understanding the weakness is part of understanding the paper.

## Files

- `scripts/build_reader.py`: render a standalone HTML reader from a JSON spec.
- `scripts/extract_figures.py`: crop figures from rendered pages using a manifest.
- `scripts/validate_spec.py`: check structure, source assets, and required teaching fields.
- `scripts/serve_reader.py`: serve readers locally and proxy optional GPT tutor requests without exposing the API key to browser code.
- `references/content-schema.md`: specification fields and authoring rules.
- `references/obsidian-integration.md`: local vault configuration, note schema,
  safety boundaries, and verification steps.
