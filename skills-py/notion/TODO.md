# Notion Skill — TODO

- [ ] Validate skill with real Notion integration token (`python scripts/test-setup.py skills/notion`)
- [ ] Test setup flow end-to-end (enter token, verify connection, check config.json persisted)
- [ ] Test tools interactively (`python scripts/test-server.py` → browse and call notion_search, notion_get_page_content, etc.)
- [ ] Verify entity emission (pages, databases, users appear after load)
- [ ] Test error handling (invalid token, revoked token, unshared pages, rate limiting)
- [ ] Test convenience tools (notion_get_page_content recursive rendering, notion_append_text)
- [ ] Test database query with filters and sorts
- [ ] Validate manifest.json entity schema matches actual emitted entities
