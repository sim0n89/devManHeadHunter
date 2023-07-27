import requests
import os
from os.path import join, dirname
from dotenv import load_dotenv
import argparse
import math
from terminaltables import AsciiTable


def hh_search_request(lang, region_id, page=1):
    response = requests.get(
        "https://api.hh.ru/vacancies",
        params={"text": f"Программист {lang}", "area": region_id, "page": page},
    )
    response.raise_for_status()
    return response.json()


def predict_rub_salary(vacancy):
    salary = vacancy["salary"]
    if not salary or salary["currency"] != "RUR":
        return None
    if salary["to"] and salary["from"]:
        return (salary["to"] + salary["from"]) / 2
    elif not salary["to"]:
        return salary["from"] * 1.2
    elif not salary["from"]:
        return salary["to"] * 0.8


def get_stat_from_hh(languages):
    region_id = 1
    stat = {}
    for lang in languages:
        salary_summ = 0
        salary_count = 0
        page = 0
        page_count = 2
        try:
            while page < page_count:
                try:
                    vacancies = hh_search_request(lang, region_id, page)
                    page_count = vacancies["pages"]
                    print(page_count)
                    found = vacancies["found"]
                    for vacancy in vacancies["items"]:
                        salary = predict_rub_salary(vacancy)
                        if salary:
                            salary_summ += salary
                            salary_count += 1
                    
                except requests.HTTPError as e:
                    continue
                page += 1
            try:
                average_salary = int(salary_summ / salary_count)
            except ZeroDivisionError:
                average_salary = 0

            stat[lang] = {
                "vacancies_found": found,
                "vacancies_processed": salary_count,
                "average_salary": average_salary,
            }
            print (stat)
        except requests.HTTPError as e:
            continue

    return stat


def super_job_search_request(token, lang, page=0):
    headers = {"X-Api-App-Id": token}
    response = requests.get(
        "https://api.superjob.ru/2.0/vacancies/",
        params={"text": f"Программист {lang}", "town": "Москва"},
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


def predict_rub_salary_for_superJob(vacancy):
    payment_from = vacancy["payment_from"]
    payment_to = vacancy["payment_to"]
    if vacancy["currency"] != "rub":
        return None
    if payment_from > 0 and payment_to > 0:
        return (payment_to + payment_from) / 2
    elif payment_from == 0 and payment_to > 0:
        return payment_to * 0.8
    elif payment_to == 0 and payment_from > 0:
        return payment_from * 1.2
    else:
        return None


def get_stat_from_super_job(token, languages):
    stat = {}
    for lang in languages:
        salary_summ = 0
        salary_count = 0
        vacancies = super_job_search_request(token, lang)
        page_count = math.ceil(vacancies["total"] / 20) - 1
        page = 0
        while page <= page_count:
            vacancies = vacancies["objects"]
            for vacancy in vacancies:
                salary = predict_rub_salary_for_superJob(vacancy)
                if salary:
                    salary_summ += salary
                    salary_count += 1
            page += 1
            vacancies = super_job_search_request(token, lang, page)
        try:
            average_salary = int(salary_summ / salary_count)
        except ZeroDivisionError:
            average_salary = 0

        stat[lang] = {
            "vacancies_found": vacancies["total"],
            "vacancies_processed": salary_count,
            "average_salary": average_salary,
        }
    return stat


def main():
    dotenv_path = join(dirname(__file__), ".env")
    load_dotenv(dotenv_path)
    try:
        languages = eval(os.environ.get("LANGUAGES"))
    except KeyError:
        print("Вы не заполyнили массив языков программирования для поиска")
        return
    try:
        super_job_token = os.environ.get("SUPER_JOB_TOKEN")
    except KeyError:
        print("Вы не заполнили токен от super job")
        return

    hh_stat = get_stat_from_hh(languages)
    sj_stat = get_stat_from_super_job(super_job_token, languages)
    print(make_stat_table("HeadHunter Moscow", hh_stat))
    print(make_stat_table("SuperJob Moscow", sj_stat))


def make_stat_table(table_title, stat):
    table_stat = [
        (
            "Язык программирования",
            "Вакансий найдено",
            "Вакансий обработано",
            "Средняя зарплата",
        )
    ]
    for stat_name in stat.keys():
        stat_item = (
            stat_name,
            stat[stat_name]["vacancies_found"],
            stat[stat_name]["vacancies_processed"],
            stat[stat_name]["average_salary"],
        )
        table_stat.append(stat_item)

    table_instance = AsciiTable(table_stat, table_title)
    return table_instance


if __name__ == "__main__":
    main()
