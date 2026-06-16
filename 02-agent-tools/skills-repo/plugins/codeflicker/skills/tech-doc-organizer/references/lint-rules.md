# Documentation Lint Rules

This file defines the lint rules applied by the tech-doc-organizer skill.

## 1. Consistency Rules

### API Signature Mismatch
**Issue Type:** `api_signature_mismatch`
**Severity:** Warning

Detects when documentation references an API that doesn't exist in the codebase.

```markdown
<!-- Problem -->
The `processUserData(user_id, options)` function handles...

<!-- Should be -->
The `processUserData(userId, config)` function handles...
```

**Check Pattern:**
```python
# Looks for `function_name(args)` patterns in docs
# Verifies against function/class definitions in code
```

### Function Signature Mismatch
**Issue Type:** `function_signature_mismatch`
**Severity:** Warning

Similar to API mismatch but for internal functions.

### Config Mismatch
**Issue Type:** `config_mismatch`
**Severity:** Info

Detects config constants referenced in docs that may not exist.

**Check Pattern:**
```python
# Looks for `CONFIG_NAME` (uppercase) patterns in docs
# Verifies against const/variable definitions
```

### Dead Links
**Issue Type:** `dead_link`
**Severity:** Warning

Detects file references in docs that don't exist.

```markdown
<!-- Problem -->
See [the configuration guide](config/settings.md) for details.

<!-- Fix: Update path or create the referenced file -->
```

---

## 2. Organization Rules

### Overlapping Content
**Issue Type:** `overlapping_content`
**Severity:** Warning

Detects documents with >70% similar content.

**Action:** Consider merging or consolidating.

**Example:**
```
00-overview.md  <-> 01-introduction.md  (85% similar)
```

**Suggested Actions:**
1. Merge into a single comprehensive document
2. Consolidate into one and add redirect/toC links
3. Differentiate and keep separate with clear purpose

### Long Documents
**Issue Type:** `long_document`
**Severity:** Info

Documents exceeding 500 lines.

**Best Practices:**
- Split by major sections
- Create separate guides for different use cases
- Use table of contents for navigation

---

## 3. Lint Rules

### Duplicate Content
**Issue Type:** `duplicate_content`
**Severity:** Warning

Detects consecutive duplicate lines (3+ occurrences).

```markdown
<!-- Problem -->
This is important.
This is important.
This is important.

<!-- Fix: Remove duplicates -->
This is important.
```

### Outdated Version Markers
**Issue Type:** `outdated_version`
**Severity:** Info

Detects potentially outdated content:
- Old TODO dates (YYYY-MM-DD)
- Version numbers
- "Deprecated" mentions

```markdown
<!-- Problem -->
TODO: 2023-01-15 - Update this section

<!-- Action: Either complete the TODO or remove it -->
```

### Line Length Limit
**Issue Type:** `line_limit_exceeded`
**Severity:** Info

Lines exceeding 120 characters.

**Fix:** Wrap lines or restructure sentences.

---

## 4. Customizable Thresholds

You can customize these thresholds in your project config:

```json
{
  "doc_organizer": {
    "similarity_threshold": 0.7,      // Merge suggestion threshold
    "max_document_lines": 500,        // Split suggestion threshold
    "max_line_length": 120,           // Line length limit
    "ignored_patterns": [
      "**/CHANGELOG.md",
      "**/HISTORY.md"
    ]
  }
}
```

---

## 5. Supported File Types

- Markdown (.md)
- Plain text (.txt)
- reStructuredText (.rst)
- AsciiDoc (.adoc)

---

## 6. Directory Scanning

Documents are scanned in these locations (in order):
1. `/docs/` - Dedicated docs directory
2. `/doc/` - Alternative docs directory
3. `/documentation/` - Another common name
4. Root directory - For README files
5. Code directories - For inline documentation
