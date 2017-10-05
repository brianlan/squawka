from .models import process_entry_page


if __name__ == '__main__':
    # TODO: use apscheduler
    # TODO: cron producer job to run every day (5 job for 5 different leagues), insert todo-match in queue
    # TODO: cron consumer job to run every 30 min to process a match in queue
    entry_page = 'http://www.squawka.com/match-results?ctl=23_s2017'
    process_entry_page(entry_page)