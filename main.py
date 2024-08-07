from flask import Flask, jsonify
import asyncio
import os
import pickle
import re

from dotenv import load_dotenv
import requests
import telegram
from bs4 import BeautifulSoup

CHAT_ID = '-1002020059001'
BOT_TOKEN = "6456854514:AAGdDKlGukbxip1vHS2SfUKnKlKlJ_QzD5E"

PRIMARY_URL = "https://mostaql.com/projects?category=development&budget_max=10000&sort=latest"
PROJECT_URL = "https://mostaql.com/project/"

app = Flask(__name__)
bot = telegram.Bot(token=BOT_TOKEN)

# Function to load previously sent jobs
sent_jobs = set()

def load_sent_jobs():
    if os.path.exists("sent_jobs_mostaql.pkl"):
        with open("sent_jobs_mostaql.pkl", "rb") as f:
            return pickle.load(f)
    return set()

sent_jobs = load_sent_jobs()

# Function to save sent jobs
def save_sent_jobs(sent_jobs):
    with open("sent_jobs_mostaql.pkl", "wb") as f:
        pickle.dump(sent_jobs, f)

def generate_message(job):
    title = job.get('title') or 'No Title'
    description = job.get('description') or 'No Description'
    budget = job.get("project_budget_value") or 'No Budget'
    msg_link = f'{PROJECT_URL}{job["project_id"]}'
    deadline = re.sub(r'\s+', ' ', job.get("project_deadline_value") or 'No Deadline')
    date = re.sub(r'\s+', ' ', job.get("project_date_value") or 'No Date')

    html_message = f'<b><a href="{msg_link}">{title}</a></b>\n<b>- {date}</b>\n- <b>مدة التنفيذ  {deadline}</b>\n- <b>الميزانية {budget}</b>\n{description}\n'
    return html_message

def get_headers():
    return {
        "authority": "mostaql.com",
        "scheme": "https",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ar,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
        "Cache-Control": "max-age=0",
        "Referer": "https://mostaql.com/",
        "Sec-Ch-Ua-Platform": "Windows",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    }

async def scrape_and_send_jobs():
    headers = get_headers()
    response = requests.get(PRIMARY_URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    jobs = []
    for project_row in soup.select(".project-row"):
        original_link = project_row.select_one(".mrg--bt-reset a")
        if original_link:
            project_id = original_link.get('href')[28:34]
            print("project_id:", project_id)

            URL = PROJECT_URL + project_id
            project_res = requests.get(URL, headers=headers)
            project_soup = BeautifulSoup(project_res.text, "html.parser")

            # Title
            title_element = project_soup.select_one("h1[data-page-title]")
            title = title_element.get_text(strip=True) if title_element else None
            if title is None:
                print(f"Title not found for project ID: {project_id}")

            # Description
            project_desc = project_soup.select_one(".carda__content")
            description = project_desc.get_text() if project_desc else None
            if description is None:
                print(f"Description not found for project ID: {project_id}")

            # Project Details
            table_meta = project_soup.select(".table-meta tr")

            project_date_value = table_meta[1].select('td')[1].get_text() if len(table_meta) > 1 else None
            if project_date_value is None:
                print(f"Project date not found for project ID: {project_id}")

            project_budget_value = table_meta[2].select('td')[1].get_text() if len(table_meta) > 2 else None
            if project_budget_value is None:
                print(f"Project budget not found for project ID: {project_id}")

            project_deadline_value = table_meta[3].select('td')[1].get_text() if len(table_meta) > 3 else None
            if project_deadline_value is None:
                print(f"Project deadline not found for project ID: {project_id}")

            jobs.append({
                "project_id": project_id,
                "title": title,
                "description": description,
                "project_date_value": project_date_value,
                "project_budget_value": project_budget_value,
                "project_deadline_value": project_deadline_value,
            })
        else:
            print("Could not find original link for project row")

    new_jobs = []
    for job in jobs:
        if job['project_id'] not in sent_jobs:
            new_jobs.append(job)
            sent_jobs.add(job['project_id'])

    if new_jobs:
        for job in new_jobs:
            message = generate_message(job)
            try:
                await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='HTML', disable_web_page_preview=True)
                sent_jobs.add(job['project_id'])
                await asyncio.sleep(.5)
            except Exception as e:
                print(f"Error sending message: {e}")
        save_sent_jobs(sent_jobs)

async def main():
    try:
        while True:
            await scrape_and_send_jobs()
            await asyncio.sleep(90)
            print('New Check')
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
    app.run(debug=True)

@app.route('/')
def home():
    return jsonify(message='Mostaql Bot Server')
