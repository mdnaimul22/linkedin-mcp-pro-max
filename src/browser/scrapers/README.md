## English
The job of src/browser/scrapers/ is just to extract data or read information from the browser. For example, if you add a new scrapers/jobs.py, its job will just be to read job listings and send them to the database or service.

If you want to read data from a new page (e.g. company details or job circular), then you will create a new Scraper (scrapers/company.py) and send the data to the service from manager.py.

## Bangla
src/browser/scrapers/ এর কাজ হলো শুধু ডেটা এক্সট্র্যাক্ট করা বা ব্রাউজার থেকে তথ্য পড়া। যেমন- আপনি যদি নতুন একটি scrapers/jobs.py যোগ করেন, তার কাজ হবে শুধু জব লিস্টিং পড়ে ডেটাবেস বা সার্ভিসে পাঠানো।

যদি আপনি নতুন কোনো পেইজ থেকে ডেটা পড়তে চান (যেমন: কোম্পানির ডিটেইলস বা জব সার্কুলার), তাহলে আপনি একটি নতুন Scraper (scrapers/company.py) বানাবেন এবং manager.py থেকে সার্ভিসের কাছে ডেটা পাঠিয়ে দিবেন।