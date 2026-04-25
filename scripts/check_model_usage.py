import subprocess

classes = [
    "Certification", "Language", "Experience", "Education", "Profile",
    "CompanyInfo", "JobSearchFilter", "JobListing", "JobDetails",
    "TrackedApplication", "TrackingConfig", "ResumeHeader",
    "ResumeExperience", "ResumeEducation", "ResumeContent",
    "CoverLetterContent", "GeneratedDocument", "SourceState",
    "RuntimeState", "FieldInfo", "DiscoverySummary", "DiscoveryResult"
]

results = {}

for cls in classes:
    # Use grep to find usage outside schema directory
    cmd = f'grep -rE "\\b{cls}\\b" src | grep -v "src/schema/" | grep -v "__pycache__"'
    process = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if process.stdout.strip():
        results[cls] = "USED"
    else:
        results[cls] = "UNUSED"

for cls, status in results.items():
    print(f"{cls}: {status}")
