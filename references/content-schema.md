# Interactive paper reader content schema

The renderer accepts one UTF-8 JSON object. Paths in the spec are resolved relative to the spec file.

## Top-level fields

- `paper`: object with `title`, `subtitle`, `authors`, `journal`, `year`, `doi`, `source_pdf`, and optional `kicker`.
- `thesis`: one-sentence Chinese explanation of the paper.
- `logic_chain`: ordered array of objects with `label`, `en`, and `text`.
- `sample_audit`: array of `{label, value, note}` objects.
- `figures`: ordered array of figure objects described below.
- `validation`: object with `title`, `summary`, `steps`, `metrics`, and `audit`.
- `takeaways`: array of short conclusions.
- `questions`: array of `{q, a}` knowledge checks.
- `glossary`: array of `{zh, en, note}` terms.
- `source_note`: source and copyright note shown in the footer.

The renderer also embeds the specification as read-only GPT tutor context. No
API key or secret belongs in the specification. The optional tutor connects to
the local `/api/chat` proxy provided by `scripts/serve_reader.py`; without that
service, the standalone reader remains fully usable offline.

## Figure object

Every main figure requires:

- `number`: display label, such as `Figure 3`.
- `title_zh` and `title_en`.
- `image`: path to the cropped source figure.
- `question`: what scientific question this figure answers.
- `takeaway`: one-sentence result.
- `provenance`: array describing how the data were generated.
- `reading`: array explaining panels, axes, colors, symbols, and units.
- `observations`: array of visible observations; avoid overstating interpretation.
- `claim`: the authors' inference from those observations.
- `limitation`: what this figure cannot prove.
- `glossary`: array of `{zh, en}` terms.
- optional `callout`: important inconsistency, missing data, or caution.
- optional `diagram`: small HTML-safe text diagram such as `早期图像 → 特征 → 模型 → 预测`.

## Validation object

- `steps`: ordered objects with `label` and `text`.
- `metrics`: objects with `name`, `direction`, and `meaning`.
- `audit`: array of limitations and leakage risks.

Always name the unit being held out. “Leave-one-out” without the held-out unit is incomplete.

## Authoring rules

- All text values are plain text; the renderer escapes HTML.
- Use arrays for separate ideas instead of embedding markup in strings.
- Keep source-figure captions paraphrased. Do not reproduce long copyrighted passages.
- Images are embedded as data URIs by the renderer, so the output is portable.
- GPT tutor requests include only the current reader section, selected text,
  paper metadata, and recent in-memory conversation turns. They do not upload
  the source PDF automatically.
- Explanatory reconstructions must be identified in their labels and must not be mistaken for original figures.
