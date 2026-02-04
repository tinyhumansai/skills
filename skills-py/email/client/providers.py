"""
Email provider presets for Gmail, Outlook, Yahoo, and iCloud.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderPreset:
  name: str
  imap_host: str
  imap_port: int
  smtp_host: str
  smtp_port: int
  use_ssl: bool
  notes: str


PROVIDERS: dict[str, ProviderPreset] = {
  "gmail": ProviderPreset(
    name="Gmail",
    imap_host="imap.gmail.com",
    imap_port=993,
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    use_ssl=True,
    notes="Gmail requires an App Password. Go to myaccount.google.com > Security > 2-Step Verification > App Passwords.",
  ),
  "outlook": ProviderPreset(
    name="Outlook / Office 365",
    imap_host="outlook.office365.com",
    imap_port=993,
    smtp_host="smtp.office365.com",
    smtp_port=587,
    use_ssl=True,
    notes="Use your full Outlook email and password. You may need to enable IMAP in Outlook settings.",
  ),
  "yahoo": ProviderPreset(
    name="Yahoo Mail",
    imap_host="imap.mail.yahoo.com",
    imap_port=993,
    smtp_host="smtp.mail.yahoo.com",
    smtp_port=587,
    use_ssl=True,
    notes="Yahoo requires an App Password. Go to Account Security > Generate app password.",
  ),
  "icloud": ProviderPreset(
    name="iCloud Mail",
    imap_host="imap.mail.me.com",
    imap_port=993,
    smtp_host="smtp.mail.me.com",
    smtp_port=587,
    use_ssl=True,
    notes="iCloud requires an App-Specific Password. Go to appleid.apple.com > Sign-In and Security > App-Specific Passwords.",
  ),
}


def get_provider(provider_id: str) -> ProviderPreset | None:
  """Get a provider preset by ID."""
  return PROVIDERS.get(provider_id.lower())


def list_providers() -> list[dict[str, str]]:
  """List available providers for the setup flow."""
  result = []
  for pid, p in PROVIDERS.items():
    result.append({"id": pid, "name": p.name, "notes": p.notes})
  result.append(
    {
      "id": "custom",
      "name": "Custom IMAP/SMTP",
      "notes": "Enter your own IMAP and SMTP server settings.",
    }
  )
  return result
