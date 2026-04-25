import asyncio
import logging
from typing import Any, Literal
from patchright.async_api import Page

from browser.helpers import stabilize_navigation

logger = logging.getLogger("linkedin-mcp.browser.actors.profile_editor")


class ProfileEditor:
    """Specialized actor for modifying LinkedIn profile content."""

    def __init__(self, page: Page) -> None:
        self.page = page

    async def update_headline(self, profile_id: str, headline: str) -> dict[str, Any]:
        """Update the LinkedIn headline."""
        edit_url = f"https://www.linkedin.com/in/{profile_id}/edit/forms/intro/new/"
        logger.info("Updating headline: %s", edit_url)

        try:
            await self.page.goto(edit_url, wait_until="load", timeout=60000)
            await stabilize_navigation(self.page)
            await self._force_notify_network_off()

            headline_selector = '[id$="-headline"]'
            await self.page.wait_for_selector(
                headline_selector, state="visible", timeout=10000
            )
            await self.page.locator(headline_selector).first.fill(headline)

            # Mandatory Industry check
            industry_input = self.page.locator('input[id$="-industryId"]').first
            if await industry_input.is_visible():
                val = await industry_input.input_value()
                if not val.strip():
                    await industry_input.fill("Software Development")
                    await asyncio.sleep(1)
                    await self.page.keyboard.press("ArrowDown")
                    await self.page.keyboard.press("Enter")

            await self.page.locator(
                'button.artdeco-button--primary:has-text("Save")'
            ).first.click()

            # Check for errors
            try:
                await self.page.wait_for_selector(
                    ".artdeco-inline-feedback--error", timeout=2000
                )
                error_text, suggestion = await self._get_ui_error_and_suggestion()
                return {
                    "status": "error",
                    "message": error_text,
                    "suggestion": suggestion,
                }
            except Exception:
                return {"status": "success", "message": "Headline updated."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def update_summary(self, profile_id: str, summary: str) -> dict[str, Any]:
        """Update the LinkedIn 'About' summary."""
        edit_url = f"https://www.linkedin.com/in/{profile_id}/edit/about/"
        logger.info("Updating summary: %s", edit_url)

        try:
            await self.page.goto(edit_url, wait_until="load", timeout=60000)
            await stabilize_navigation(self.page)
            await self._force_notify_network_off()

            summary_selector = '[id$="-summary"]'
            await self.page.wait_for_selector(
                summary_selector, state="visible", timeout=10000
            )
            await self.page.locator(summary_selector).first.fill(summary)

            await self.page.locator(
                'button.artdeco-button--primary:has-text("Save")'
            ).first.click()

            try:
                await self.page.wait_for_selector(
                    ".artdeco-inline-feedback--error", timeout=2000
                )
                error_text, suggestion = await self._get_ui_error_and_suggestion()
                return {
                    "status": "error",
                    "message": error_text,
                    "suggestion": suggestion,
                }
            except Exception:
                return {"status": "success", "message": "Summary updated."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def upsert_experience(
        self,
        profile_id: str,
        title: str,
        company: str,
        description: str | None = None,
        location: str | None = None,
        employment_type: str | None = None,
        start_date_month: str | None = None,
        start_date_year: str | None = None,
        end_date_month: str | None = None,
        end_date_year: str | None = None,
        is_current: bool = True,
        position_id: str | None = None,
    ) -> dict[str, Any]:
        """Add or update a work experience entry."""
        if position_id:
            url = f"https://www.linkedin.com/in/{profile_id}/edit/forms/position/{position_id}/"
        else:
            url = f"https://www.linkedin.com/in/{profile_id}/edit/forms/position/new/"

        try:
            await self.page.goto(url, wait_until="load", timeout=60000)
            await stabilize_navigation(self.page)
            await self._force_notify_network_off()

            await self.page.locator('input[id$="-title"]').first.fill(title)
            await self.page.locator('input[id$="-requiredCompany"]').first.fill(company)

            if employment_type:
                try:
                    await self.page.locator(
                        'select[id$="-employmentStatus"]'
                    ).select_option(label=employment_type)
                except Exception:
                    pass

            if location:
                await self.page.locator('input[id$="-geoPositionLocation"]').first.fill(
                    location
                )
                await asyncio.sleep(1.5)
                await self.page.keyboard.press("ArrowDown")
                await self.page.keyboard.press("Enter")

            if description:
                await self.page.locator('textarea[id$="-description"]').first.fill(
                    description
                )

            if start_date_month:
                await self.page.locator(
                    'select[id$="-dateRange-start-date"]'
                ).select_option(label=start_date_month)
            if start_date_year:
                await self.page.locator(
                    'select[id$="-dateRange-start-date-year-select"]'
                ).select_option(label=start_date_year)

            # Current role checkbox logic
            # The most reliable way to check the toggle state is by looking at the end-date dropdown's disabled state
            end_date_select = self.page.locator('select[id$="-dateRange-end-date"]').first
            is_end_date_disabled = True
            if await end_date_select.count() > 0:
                is_end_date_disabled = await end_date_select.evaluate("el => el.disabled")

            needs_toggle = False
            if is_current and not is_end_date_disabled:
                # User is current, but end date is enabled -> needs checking
                needs_toggle = True
            elif not is_current and is_end_date_disabled:
                # User is not current, but end date is disabled -> needs unchecking
                needs_toggle = True

            if needs_toggle:
                try:
                    await self.page.locator('label:has-text("I am currently working in this role"), label[for$="-isCurrent"]').first.click(force=True)
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning(f"Failed to toggle is_current: {e}")

            if not is_current:
                if end_date_month:
                    await self.page.locator(
                        'select[id$="-dateRange-end-date"]'
                    ).select_option(label=end_date_month)
                if end_date_year:
                    await self.page.locator(
                        'select[id$="-dateRange-end-date-year-select"]'
                    ).select_option(label=end_date_year)

            await self.page.locator(
                'button.artdeco-button--primary:has-text("Save")'
            ).first.click()
            await asyncio.sleep(2)

            error_text, suggestion = await self._get_ui_error_and_suggestion()
            if error_text:
                return {
                    "status": "error",
                    "message": error_text,
                    "suggestion": suggestion,
                }

            return {"status": "success", "message": "Experience saved."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def upsert_education(
        self,
        profile_id: str,
        school: str,
        degree: str,
        field_of_study: str | None = None,
        grade: str | None = None,
        start_year: str | None = None,
        end_year: str | None = None,
        description: str | None = None,
        education_id: str | None = None,
    ) -> dict[str, Any]:
        """Add or update an education entry."""
        if education_id:
            url = f"https://www.linkedin.com/in/{profile_id}/edit/forms/education/{education_id}/"
        else:
            url = f"https://www.linkedin.com/in/{profile_id}/edit/forms/education/new/"

        try:
            await self.page.goto(url, wait_until="load", timeout=60000)
            await stabilize_navigation(self.page)
            await self._force_notify_network_off()

            # Fill School
            school_input = self.page.locator('input[id$="-school"]').first
            await school_input.fill(school)
            await asyncio.sleep(1.5)
            await self.page.keyboard.press("ArrowDown")
            await self.page.keyboard.press("Enter")

            # Fill Degree
            degree_input = self.page.locator('input[id$="-degree"]').first
            await degree_input.fill(degree)
            await asyncio.sleep(1.5)
            await self.page.keyboard.press("ArrowDown")
            await self.page.keyboard.press("Enter")

            if field_of_study:
                field_input = self.page.locator('input[id$="-fieldOfStudy"]').first
                if await field_input.is_visible():
                    await field_input.fill(field_of_study)
                    await asyncio.sleep(1.5)
                    await self.page.keyboard.press("ArrowDown")
                    await self.page.keyboard.press("Enter")

            if grade:
                grade_input = self.page.locator('input[id$="-grade"]').first
                if await grade_input.is_visible():
                    await grade_input.fill(grade)

            if start_year:
                await self.page.locator(
                    'select[id$="-dateRange-start-date-year-select"]'
                ).select_option(label=start_year)
            if end_year:
                await self.page.locator(
                    'select[id$="-dateRange-end-date-year-select"]'
                ).select_option(label=end_year)

            if description:
                await self.page.locator('textarea[id$="-description"]').first.fill(
                    description
                )

            await self.page.locator(
                'button.artdeco-button--primary:has-text("Save")'
            ).first.click()
            await asyncio.sleep(2)

            error_text, suggestion = await self._get_ui_error_and_suggestion()
            if error_text:
                return {
                    "status": "error",
                    "message": error_text,
                    "suggestion": suggestion,
                }

            return {"status": "success", "message": "Education saved."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def update_cover_image(self, profile_id: str, image_path: str) -> dict[str, Any]:
        """Update the LinkedIn profile background/cover image."""
        url = f"https://www.linkedin.com/in/{profile_id}/"
        try:
            await self.page.goto(url, wait_until="load", timeout=60000)
            await stabilize_navigation(self.page)

            # Look for edit background button
            edit_btn_selector = 'button[aria-label*="Edit background"], .profile-background-image__edit-btn, button:has(.profile-background-image__edit-icon)'
            edit_btn = self.page.locator(edit_btn_selector).first
            
            if not await edit_btn.is_visible():
                # Force visibility or scroll
                await edit_btn.scroll_into_view_if_needed()
                await asyncio.sleep(1)
            
            await edit_btn.click()
            logger.info("Clicked edit background button, waiting for modal...")
            await asyncio.sleep(3)

            # LinkedIn often uses a hidden input[type="file"] with a specific ID pattern
            file_input_selector = 'input[type="file"][id*="image-upload"], input[type="file"][name="file"], input[type="file"]'
            file_input = self.page.locator(file_input_selector).first
            
            # Wait up to 5 seconds for the input to be attached to DOM
            try:
                await self.page.wait_for_selector(file_input_selector, state="attached", timeout=5000)
            except Exception:
                pass

            if await file_input.count() == 0:
                 return {"status": "error", "message": "File upload input not found after clicking edit button."}

            logger.info("Uploading image: %s", image_path)
            await file_input.set_input_files(image_path)
            
            # Wait for the 'Apply' or 'Save' button in the editor modal
            # LinkedIn UI can be slow here while it processes the image
            apply_btn_selector = 'button.artdeco-button--primary:has-text("Apply"), button:has-text("Apply"), button:has-text("Save")'
            await self.page.wait_for_selector(apply_btn_selector, state="visible", timeout=30000)
            
            apply_btn = self.page.locator(apply_btn_selector).first
            if await apply_btn.is_visible():
                logger.info("Clicking Apply/Save button")
                await apply_btn.click()
                await asyncio.sleep(5) # Wait for processing and page refresh
                return {"status": "success", "message": "Cover image updated successfully."}
            else:
                return {"status": "error", "message": "Apply/Save button not found after upload."}

        except Exception as e:
            logger.error("Failed to update cover image: %s", e)
            return {"status": "error", "message": str(e)}

    async def remove_experience(
        self,
        profile_id: str,
        company: str,
        title: str,
    ) -> dict[str, Any]:
        """Remove a work experience entry by matching title and company."""
        url = f"https://www.linkedin.com/in/{profile_id}/details/experience/"
        try:
            from browser.helpers import stabilize_navigation
            await self.page.goto(url, wait_until="load", timeout=60000)
            await stabilize_navigation(self.page)

            # Find the experience card containing the company and title
            experience_items = self.page.locator("li.pvs-list__paged-list-item")
            count = await experience_items.count()

            target_item = None
            for i in range(count):
                item = experience_items.nth(i)
                text = await item.inner_text()
                # Use robust matching avoiding case issues
                if company.lower().strip() in text.lower() and title.lower().strip() in text.lower():
                    target_item = item
                    break

            if not target_item:
                return {
                    "status": "error",
                    "message": f"Experience with title '{title}' at '{company}' not found.",
                }

            # Click the edit button (pencil icon) within this item
            edit_button = target_item.locator("a[href*='/edit/forms/position/'], a[href*='/add-edit/POSITION/']").first
            if not await edit_button.is_visible():
                return {
                    "status": "error",
                    "message": "Edit button not found for this experience.",
                }

            await edit_button.click()
            await stabilize_navigation(self.page)

            # Now we are in the edit modal. Click "Delete experience"
            delete_btn = self.page.locator(
                'button.artdeco-button--secondary:has-text("Delete experience"), button:has-text("Delete experience")'
            ).first
            if not await delete_btn.is_visible():
                return {
                    "status": "error",
                    "message": "Delete experience button not found in modal.",
                }

            await delete_btn.click()
            await asyncio.sleep(1)

            # Confirm deletion modal
            confirm_btn = self.page.locator(
                'button.artdeco-button--primary:has-text("Delete")'
            ).first
            if await confirm_btn.is_visible():
                await confirm_btn.click()

            await asyncio.sleep(2)
            return {
                "status": "success",
                "message": f"Successfully deleted experience '{title}' at '{company}'.",
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}



    async def manage_skills(
        self, profile_id: str, skill_name: str, action: Literal["add", "delete"] = "add"
    ) -> dict[str, Any]:
        """Add or delete skills from the profile."""
        url = f"https://www.linkedin.com/in/{profile_id}/details/skills/"
        try:
            await self.page.goto(url, wait_until="load")
            await stabilize_navigation(self.page)

            if action == "add":
                add_btn_selector = 'a[href*="/add-edit/SKILL"], button[aria-label*="Add skill"], a[href*="/edit/forms/skill/new/"]'
                await self.page.wait_for_selector(
                    add_btn_selector, state="visible", timeout=10000
                )
                await self.page.locator(add_btn_selector).first.click()

                input_selector = 'input.typeahead-cta__input, input[role="combobox"], input[id*="typeahead"], input[type="text"]'
                await self.page.wait_for_selector(
                    input_selector, state="visible", timeout=30000
                )
                input_field = self.page.locator(input_selector).first
                await input_field.fill(skill_name)
                await asyncio.sleep(2)
                await self.page.keyboard.press("ArrowDown")
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(1)

                save_btn = self.page.locator(
                    'button.artdeco-button--primary:has-text("Save")'
                ).first
                if await save_btn.is_visible():
                    await save_btn.click()
                return {"status": "success", "message": f"Skill '{skill_name}' added."}
            else:
                skill_row = self.page.locator(f"li:has-text('{skill_name}')").first
                edit_pencil = skill_row.locator(
                    'a[href*="/details/skills/edit/forms/"]'
                ).first
                if not await edit_pencil.is_visible():
                    return {
                        "status": "error",
                        "message": f"Skill '{skill_name}' not found.",
                    }
                await edit_pencil.click()
                await asyncio.sleep(1)
                await self.page.locator(
                    'button.artdeco-button--tertiary:has-text("Delete skill")'
                ).first.click()
                await asyncio.sleep(1)
                confirm_btn = self.page.locator(
                    "button.artdeco-modal__confirm-dialog-btn.artdeco-button--primary"
                ).first
                if await confirm_btn.is_visible():
                    await confirm_btn.click()
                return {
                    "status": "success",
                    "message": f"Skill '{skill_name}' deleted.",
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _force_notify_network_off(self) -> None:
        """Ensure 'Notify network' toggle is OFF."""
        try:
            toggle = self.page.locator(
                'input[id*="-notifyNetwork"], .artdeco-toggle input'
            ).first
            if await toggle.is_visible(timeout=2000):
                if await toggle.is_checked():
                    await self.page.locator(
                        'label[for*="-notifyNetwork"], .artdeco-toggle'
                    ).first.click()
                    await asyncio.sleep(0.5)
        except Exception:
            pass

    async def _get_ui_error_and_suggestion(self) -> tuple[str | None, str | None]:
        """Extract UI error text and provide suggestions."""
        try:
            error_selector = ".artdeco-inline-error, .artdeco-inline-feedback--error"
            if await self.page.locator(error_selector).count() > 0:
                error_text = (
                    await self.page.locator(error_selector).first.inner_text()
                ).strip()
                suggestion = "Please check the mandatory fields marked in red."
                if "title" in error_text.lower():
                    suggestion = "Job title is required."
                elif "company" in error_text.lower():
                    suggestion = "Company name is required."
                return error_text, suggestion
        except Exception:
            pass
        return None, None


# ── Registry Convention ───────────────────────────────────────────────────────
from helpers.registry import ActorMeta
ACTOR = ActorMeta(attr="profile_editor", cls=ProfileEditor)
