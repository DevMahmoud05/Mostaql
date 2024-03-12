from flask import Flask, jsonify
from flask_cors import CORS
import asyncio
import os
import pickle
import re

from dotenv import load_dotenv
import requests
import telegram
from bs4 import BeautifulSoup


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')


app = Flask(__name__)
CORS(app)
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
    title = job['title']
    offers = job['offers']
    time = re.sub(r'\s+', ' ', job['time'])
    desc = job['desc']
    msg_link = f'https://mostaql.com/project/{job["link"]}'
    html_message = f'<b><a href="{msg_link}">💡 {title}</a></b>\n\n<b>🕰️ {time}</b>\n🎨 {desc}\n<b>💼 {offers}</b>\n'
    return html_message


def get_headers():
    return {
        "authority":
        "mostaql.com",
        "scheme":
        "https",
        "Accept":
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding":
        "gzip, deflate, br",
        "Accept-Language":
        "ar,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
        "Cache-Control":
        "max-age=0",
        "Referer":
        "https://mostaql.com/",
        "Sec-Ch-Ua-Platform":
        "Windows",
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    }


async def scrape_and_send_jobs():
    url = "https://mostaql.com/projects?category=development&budget_max=10000&sort=latest"
    headers = get_headers()
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    jobs = []
    for project_row in soup.select(".project-row"):
        title_element = project_row.select_one(".mrg--bt-reset")
        link = project_row.select_one(".mrg--bt-reset a").get('href')
        title = title_element.get_text(strip=True) if title_element else None

        desc_element = project_row.select_one(".details-url")
        desc = desc_element.get_text(strip=True) if desc_element else None

        time_element = project_row.select_one("time")

        datetime = time_element['title'] if time_element else None

        # Find the start index of the project number
        start_index = link.find("https://mostaql.com/project/") + len(
            "https://mostaql.com/project/")
        # Slice the URL to get the project number
        project_number = link[start_index:].split('-')[0]

        meta_el = project_row.select(".list-meta-items")
        offers = ''
        time = ''
        for meta in meta_el:
            last = meta.select('.text-muted')
            offers = last[2].getText(strip=True)
            time = last[1].getText(strip=True)

        jobs.append({
            "title": title,
            "desc": desc,
            "time": time,
            "datetime": datetime,
            "link": project_number,
            "offers": offers
        })

    new_jobs = []

    for job in jobs:

        if job['datetime'] not in sent_jobs:
            new_jobs.append(job)
            sent_jobs.add(job['datetime'])

    if new_jobs:

        for job in new_jobs:
            message = generate_message(job)
            try:
                await bot.send_message(chat_id=CHAT_ID,
                                       text=message, parse_mode='HTML',
                                       disable_web_page_preview=True)
                sent_jobs.add(job['datetime'])
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
    return jsonify(msg='Mostaql Bot Server')
