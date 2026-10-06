"""
Bluesky AT Protocol client — authentication and posting with link facets.
"""

import logging
import os

from atproto import Client, models

log = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is not None:
        return _client

    handle = os.environ.get("BLUESKY_HANDLE", "").strip()
    password = os.environ.get("BLUESKY_APP_PASSWORD", "").strip()

    if not handle or not password:
        raise RuntimeError(
            "BLUESKY_HANDLE and BLUESKY_APP_PASSWORD environment variables must be set."
        )

    client = Client()
    client.login(handle, password)
    log.info("Logged in to Bluesky as %s", handle)
    _client = client
    return _client


def post_with_link(
    text: str,
    link_url: str,
    mentions: list[str] | None = None,
    dry_run: bool = False,
) -> bool:
    """Post text to Bluesky, making link_url clickable and tagging any mention handles."""
    if dry_run:
        log.info("[DRY RUN] Would post (%d chars):\n%s", len(text), text)
        if mentions:
            log.info("[DRY RUN] Would tag: %s", ", ".join(mentions))
        return True

    try:
        client = get_client()

        # Facets use UTF-8 byte offsets
        text_bytes = text.encode("utf-8")
        facets = []

        url_bytes = link_url.encode("utf-8")
        byte_start = text_bytes.find(url_bytes)
        if byte_start != -1:
            facets.append(
                models.AppBskyRichtextFacet.Main(
                    features=[models.AppBskyRichtextFacet.Link(uri=link_url)],
                    index=models.AppBskyRichtextFacet.ByteSlice(
                        byte_start=byte_start,
                        byte_end=byte_start + len(url_bytes),
                    ),
                )
            )

        for handle in mentions or []:
            tag_bytes = f"@{handle}".encode("utf-8")
            tag_start = text_bytes.find(tag_bytes)
            if tag_start == -1:
                continue
            try:
                did = client.resolve_handle(handle).did
            except Exception as e:
                log.warning("Could not resolve @%s, posting without tag: %s", handle, e)
                continue
            facets.append(
                models.AppBskyRichtextFacet.Main(
                    features=[models.AppBskyRichtextFacet.Mention(did=did)],
                    index=models.AppBskyRichtextFacet.ByteSlice(
                        byte_start=tag_start,
                        byte_end=tag_start + len(tag_bytes),
                    ),
                )
            )

        client.send_post(text=text, facets=facets or None)

        log.info("Posted successfully")
        return True
    except Exception as e:
        log.error("Failed to post to Bluesky: %s", e)
        return False
