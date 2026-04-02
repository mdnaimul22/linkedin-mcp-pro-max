## English
The job of src/browser/actors/ is to change something or take an action through the browser. For example: submitting a form, adding/removing data by clicking a button or sending a connection request to someone.

If you want to take a new action on LinkedIn (such as automatically applying to jobs, or sending messages), only then do you need to create a new Actor (actors/job_applier.py or actors/messenger.py)

## Bangla
src/browser/actors/ এর কাজ হলো ব্রাউজারের মাধ্যমে কোনো কিছু পরিবর্তন (Mutate) করা বা অ্যাকশন নেওয়া। যেমন: ফর্ম সাবমিট করা, বাটনে ক্লিক করে ডেটা অ্যাড/রিমুভ করা, বা কাউকে কানেকশন রিকোয়েস্ট পাঠানো।

আপনি যদি লিংকডইন-এ নতুন কোনো অ্যাকশন নিতে চান (যেমন: অটোমেটিক্যালি জবে অ্যাপ্লাই করা, বা মেসেজ পাঠানো), শুধুমাত্র তখনই আপনাকে নতুন একটি Actor (actors/job_applier.py বা actors/messenger.py) বানাতে হবে।

Actors লিস্টঃ
১. অথেন্টিকেশন ও প্রোফাইল ডোমেইন (Auth & Profile Editor)
auth.py (ইতিমধ্যেই আছে): লগইন ফর্ম ফিলআপ করা এবং অথেন্টিকেশন ভ্যালিডেট করা।
profile_editor.py (আংশিক আছে): "Add Experience", "Remove Experience" (আমরা যেটা করেছি), স্কিল অ্যাড বা রিমুভ করা, হেডলাইন বা অ্যাবাউট সেকশন এডিট করা।
২. নেটওয়ার্ক ও কানেকশন ডোমেইন (Network Actions)
connection_manager.py:
send_connect_request(page, profile_url, optional_note): কাউকে ইনভাইটেশন পাঠানো (অটো-কানেক্ট)।
withdraw_request(page): যেগুলো পেন্ডিং হয়ে আছে সেগুলো ক্যানসেল করা।
accept_invitation(page) বা ignore_invitation(page): কেউ রিকোয়েস্ট পাঠালে এক্সেপ্ট বা রিজেক্ট করা।
remove_connection(page): কাউকে আনফ্রেন্ড (রিমুভ) করা।
৩. মেসেজিং ও চ্যাট ডোমেইন (Messaging & Cold DM)
messenger.py:
send_message(page, profile_id, text): নির্দিষ্ট প্রোফাইলে গিয়ে "Message" বাটনে ক্লিক করে টেক্সট পাঠানো (কোল্ড ডিএম)।
reply_inbox(page, thread_id, text): ইনবক্সের সুনির্দিষ্ট কোনো থ্রেডে রিপ্লাই করা।
block_user(page): স্প্যামারদের ব্লক করা।
৪. জবস ও অ্যাপ্লিকেশন ডোমেইন (Jobs & Applications)
job_applier.py:
easy_apply(page, job_id, resume_path, cover_letter): "Easy Apply" এর ফর্মগুলো স্টেপ-বাই-স্টেপ পূরণ করা, সিভি আপলোড করা এবং সাবমিট করা। (এটিতে বেশ কিছু কমপ্লেক্স লজিক থাকে কারণ ফর্ম ডাইনামিক হয়)।
save_job(page, job_id) বা unsave_job(page): পছন্দের জব সেভ করে রাখা।
৫. কন্টেন্ট ও এনগেজমেন্ট ডোমেইন (Content & Engagement)
content_publisher.py (অটো-পোস্টিং):
create_post(page, text, media_files): হোম ফিডের "Start a post" বক্সে ক্লিক করে টেক্সট, ছবি বা ভিডিও পপুলেট করে পাবলিশ করা।
delete_post(page, post_id): নিজের কোনো পোস্ট ডিলিট করা।
interactor.py (অটো-এনগেজমেন্ট):
like_post(page, post_url, reaction_type): কোনো পোস্টে লাইক, লাভ, বা ইনসাইটফুল রিয়্যাক্ট দেওয়া।
comment_on_post(page, post_url, comment_text): পোস্টে কমেন্ট করা (এআই জেনারেটেড কমেন্টিং এর জন্য সুপারপাওয়ার)।
repost_content(page, post_url): অন্যের পোস্ট নিজের প্রোফাইলে শেয়ার করা।
৬. কোম্পানি এবং কমিউনিটি পলিসি (Company & Community)
group_manager.py:
join_group(page, group_id): কোনো গ্রুপে জয়েন রিকোয়েস্ট পাঠানো।
company_interactor.py:
follow_company(page) বা unfollow_company(page): টার্গেটেড কোম্পানির পেজে ফলো দেওয়া।