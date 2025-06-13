Below is a **field‑guide for cloning every visible Cursor feature—context awareness, chat, ghost‑text, multi‑file diffs, command palette, telemetry toggles—inside an Epic SMART iframe that streams real‐time FHIR from Palantir Foundry.**  Each subsection explains *what Cursor does*, *why it matters for clinicians*, and *how to implement it with code‑server + React + FastAPI + Foundry*.  Follow the “Ship‑checks” to graduate each feature from dev to prod.

---

## Cursor Feature Surface (what we must clone)

| Cursor UX element                      | Native behaviour                                                                                 | Sources |
| -------------------------------------- | ------------------------------------------------------------------------------------------------ | ------- |
| **Ghost‑text autocomplete**            | Inline, greyed prediction; <kbd>Tab</kbd> to accept ([Cursor][1], [Cursor - Community Forum][2]) |         |
| **Chat / Composer side‑kick**          | Natural‑language edits & Q‑A in a collapsible sidebar ([Cursor][3])                              |         |
| **Multi‑file diff review**             | Chat returns patch; user stages hunks like `git add ‑p` ([Cursor][1])                            |         |
| **Command‑palette chat**               | <kbd>⌘ K</kbd> opens chat pre‑filled with context ([Open VSX][4])                                |         |
| **Context index**                      | Vector DB of full repo for retrieval‑augmented prompts ([Cursor][3])                             |         |
| **Telemetry opt‑out (“Privacy Mode”)** | All analytics disabled client‑side ([Stack Overflow][5])                                         |         |

---

## Target Architecture Snapshot

```
Epic Sidebar (iframe  ≤ 600 px)
┌──────────────────────────────────────────┐
│ React Shell (Next.js static export)      │
│  ├─ <MonacoEditor> (code‑server iframe)  │
│  ├─ <SidekickDrawer/>   ← Chat & Docs    │
│  └─ useCommandPalette()  ← ⌘K handler    │
└──────────────────────────────────────────┘
      ↑ postMessage nonce
FastAPI Proxy  ← Istio mTLS →  Foundry GraphQL + Vector Search
      ↓ SSE stream
o4‑mini‑high LLM  (private endpoint)
```

---

## 1 Context Engine (Repo + Patient)

### 1.1 What Cursor does

It chunks every file, embeds it, and on each chat/ghost‑text call retrieves the top‑K chunks. ([Cursor][3])

### 1.2 Healthcare twist

Alongside code, embed **FHIR “sentence chunks”** (labs, meds, conditions) for the active patient ID.

### 1.3 How to build

1. **Foundry vector index**:

   ````python
   embeddings = encode_fhir_rows(df)   # BGE-small
   ctx.search.index("patient_ctx").upsert(embeddings)
   ``` :contentReference[oaicite:7]{index=7}  
   ````
2. **Side‑panel “Patient Context” chips** call

   ```graphql
   { PatientAll(id:$id){
       observation(code:"vital-signs"){code value issued} } }
   ```

   cache in Apollo with key `<pid>|<resource>` ([Apollo GraphQL][6])

**Ship‑check**

* [ ] Retrieval API P50 < 150 ms for 2 K chunks.

---

## 2 Chat / Composer Side‑kick

### 2.1 WebView implementation

Create a VS Code **webview** panel named `atlas.chat`. Webviews run in an isolated iframe and can host React. ([Visual Studio Code][7])

### 2.2 Streaming UX

Cursor streams tokens into the chat bubble. Use FastAPI SSE:

```python
@app.post("/chat/stream")
async def stream(prompt: Prompt):
    async for chunk in llm.stream(prompt):
        yield {"event":"token","data":chunk}
```

Monaco diff viewer pops automatically when a patch is detected.

**Ship‑check**

* [ ] Chat loads collapsed and opens only on first use (Epic width precious).
* [ ] SSE disconnect reconnection < 2 s.

---

## 3 Ghost‑Text Autocomplete

### 3.1 Monaco Inline API

Register an `InlineCompletionsProvider`; feed FastAPI `/ghost` stream into `provideInlineCompletions`. ([Microsoft GitHub][8])

```ts
monaco.languages.registerInlineCompletionsProvider('*',{
  async provideInlineCompletions(model, pos, ctx){
    const res = await fetch('/proxy/ghost', {method:'POST', body: snippet});
    return { items: [{ insertText: await res.text(), range }] };
  }
});
```

Style via `.ghost-text { opacity: .4 }` (Cursor lets users recolour  ([Cursor - Community Forum][9])).

**Ship‑check**

* [ ] Ghost‑text latency P95 < 650 ms (Cursor bench ([Palantir][10])).
* [ ] <kbd>Tab</kbd> applies, <kbd>Esc</kbd> hides decoration.

---

## 4 Multi‑file Diffs & Apply

### 4.1 Generate patch server‑side

Return `unified‑diff` text from LLM.

### 4.2 Client diff viewer

Use `MonacoDiffEditor` in modal; apply via:

```ts
monaco.editor.getModel(uri)
      .applyEdits(monacoDiffToEdits(patch))
