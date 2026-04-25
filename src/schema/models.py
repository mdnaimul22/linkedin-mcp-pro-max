from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def _format_timestamp(value: Any) -> str:
    try:
        if isinstance(value, (int, float)) and value > 0:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        pass
    return str(value) if value else ""


def _format_date_obj(date_obj: dict[str, Any] | None) -> str:
    if not date_obj:
        return ""
    
    month = date_obj.get("month", 0)
    year = date_obj.get("year", 0)
    
    if month and year:
        return f"{_MONTHS[min(month, 12)]} {year}"
    return str(year) if year else ""


MODEL_CONFIG = ConfigDict(
    from_attributes=True,
    validate_assignment=True,
    extra="ignore",
    frozen=False,
)


class Certification(BaseModel):
    model_config = MODEL_CONFIG
    name: str = ""
    authority: str = ""


class Language(BaseModel):
    model_config = MODEL_CONFIG
    name: str = ""
    proficiency: str = ""

OutputFormat = Literal["html", "md", "pdf"]

class Experience(BaseModel):
    model_config = MODEL_CONFIG

    title: str
    company: str
    location: str = ""
    start_date: str = ""
    end_date: str = "Present"
    description: str = ""

    @model_validator(mode="before")
    @classmethod
    def parse_raw_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # API format
            if "companyName" in data or "timePeriod" in data:
                period = data.get("timePeriod", {})
                return {
                    "title": data.get("title", ""),
                    "company": data.get("companyName", ""),
                    "location": data.get("locationName", ""),
                    "start_date": _format_date_obj(period.get("startDate")),
                    "end_date": _format_date_obj(period.get("endDate")) or "Present",
                    "description": data.get("description", ""),
                }
            # Browser format is already structurally matching (title, company, location, etc.)
        return data


class Education(BaseModel):
    model_config = MODEL_CONFIG

    school: str
    degree: str = ""
    field_of_study: str = ""
    start_date: str = ""
    end_date: str = ""

    @model_validator(mode="before")
    @classmethod
    def parse_raw_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # API format
            if "schoolName" in data or "timePeriod" in data:
                period = data.get("timePeriod", {})
                return {
                    "school": data.get("schoolName", ""),
                    "degree": data.get("degreeName", ""),
                    "field_of_study": data.get("fieldOfStudy", ""),
                    "start_date": _format_date_obj(period.get("startDate")),
                    "end_date": _format_date_obj(period.get("endDate")),
                }
        return data


class Profile(BaseModel):
    model_config = MODEL_CONFIG

    profile_id: str
    name: str
    headline: str = ""
    summary: str = ""
    location: str = ""
    industry: str = ""
    email: str = ""
    phone: str = ""
    profile_url: str = ""
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def parse_raw_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # API format detection
            if "firstName" in data or "lastName" in data:
                # The API provides contact info and skills separately sometimes,
                # but if they are merged into `data`, handle them.
                skills_raw = data.get("_skills_data", [])
                contact_raw = data.get("_contact_data", {})
                
                return {
                    "profile_id": data.get("profile_id", ""),
                    "name": f"{data.get('firstName', '')} {data.get('lastName', '')}".strip(),
                    "headline": data.get("headline", ""),
                    "summary": data.get("summary", ""),
                    "location": data.get("locationName", ""),
                    "industry": data.get("industryName", ""),
                    "email": contact_raw.get("email_address", ""),
                    "phone": (
                        ", ".join(contact_raw.get("phone_numbers", []))
                        if contact_raw.get("phone_numbers")
                        else ""
                    ),
                    "profile_url": f"https://www.linkedin.com/in/{data.get('profile_id', '')}",
                    "experience": data.get("experience", []),
                    "education": data.get("education", []),
                    "skills": [skill.get("name", "") for skill in skills_raw if skill.get("name")],
                    "languages": [
                        {"name": lang.get("name", ""), "proficiency": lang.get("proficiency", "")}
                        for lang in data.get("languages", [])
                    ],
                    "certifications": [
                        {"name": cert.get("name", ""), "authority": cert.get("authority", "")}
                        for cert in data.get("certifications", [])
                    ],
                }
            # Browser format is already matching names closely (except maybe missing fields)
            # Just ensure profile_url is generated if missing
            if "profile_id" in data and "profile_url" not in data:
                data["profile_url"] = f"https://www.linkedin.com/in/{data['profile_id']}"
                
        return data


