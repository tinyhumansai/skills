"""
Network mixin for browser client.
"""

from __future__ import annotations

from typing import Any


class BrowserNetworkMixin:
  """Mixin providing network methods."""

  async def intercept_request(
    self,
    url_pattern: str,
    action: str = "continue",
    response_status: int = 200,
    response_body: str | None = None,
    response_headers: dict[str, str] | None = None,
  ) -> dict[str, Any]:
    """Intercept network requests."""
    page = self._get_current_page()

    async def handle_route(route: Any) -> None:
      if action == "abort":
        await route.abort()
      elif action == "fulfill" or action == "respond":
        await route.fulfill(
          status=response_status,
          body=response_body or "",
          headers=response_headers or {},
        )
      else:
        await route.continue_()

    try:
      await page.route(url_pattern, handle_route)
      return {"success": True}
    except Exception as e:
      return {"success": False, "error": str(e)}

  async def get_network_logs(
    self,
    url_pattern: str | None = None,
    method: str | None = None,
    status: int | None = None,
  ) -> dict[str, Any]:
    """Get network logs."""
    logs = self.network_logs
    if url_pattern:
      import re

      pattern = re.compile(url_pattern.replace("*", ".*"))
      logs = [log for log in logs if pattern.search(log.get("url", ""))]
    if method:
      logs = [log for log in logs if log.get("method") == method.upper()]
    if status:
      logs = [log for log in logs if log.get("status") == status]
    return {"success": True, "logs": logs, "count": len(logs)}
