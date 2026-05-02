from typing import Any
from jinja2 import FileSystemLoader, select_autoescape
from jinja2.sandbox import SandboxedEnvironment

from config import Settings, setup_logger, ensure_dir, exists
from helpers.exceptions import TemplateError

logger = setup_logger(Settings.LOG_DIR / "template.log", name="linkedin-mcp.services.template")


class TemplateManager:
    """Manages Jinja2 templates for resume and cover letter generation."""

    def __init__(self, template_dirs: list[str] | None = None) -> None:
        # Templates are loaded from Settings.TEMPLATES_DIR (internal) 
        # and Settings.DATA_DIR / "templates" (user customized)
        
        internal_templates = Settings.TEMPLATES_DIR
        user_templates = Settings.DATA_DIR / "templates"

        # template_dirs coming as strings from external calls if any
        custom_dirs = []
        for d in (template_dirs or []):
            try:
                custom_dirs.append(Settings.resolve_path(d))
            except Exception as e:
                logger.debug(f"Failed to resolve custom template directory '{d}': {e}")
                pass
        
        self.template_dirs = custom_dirs + [
            internal_templates,
            user_templates,
        ]

        try:
            ensure_dir(str(user_templates))
        except Exception as exc:
            logger.warning(f"Could not create user templates directory: {exc}")

        # Filter only existing directories for FileSystemLoader
        valid_dirs = [str(d) for d in self.template_dirs if d.exists()]
        
        self.env = SandboxedEnvironment(
            loader=FileSystemLoader(valid_dirs),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def get_available_templates(self, template_type: str) -> dict[str, str]:
        """Return available templates as {name: display_name}."""
        templates: dict[str, str] = {}
        for template_dir in self.template_dirs:
            if not template_dir.exists():
                continue
            type_dir = template_dir / template_type
            if not type_dir.exists():
                continue
            # glob returns Path objects, we use .stem
            for template_file in type_dir.glob("*.j2"):
                name = template_file.stem
                templates[name] = name.replace("_", " ").title()
        return templates

    def render_template(
        self,
        template_type: str,
        template_name: str,
        context: dict[str, Any],
        output_format: str = "html",
    ) -> str:
        """Render a template with the given context."""
        template_path = f"{template_type}/{template_name}.j2"
        try:
            template = self.env.get_template(template_path)
            rendered = template.render(**context)
            if output_format == "md":
                rendered = "\n".join(line.rstrip() for line in rendered.split("\n"))
            return rendered
        except Exception as exc:
            logger.error(f"Error rendering template {template_path}: {exc}")
            raise TemplateError(
                f"Error rendering template {template_path}: {exc}"
            ) from exc

    def get_template_preview(
        self,
        template_type: str,
        template_name: str,
        sample_context: dict[str, Any] | None = None,
    ) -> str:
        """Preview a template with sample data."""
        if sample_context is None:
            sample_context = self._get_sample_context(template_type)
        return self.render_template(template_type, template_name, sample_context)

    def _get_sample_context(self, template_type: str) -> dict[str, Any]:
        """Provide fallback sample data for template previews."""
        if template_type == "resume":
            return {
                "header": {
                    "name": "John Doe",
                    "headline": "Senior Software Engineer",
                    "email": "john.doe@example.com",
                    "phone": "(123) 456-7890",
                    "location": "San Francisco, CA",
                    "linkedin_url": "https://linkedin.com/in/johndoe",
                },
                "summary": "Experienced software engineer with 5+ years...",
                "experience": [
                    {
                        "title": "Senior Software Engineer",
                        "company": "Tech Corp",
                        "location": "San Francisco, CA",
                        "start_date": "Jan 2020",
                        "end_date": "Present",
                        "description": "Led development of key features...",
                    }
                ],
                "education": [
                    {
                        "school": "UC Berkeley",
                        "degree": "B.S.",
                        "field": "Computer Science",
                        "end_date": "2015",
                    }
                ],
                "skills": ["Python", "JavaScript", "AWS", "Docker"],
                "languages": [{"name": "English", "proficiency": "Native"}],
            }
        return {
            "date": "2024-01-15",
            "candidate_name": "John Doe",
            "candidate_contact": "john.doe@example.com | (123) 456-7890",
            "recipient": "Hiring Manager",
            "company": "Tech Innovations Inc.",
            "job_title": "Senior Software Engineer",
            "greeting": "Dear Hiring Manager,",
            "introduction": "I am excited to apply...",
            "body_paragraphs": ["With over 5 years of experience..."],
            "closing": "I look forward to discussing...",
            "signature": "Best regards,\nJohn Doe",
        }


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ServiceMeta
SERVICE = ServiceMeta(
    attr="template_manager",
    cls=TemplateManager,
    lazy=False,
    factory=lambda ctx: TemplateManager(),
)
