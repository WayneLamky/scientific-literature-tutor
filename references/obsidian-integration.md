# Obsidian integration

Use direct Markdown writes for a local Obsidian vault. This keeps the reader
independent of community plugins and lets Obsidian refresh external changes.

## Configuration

Keep the vault path outside generated HTML. By default, `serve_reader.py` reads
`paper-readers/obsidian-config.json` from the workspace root:

```json
{
  "vault": "/absolute/path/to/Vault",
  "papers_dir": "Research/Papers",
  "concepts_dir": "Research/Concepts",
  "attachments_dir": "Research/Attachments/Papers"
}
```

Use `--obsidian-config PATH` for another config location. Validate that `vault`
exists, contains `.obsidian`, and that every target resolves inside the vault.
Do not enumerate or read unrelated notes.

When Obsidian is already open, inspect only its application state or vault
registry to identify the entry marked open. On macOS the registry is normally
`~/Library/Application Support/obsidian/obsidian.json`. Extract only vault IDs,
paths, and open flags; do not use vault discovery as permission to inspect note
contents.

## Capture contract

The browser sends only:

- paper title, authors, year, and DOI;
- the user's question and the Codex answer;
- active Figure or reader-section label and kind;
- selected text, when present;
- an optional user-authored note and tags.

Save all captures for one paper to a stable paper note under `papers_dir`.
Create YAML properties for `type`, `citekey`, `title`, `authors`, `year`, `doi`,
`status`, and tags. Append captures under `## Reader captures` with the question,
answer, selected text, user note, reading position, timestamp, and a stable
`^ipr-...` block ID.

Derive the block ID from the paper identity, reading position, question, and
answer. If the ID already exists, return the existing target without appending.
Write through a temporary sibling file and atomically replace the note.

## Local endpoints

- `GET /api/obsidian/status`: report configuration, vault name, and paper folder.
- `POST /api/obsidian/save`: validate and append one capture.

Return the vault-relative note path, block ID, duplicate flag, and an
`obsidian://open` URI targeting the block. Do not return the absolute vault path
to browser code.

## Verification

1. Start the server on loopback only.
2. Confirm the status endpoint names the intended vault and directory.
3. Save one realistic capture and inspect only the created note.
4. Repeat the identical request and confirm `duplicate: true`.
5. Open the returned URI and confirm Obsidian selects the created paper note.