```

Patch mapping logic adapted from community snippet ([Stack Overflow][5]).

**Ship‑check**

* [ ] Applying > 1 file triggers VSIX command `workbench.files.saveAll`.

---

## 5 Command‑Palette Chat

### 5.1 Implementation

`vscode.commands.registerCommand('atlas.fhirPalette', handler)` triggers the chat modal prefilled with `/fhir labs 7d`. Mirror Cursor’s `⌘ K` binding ([Open VSX][4]).

### 5.2 FHIR helpers

Palette parses:

```
/fhir labs 7d
/fhir echo "last note"
/fhir compare patient 42 43
```

Each macro calls Foundry GraphQL.

**Ship‑check**

* [ ] Palette closes on <kbd>Esc</kbd>, focusing back to editor.

---

## 6 Embedding in Epic Sidebar

1. **Same‑origin**: host React & code‑server on `atlas.example.com`; Epic embeds via HTTPS iframe.
2. **PKCE OAuth flow** (Section 1) delivers Foundry JWT.
3. **CSP**:

   ````http
   Content-Security-Policy: frame-ancestors 'self' https://*.epic.com;
   ``` :contentReference[oaicite:15]{index=15}  
   ````

**Ship‑check**

* [ ] Epic QA tool passes frame‑busting & OAuth tests ([fhir.epic.com][11]).

---

## 7 Extension Distribution & Updates

* Publish VSIX to a **private Open‑VSX** registry; code‑server auto‑installs at container start ([Open VSX][4]).
* Update flow: push new VSIX → bump Docker tag → Argo CD sync.

---

## 8 Security & Observability

| Layer   | Hardening                                          |
| ------- | -------------------------------------------------- |
| Browser | CSP + SRI hashes (Section 5)                       |
| Network | Istio STRICT mTLS; health probes ([Istio][12])     |
| Backend | PHI redaction before LLM; audit to Foundry dataset |

Prometheus metrics: `ghost_latency_ms`, `chat_tokens_used`, `fhir_query_ms`.

---

## 9 Developer Workflow

1. **Nx monorepo**—`apps/ide-shell`, `libs/fhir-hooks`, `extensions/chat`.
2. Storybook with Axe plug‑in for cada component.
3. Cypress Component Test harness VSCode WebView via `.mount()`.

---

### Final Ship‑List

* [ ] Token‑swap & refresh complete.
* [ ] Context engine returns top‑5 chunks (< 150 ms).
* [ ] Ghost‑text P95 < 650 ms.
* [ ] Chat diff reviewer applies multi‑file edits.
* [ ] Command palette macros for top 5 FHIR queries.
* [ ] Epic iframe passes QA; mTLS enforced; telemetry opt‑out defaults **ON**.

With these additions you achieve **Cursor‑parity inside Epic**—clinicians get inline AI, chat‑driven edits, instant FHIR context, and a modern command palette, all delivered through a secure, maintainable stack.

[1]: https://www.cursor.com/features?utm_source=chatgpt.com "Features | Cursor - The AI Code Editor"
[2]: https://forum.cursor.com/t/how-the-f-do-i-remove-this-inline-suggest-thing/36286?utm_source=chatgpt.com "How the F do i remove this inline suggest thing?! - Discussion - Cursor"
[3]: https://docs.cursor.com/chat/overview?utm_source=chatgpt.com "Overview - Cursor"
[4]: https://open-vsx.org/?utm_source=chatgpt.com "Open VSX Registry"
[5]: https://stackoverflow.com/questions/70765928/is-there-a-way-to-determine-if-the-model-value-was-changed-programmatically-or-m?utm_source=chatgpt.com "monaco editor - Is there a way to determine if the model value was ..."
[6]: https://tanstack.com/query/latest/docs/react/guides/caching "Caching with TanStack Query"
[7]: https://code.visualstudio.com/api/extension-guides/webview?utm_source=chatgpt.com "Webview API | Visual Studio Code Extension API"
[8]: https://microsoft.github.io/monaco-editor/typedoc/interfaces/languages.InlineCompletion.html?utm_source=chatgpt.com "InlineCompletion | Monaco Editor API - Microsoft Open Source"
[9]: https://forum.cursor.com/t/how-to-change-suggestions-color/7395?utm_source=chatgpt.com "How to change suggestions color? - Cursor - Community Forum"
[10]: https://palantir.com/docs/foundry/api/general/overview/introduction//?utm_source=chatgpt.com "Introduction • API Reference - Palantir"
[11]: https://fhir.epic.com/Documentation?utm_source=chatgpt.com "Documentation - Epic on FHIR"
[12]: https://istio.io/latest/docs/ops/configuration/mesh/app-health-check/?utm_source=chatgpt.com "Health Checking of Istio Services"
