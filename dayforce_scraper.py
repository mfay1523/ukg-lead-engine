def main():
    print("Fetching JSearch Dayforce jobs...")
    jobs = fetch_jsearch_results()
    print(f"Raw jobs from API: {len(jobs)}")

    if jobs:
        print("Sample jobs:")
        for job in jobs[:5]:
            print(job)

    jobs = dedupe_jobs(jobs)
    print(f"After dedupe: {len(jobs)}")

    seen_links = load_seen_links()
    new_jobs = []

    for job in jobs:
        link = clean_text(job.get("link", ""))
        dedupe_key = link or f"{job['company']}|{job['title']}|{job['location']}"
        if dedupe_key not in seen_links:
            new_jobs.append(job)
            seen_links.add(dedupe_key)

    save_seen_links(seen_links)
    print(f"New jobs: {len(new_jobs)}")

    subject = f"Dayforce Hiring Leads: {len(new_jobs)} new postings"
    body = build_email_body(new_jobs[:50])
    send_email(subject, body)
    print(body)
