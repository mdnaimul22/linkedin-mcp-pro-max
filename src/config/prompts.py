
MCP_JOB_SEARCH_WORKFLOW = (
    "Help me find {role} jobs{loc}.\n\n"
    "Steps:\n"
    "1. Search for jobs matching my criteria using search_jobs\n"
    "2. Review the most promising listings with get_job_details\n"
    "3. Compare them with my profile using get_profile('me')\n"
    "4. Track interesting ones with track_application\n"
    "5. Generate tailored resumes for top choices with tailor_resume"
)

MCP_APPLICATION_WORKFLOW = (
    "Help me prepare a complete application for job {job_id}.\n\n"
    "Steps:\n"
    "1. Get the full job details with get_job_details('{job_id}')\n"
    "2. Review my profile with get_profile('me')\n"
    "3. Generate a tailored resume with tailor_resume('me', '{job_id}')\n"
    "4. Generate a cover letter with generate_cover_letter('me', '{job_id}')\n"
    "5. Track this application with track_application"
)

MCP_PROFILE_OPTIMIZATION = (
    "Help me optimize my LinkedIn profile.\n\n"
    "Steps:\n"
    "1. Analyze my current profile with analyze_profile('me')\n"
    "2. Review the suggestions and prioritize changes\n"
    "3. Generate a polished resume to see how the profile looks in document form with generate_resume('me')"
)


CONTENT_GENERATION_SYSTEM_PROMPT = """You are a professional LinkedIn content strategist and writer.
Your task is to write an engaging, authentic LinkedIn post.

Rules:
- Length: 150–400 words. Be concise but impactful.
- Tone: Professional, thoughtful, and human. NOT robotic or promotional.
- Structure:
  1. A strong hook (first 1-2 lines, this is what people see before 'see more').
  2. 2-3 key insights, observations, or story beats.
  3. A soft call-to-action (e.g., a question to the reader) OR a strong personal takeaway.
- Emojis: Use sparingly (0–3 max).
- Hashtags: Add 3–5 relevant hashtags at the very end, on a new line.
- Do NOT use phrases like 'Excited to share', 'Thrilled to announce', or 'I am delighted'.
- Output the final post text ONLY. No title, no intro, no explanation."""

CONTENT_GENERATION_USER_PROMPT_TEMPLATE = (
    "Write a LinkedIn post about the following topic:\n\n"
    "Topic: {topic}\n"
    "Tone: {tone}\n"
    "{cta_instruction}"
)
