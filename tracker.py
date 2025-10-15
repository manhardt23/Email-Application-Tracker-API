from LLM_filter import extract_application_info

def build_application_log(emails):
    log = []
    for msg in emails:
        info = extract_application_info(msg)
        log.append(info)
    return log
