import asyncio
from typing import Any, Literal
from patchright.async_api import Page
from browser.helpers.executor import ApiExecutor
from browser.helpers import stabilize_navigation, wait_for_any_selector
from config import Settings, setup_logger

logger = setup_logger(Settings.LOG_DIR / "browser.log", name="browser.actors.profile_editor")


class ProfileEditor:
    def __init__(self, page: Page) -> None:
        self.page = page

    async def update_headline(self, profile_id: str, headline: str) -> dict[str, Any]:
        edit_url = f"https://www.linkedin.com/in/{profile_id}/edit/forms/intro/new/"

        try:
            await self.page.goto(edit_url, wait_until="load", timeout=60000)
            await stabilize_navigation(self.page)
            await self._force_notify_network_off()

            headline_selector = '[id$="-headline"]'
            await self.page.wait_for_selector(headline_selector, state="visible", timeout=10000)
            await self.page.locator(headline_selector).first.fill(headline)

            industry_input = self.page.locator('input[id$="-industryId"]').first
            if await industry_input.is_visible():
                val = await industry_input.input_value()
                if not val.strip():
                    await industry_input.fill("Software Development")
                    await asyncio.sleep(1)
                    await self.page.keyboard.press("ArrowDown")
                    await self.page.keyboard.press("Enter")

            await self.page.locator('button.artdeco-button--primary:has-text("Save")').first.click()

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
            except PlaywrightTimeoutError:
                logger.debug("No UI error feedback found after update_headline. Assuming success.")
                return {"status": "success", "message": "Headline updated."}
            except Exception as e:
                logger.warning(f"Error checking UI feedback in update_headline: {e}")
                return {"status": "success", "message": "Headline updated (feedback check skipped)."}
        except Exception as e:
            logger.error(f"Failed to update headline: {e}")
            return {"status": "error", "message": str(e)}

    async def update_summary(self, profile_id: str, summary: str) -> dict[str, Any]:
        edit_url = f"https://www.linkedin.com/in/{profile_id}/edit/about/"

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
            except PlaywrightTimeoutError:
                logger.debug("No UI error feedback found after update_summary. Assuming success.")
                return {"status": "success", "message": "Summary updated."}
            except Exception as e:
                logger.warning(f"Error checking UI feedback in update_summary: {e}")
                return {"status": "success", "message": "Summary updated (feedback check skipped)."}
        except Exception as e:
            logger.error(f"Failed to update summary: {e}")
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

        if position_id:
            url = f"https://www.linkedin.com/in/{profile_id}/edit/forms/position/{position_id}/"
        else:
            url = f"https://www.linkedin.com/in/{profile_id}/edit/forms/position/new/"

        try:
            await self.page.goto(url, wait_until="load", timeout=60000)
            await stabilize_navigation(self.page)
            await self._force_notify_network_off()

            executor = ApiExecutor(self.page)
            # Ensure at least one input/textarea is visible before discovery
            await wait_for_any_selector(self.page, ["input", "textarea"], timeout=10000)
            discovery = await executor.discover()

            def find_field(label_query: str, fields: list):
                for f in fields:
                    if f.label and label_query.lower() in f.label.lower():
                        return f
                return None

            # Map fields to values
            field_map = {
                "title": title,
                "company": company,
                "location": location,
                "description": description,
            }

            for label_key, value in field_map.items():
                if not value:
                    continue
                
                # Discovery logic
                search_label = "company" if label_key == "company" else label_key
                field = find_field(search_label, discovery.inputs + discovery.textareas)
                
                if field and field.id:
                    selector = f"#{field.id}"
                    logger.debug(f"Discovery: matched '{label_key}' to selector {selector}")
                    await self.page.locator(selector).first.fill(value)
                    if label_key in ["company", "location"]:
                        await asyncio.sleep(1.5)
                        await self.page.keyboard.press("ArrowDown")
                        await self.page.keyboard.press("Enter")
                else:
                    # Fallback
                    selector = f'input[id$="-{label_key}"], textarea[id$="-{label_key}"]'
                    if label_key == "company":
                        selector = 'input[id$="-requiredCompany"]'
                    elif label_key == "location":
                        selector = 'input[id$="-geoPositionLocation"]'
                    
                    try:
                        await self.page.locator(selector).first.fill(value)
                        if label_key in ["company", "location"]:
                            await asyncio.sleep(1.5)
                            await self.page.keyboard.press("ArrowDown")
                            await self.page.keyboard.press("Enter")
                    except Exception as e:
                        logger.debug(f"Discovery: fallback failed for '{label_key}': {e}")
                        continue

            if employment_type:
                field = find_field("employment type", discovery.selects)
                if field and field.id:
                    await self.page.locator(f"#{field.id}").select_option(label=employment_type)
                else:
                    try:
                        await self.page.locator('select[id$="-employmentStatus"]').select_option(label=employment_type)
                    except Exception as e:
                        logger.debug(f"Failed to set employment_type via fallback: {e}")

            if start_date_month:
                field = find_field("start date", discovery.selects) # Usually "Month" is inside a fieldset or labeled
                if field and field.id:
                    await self.page.locator(f"#{field.id}").select_option(label=start_date_month)
                else:
                    await self.page.locator('select[id$="-dateRange-start-date"]').select_option(label=start_date_month)
            
            if start_date_year:
                year_field = None
                for f in discovery.selects:
                    if f.label and "year" in f.label.lower() and "start" in f.label.lower():
                        year_field = f
                        break
                
                if year_field and year_field.id:
                    await self.page.locator(f"#{year_field.id}").select_option(label=start_date_year)
                else:
                    await self.page.locator('select[id$="-dateRange-start-date-year-select"]').select_option(label=start_date_year)


            end_date_select = self.page.locator('select[id$="-dateRange-end-date"]').first
            is_end_date_disabled = True
            if await end_date_select.count() > 0:
                is_end_date_disabled = await end_date_select.evaluate("el => el.disabled")

            needs_toggle = False
            if is_current and not is_end_date_disabled:
                needs_toggle = True
            elif not is_current and is_end_date_disabled:
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

        if education_id:
            url = f"https://www.linkedin.com/in/{profile_id}/edit/forms/education/{education_id}/"
        else:
            url = f"https://www.linkedin.com/in/{profile_id}/edit/forms/education/new/"

        try:
            await self.page.goto(url, wait_until="load", timeout=60000)

            executor = ApiExecutor(self.page)
            await wait_for_any_selector(self.page, ["input", "textarea"], timeout=10000)
            discovery = await executor.discover()

            def find_field(label_query: str, fields: list):
                for f in fields:
                    if f.label and label_query.lower() in f.label.lower():
                        return f
                return None

            field_map = {
                "school": school,
                "degree": degree,
                "fieldOfStudy": field_of_study,
                "grade": grade,
                "description": description,
            }

            for label_key, value in field_map.items():
                if not value:
                    continue
                
                field = find_field(label_key, discovery.inputs + discovery.textareas)
                if field and field.id:
                    selector = f"#{field.id}"
                    logger.debug(f"Discovery: matched '{label_key}' to selector {selector}")
                    await self.page.locator(selector).first.fill(value)
                    if label_key in ["school", "degree", "fieldOfStudy"]:
                        await asyncio.sleep(1.5)
                        await self.page.keyboard.press("ArrowDown")
                        await self.page.keyboard.press("Enter")
                else:
                    selector = f'input[id$="-{label_key}"], textarea[id$="-{label_key}"]'
                    if label_key == "fieldOfStudy":
                        selector = 'input[id$="-fieldOfStudy"]'
                    
                    try:
                        await self.page.locator(selector).first.fill(value)
                        if label_key in ["school", "degree", "fieldOfStudy"]:
                            await asyncio.sleep(1.5)
                            await self.page.keyboard.press("ArrowDown")
                            await self.page.keyboard.press("Enter")
                    except Exception as e:
                        logger.warning(f"Failed to fill field '{label_key}': {e}")

            if start_year:
                field = find_field("start date", discovery.selects)
                if field and field.id:
                    await self.page.locator(f"#{field.id}").select_option(label=start_year)
                else:
                    await self.page.locator('select[id$="-dateRange-start-date-year-select"]').select_option(label=start_year)

            if end_year:
                field = find_field("end date", discovery.selects)
                if field and field.id:
                    await self.page.locator(f"#{field.id}").select_option(label=end_year)
                else:
                    await self.page.locator('select[id$="-dateRange-end-date-year-select"]').select_option(label=end_year)

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

            return {"status": "success", "message": "Education saved.", "education_id": education_id}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def remove_education(
        self,
        profile_id: str,
        school: str,
        degree: str,
    ) -> dict[str, Any]:

        url = f"https://www.linkedin.com/in/{profile_id}/details/education/"
        try:
            await self.page.goto(url, wait_until="load", timeout=60000)
            await stabilize_navigation(self.page)

            education_items = self.page.locator("li.pvs-list__paged-list-item")
            count = await education_items.count()

            target_item = None
            for i in range(count):
                item = education_items.nth(i)
                text = await item.inner_text()
                if school.lower().strip() in text.lower() and degree.lower().strip() in text.lower():
                    target_item = item
                    break

            if not target_item:
                return {
                    "status": "error",
                    "message": f"Education at '{school}' with degree '{degree}' not found.",
                }

            edit_button = target_item.locator("a[href*='/edit/forms/education/']").first
            if not await edit_button.is_visible():
                return {
                    "status": "error",
                    "message": "Edit button not found for this education entry.",
                }

            await edit_button.click()
            await stabilize_navigation(self.page)

            delete_btn = self.page.locator(
                'button.artdeco-button--secondary:has-text("Delete education"), button:has-text("Delete education")'
            ).first
            if not await delete_btn.is_visible():
                return {
                    "status": "error",
                    "message": "Delete education button not found in modal.",
                }

            await delete_btn.click()
            await asyncio.sleep(1)

            confirm_btn = self.page.locator(
                'button.artdeco-button--primary:has-text("Delete")'
            ).first
            if await confirm_btn.is_visible():
                await confirm_btn.click()

            await asyncio.sleep(2)
            return {
                "status": "success",
                "message": f"Successfully deleted education at '{school}' with degree '{degree}'.",
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def update_cover_image(self, profile_id: str, image_path: str) -> dict[str, Any]:

        url = f"https://www.linkedin.com/in/{profile_id}/"
        try:
            await self.page.goto(url, wait_until="load", timeout=60000)
            await stabilize_navigation(self.page)

            edit_btn_selector = 'button[aria-label*="Edit background"], .profile-background-image__edit-btn, button:has(.profile-background-image__edit-icon)'
            edit_btn = self.page.locator(edit_btn_selector).first
            
            if not await edit_btn.is_visible():
                await edit_btn.scroll_into_view_if_needed()
                await asyncio.sleep(1)
            
            await edit_btn.click()
            logger.info("Clicked edit background button, waiting for modal...")
            await asyncio.sleep(3)


            file_input_selector = 'input[type="file"][id*="image-upload"], input[type="file"][name="file"], input[type="file"]'
            file_input = self.page.locator(file_input_selector).first
            
            try:
                await self.page.wait_for_selector(file_input_selector, state="attached", timeout=5000)
            except PlaywrightTimeoutError:
                logger.debug("Timed out waiting for file input selector, proceeding anyway.")
            except Exception as e:
                logger.debug(f"Error waiting for file input selector: {e}")

            if await file_input.count() == 0:
                 return {"status": "error", "message": "File upload input not found after clicking edit button."}

            logger.info(f"Uploading image: {image_path}")
            await file_input.set_input_files(image_path)
            
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
            logger.error(f"Failed to update cover image: {e}")
            return {"status": "error", "message": str(e)}

    async def remove_experience(
        self,
        profile_id: str,
        company: str,
        title: str,
    ) -> dict[str, Any]:

        url = f"https://www.linkedin.com/in/{profile_id}/details/experience/"
        try:
            
            await self.page.goto(url, wait_until="load", timeout=60000)
            await stabilize_navigation(self.page)

            experience_items = self.page.locator("li.pvs-list__paged-list-item")
            count = await experience_items.count()

            target_item = None
            for i in range(count):
                item = experience_items.nth(i)
                text = await item.inner_text()
                if company.lower().strip() in text.lower() and title.lower().strip() in text.lower():
                    target_item = item
                    break

            if not target_item:
                return {
                    "status": "error",
                    "message": f"Experience with title '{title}' at '{company}' not found.",
                }

            edit_button = target_item.locator("a[href*='/edit/forms/position/'], a[href*='/add-edit/POSITION/']").first
            if not await edit_button.is_visible():
                return {
                    "status": "error",
                    "message": "Edit button not found for this experience.",
                }

            await edit_button.click()
            await stabilize_navigation(self.page)

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
        except Exception as e:
            logger.debug(f"Error ensuring network toggle is off: {e}")

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
        except Exception as e:
            logger.debug(f"Error extracting UI error feedback: {e}")
        return None, None


from helpers.registry import ActorMeta
ACTOR = ActorMeta(attr="profile_editor", cls=ProfileEditor)
