# Browser Automation Skill

Comprehensive browser automation skill using Playwright for web scraping, testing, and automation.

## Features

- **Navigation**: Navigate to URLs, go back/forward, reload pages
- **Interaction**: Click, fill forms, type text, select options, check boxes
- **Content Extraction**: Get text, HTML, attributes, take screenshots
- **JavaScript Execution**: Run custom JavaScript in page context
- **Storage Management**: Access and modify cookies, localStorage, sessionStorage
- **Network Control**: Intercept requests, monitor network logs
- **Multi-page Support**: Manage multiple tabs/pages
- **File Operations**: Upload and download files
- **Dialog Handling**: Handle alerts, confirms, and prompts

## Tools

### Navigation

- `navigate` - Navigate to a URL
- `go_back` - Go back in browser history
- `go_forward` - Go forward in browser history
- `reload` - Reload the current page
- `get_url` - Get current page URL
- `get_title` - Get page title

### Interaction

- `click` - Click an element (supports CSS selectors, text, XPath)
- `fill` - Fill an input field
- `type` - Type text character by character
- `press_key` - Press keyboard keys
- `select_option` - Select dropdown options
- `check` - Check/uncheck checkboxes and radio buttons
- `hover` - Hover over elements
- `scroll` - Scroll page or elements

### Content Extraction

- `get_text` - Get text content
- `get_html` - Get HTML content
- `get_attribute` - Get element attributes
- `screenshot` - Take screenshots

### JavaScript

- `evaluate` - Execute JavaScript in page context

### Waiting

- `wait_for_selector` - Wait for element to appear
- `wait_for_url` - Wait for URL to match pattern

### Cookies

- `get_cookies` - Get all cookies
- `set_cookie` - Set a cookie
- `clear_cookies` - Clear all cookies

### Storage

- `get_local_storage` / `set_local_storage` / `clear_local_storage`
- `get_session_storage` / `set_session_storage` / `clear_session_storage`

### Network

- `intercept_request` - Intercept and modify network requests
- `get_network_logs` - Get network request/response logs

### Pages/Tabs

- `new_page` - Open new page/tab
- `get_pages` - List all open pages
- `switch_page` - Switch between pages
- `close_page` - Close current page

### Dialogs

- `handle_dialog` - Handle browser dialogs (alert, confirm, prompt)

### Files

- `upload_file` - Upload files to file inputs
- `download_file` - Download files

## Configuration

Create `config.json` in the skill's data directory to customize browser behavior:

```json
{ "headless": false, "browser_type": "chromium" }
```

Options:

- `headless`: Run browser in headless mode (default: `true`)
- `browser_type`: Browser to use - `chromium`, `firefox`, or `webkit` (default: `chromium`)

## Installation

**Fully automated!** The skill automatically installs Playwright browsers when needed. No manual CLI steps required.

When the skill loads for the first time, it will automatically download and install the required browser binaries (Chromium by default). This happens transparently in the background - users don't need to do anything.

If auto-installation fails (e.g., due to network issues), the skill will provide clear error messages with instructions.

## Usage Examples

### Navigate and Extract Content

```python
# Navigate to a page
navigate(url="https://example.com")

# Wait for content to load
wait_for_selector(selector="h1")

# Get page title
get_title()

# Extract text
get_text(selector="h1")

# Take a screenshot
screenshot(full_page=True)
```

### Form Filling

```python
# Fill a form
fill(selector="#username", text="user@example.com")
fill(selector="#password", text="password123")

# Click submit button
click(selector="button[type='submit']")

# Wait for navigation
wait_for_url(url="**/dashboard")
```

### JavaScript Execution

```python
# Execute custom JavaScript
evaluate(script="document.querySelector('h1').textContent")
```

### Cookie Management

```python
# Set a cookie
set_cookie(name="session", value="abc123", url="https://example.com")

# Get all cookies
get_cookies()
```

### Network Interception

```python
# Intercept API requests
intercept_request(
  url_pattern="**/api/**",
  action="continue"
)

# Get network logs
get_network_logs(url_pattern="**/api/**")
```

## Browser Types

- **chromium**: Chrome/Edge (recommended, most compatible)
- **firefox**: Firefox browser
- **webkit**: Safari (macOS only)

## Notes

- The browser runs in headless mode by default. Set `headless: false` in config to see the browser window.
- Playwright automatically handles waiting for elements and network requests.
- Screenshots can be saved to disk or returned as base64-encoded strings.
- Network interception allows modifying requests/responses for testing and automation.
