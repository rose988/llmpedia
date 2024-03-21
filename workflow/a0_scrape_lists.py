import sys, os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil.parser import parse
from selenium import webdriver
from dotenv import load_dotenv
import time

load_dotenv()
sys.path.append(os.environ.get("PROJECT_PATH"))

import utils.paper_utils as pu
import utils.db as db


def scrape_ml_papers_of_the_week(start_date, end_date=None):
    if end_date is None:
        end_date = start_date

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    year = start_date.year

    df = pd.DataFrame(columns=["arxiv_code", "title"])

    response = requests.get("https://github.com/dair-ai/ML-Papers-of-the-Week")
    soup = BeautifulSoup(response.content, "html.parser")

    for header in soup.find_all("h2"):
        date_range_text = header.get_text(strip=True)
        if "Top ML Papers of the Week" in date_range_text:
            date_range = extract_date_range(date_range_text, year)

            if overlaps_with_range(date_range, start_date, end_date):
                table = header.find_next("table")
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    if len(cols) == 2:
                        title = cols[0].get_text(strip=True)
                        links = cols[1].find_all("a", href=True)
                        arxiv_link = next(
                            (link for link in links if "arxiv.org" in link["href"]),
                            None,
                        )
                        if arxiv_link:
                            arxiv_code = arxiv_link["href"].split("/")[-1]
                            df = df._append(
                                {"arxiv_code": arxiv_code, "title": title},
                                ignore_index=True,
                            )

    return df


def extract_date_range(header_text, year):
    date_part = header_text.split("(")[-1].split(")")[0]
    if " - " in date_part:
        start_date_str, end_date_str = date_part.split(" - ")
    else:
        start_date_str, end_date_str = date_part.split("-")

    if len(end_date_str.split()) == 1:
        end_date_str = start_date_str.split()[0] + " " + end_date_str

    start_date = parse(start_date_str.strip() + f", {year}")
    end_date = parse(end_date_str.strip() + f", {year}")
    return (start_date, end_date)



def overlaps_with_range(date_range, start_date, end_date):
    range_start, range_end = date_range
    return not (range_end < start_date or range_start > end_date)


def scrape_huggingface_papers(start_date, end_date=None):
    """Scrape arxiv codes and titles from huggingface.co/papers."""
    if end_date is None:
        end_date = start_date

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    df = pd.DataFrame(columns=["arxiv_code", "title"])
    delta = timedelta(days=1)
    while start_date <= end_date:
        date_str = start_date.strftime("%Y-%m-%d")
        url = f"https://huggingface.co/papers?date={date_str}"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        for link in soup.find_all("a", href=True, class_="cursor-pointer"):
            href = link["href"]
            if href.startswith("/papers/"):
                code = href.split("/")[-1]
                title = link.get_text(strip=True)
                if title:
                    df = df._append(
                        {"arxiv_code": code, "title": title}, ignore_index=True
                    )

        start_date += delta

    df.drop_duplicates(subset="arxiv_code", keep="first", inplace=True)
    return df


def scrape_rsrch_space_papers(start_date, end_date=None):
    if end_date is None:
        end_date = start_date

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    df = pd.DataFrame(columns=["arxiv_code", "title"])

    driver = webdriver.Chrome()
    driver.get("http://rsrch.space")

    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    for entry in soup.find_all(
        "a", class_="flex justify-between text-secondary py-1 group text-md"
    ):
        date_str = entry.find("p", class_="font-berkeley").text.strip()
        entry_date = datetime.strptime(date_str, "%Y-%m-%d")

        if start_date <= entry_date <= end_date:
            href = entry["href"]
            arxiv_code = href.split("/")[-1]
            title = entry.find("strong").get_text(strip=True)
            df = df._append(
                {"arxiv_code": arxiv_code, "title": title}, ignore_index=True
            )

    return df


def scrape_ai_news_papers(start_date, end_date=None):
    if end_date is None:
        end_date = start_date

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    df = pd.DataFrame(columns=["arxiv_code", "title"])

    response = requests.get("https://buttondown.email/ainews/archive/")
    soup = BeautifulSoup(response.content, "html.parser")
    mailinglist_entry = soup.find_all("div", class_="email-list")[0]
    ## Get all <a> elements under the div
    mailinglist_entry = mailinglist_entry.find_all("a", href=True)

    for entry in mailinglist_entry:
        date_str = entry.find("div", class_="email-metadata").text.strip()
        entry_date = datetime.strptime(date_str, "%B %d, %Y")

        if start_date <= entry_date <= end_date:
            time.sleep(2)
            href = entry["href"]
            deep_response = requests.get(href)
            deep_soup = BeautifulSoup(deep_response.content, "html.parser")

            ## Find all arxiv links.
            arxiv_links = deep_soup.find_all("a", href=True)
            for link in arxiv_links:
                if "arxiv.org/abs" in link["href"]:
                    arxiv_code = link["href"].split("/")[-1]
                    arxiv_code = arxiv_code[:10]
                    title = link.get_text(strip=True)
                    df = df._append(
                        {"arxiv_code": arxiv_code, "title": title}, ignore_index=True
                    )
    df.drop_duplicates(subset="arxiv_code", keep="first", inplace=True)
    return df


def main():
    """Scrape arxiv codes and titles from huggingface.co/papers."""
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        start_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        start_date = sys.argv[1]
        end_date = sys.argv[2] if len(sys.argv) == 3 else None

    # Perform scraping.
    print("Scraping HuggingFace...")
    hf_df = scrape_huggingface_papers(start_date, end_date)
    print("Scraping Research Space...")
    rsrch_df = scrape_rsrch_space_papers(start_date, end_date)
    print("Scraping ML Papers of the Week...")
    dair_df = scrape_ml_papers_of_the_week(start_date, end_date)
    print("Scraping AI News...")
    ai_news_df = scrape_ai_news_papers(start_date, end_date)

    ## Combine and extract new codes.
    df = pd.concat([hf_df, rsrch_df, dair_df, ai_news_df], ignore_index=True)
    df.drop_duplicates(subset="arxiv_code", keep="first", inplace=True)
    ## Remove "vX" from arxiv codes if present.
    df["arxiv_code"] = df["arxiv_code"].str.replace(r"v\d+$", "", regex=True)
    new_codes = df["arxiv_code"].tolist()
    new_codes = [code for code in new_codes if pu.is_arxiv_code(code)]
    done_codes = pu.get_local_arxiv_codes()
    nonllm_codes = pu.get_local_arxiv_codes("nonllm_arxiv_text")

    ## Get paper list.
    gist_id = "1dd189493c1890df6e04aaea6d049643"
    gist_filename = "llm_queue.txt"
    paper_list = pu.fetch_queue_gist(gist_id, gist_filename)

    ## Update and upload arxiv codes.
    paper_list = list(set(paper_list + new_codes))
    paper_list = list(set(paper_list) - set(done_codes) - set(nonllm_codes))
    if len(paper_list) == 0:
        print("No new papers found. Exiting...")
        sys.exit(0)
    gist_url = pu.update_gist(
        os.environ["GITHUB_TOKEN"],
        gist_id,
        gist_filename,
        "Updated LLM queue.",
        "\n".join(paper_list),
    )

if __name__ == "__main__":
    main()
