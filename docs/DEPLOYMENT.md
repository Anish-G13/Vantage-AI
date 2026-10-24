# Deployment and configuration

Preserve **https://vantageai.streamlit.app/** and the existing Streamlit Community
Cloud app: **Anish-G13/Vantage-AI**, branch **main**, entry point **app.py**.
Do not create a replacement app or change its URL.

The existing Cloud dashboard may display the repository's former name,
`competitor-feature-gap-analyzer`. GitHub redirects that name to the same
`Anish-G13/Vantage-AI` repository. Verify the redirect before changing any app
configuration. The upgraded deployment uses Python 3.12.

## Existing app update

1. Commit tested source, requirements, and documentation to the existing repository.
2. Let Community Cloud rebuild the existing deployment from `main`.
3. Verify the title is **Vantage AI | Competitive Intelligence**, with **Explore
   the demonstration** and sidebar version **2.0.0**.
4. Test the demo, an edit, weight changes, roadmap, and PDF preparation. Run real
   research only with valid server-side model access and quota.

The existing `GOOGLE_API_KEY` remains compatible. No secrets are committed or
copied into public code. Optional settings in the existing app's Secrets:

```toml
GOOGLE_API_KEY = "your-existing-key"
GEMINI_MODEL = "gemini-2.5-flash"
MAX_HOURLY_AI_CALLS = 60
```

Use Python 3.11 or 3.12. If an older Python runtime blocks dependency installation,
update the existing app's Python version through its available Community Cloud
configuration; preserve the app and URL. Runtime dependencies are pinned in
`requirements.txt`.

## Recovery

- **Old interface:** confirm the app watches `main` and `app.py`; use the existing
  reboot control if its automatic rebuild did not occur.
- **Missing credential:** demo/manual modes remain available. Configure the key
  in Secrets; never paste it into a public issue or commit.
- **Quota/access error:** check API project quota, billing, and model access.
  Repeated requests are not a fix; edits and exports remain available.
- **Grounding unavailable:** unsupported ratings remain Unverified. Select a
  supported search-grounding model through `GEMINI_MODEL` if needed.
- **No claim-linked evidence:** inspect response metadata and product specificity.
  Do not weaken citation checks to fabricate a full matrix.
- **Bad release:** revert the application commit in the same branch and let the
  existing Streamlit app rebuild. No unrelated content needs deletion.

Account access, credentials, and provider quota are deployment dependencies.
Report their actual status separately from mocked automated tests.
