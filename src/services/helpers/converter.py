import re
from typing import Any
from config import Settings, setup_logger, ensure_dir

logger = setup_logger(Settings.LOG_DIR / "helper.log", name="linkedin-mcp.converter")

# Google Fonts domains allowed for template font loading
_ALLOWED_FONT_DOMAINS = (
    "https://fonts.googleapis.com/",
    "https://fonts.gstatic.com/",
)


def convert_html_to_pdf(html_content: str, output_path: Any) -> Any:
    """Convert HTML to PDF using WeasyPrint (blocking — run in a thread).

    Blocks all external URL fetching to prevent SSRF attacks.
    Google Fonts domains are explicitly allowed so template fonts render correctly.
    """
    try:
        from weasyprint import HTML, default_url_fetcher  # noqa: PLC0415

        ensure_dir(str(output_path.parent))

        def _url_fetcher(
            url: str, timeout: int = 10, ssl_context: object = None
        ) -> dict:
            """Block all external URLs except Google Fonts and data: URIs."""
            if url.startswith("data:"):
                if len(url) > 5_000_000:
                    raise ValueError("data: URI exceeds 5MB size limit")
                return default_url_fetcher(url)  # type: ignore[no-any-return]

            if any(url.startswith(domain) for domain in _ALLOWED_FONT_DOMAINS):
                return default_url_fetcher(url)  # type: ignore[no-any-return]

            raise ValueError(f"External URL fetching blocked: {url}")

        HTML(string=html_content, url_fetcher=_url_fetcher).write_pdf(
            str(output_path)
        )
        return output_path
    except ImportError:
        logger.error("WeasyPrint not installed. PDF generation will fail.")
        raise RuntimeError(
            "WeasyPrint is required for PDF generation. Install with: pip install weasyprint"
        )
    except Exception as exc:
        import traceback
        error_msg = f"PDF generation failed ({type(exc).__name__}): {exc}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise RuntimeError(error_msg) from exc


def convert_html_to_markdown(html_content: str) -> str:
    """Simple HTML to Markdown conversion."""
    md = html_content

    md = re.sub(r"<style[^>]*>.*?</style>", "", md, flags=re.DOTALL)
    md = re.sub(r"<script[^>]*>.*?</script>", "", md, flags=re.DOTALL)

    for i in range(6, 0, -1):
        md = re.sub(
            rf"<h{i}[^>]*>(.*?)</h{i}>", rf"{'#' * i} \1\n", md, flags=re.DOTALL
        )

    md = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", md, flags=re.DOTALL)
    md = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", md, flags=re.DOTALL)
    md = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", md, flags=re.DOTALL)
    md = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", md, flags=re.DOTALL)

    md = re.sub(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", md, flags=re.DOTALL
    )
    md = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", md, flags=re.DOTALL)
    md = re.sub(r"<[uo]l[^>]*>", "\n", md)
    md = re.sub(r"</[uo]l>", "\n", md)

    md = re.sub(r"<br\s*/?>", "\n", md)
    md = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", md, flags=re.DOTALL)
    md = re.sub(r"<div[^>]*>(.*?)</div>", r"\1\n", md, flags=re.DOTALL)
    md = re.sub(r"<hr[^>]*/?>", "\n---\n", md)

    md = re.sub(r"<[^>]+>", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md)

    # HTML entities
    md = re.sub(r"&nbsp;", " ", md)
    md = re.sub(r"&amp;", "&", md)
    md = re.sub(r"&lt;", "<", md)
    md = re.sub(r"&gt;", ">", md)
    md = re.sub(r"&quot;", '"', md)
    md = re.sub(r"&#x27;|&#39;", "'", md)
    md = re.sub(r"&mdash;", "—", md)
    md = re.sub(r"&ndash;", "–", md)
    md = re.sub(r"&middot;", "·", md)  # used in professional.j2 skill dots

    return md.strip()