class CompanyInfo(BaseModel):
    model_config = MODEL_CONFIG

    company_id: str
    name: str
    tagline: str = ""
    description: str = ""
    website: str = ""
    industry: str = ""
    company_size: str = ""
    headquarters: str = ""
    specialties: list[str] = Field(default_factory=list)
    url: str = ""

    @model_validator(mode="before")
    @classmethod
    def parse_raw_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # API format
            if "headquarter" in data or "staffCount" in data:
                hq = data.get("headquarter", {})
                parts = [hq.get("city", ""), hq.get("geographicArea", ""), hq.get("country", "")]
                headquarters = ", ".join(p for p in parts if p)

                industry = data.get("industryName", "")
                if not industry and data.get("companyIndustries"):
                    industry = data["companyIndustries"][0].get("localizedName", "")

                return {
                    "company_id": data.get("company_id", ""),
                    "name": data.get("name", ""),
                    "tagline": data.get("tagline", ""),
                    "description": data.get("description", ""),
                    "website": data.get("companyPageUrl", data.get("website", "")),
                    "industry": industry,
                    "company_size": f"{data.get('staffCount', 'Unknown')} employees",
                    "headquarters": headquarters,
                    "specialties": data.get("specialities", data.get("specialties", [])),
                    "url": f"https://www.linkedin.com/company/{data.get('company_id', '')}",
                }
        return data


# --- Job Models ---

class JobSearchFilter(BaseModel):
    model_config = MODEL_CONFIG

    keywords: str = ""
    location: str = ""
    distance: int | None = None
    job_type: list[str] | None = None
    experience_level: list[str] | None = None
    remote: bool | None = None
    date_posted: str | None = None
    company: str | None = None


class JobListing(BaseModel):
    model_config = MODEL_CONFIG

    job_id: str
    title: str
    company: str
    location: str
    url: str = ""
    date_posted: str = ""
    applicant_count: int | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_raw_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # API format detection
            if "entityUrn" in data or "jobPostingId" in data or "trackingUrn" in data:
                entity_urn = data.get("entityUrn", "")
                job_id = (
                    entity_urn.split(":")[-1]
                    if entity_urn
                    else str(data.get("jobPostingId", ""))
                )
                if not job_id:
                    job_id = (
                        str(data.get("trackingUrn", "")).split(":")[-1] or f"unknown_{id(data)}"
                    )

                company = data.get("companyName") or data.get("companyDetails", {}).get("company")
                if not company and "title" in data:
                    company = "See job details"

                return {
                    "job_id": job_id,
                    "title": data.get("title", "Unknown"),
                    "company": company or "Unknown",
                    "location": data.get("formattedLocation", data.get("location", "Not specified")),
                    "url": f"https://www.linkedin.com/jobs/view/{job_id}",
                    "date_posted": _format_timestamp(data.get("listedAt", "")),
                    "applicant_count": data.get("applicantCount"),
                }
        return data


class JobDetails(BaseModel):
    model_config = MODEL_CONFIG

    job_id: str
    title: str
    company: str
    location: str
    description: str = ""
    url: str = ""
    employment_type: str = ""
    seniority_level: str = ""
    skills: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    job_functions: list[str] = Field(default_factory=list)
    date_posted: str = ""
    applicant_count: int | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_raw_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Try to unwrap if jobDetails is nested (API response style)
            job = data.get("jobDetails", data)
            
            # Identify API style
            if "formattedLocation" in job or "listedAt" in job:
                description = job.get("description", {}).get("text", "")

                skills = []
                if "skills" in job:
                    skills = [s.get("name", "") for s in job["skills"] if s.get("name")]

                return {
                    "job_id": data.get("job_id", job.get("jobPostingId", "")),
                    "title": job.get("title", ""),
                    "company": job.get("companyDetails", {}).get(
                        "company", job.get("companyName", "Unknown")
                    ),
                    "location": job.get("formattedLocation", job.get("location", "")),
                    "description": description if isinstance(description, str) else "",
                    "url": f"https://www.linkedin.com/jobs/view/{data.get('job_id', job.get('jobPostingId', ''))}",
                    "employment_type": job.get("employmentType", ""),
                    "seniority_level": job.get("seniorityLevel", ""),
                    "skills": skills,
                    "industries": job.get("industries", []),
                    "job_functions": job.get("jobFunctions", []),
                    "date_posted": _format_timestamp(job.get("listedAt", "")),
                    "applicant_count": job.get("applicantCount"),
                }
        return data


