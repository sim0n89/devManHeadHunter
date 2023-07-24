import requests
import os
from os.path import join, dirname
from dotenv import load_dotenv
import argparse
import math
from terminaltables import AsciiTable


def get_hh_search(lang, region_id, page=1):
    try:
        response = requests.get(
            "https://api.hh.ru/vacancies",
            params={"text": f"Программист {lang}", "area": region_id, "page": page},
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        print('Error', e)
        return None


def predict_rub_salary(vacance):
    salary = vacance["salary"]
    if salary:
        if salary["currency"] == "RUR":
            if salary["to"] and salary["from"]:
                return (salary["to"] + salary["from"]) / 2
            elif not salary["to"]:
                return salary["from"] * 1.2
            elif not salary["from"]:
                return salary["to"] * 0.8
        else:
            return None
    else:
        return None


def get_stat_from_hh(languages):
    region_id = 1
    stat = {}
    for lang in languages:
        salary_summ = 0
        salary_count = 0
        page = 0
        vacancies = get_hh_search(lang, region_id)
        if vacancies:
            page_count = vacancies["pages"]
            found = vacancies["found"]
            while page < page_count:
                vacancies = get_hh_search(lang, region_id, page)
                if vacancies:
                    for vacance in vacancies["items"]:
                        salary = predict_rub_salary(vacance)
                        if salary:
                            salary_summ += salary
                            salary_count += 1
                page += 1
            average_salary = int(salary_summ / salary_count)
            stat[lang] = {
                "vacancies_found": found,
                "vacancies_processed": salary_count,
                "average_salary": average_salary,
            }

    return stat


def get_super_job_search(token, lang, page=0):
    headers = {"X-Api-App-Id": token}
    response = requests.get(
        "https://api.superjob.ru/2.0/vacancies/",
        params={"text": f"Программист {lang}", "town": "Москва"},
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


def predict_rub_salary_for_superJob(vacance):
    payment_from = vacance["payment_from"]
    payment_to = vacance["payment_to"]
    if vacance["currency"] == "rub":
        if payment_from > 0 and payment_to > 0:
            return (payment_to + payment_from) / 2
        elif payment_from == 0 and payment_to > 0:
            return payment_to * 0.8
        elif payment_to == 0 and payment_from > 0:
            return payment_from * 1.2
        else:
            return None
    else:
        return None


def get_stat_from_super_job(token, languages):
    stat = {}
    for lang in languages:
        salary_summ = 0
        salary_count = 0
        vacancies = get_super_job_search(token, lang)
        page_count = math.ceil(vacancies["total"] / 20) - 1
        page_count = 20
        page = 0
        while page <= page_count:
            vacancies = get_super_job_search(token, lang, page)
            vacancies_list = vacancies["objects"]
            for vacance in vacancies_list:
                salary = predict_rub_salary_for_superJob(vacance)
                if salary:
                    salary_summ += salary
                    salary_count += 1
            page += 1
        average_salary = int(salary_summ / salary_count)
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
    print_stat("HeadHunter Moscow", hh_stat)
    print_stat("SuperJob Moscow", sj_stat)


def print_stat(table_title, stat):
    table_data = [
        (
            "Язык программирования",
            "Вакансий найдено",
            "Вакансий обработано",
            "Средняя зарплата",
        )
    ]
    for key in stat.keys():
        stat_item = (
            key,
            stat[key]["vacancies_found"],
            stat[key]["vacancies_processed"],
            stat[key]["average_salary"],
        )
        table_data.append(stat_item)

    table_instance = AsciiTable(table_data, table_title)
    print(table_instance.table)


if __name__ == "__main__":
    main()
