import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from app import get_ctx
from schema import ResumeContent, ResumeHeader, ResumeExperience, ResumeEducation

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("autopsy_v3")

# Mock Resume Content
MOCK_RESUME = ResumeContent(
    header=ResumeHeader(
        name="Naimul Islam",
        headline="Industrial Engineer",
        email="naimul@example.com",
        phone="+880123456789",
        location="Khulna, Bangladesh",
        profile_url="https://linkedin.com/in/mdnaimul22"
    ),
    summary="Expert in AI automation.",
    experience=[
        ResumeExperience(
            title="Senior Technician",
            company="My Union BD, Ltd.",
            period="2016 - 2023",
            description="Technical leadership."
        )
    ],
    education=[
        ResumeEducation(
            school="Khulna Polytechnic Institute",
            degree="Diploma in Engineering",
            period="2006 - 2010"
        )
    ],
    skills=["Python", "AI"]
)

async def run_autopsy_v3():
    logger.info("Starting Pipeline Autopsy V3...")
    
    try:
        ctx = await get_ctx()
        # We don't even need the browser for this rendering test
        logger.info("Context ready.")

        # Step 1: Direct WeasyPrint Test (Isolated)
        logger.info("Step 1: Isolated WeasyPrint Test...")
        try:
            from weasyprint import HTML
            simple_html = "<html><body><h1>Test PDF</h1><p>Hello World</p></body></html>"
            test_path = Path("tests/isolated_test.pdf")
            logger.info("Calling WeasyPrint directly...")
            HTML(string=simple_html).write_pdf(str(test_path))
            logger.info(f"Isolated PDF generated at {test_path}")
        except Exception as e:
            logger.error(f"Isolated WeasyPrint failed: {e}", exc_info=True)

        # Step 2: Real Template Rendering
        logger.info("Step 2: Rendering modern.j2 with Mock ResumeContent...")
        try:
            context = MOCK_RESUME.model_dump()
            html = ctx.template_manager.render_template("resume", "modern", context)
            logger.info("Template rendered successfully.")
        except Exception as e:
            logger.error(f"Template rendering failed: {e}", exc_info=True)
            return

        # Step 3: Full Conversion Test
        logger.info("Step 3: Full Conversion Test (Resume Content -> PDF)...")
        try:
            from services.helpers.converter import convert_html_to_pdf
            output_path = Path("tests/autopsy_full_resume.pdf")
            logger.info(f"Converting resume HTML to PDF at {output_path}...")
            await asyncio.to_thread(convert_html_to_pdf, html, output_path)
            logger.info("Full Resume PDF generated successfully!")
        except Exception as e:
            logger.error(f"Full Resume PDF conversion failed: {e}", exc_info=True)

    except Exception as e:
        logger.critical(f"Autopsy V3 crashed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_autopsy_v3())
