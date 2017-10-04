from .models import process_entry_page


if __name__ == '__main__':
    entry_page = 'http://www.squawka.com/match-results?ctl=23_s2017'
    process_entry_page(entry_page)