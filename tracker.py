from LLM_filter import Filter

def build_application_log(emails):
    log = []
    for email in emails:
        info = [email["sender"],
            email["subject"],
            email["body"]]
        log.append(info)
    return log