# --- Tracking Models ---

StatusType = Literal[
    "interested", "applied", "interviewing", "offered", "rejected", "withdrawn"
]
VALID_STATUSES = [
    "interested",
    "applied",
    "interviewing",
    "offered",
    "rejected",
    "withdrawn",
]


class TrackedApplication(BaseModel):
    model_config = MODEL_CONFIG

    job_id: str
    job_title: str
    company: str
    status: StatusType = "interested"
    applied_date: str | None = None
    notes: str = ""
    url: str = ""
    resume_used: str | None = None
    cover_letter_used: str | None = None
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ResumeHeader(BaseModel):
    model_config = MODEL_CONFIG
    name: str
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""


class ResumeExperience(BaseModel):
    model_config = MODEL_CONFIG

    title: str
    company: str
    location: str = ""
    start_date: str = ""
    end_date: str = "Present"
    description: str = ""


class ResumeEducation(BaseModel):
    model_config = MODEL_CONFIG

    school: str
    degree: str = ""
    field: str = ""
    start_date: str = ""
    end_date: str = ""


class ResumeContent(BaseModel):
    model_config = MODEL_CONFIG

    header: ResumeHeader
    summary: str = ""
    experience: list[ResumeExperience] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)


class CoverLetterContent(BaseModel):
    model_config = MODEL_CONFIG

    date: str
    candidate_name: str
    candidate_contact: str = ""
    recipient: str = ""
    company: str = ""
    job_title: str = ""
    greeting: str = "Dear Hiring Manager,"
    introduction: str = ""
    body_paragraphs: list[str] = Field(default_factory=list)
    closing: str = ""
    signature: str = ""


class GeneratedDocument(BaseModel):
    model_config = MODEL_CONFIG

    content: str
    format: OutputFormat
    file_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Session Models ---

class SourceState(BaseModel):
    model_config = MODEL_CONFIG

    version: int = 1
    source_runtime_id: str
    login_generation: str
    created_at: str
    profile_path: str
    cookies_path: str


class RuntimeState(BaseModel):
    model_config = MODEL_CONFIG

    version: int = 1
    runtime_id: str
    source_runtime_id: str
    source_login_generation: str
    created_at: str
    committed_at: str
    profile_path: str
    storage_state_path: str
    commit_method: str = "checkpoint_restart"


# --- Discovery Models ---

class FieldInfo(BaseModel):
    model_config = MODEL_CONFIG

    tag: str
    type: str | None = None
    id: str | None = None
    name: str | None = None
    placeholder: str | None = None
    value: str | None = None
    label: str | None = None
    aria_label: str | None = None
    required: bool = False
    disabled: bool = False
    is_contenteditable: bool = False
    selector: str | None = None


class DiscoverySummary(BaseModel):
    model_config = MODEL_CONFIG

    total_inputs: int = 0
    total_textareas: int = 0
    total_selects: int = 0
    total_buttons: int = 0

    @property
    def total_fields(self) -> int:
        return self.total_inputs + self.total_textareas + self.total_selects + self.total_buttons


class DiscoveryResult(BaseModel):
    model_config = MODEL_CONFIG

    url: str
    success: bool = True
    error: str | None = None
    inputs: list[FieldInfo] = Field(default_factory=list)
    textareas: list[FieldInfo] = Field(default_factory=list)
    selects: list[FieldInfo] = Field(default_factory=list)
    buttons: list[FieldInfo] = Field(default_factory=list)
    summary: DiscoverySummary = Field(default_factory=DiscoverySummary)

    def rebuild_summary(self) -> None:
        self.summary = DiscoverySummary(
            total_inputs=len(self.inputs),
            total_textareas=len(self.textareas),
            total_selects=len(self.selects),
            total_buttons=len(self.buttons),
        )
